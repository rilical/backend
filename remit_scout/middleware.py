"""
Custom middleware components for the RemitScout application.

This module defines middleware classes for:
- Security headers
- Request ID generation and tracking
- Logging
- Rate limiting
- Session-based authorization
"""
import logging
import time
import uuid
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import JsonResponse
import hashlib
from django.conf import settings

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses.
    
    These headers help protect against common web vulnerabilities.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['X-Frame-Options'] = 'DENY'
        
        # In development mode, use a more permissive CSP
        if settings.DEBUG:
            response['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:;"
        else:
            response['Content-Security-Policy'] = "default-src 'self'; img-src 'self' https://remitscout.com; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self'"
        
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        
        # Add HSTS header in production
        if not request.is_secure():
            # Don't add HSTS header for non-HTTPS requests
            pass
        else:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response

class RequestIDMiddleware:
    """
    Middleware to generate and attach a unique request ID to each request.
    
    This allows for request tracing across multiple components and services.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Add request ID to the request object
        request.request_id = request_id
        
        # Process the request
        response = self.get_response(request)
        
        # Add request ID to response headers
        response['X-Request-ID'] = request_id
        
        return response

class RateLimitMiddleware:
    """
    Middleware to implement rate limiting for API endpoints.
    
    Rate limits are applied based on client IP address and optionally API key.
    Different limits apply to authenticated vs. unauthenticated requests.
    """
    
    # Rate limits (requests per minute)
    RATE_LIMIT_ANONYMOUS = 60  # 60 requests per minute for anonymous users
    RATE_LIMIT_AUTHENTICATED = 300  # 300 requests per minute for authenticated users
    RATE_LIMIT_WINDOW = 60  # 1 minute window
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Only apply rate limiting to API endpoints
        if not request.path.startswith('/api/'):
            return self.get_response(request)
            
        # Get client identifier (IP address + API key if available)
        client_identifier = self._get_client_identifier(request)
        
        # Check if client is authenticated
        is_authenticated = self._is_authenticated(request)
        
        # Apply different rate limits based on authentication
        rate_limit = self.RATE_LIMIT_AUTHENTICATED if is_authenticated else self.RATE_LIMIT_ANONYMOUS
        
        # If session tier is available from SessionAuthMiddleware, use that instead
        if hasattr(request, 'rate_limit'):
            rate_limit = request.rate_limit
            
        # Check rate limit
        if not self._check_rate_limit(client_identifier, rate_limit):
            logger.warning(f"Rate limit exceeded for {client_identifier}")
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'detail': f'Maximum {rate_limit} requests per minute allowed'
            }, status=429)
            
        # Proceed with the request
        return self.get_response(request)
    
    def _get_client_identifier(self, request):
        """
        Generate a unique identifier for the client based on IP and API key.
        
        This helps distinguish between different clients while maintaining privacy.
        """
        client_ip = self._get_client_ip(request)
        api_key = request.META.get('HTTP_X_API_KEY', '')
        
        # If session token is available, use that too
        session_token = getattr(request, 'session_token', '')
        
        # Hash the IP address for privacy
        hashed_ip = hashlib.md5(client_ip.encode()).hexdigest()
        
        if session_token:
            return f"{hashed_ip}:{session_token[:8]}"
        elif api_key:
            # If API key is provided, include it in the identifier
            return f"{hashed_ip}:{api_key[:8]}"
        else:
            return hashed_ip
    
    def _is_authenticated(self, request):
        """
        Check if the request is authenticated.
        
        A request is considered authenticated if it has a valid API key.
        """
        api_key = request.META.get('HTTP_X_API_KEY', '')
        
        # This is a simple check - in a real implementation, you'd validate the API key
        return bool(api_key)
    
    def _check_rate_limit(self, client_identifier, rate_limit):
        """
        Check if the client has exceeded their rate limit.
        
        Uses Redis to track request counts within the rate limit window.
        """
        cache_key = f"rate_limit:{client_identifier}"
        
        # Get current count
        count = cache.get(cache_key, 0)
        
        if count >= rate_limit:
            return False
        
        # Increment count
        cache.set(cache_key, count + 1, self.RATE_LIMIT_WINDOW)
        return True
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class RequestLoggingMiddleware:
    """
    Middleware to log all API requests with detailed information.
    
    Logs include:
    - HTTP method
    - Path
    - Status code
    - Response time
    - IP address
    - User agent
    - Request ID (if available)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Record start time
        start_time = time.time()
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Process the request
        response = self.get_response(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Get request ID if available
        request_id = getattr(request, 'request_id', 'N/A')
        
        # Only log API requests
        if request.path.startswith('/api/'):
            log_data = {
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'response_time': f"{response_time:.4f}s",
                'client_ip': client_ip,
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'request_id': request_id,
            }
            
            # Add session info if available
            if hasattr(request, 'session_tier'):
                log_data['session_tier'] = request.session_tier
            
            # Log at different levels based on status code
            if response.status_code >= 500:
                logger.error(f"API Request: {log_data}")
            elif response.status_code >= 400:
                logger.warning(f"API Request: {log_data}")
            else:
                logger.info(f"API Request: {log_data}")
        
        return response
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class SessionAuthMiddleware:
    """
    Middleware to implement cookie-based session authorization without requiring login.
    
    This middleware:
    1. Automatically generates a session token for new users
    2. Sets a secure cookie with this token
    3. Associates the token with a rate limit tier and feature access
    4. Allows upgrading to higher tiers via API keys
    """
    
    # Session cookie settings
    SESSION_COOKIE_NAME = 'remitscout_session'
    SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
    
    # Rate tiers (requests per minute)
    RATE_TIER_ANONYMOUS = 60
    RATE_TIER_REGISTERED = 300
    RATE_TIER_PREMIUM = 1000
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Get or generate a session token
        session_token = self._get_or_create_session_token(request)
        
        # Add session information to the request
        request.session_token = session_token
        request.session_tier = self._get_session_tier(session_token, request)
        request.rate_limit = self._get_rate_limit_for_tier(request.session_tier)
        
        # Process the request
        response = self.get_response(request)
        
        # If this is a new session, set the cookie
        if not request.COOKIES.get(self.SESSION_COOKIE_NAME):
            self._set_session_cookie(response, session_token)
            
        return response
    
    def _get_or_create_session_token(self, request):
        """
        Get the existing session token from cookies or create a new one.
        """
        # Try to get the token from cookies
        token = request.COOKIES.get(self.SESSION_COOKIE_NAME)
        
        # Check if token exists and is valid
        if token and self._is_valid_token(token):
            return token
            
        # Generate a new token
        return self._generate_session_token()
    
    def _generate_session_token(self):
        """
        Generate a new session token with a UUID.
        """
        return str(uuid.uuid4())
    
    def _is_valid_token(self, token):
        """
        Validate the session token.
        """
        # Basic validation - could be expanded to check against a database
        try:
            uuid.UUID(token)
            return True
        except ValueError:
            return False
    
    def _set_session_cookie(self, response, token):
        """
        Set the session cookie with the token.
        """
        # Default to secure=False since we're in development
        secure = False
        
        # If we have a request object available, use its is_secure() method
        if hasattr(response, '_request') and response._request is not None:
            secure = response._request.is_secure()
        
        response.set_cookie(
            self.SESSION_COOKIE_NAME,
            token,
            max_age=self.SESSION_COOKIE_MAX_AGE,
            secure=secure,
            httponly=True,
            samesite='Lax'
        )
    
    def _get_session_tier(self, session_token, request):
        """
        Determine the user's session tier based on token and API key.
        
        Tiers:
        - 'anonymous': Basic access
        - 'registered': Registered user with API key
        - 'premium': Premium user with verified API key
        """
        # Check for API key
        api_key_header = request.META.get('HTTP_X_API_KEY', '')
        
        # If API key exists, verify it and determine tier
        if api_key_header:
            try:
                # Lazy import to avoid circular imports
                from remit_scout.models import APIKey
                
                # Get API key from database
                api_key = APIKey.objects.filter(key=api_key_header, is_active=True).first()
                
                # If API key is valid, record usage and return tier
                if api_key and api_key.is_valid():
                    # Record API key usage asynchronously if we're in an API endpoint
                    if request.path.startswith('/api/'):
                        self._record_api_key_usage(api_key, request)
                    
                    # Return tier from the API key
                    return api_key.tier
                    
            except Exception as e:
                # Log the error but continue as anonymous
                logger.error(f"Error validating API key: {str(e)}")
        
        # If no valid API key, check if the session is known
        # In a real implementation, this would check against a database
        # For this example, we'll just return 'anonymous'
        return 'anonymous'
    
    def _get_rate_limit_for_tier(self, tier):
        """
        Get the rate limit for a given tier.
        """
        if tier == 'enterprise':
            return 2000  # Enterprise tier gets 2000 requests per minute
        elif tier == 'premium':
            return self.RATE_TIER_PREMIUM
        elif tier == 'registered':
            return self.RATE_TIER_REGISTERED
        else:
            return self.RATE_TIER_ANONYMOUS
            
    def _record_api_key_usage(self, api_key, request):
        """
        Record API key usage for analytics and billing.
        """
        try:
            # Update the last_used timestamp and increment request count
            api_key.record_usage()
            
            # If we should log detailed usage, create a log entry
            # This could be done in Celery for better performance
            from django.db import transaction
            transaction.on_commit(lambda: self._create_usage_log_entry(api_key, request))
                
        except Exception as e:
            logger.error(f"Error recording API key usage: {str(e)}")
    
    def _create_usage_log_entry(self, api_key, request):
        """Create a detailed log entry for the API key usage."""
        try:
            from remit_scout.models import APIKeyUsageLog
            
            # Get request details
            path = request.path
            method = request.method
            ip = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Create the log entry (status code and response time will be updated later)
            APIKeyUsageLog.objects.create(
                api_key=api_key,
                endpoint=path,
                http_method=method,
                response_time_ms=0,  # This will be updated by middleware or signal
                status_code=200,     # This will be updated by middleware or signal
                ip_address=ip,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Error creating API key usage log: {str(e)}")
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 