#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Xoom Money Transfer Integration
===============================

This module implements an integration with Xoom (a PayPal service) for international money transfers.

Payment Methods:
- PayPal balance
- Bank account
- Debit card
- Credit card

Delivery Methods:
- Bank deposit
- Cash pickup
- Mobile wallet
- Home delivery (in some countries)

API Notes:
- Xoom does not offer a public API, this integration uses their web interface
- Rate queries are done through their fee calculator endpoint
- Authentication is cookie-based
"""

import html
import json
import logging
import os
import re
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.utils.country_currency_standards import ISO_COUNTRY_NAMES
from apps.providers.utils.currency_mapping import (
    COUNTRY_NAMES,
    CURRENCY_NAMES,
    get_country_currencies,
    get_country_name,
    get_currency_name,
)
from apps.providers.xoom.exceptions import (
    XoomAuthenticationError,
    XoomConnectionError,
    XoomError,
    XoomRateLimitError,
    XoomValidationError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)


def log_request_details(
    method: str, url: str, headers: Dict, params: Dict = None, data: Dict = None
):
    """Log API request details for debugging."""
    logger = logging.getLogger("xoom_provider")
    logger.debug(f"REQUEST: {method} {url}")

    if params:
        logger.debug(f"PARAMS: {json.dumps(params, indent=2)}")

    if data:
        logger.debug(f"DATA: {json.dumps(data, indent=2)}")

    logger.debug(f"HEADERS: {json.dumps(dict(headers), indent=2)}")


def log_response_details(response):
    """Log API response details for debugging."""
    logger = logging.getLogger("xoom_provider")
    logger.debug(f"RESPONSE: {response.status_code} {response.reason}")

    try:
        logger.debug(f"RESPONSE BODY: {json.dumps(response.json(), indent=2)}")
    except Exception:
        logger.debug(f"RESPONSE BODY (text): {response.text[:500]}...")

    logger.debug(f"RESPONSE HEADERS: {json.dumps(dict(response.headers), indent=2)}")


class ExchangeRateResult:
    """Standardized exchange rate result."""

    def __init__(
        self,
        provider_id: str,
        source_currency: str,
        source_amount: float,
        destination_currency: str,
        destination_amount: float,
        exchange_rate: float,
        fee: float,
        delivery_method: str,
        delivery_time_minutes: Optional[int] = None,
        corridor: Optional[str] = None,
        payment_method: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        self.provider_id = provider_id
        self.source_currency = source_currency
        self.source_amount = source_amount
        self.destination_currency = destination_currency
        self.destination_amount = destination_amount
        self.exchange_rate = exchange_rate
        self.fee = fee
        self.delivery_method = delivery_method
        self.delivery_time_minutes = delivery_time_minutes
        self.corridor = corridor or f"{source_currency}->{destination_currency}"
        self.payment_method = payment_method
        self.details = details or {}

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "provider_id": self.provider_id,
            "source_currency": self.source_currency,
            "source_amount": self.source_amount,
            "destination_currency": self.destination_currency,
            "destination_amount": self.destination_amount,
            "exchange_rate": self.exchange_rate,
            "fee": self.fee,
            "delivery_method": self.delivery_method,
            "delivery_time_minutes": self.delivery_time_minutes,
            "corridor": self.corridor,
            "payment_method": self.payment_method,
            "details": self.details,
        }


class XoomProvider(RemittanceProvider):
    """Integration with Xoom (PayPal) money transfer service."""

    BASE_URL = "https://www.xoom.com"
    API_URL = "https://www.xoom.com/wapi/send-money-app/remittance-engine/remittance"
    QUOTE_API_URL = "https://www.xoom.com/xoom/api/send/quote"
    FEE_TABLE_API_URL = "https://www.xoom.com/calculate-fee-table"

    # Provider ID for aggregator system
    provider_id = "xoom"

    # Mapping of Xoom payment method types to standardized names
    PAYMENT_METHODS = {
        "CRYPTO_PYUSD": "PayPal USD (PYUSD)",
        "PAYPAL_BALANCE": "PayPal balance",
        "ACH": "Bank Account",
        "DEBIT_CARD": "Debit Card",
        "CREDIT_CARD": "Credit Card",
    }

    # Mapping of Xoom disbursement types to standardized names
    DELIVERY_METHODS = {
        "DEPOSIT": "Bank Deposit",
        "MOBILE_WALLET": "Mobile Wallet",
        "CARD_DEPOSIT": "Card Deposit",
        "PICKUP": "Cash Pickup",
        "HOME_DELIVERY": "Cash Home Delivery",
        "UPI": "UPI",
        "CASH": "Cash Pickup",
    }

    # Mapping of country codes to common country names
    COUNTRY_CODES = {
        "MX": "Mexico",
        "PH": "Philippines",
        "IN": "India",
        "CO": "Colombia",
        "GT": "Guatemala",
        "SV": "El Salvador",
        "DO": "Dominican Republic",
        "HN": "Honduras",
        "PE": "Peru",
        "EC": "Ecuador",
    }

    def __init__(self, name="xoom", base_url=None):
        """
        Initialize Xoom provider.

        Args:
            name: Provider name (default: "xoom")
            base_url: Base URL for API (default: None, uses class BASE_URL)
        """
        super().__init__(name=name, base_url=base_url or self.BASE_URL)
        self.session = requests.Session()

        # Initialize logger
        self.logger = logging.getLogger("xoom_provider")

        # Configure session with retries and timeouts
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])

        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.timeout = 30  # Default timeout in seconds

        # Initialize session
        self._initialize_session()

        # Random request ID for tracing
        self.request_id = str(uuid.uuid4())

        # Cache for supported countries and corridors
        self._countries_cache = None
        self._corridors_cache = {}

    def _initialize_session(self) -> None:
        """Initialize the session by visiting home page and setting up cookies."""
        self.timeout = 30  # Default timeout in seconds

        # Set user agent and common headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
            }
        )

        # Visit home page to set cookies and initialize session
        self._visit_home_page()

    def _visit_home_page(self) -> None:
        """
        Visit the Xoom homepage to initialize the session with cookies.
        """
        try:
            self.logger.info("Visiting Xoom homepage to initialize session")

            # First visit the main site
            response = self.session.get(self.base_url, timeout=self.timeout, allow_redirects=True)

            if response.status_code != 200:
                self.logger.warning(f"Home page returned status code {response.status_code}")

            # Then try to visit the send money page
            send_money_url = f"{self.base_url}/en-us/send-money"
            response = self.session.get(send_money_url, timeout=self.timeout, allow_redirects=True)

            # Check if we were redirected to sign-in
            if "/sign-in" in response.url:
                self.logger.warning("Redirected to sign-in page. Using anonymous mode.")

            # Try visiting a specific corridor
            corridor_url = f"{self.base_url}/en-us/send-money/us/mx"
            response = self.session.get(corridor_url, timeout=self.timeout, allow_redirects=True)

            # Check for CSRF token
            csrf_token = self._get_csrf_token()
            if csrf_token:
                self.session.headers.update({"X-CSRF-Token": csrf_token})

            # Fetch segment settings
            self.session.get(f"{self.base_url}/segment/settings.json", timeout=self.timeout)

            # GET GDPR status
            self.session.get(f"{self.base_url}/pa/gdpr", timeout=self.timeout)

        except Exception as e:
            self.logger.error(f"Error visiting homepage: {e}")
            # Continue even if homepage visit fails

    def _get_csrf_token(self) -> Optional[str]:
        """
        Get CSRF token from the current page.

        Returns:
            CSRF token if found, None otherwise
        """
        try:
            # Get the current page content
            response = self.session.get(self.base_url, timeout=self.timeout)

            if response.status_code != 200:
                self.logger.warning(
                    f"Failed to get page for CSRF token, status: {response.status_code}"
                )
                return None

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for meta tag with csrf-token
            meta_tag = soup.find("meta", attrs={"name": "csrf-token"})
            if meta_tag and "content" in meta_tag.attrs:
                token = meta_tag["content"]
                self.logger.info("Found CSRF token in meta tag")
                return token

            # Look in script tags for CSRF token
            script_tags = soup.find_all("script")
            for script in script_tags:
                if script.string and "csrf" in script.string.lower():
                    csrf_match = re.search(r'csrf[\'"]*\s*:\s*[\'"]([^\'"]*)[\'"]*', script.string)
                    if csrf_match:
                        token = csrf_match.group(1)
                        self.logger.info("Found CSRF token in script tag")
                        return token

            # Look for nonce attributes as fallback
            nonce_script = soup.find("script", attrs={"nonce": True})
            if nonce_script and "nonce" in nonce_script.attrs:
                nonce = nonce_script["nonce"]
                self.logger.info("Using script nonce as fallback CSRF token")
                return nonce

            self.logger.warning("Could not find CSRF token")
            return None

        except Exception as e:
            self.logger.error(f"Error getting CSRF token: {e}")
            return None

    def _make_api_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        retry_auth: bool = True,
        max_retries: int = 2,
    ) -> Dict:
        """
        Make a request to the Xoom API with proper error handling.

        Args:
            method: HTTP method (GET or POST)
            url: API endpoint URL
            data: Request payload for POST requests
            params: URL parameters for GET requests
            retry_auth: Whether to retry with a new session if authentication fails
            max_retries: Maximum number of retries for authentication issues

        Returns:
            API response as a dictionary
        """
        retry_count = 0

        while retry_count <= max_retries:
            try:
                # Update headers for this specific request
                current_headers = self.session.headers.copy()

                # Add common API request headers
                current_headers.update(
                    {
                        "Referer": f"{self.BASE_URL}/en-us/send-money",
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/plain, */*",
                    }
                )

                # Log request details
                log_request_details(method, url, current_headers, params, data)

                # Make the request
                if method.upper() == "GET":
                    response = self.session.get(
                        url=url,
                        params=params,
                        timeout=self.timeout,
                        headers=current_headers,
                        allow_redirects=False,  # Don't automatically follow redirects
                    )
                else:  # POST
                    response = self.session.post(
                        url=url,
                        json=data,
                        params=params,
                        timeout=self.timeout,
                        headers=current_headers,
                        allow_redirects=False,  # Don't automatically follow redirects
                    )

                # Log response
                log_response_details(response)

                # Handle redirects manually to capture authentication issues
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_url = response.headers.get("Location")
                    self.logger.debug(f"Redirected to: {redirect_url}")

                    # Check if redirected to sign-in page
                    if redirect_url and "/sign-in" in redirect_url:
                        if retry_auth and retry_count < max_retries:
                            self.logger.warning(
                                f"Redirected to sign-in page, refreshing session (attempt {retry_count + 1}/{max_retries})"
                            )
                            self._initialize_session()
                            time.sleep(1)  # Add delay between retries
                            retry_count += 1
                            continue
                        else:
                            raise XoomAuthenticationError(
                                "Authentication failed: redirected to sign-in page"
                            )

                    # Follow normal redirects manually
                    if redirect_url:
                        if redirect_url.startswith("/"):
                            redirect_url = f"{self.BASE_URL}{redirect_url}"
                        return self._make_api_request(
                            "GET",
                            redirect_url,
                            None,
                            None,
                            retry_auth=retry_auth,
                            max_retries=max_retries - retry_count,
                        )

                # Check for common error status codes
                if response.status_code in (401, 403):
                    if retry_auth and retry_count < max_retries:
                        self.logger.warning(
                            f"Authentication failed, refreshing session and retrying (attempt {retry_count + 1}/{max_retries})"
                        )
                        self._initialize_session()
                        time.sleep(1)  # Add delay between retries
                        retry_count += 1
                        continue
                    raise XoomAuthenticationError("Authentication failed")

                if response.status_code == 429:
                    # With rate limits, we should wait longer before retrying
                    if retry_count < max_retries:
                        wait_time = 5 * (retry_count + 1)  # Progressive backoff
                        self.logger.warning(
                            f"Rate limit exceeded, waiting {wait_time} seconds before retry"
                        )
                        time.sleep(wait_time)
                        retry_count += 1
                        continue
                    raise XoomRateLimitError("Rate limit exceeded")

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get(
                            "message", "Unknown API error"
                        )
                        raise XoomError(f"API error: {error_message}")
                    except (ValueError, KeyError):
                        raise XoomError(f"API error: {response.status_code}")

                # Check for HTML response when JSON expected (likely a redirect to login)
                content_type = response.headers.get("Content-Type", "")
                if "json" in current_headers.get("Accept", "") and "html" in content_type.lower():
                    if retry_auth and retry_count < max_retries:
                        self.logger.warning(
                            f"Received HTML when expecting JSON, session may be invalid. Refreshing (attempt {retry_count + 1}/{max_retries})"
                        )
                        self._initialize_session()
                        time.sleep(1)
                        retry_count += 1
                        continue
                    raise XoomError(
                        "Received HTML response when expecting JSON (possible auth issue)"
                    )

                # Parse and return response
                try:
                    return response.json()
                except ValueError:
                    # If the response is empty but status is 200, return empty dict
                    if response.status_code == 200 and not response.text.strip():
                        return {}
                    raise XoomError("Invalid JSON response from API")

            except requests.RequestException as e:
                self.logger.error(f"Request failed: {e}")

                # Retry network errors
                if retry_count < max_retries:
                    self.logger.warning(
                        f"Connection error, retrying (attempt {retry_count + 1}/{max_retries})"
                    )
                    time.sleep(2)
                    retry_count += 1
                    continue

                raise XoomConnectionError(f"Connection error: {e}")

        # This should not be reached, but just in case
        raise XoomError("Maximum retries exceeded")

    def standardize_response(self, local_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize API response to common format.

        Args:
            local_data: Raw response data from Xoom

        Returns:
            Standardized response dictionary
        """
        # Initialize standardized result with default values
        standardized = {
            "provider_id": self.name,
            "provider_name": "Xoom",
            "success": local_data.get("success", True),
            "source_country": local_data.get("source_country", "US"),
            "destination_country": local_data.get("destination_country", ""),
            "source_currency": local_data.get("source_currency", "USD"),
            "destination_currency": local_data.get("destination_currency", ""),
            "source_amount": local_data.get("source_amount", 0.0),
            "destination_amount": local_data.get("destination_amount", 0.0),
            "exchange_rate": local_data.get("exchange_rate", 0.0),
            "fee": local_data.get("fee", 0.0),
            "delivery_method": local_data.get("delivery_method", ""),
            "payment_method": local_data.get("payment_method", ""),
            "delivery_time_minutes": local_data.get("delivery_time_minutes", 0),
        }

        # Add source and destination country names
        source_code = standardized["source_country"]
        dest_code = standardized["destination_country"]

        standardized["source_country_name"] = get_country_name(
            source_code
        ) or ISO_COUNTRY_NAMES.get(source_code, source_code)
        standardized["destination_country_name"] = get_country_name(
            dest_code
        ) or ISO_COUNTRY_NAMES.get(dest_code, dest_code)

        # Add currency names
        source_currency = standardized["source_currency"]
        dest_currency = standardized["destination_currency"]

        standardized["source_currency_name"] = get_currency_name(source_currency) or source_currency
        standardized["destination_currency_name"] = (
            get_currency_name(dest_currency) or dest_currency
        )

        # Add details from original response
        if "details" in local_data:
            standardized["details"] = local_data["details"]
        else:
            standardized["details"] = {
                "provider": "Xoom",
                "url": f"https://www.xoom.com/",
            }

            # Add destination country to URL if available
            if dest_code:
                standardized["details"][
                    "url"
                ] = f"https://www.xoom.com/{dest_code.lower()}/send-money"

        return standardized

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str,
        dest_country: str,
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get a quote for sending money from source to destination.

        Args:
            amount: Amount to send
            source_currency: Currency to send (e.g., USD)
            dest_currency: Currency to receive (e.g., MXN)
            source_country: Country sending from (e.g., US)
            dest_country: Country sending to (e.g., MX)
            payment_method: Payment method (optional)
            delivery_method: Delivery method (optional)

        Returns:
            Quote information
        """
        print(
            f"DEBUG: Xoom get_quote called with amount={amount}, source_country={source_country}, dest_country={dest_country}, source_currency={source_currency}, dest_currency={dest_currency}"
        )

        self.logger.info(
            f"Getting quote for {amount} {source_currency} to {dest_country} ({dest_currency})"
        )

        # Convert amount to Decimal if it's not already
        float_amount = float(amount)

        try:
            # First try the fee table API as it doesn't require auth
            print("DEBUG: Xoom trying fee table API")
            exchange_rate_result = self._get_exchange_rate_via_fee_table(
                send_amount=amount,
                send_currency=source_currency,
                receive_country=dest_country,
                receive_currency=dest_currency,
            )

            # If successful, return the result
            if exchange_rate_result and "exchange_rate" in exchange_rate_result:
                print(
                    f"DEBUG: Xoom successfully got quote via fee table API: {exchange_rate_result}"
                )
                self.logger.info(
                    f"Successfully got quote via fee table API: {exchange_rate_result}"
                )
                return exchange_rate_result
            else:
                print(
                    f"DEBUG: Xoom fee table API didn't return exchange rate: {exchange_rate_result}"
                )
        except Exception as e:
            print(f"DEBUG: Xoom error getting quote via fee table API: {str(e)}")
            self.logger.error(f"Error getting quote via fee table API: {str(e)}")

        # If fee table API failed, try the exchange rate endpoint
        print("DEBUG: Xoom fee table API failed, trying exchange rate endpoint")
        self.logger.info("Fee table API failed, trying exchange rate endpoint")
        try:
            exchange_rate_result = self.get_exchange_rate(
                send_amount=amount,
                send_currency=source_currency,
                receive_country=dest_country,
                receive_currency=dest_currency,
                delivery_method=delivery_method,
                payment_method=payment_method,
            )

            if exchange_rate_result and "exchange_rate" in exchange_rate_result:
                print(
                    f"DEBUG: Xoom successfully got quote via exchange rate endpoint: {exchange_rate_result}"
                )
                self.logger.info(
                    f"Successfully got quote via exchange rate endpoint: {exchange_rate_result}"
                )
                return exchange_rate_result
            else:
                print(
                    f"DEBUG: Xoom exchange rate endpoint didn't return exchange rate: {exchange_rate_result}"
                )
        except Exception as e:
            print(f"DEBUG: Xoom error getting quote via exchange rate endpoint: {str(e)}")
            self.logger.error(f"Error getting quote via exchange rate endpoint: {str(e)}")

        # If both attempts failed, return a fallback estimate or error response
        print("DEBUG: Xoom all quote attempts failed, returning fallback response")
        self.logger.warning("All quote attempts failed, returning fallback response")

        # Create fallback response
        exchange_rate_result = {
            "provider_id": "xoom",
            "provider_name": "Xoom",
            "source_country": source_country,
            "destination_country": dest_country,
            "source_currency": source_currency,
            "destination_currency": dest_currency,
            "source_amount": float_amount,
            "destination_amount": 0.0,
            "exchange_rate": 0.0,
            "fee": 4.99,  # Default fee
            "payment_method": "PayPal balance",
            "delivery_method": "Bank Deposit",
            "success": False,
            "error_message": "Failed to get quote from Xoom API",
            "details": {
                "provider": "Xoom",
                "url": f"https://www.xoom.com/{dest_country.lower()}/send-money",
                "fallback": True,  # Indicate this is a fallback response
            },
        }

        # Return standardized result
        print(f"DEBUG: Xoom returning fallback response: {exchange_rate_result}")
        return exchange_rate_result

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str = "USD",
        receive_country: str = None,
        receive_currency: str = None,
        delivery_method: str = None,  # Optional
        payment_method: str = None,  # Optional
    ) -> Dict:
        """
        Get exchange rate information for a specific amount and currency pair.

        Args:
            send_amount: Amount to send
            send_currency: Source currency code (default USD)
            receive_country: Destination country code (required if receive_currency not provided)
            receive_currency: Destination currency code (required if receive_country not provided)
            delivery_method: Optional filter for specific delivery method
            payment_method: Optional filter for specific payment method

        Returns:
            Dictionary with exchange rate information or error
        """
        # Initialize default response with all required fields
        result = {
            "provider_id": self.provider_id,
            "source_country": "US",
            "source_currency": send_currency,
            "destination_country": receive_country if receive_country else "",
            "destination_currency": receive_currency if receive_currency else "",
            "source_amount": float(send_amount),
            "destination_amount": 0.0,
            "exchange_rate": 0.0,
            "fee": 0.0,
            "delivery_method": delivery_method if delivery_method else "bank deposit",
            "payment_method": payment_method if payment_method else "PayPal balance",
            "delivery_time_minutes": 1440,  # Default to 24 hours
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Validate currency or country
            if not receive_country and not receive_currency:
                self.logger.error("Either receive_country or receive_currency must be provided")
                result[
                    "error_message"
                ] = "Either receive_country or receive_currency must be provided"
                return result

            # If only receive_currency is provided, try to get country
            if not receive_country:
                from_currency_to_country = self._get_country_from_currency(receive_currency)
                if from_currency_to_country:
                    self.logger.info(
                        f"Derived country {from_currency_to_country} from currency {receive_currency}"
                    )
                    receive_country = from_currency_to_country
                    result["destination_country"] = receive_country
                else:
                    self.logger.error(f"Could not derive country from currency {receive_currency}")
                    result[
                        "error_message"
                    ] = f"Could not determine country for currency {receive_currency}"
                    return result

            # If only receive_country is provided, try to get currency
            if not receive_currency:
                country_default_currency = self._get_currency_from_country(receive_country)
                if country_default_currency:
                    self.logger.info(
                        f"Using default currency {country_default_currency} for country {receive_country}"
                    )
                    receive_currency = country_default_currency
                    result["destination_currency"] = receive_currency
                else:
                    self.logger.error(f"No default currency found for country {receive_country}")
                    result[
                        "error_message"
                    ] = f"Could not determine currency for country {receive_country}"
                    return result

            # First try to get rate from fee table
            try:
                fee_table_result = self._get_exchange_rate_via_fee_table(
                    send_amount=send_amount,
                    send_currency=send_currency,
                    receive_country=receive_country,
                    receive_currency=receive_currency,
                )

                if (
                    fee_table_result
                    and "exchange_rate" in fee_table_result
                    and fee_table_result["exchange_rate"] > 0
                ):
                    self.logger.info(
                        f"Successfully retrieved rate from fee table: {fee_table_result}"
                    )

                    # Update result with fee table data
                    result.update(
                        {
                            "success": True,
                            "exchange_rate": fee_table_result["exchange_rate"],
                            "fee": fee_table_result.get("fee", 0.0),
                            "destination_amount": fee_table_result.get("destination_amount", 0.0),
                            "delivery_method": fee_table_result.get(
                                "delivery_method", result["delivery_method"]
                            ),
                            "payment_method": fee_table_result.get(
                                "payment_method", result["payment_method"]
                            ),
                            "delivery_time_minutes": fee_table_result.get(
                                "delivery_time_minutes", result["delivery_time_minutes"]
                            ),
                        }
                    )

                    # Include any additional details
                    if "details" in fee_table_result:
                        result["details"] = fee_table_result["details"]
                    else:
                        result["details"] = {
                            "provider": "Xoom",
                            "url": f"https://www.xoom.com/{receive_country.lower()}/send-money",
                        }

                    return result
            except Exception as e:
                self.logger.warning(f"Failed to get rate from fee table: {str(e)}")
                # Continue to next method

            # If fee table fails, try the quote API (requires login)
            try:
                # Ensure we're authenticated
                if not self._is_authenticated():
                    self.logger.info("Not authenticated, attempting to authenticate")
                    self._authenticate()

                # Make request to quote API
                quote_result = self._get_quote_from_api(
                    send_amount=send_amount,
                    send_currency=send_currency,
                    receive_country=receive_country,
                    receive_currency=receive_currency,
                    delivery_method=delivery_method,
                )

                if (
                    quote_result
                    and "exchange_rate" in quote_result
                    and quote_result["exchange_rate"] > 0
                ):
                    self.logger.info(f"Successfully retrieved rate from quote API: {quote_result}")

                    # Update result with quote API data
                    result.update(
                        {
                            "success": True,
                            "exchange_rate": quote_result["exchange_rate"],
                            "fee": quote_result.get("fee", 0.0),
                            "destination_amount": quote_result.get("destination_amount", 0.0),
                            "delivery_method": quote_result.get(
                                "delivery_method", result["delivery_method"]
                            ),
                            "payment_method": quote_result.get(
                                "payment_method", result["payment_method"]
                            ),
                            "delivery_time_minutes": quote_result.get(
                                "delivery_time_minutes", result["delivery_time_minutes"]
                            ),
                        }
                    )

                    # Include any additional details
                    if "details" in quote_result:
                        result["details"] = quote_result["details"]

                    return result
            except Exception as e:
                self.logger.warning(f"Failed to get rate from quote API: {str(e)}")
                # Fallback to default values

            # If we get here, all methods failed - use default/fallback values
            self.logger.warning("Using fallback exchange rate estimation")

            # Estimate exchange rate based on corridor
            estimated_rates = {
                "USD-MXN": 19.5,
                "USD-INR": 83.0,
                "USD-PHP": 56.0,
                "USD-BDT": 110.0,
                "USD-PKR": 279.0,
                "USD-BHD": 0.376,
                "USD-EUR": 0.92,
                "USD-GBP": 0.78,
            }

            corridor = f"{send_currency}-{receive_currency}"
            exchange_rate = estimated_rates.get(corridor, 1.0)
            destination_amount = float(send_amount) * exchange_rate

            # Use default fee structure
            float_amount = float(send_amount)
            if float_amount < 1000:
                fee = 2.99
            else:
                fee = 4.99

            # Update result with fallback data
            result.update(
                {
                    "success": True,
                    "exchange_rate": exchange_rate,
                    "fee": fee,
                    "destination_amount": destination_amount,
                    "details": {
                        "provider": "Xoom",
                        "url": f"https://www.xoom.com/{receive_country.lower()}/send-money",
                        "fallback": True,  # Indicate this is a fallback response
                    },
                }
            )

            return result

        except Exception as e:
            error_msg = f"Error getting exchange rate: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result["error_message"] = error_msg
            return result

    def _get_exchange_rate_via_fee_table(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        receive_currency: str,
    ) -> Dict:
        """
        Get exchange rate and fee information via the fee table endpoint.
        This method doesn't require authentication.
        """
        self.logger.info(
            f"Getting exchange rate via fee table for {send_amount} {send_currency} to {receive_country} ({receive_currency})"
        )

        # Convert send amount to float with 2 decimal places
        send_amount_float = float(send_amount)

        # Maximum number of retries for API requests
        max_retries = 3
        retry_count = 0
        backoff_factor = 1.5

        while retry_count < max_retries:
            try:
                # Generate random request ID and timestamp
                request_id = str(uuid.uuid4())
                timestamp = int(time.time() * 1000)

                # Setup query parameters based on the provided curl example
                params = {
                    "sourceCountryCode": "US",  # Default source country
                    "sourceCurrencyCode": send_currency,
                    "destinationCountryCode": receive_country,
                    "destinationCurrencyCode": receive_currency,
                    "sendAmount": send_amount_float,
                    "receiveAmount": 0,  # Will be calculated by Xoom
                    "localCurrency": "true",
                    "serviceType": "",
                    "serviceSlug": "",
                    "receiveAmountEntered": "false",
                    "oldSourceCurrencyCode": send_currency,
                    "oldDestinationCurrencyCode": receive_currency,
                    "remittanceResourceID": request_id,
                    "_": timestamp,
                }

                # Set required headers to simulate browser request
                headers = {
                    "Pragma": "no-cache",
                    "Accept": "*/*",
                    "Sec-Fetch-Site": "same-origin",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                    "Sec-Fetch-Mode": "cors",
                    "Accept-Encoding": "gzip, deflate, br",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                    "Referer": f"https://www.xoom.com/{receive_country.lower()}/send-money",
                    "Sec-Fetch-Dest": "empty",
                    "X-Requested-With": "XMLHttpRequest",
                    "Priority": "u=3, i",
                }

                # Ensure session cookies are set
                if not self.session.cookies:
                    self._visit_home_page()

                # Make GET request to fee table endpoint
                response = self.session.get(
                    f"{self.BASE_URL}/calculate-fee-table",
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )

                # Check if response is successful
                if response.status_code != 200:
                    self.logger.error(f"Fee table API returned status code {response.status_code}")
                    retry_count += 1
                    time.sleep(backoff_factor**retry_count)
                    continue

                # Parse the HTML response to extract exchange rate and fee information
                result = self._parse_fee_table_response(
                    response.text,
                    send_amount_float,
                    send_currency,
                    receive_country,
                    receive_currency,
                )

                # If exchange rate extraction was successful, return the result
                if result and "exchange_rate" in result and result["exchange_rate"] > 0:
                    self.logger.info(
                        f"Successfully extracted exchange rate: {result['exchange_rate']}"
                    )
                    return result

                # If we got a response but couldn't extract the data, retry
                self.logger.warning("Failed to extract exchange rate from response")
                retry_count += 1
                time.sleep(backoff_factor**retry_count)

            except (requests.RequestException, ConnectionError) as e:
                self.logger.error(f"Request error during attempt {retry_count + 1}: {str(e)}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise XoomConnectionError(
                        f"Failed to connect to Xoom API after {max_retries} attempts: {str(e)}"
                    )
                time.sleep(backoff_factor**retry_count)

            except Exception as e:
                self.logger.error(f"Unexpected error during attempt {retry_count + 1}: {str(e)}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise XoomError(f"Unexpected error when fetching exchange rate: {str(e)}")
                time.sleep(backoff_factor**retry_count)

        raise XoomError(f"Failed to get exchange rate after {max_retries} attempts")

    def _parse_fee_table_response(
        self,
        html_response: str,
        send_amount: float,
        send_currency: str,
        receive_country: str,
        receive_currency: str,
    ) -> Dict:
        """
        Parse the HTML response from the fee table API to extract exchange rate and fee information.

        Args:
            html_response: HTML response from the fee table API
            send_amount: Amount being sent
            send_currency: Source currency code
            receive_country: Destination country code
            receive_currency: Destination currency code

        Returns:
            Dictionary with exchange rate information
        """
        self.logger.info("Parsing fee table response")

        # Initialize a complete result structure with defaults to avoid missing keys
        result = {
            "provider_id": self.provider_id,
            "provider_name": "Xoom",
            "source_country": "US",
            "destination_country": receive_country,
            "source_currency": send_currency,
            "destination_currency": receive_currency,
            "source_amount": send_amount,
            "destination_amount": 0.0,
            "exchange_rate": 0.0,
            "fee": 4.99,  # Default fee
            "payment_method": "PayPal balance",  # Default payment method
            "delivery_method": "Bank Deposit",  # Default delivery method
            "delivery_time_minutes": 1440,  # Default 24 hour delivery
            "fixed_delivery_time": "Within 24 hours",
            "success": False,
        }

        try:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_response, "html.parser")

            # First try to extract embedded JSON data (preferred)
            json_data_element = soup.select_one("data#jsonData")
            if json_data_element and json_data_element.string:
                # Extract and clean the JSON string
                json_str = html.unescape(json_data_element.string)

                try:
                    # Parse the JSON data
                    data_json = json.loads(json_str)
                    if "data" in data_json and isinstance(data_json["data"], dict):
                        data = data_json["data"]

                        # Extract exchange rate
                        if "fxRate" in data and data["fxRate"]:
                            try:
                                result["exchange_rate"] = float(data["fxRate"])
                                self.logger.info(
                                    f"Extracted fxRate from JSON: {result['exchange_rate']}"
                                )
                            except (ValueError, TypeError):
                                self.logger.warning(
                                    f"Could not convert fxRate to float: {data['fxRate']}"
                                )

                        # Extract receive amount
                        if "receiveAmount" in data and data["receiveAmount"]:
                            try:
                                result["destination_amount"] = float(data["receiveAmount"])
                                self.logger.info(
                                    f"Extracted receiveAmount from JSON: {result['destination_amount']}"
                                )
                            except (ValueError, TypeError):
                                self.logger.warning(
                                    f"Could not convert receiveAmount to float: {data['receiveAmount']}"
                                )

                        # Extract fee if available
                        if "fee" in data and data["fee"]:
                            try:
                                result["fee"] = float(data["fee"])
                                self.logger.info(f"Extracted fee from JSON: {result['fee']}")
                            except (ValueError, TypeError):
                                self.logger.warning(
                                    f"Could not convert fee to float: {data['fee']}"
                                )

                        # Mark as successful if we got the essential exchange rate
                        if result["exchange_rate"] > 0:
                            result["success"] = True
                except json.JSONDecodeError as e:
                    self.logger.warning(
                        f"Failed to parse JSON: {str(e)}, content: {json_str[:100]}..."
                    )

            # If no exchange rate from JSON, try to parse the HTML tables
            if result["exchange_rate"] == 0:
                # Look for exchange rate spans
                rate_spans = soup.select(".exchangeRate, .fxRate")
                for span in rate_spans:
                    rate_text = span.text.strip()
                    rate = self._extract_exchange_rate(rate_text)
                    if rate > 0:
                        result["exchange_rate"] = rate
                        result["success"] = True
                        self.logger.info(f"Extracted exchange rate from HTML: {rate}")
                        break

            # Extract fee information from tables in HTML
            fees = {}
            fee_rows = soup.select("tr.xvx-table--fee__body-tr")
            if fee_rows:
                self.logger.info(f"Found {len(fee_rows)} fee options in the table")
                for row in fee_rows:
                    payment_cell = row.select_one("td.xvx-table--fee__body-td:not(.fee-value)")
                    fee_cell = row.select_one("td.xvx-table--fee__body-td.fee-value")

                    if payment_cell and fee_cell:
                        payment_option = payment_cell.text.strip()
                        fee_value_text = fee_cell.text.strip().replace("$", "").replace(",", "")

                        try:
                            fee_value = float(fee_value_text)
                            payment_method_key = payment_option.strip()

                            # Store fee for this payment method
                            fees[payment_method_key] = fee_value

                            # Use lowest fee payment method first, prioritizing PYUSD or PayPal balance if they have zero fee
                            if (
                                payment_method_key in ["PayPal USD (PYUSD)", "PayPal balance"]
                                and fee_value == 0.0
                            ):
                                result["payment_method"] = payment_method_key
                                result["fee"] = fee_value
                            elif (
                                "payment_method" not in result
                                or fees.get(result["payment_method"], float("inf")) > fee_value
                            ):
                                result["payment_method"] = payment_method_key
                                result["fee"] = fee_value
                        except ValueError:
                            self.logger.warning(f"Could not parse fee value: {fee_value_text}")

            # If we haven't found any fees, use default fee structure
            if not fees:
                self.logger.warning("Could not extract fees from HTML, using default fee structure")
                fees = {
                    "PayPal USD (PYUSD)": 0.00,
                    "PayPal balance": 4.99 if send_amount >= 1000 else 2.99,
                    "Bank account": 4.99 if send_amount >= 1000 else 2.99,
                    "Debit card": 5.99,
                    "Credit card": 5.99,
                }

                # Set default fee and payment method
                if "PayPal USD (PYUSD)" in fees:
                    result["payment_method"] = "PayPal USD (PYUSD)"
                    result["fee"] = fees["PayPal USD (PYUSD)"]
                else:
                    result["payment_method"] = "PayPal balance"
                    result["fee"] = fees["PayPal balance"]

            # If we still don't have an exchange rate, try to calculate from amounts or use estimate
            if result["exchange_rate"] == 0:
                if result["destination_amount"] > 0:
                    result["exchange_rate"] = result["destination_amount"] / send_amount
                    self.logger.info(
                        f"Calculated exchange rate from amounts: {result['exchange_rate']}"
                    )
                else:
                    # Fallback to estimated rates for common corridors
                    estimated_rates = {
                        "USD-MXN": 19.5,
                        "USD-INR": 83.0,
                        "USD-PHP": 56.0,
                        "USD-BDT": 110.0,
                        "USD-PKR": 279.0,
                        "USD-EUR": 0.92,
                        "USD-GBP": 0.78,
                    }
                    corridor = f"{send_currency}-{receive_currency}"
                    if corridor in estimated_rates:
                        result["exchange_rate"] = estimated_rates[corridor]
                        result["destination_amount"] = send_amount * result["exchange_rate"]
                        result["success"] = True
                        self.logger.info(
                            f"Using estimated exchange rate for {corridor}: {result['exchange_rate']}"
                        )

            # Add available payment methods to result
            result["available_payment_methods"] = [
                {"id": key, "name": key, "fee": value} for key, value in fees.items()
            ]

            # Add details
            result["details"] = {
                "provider": "Xoom",
                "url": f"https://www.xoom.com/{receive_country.lower()}/send-money",
                "estimated": result.get("exchange_rate", 0) == 0,
            }

            self.logger.info(
                f"Parsed result: exchange_rate={result['exchange_rate']}, fee={result['fee']}, payment_method={result['payment_method']}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Error parsing fee table response: {str(e)}", exc_info=True)

            # Ensure a valid result is returned with basic info
            result["error_message"] = f"Error parsing response: {str(e)}"
            return result

    def _filter_pricing_options(
        self,
        pricing_options: List[Dict],
        preferred_delivery_method: Optional[str] = None,
        preferred_payment_method: Optional[str] = None,
    ) -> List[Dict]:
        """
        Filter pricing options based on delivery and payment method preferences.

        Args:
            pricing_options: List of pricing options from the API
            preferred_delivery_method: Preferred delivery method (e.g., "DEPOSIT")
            preferred_payment_method: Preferred payment method (e.g., "DEBIT_CARD")

        Returns:
            Filtered list of pricing options
        """
        if not pricing_options:
            return []

        filtered_options = pricing_options.copy()

        # Filter by delivery method if specified
        if preferred_delivery_method:
            delivery_filtered = [
                opt
                for opt in filtered_options
                if opt.get("disbursementType") == preferred_delivery_method
            ]
            if delivery_filtered:
                filtered_options = delivery_filtered

        # Filter by payment method if specified
        if preferred_payment_method:
            payment_filtered = [
                opt
                for opt in filtered_options
                if opt.get("paymentType", {}).get("type") == preferred_payment_method
            ]
            if payment_filtered:
                filtered_options = payment_filtered

        # If no options match the preferences, return all options
        if not filtered_options:
            return pricing_options

        # Sort by fee (lowest first)
        filtered_options.sort(
            key=lambda opt: float(opt.get("feeAmount", {}).get("rawValue", "9999"))
        )

        return filtered_options

    def _find_best_pricing_option(
        self,
        pricing_options: List[Dict],
        preferred_delivery_method: Optional[str] = None,
        preferred_payment_method: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Find the best pricing option based on preferences.

        Args:
            pricing_options: List of pricing options from the API
            preferred_delivery_method: Preferred delivery method (e.g., "DEPOSIT")
            preferred_payment_method: Preferred payment method (e.g., "DEBIT_CARD")

        Returns:
            The best pricing option or None if no matching option found
        """
        if not pricing_options:
            return None

        # Create a scoring function for options
        def score_option(option):
            score = 0

            # Delivery method match
            if (
                preferred_delivery_method
                and option["disbursementType"] == preferred_delivery_method
            ):
                score += 100

            # Payment method match
            if (
                preferred_payment_method
                and option["paymentType"]["type"] == preferred_payment_method
            ):
                score += 50

            # Prefer options with lower fees
            fee = float(option["feeAmount"]["rawValue"])
            score -= fee * 2

            # Prefer options with higher receive amount
            receive_amount = float(option["receiveAmount"]["rawValue"])
            score += receive_amount * 0.001

            return score

        # Score and sort options
        scored_options = [(score_option(option), option) for option in pricing_options]
        scored_options.sort(reverse=True)  # Sort by score in descending order

        # Return the highest-scored option
        return scored_options[0][1] if scored_options else None

    def _get_default_currency_for_country(self, country_code: str) -> Optional[str]:
        """
        Get the default currency for a given country.

        Args:
            country_code: ISO-3166-1 alpha-2 country code

        Returns:
            Default currency code for the country
        """
        # Use the utility function to get country currencies
        currencies = get_country_currencies(country_code)
        if currencies:
            return currencies[0]

        # Fallback mapping for countries not in standard mapping
        country_currency_map = {
            "MX": "MXN",
            "PH": "PHP",
            "IN": "INR",
            "CO": "COP",
            "GT": "GTQ",
            "SV": "USD",
            "DO": "DOP",
            "HN": "HNL",
            "PE": "PEN",
            "EC": "USD",
            "AU": "AUD",
            "CA": "CAD",
            "GB": "GBP",
            "US": "USD",
            "BH": "BHD",
            "NG": "NGN",
            "BD": "BDT",
            "PK": "PKR",
        }

        return country_currency_map.get(country_code.upper())

    def _get_currency_for_country(self, country_code: str) -> str:
        """
        Get the currency for a country, handling fallbacks.

        Args:
            country_code: ISO-3166-1 alpha-2 country code

        Returns:
            Currency code for the country
        """
        currency = self._get_default_currency_for_country(country_code)

        if not currency:
            self.logger.warning(
                f"No currency found for country code {country_code}, defaulting to USD"
            )
            currency = "USD"

        return currency

    def get_supported_countries(self) -> List[Dict]:
        """
        Get a list of countries supported by Xoom.

        Returns:
            List of dictionaries with country information
        """
        self.logger.info("Getting supported countries")

        try:
            # First try to get from API
            if not self.session.cookies:
                self._initialize_session()

            response = self._make_api_request(
                method="GET",
                url=f"{self.BASE_URL}/xoom/api/country/receiving",
                retry_auth=False,
            )

            if response and "countries" in response:
                countries = []

                for country_data in response["countries"]:
                    code = country_data.get("code")
                    name = country_data.get("displayName") or get_country_name(code) or code

                    # Get currency for the country
                    currency = self._get_currency_for_country(code)

                    countries.append({"code": code, "name": name, "currency": currency})

                return countries
            else:
                self.logger.warning("Failed to get countries from API, using static list")
        except Exception as e:
            self.logger.error(f"Error getting supported countries: {str(e)}")

        # Fall back to static list
        return self._get_static_country_list()

    def _get_static_country_list(self) -> List[Dict]:
        """
        Get a static list of countries supported by Xoom.
        Used as a fallback when the API call fails.

        Returns:
            List of dictionaries with country information
        """
        # Common countries supported by Xoom
        country_codes = [
            "MX",
            "PH",
            "IN",
            "CO",
            "GT",
            "SV",
            "DO",
            "HN",
            "PE",
            "EC",
            "BR",
            "JM",
            "NI",
            "PY",
            "UY",
            "CL",
            "VN",
            "CN",
            "BD",
            "PK",
            "LK",
            "BH",
            "NG",
            "GH",
            "KE",
            "FR",
            "DE",
            "IT",
            "ES",
            "PT",
            "AU",
        ]

        countries = []
        for code in country_codes:
            # Use the utility functions to get country names
            name = get_country_name(code) or ISO_COUNTRY_NAMES.get(code, code)
            currency = self._get_currency_for_country(code)

            countries.append({"code": code, "name": name, "currency": currency})

        return countries

    def get_payment_methods(
        self, source_country: str = "US", target_country: str = "MX"
    ) -> List[Dict]:
        """
        Get available payment methods for a specific corridor.

        Args:
            source_country: Source country code (e.g., "US")
            target_country: Target country code (e.g., "MX")

        Returns:
            List of payment method objects
        """
        # Prepare payload for a minimum amount query
        payload = {
            "data": {
                "remittance": {
                    "sourceCurrency": "USD",
                    "destinationCountry": target_country,
                    "destinationCurrency": self._get_currency_for_country(target_country),
                }
            }
        }

        try:
            # Make API request
            response = self._make_api_request(method="POST", url=self.API_URL, data=payload)

            # Extract payment methods from pricing options
            if (
                not response
                or "data" not in response
                or "remittance" not in response["data"]
                or "quote" not in response["data"]["remittance"]
                or "pricing" not in response["data"]["remittance"]["quote"]
            ):
                return self._get_static_payment_methods()

            pricing_options = response["data"]["remittance"]["quote"]["pricing"]

            # Extract unique payment methods
            payment_methods = []
            payment_method_ids = set()

            for option in pricing_options:
                payment_type = option["paymentType"]["type"]

                if payment_type not in payment_method_ids:
                    payment_method_ids.add(payment_type)

                    # Extract fee info
                    fee = float(option["feeAmount"]["rawValue"])

                    # Get description from content
                    description = None
                    for content_item in option.get("content", []):
                        if content_item["key"] == "feesFx.paymentType":
                            description = content_item["value"]
                            break

                    payment_methods.append(
                        {
                            "id": payment_type,
                            "name": self.PAYMENT_METHODS.get(payment_type, payment_type),
                            "type": "card" if "CARD" in payment_type else "electronic",
                            "description": description
                            or f"Pay with {self.PAYMENT_METHODS.get(payment_type, payment_type)}",
                            "fee": fee,
                            "is_default": payment_type == "PAYPAL_BALANCE",
                        }
                    )

            # Sort by fee (lowest first)
            payment_methods.sort(key=lambda x: x.get("fee", 0))

            return payment_methods

        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return self._get_static_payment_methods()

    def _get_static_payment_methods(self) -> List[Dict]:
        """Return a static list of payment methods supported by Xoom."""
        return [
            {
                "id": "PAYPAL_BALANCE",
                "name": "PayPal balance",
                "type": "electronic",
                "description": "Pay with PayPal balance",
                "fee": 0.00,
                "is_default": True,
            },
            {
                "id": "CRYPTO_PYUSD",
                "name": "PayPal USD (PYUSD)",
                "type": "electronic",
                "description": "Pay with PayPal USD stablecoin",
                "fee": 0.00,
                "is_default": False,
            },
            {
                "id": "ACH",
                "name": "Bank Account",
                "type": "electronic",
                "description": "Pay with your bank account",
                "fee": 0.00,
                "is_default": False,
            },
            {
                "id": "DEBIT_CARD",
                "name": "Debit Card",
                "type": "card",
                "description": "Pay with your debit card",
                "fee": 3.99,
                "is_default": False,
            },
            {
                "id": "CREDIT_CARD",
                "name": "Credit Card",
                "type": "card",
                "description": "Pay with your credit card",
                "fee": 3.99,
                "is_default": False,
            },
        ]

    def get_delivery_methods(
        self, source_country: str = "US", target_country: str = "MX"
    ) -> List[Dict]:
        """
        Get available delivery methods for a specific corridor.

        Args:
            source_country: Source country code (e.g., "US")
            target_country: Target country code (e.g., "MX")

        Returns:
            List of delivery method objects
        """
        # Prepare payload for a minimum amount query
        payload = {
            "data": {
                "remittance": {
                    "sourceCurrency": "USD",
                    "destinationCountry": target_country,
                    "destinationCurrency": self._get_currency_for_country(target_country),
                }
            }
        }

        try:
            # Make API request
            response = self._make_api_request(method="POST", url=self.API_URL, data=payload)

            # Extract delivery methods from pricing options
            if (
                not response
                or "data" not in response
                or "remittance" not in response["data"]
                or "quote" not in response["data"]["remittance"]
                or "pricing" not in response["data"]["remittance"]["quote"]
            ):
                return self._get_static_delivery_methods()

            pricing_options = response["data"]["remittance"]["quote"]["pricing"]

            # Extract unique delivery methods
            delivery_methods = []
            delivery_method_ids = set()

            for option in pricing_options:
                disbursement_type = option["disbursementType"]

                if disbursement_type not in delivery_method_ids:
                    delivery_method_ids.add(disbursement_type)

                    # Extract info from content
                    name = None
                    description = None
                    delivery_time = None

                    for content_item in option.get("content", []):
                        if content_item["key"] == "feesFx.disbursementType":
                            name = content_item["value"]
                        elif content_item["key"] == "feesFx.paymentTypeParagraph":
                            description = content_item["value"]
                        elif (
                            content_item["key"] == "feesFx.paymentTypeHeader"
                            and "minutes" in content_item["value"].lower()
                        ):
                            delivery_time = content_item["value"]

                    delivery_methods.append(
                        {
                            "id": disbursement_type,
                            "name": name
                            or self.DELIVERY_METHODS.get(disbursement_type, disbursement_type),
                            "description": description
                            or f"Send money via {self.DELIVERY_METHODS.get(disbursement_type, disbursement_type)}",
                            "delivery_time": delivery_time,
                            "is_default": disbursement_type == "DEPOSIT",
                        }
                    )

            return delivery_methods

        except Exception as e:
            logger.error(f"Error getting delivery methods: {e}")
            return self._get_static_delivery_methods()

    def _get_static_delivery_methods(self) -> List[Dict]:
        """Return a static list of delivery methods supported by Xoom."""
        return [
            {
                "id": "DEPOSIT",
                "name": "Bank Deposit",
                "description": "Transfer directly to bank account",
                "delivery_time": "Typically available in 1-2 business days",
                "is_default": True,
            },
            {
                "id": "PICKUP",
                "name": "Cash Pickup",
                "description": "Available at partner locations like Walmart, OXXO",
                "delivery_time": "Typically available within hours",
                "is_default": False,
            },
            {
                "id": "MOBILE_WALLET",
                "name": "Mobile Wallet",
                "description": "Send to mobile wallet services like Mercado Pago",
                "delivery_time": "Typically available in minutes",
                "is_default": False,
            },
            {
                "id": "CARD_DEPOSIT",
                "name": "Debit Card Deposit",
                "description": "Send directly to debit card",
                "delivery_time": "Typically available in minutes",
                "is_default": False,
            },
        ]

    def _extract_exchange_rate(self, rate_string: str) -> float:
        """
        Extract the exchange rate from a string like "1 USD = 19.9384 MXN".

        Args:
            rate_string: String containing the exchange rate

        Returns:
            Exchange rate as a float
        """
        if not rate_string:
            return 0.0

        # Try to extract with regex
        match = re.search(r"(\d+[\.,]?\d*)\s*[A-Z]{3}", rate_string)
        if match:
            try:
                # Convert to float, handling commas
                rate_str = match.group(1).replace(",", ".")
                return float(rate_str)
            except (ValueError, IndexError):
                pass

        # Try another approach with regex
        match = re.search(r"=\s*(\d+[\.,]?\d*)", rate_string)
        if match:
            try:
                rate_str = match.group(1).replace(",", ".")
                return float(rate_str)
            except (ValueError, IndexError):
                pass

        # Return 0 if extraction failed
        return 0.0

    def _normalize_delivery_method(self, method_type: str) -> str:
        """
        Normalize delivery method to consistent format.

        Args:
            method_type: Raw delivery method from API

        Returns:
            Normalized delivery method string
        """
        method_map = {
            "DEPOSIT": "bank deposit",
            "PICKUP": "cash pickup",
            "CARD_DEPOSIT": "card deposit",
            "MOBILE_WALLET": "mobile wallet",
        }

        return method_map.get(method_type, method_type.lower())

    def _process_content_fields(self, content_fields: List[Dict]) -> Dict:
        """
        Process content fields from API response into a dictionary.

        Args:
            content_fields: List of content field objects

        Returns:
            Dictionary of processed content fields
        """
        result = {}

        for field in content_fields:
            key = field.get("key", "").split(".")[-1]  # Use the last part of the key
            value = field.get("value", "")

            if key and value:
                result[key] = value

        return result

    def _parse_delivery_time(self, time_string: str) -> Optional[int]:
        """
        Parse delivery time string to minutes.

        Args:
            time_string: String like "Available in 60 minutes"

        Returns:
            Minutes as integer or None if not parseable
        """
        if not time_string:
            return None

        # Try to match minutes pattern
        minutes_match = re.search(r"(\d+)\s*minutes?", time_string.lower())
        if minutes_match:
            try:
                return int(minutes_match.group(1))
            except (ValueError, IndexError):
                pass

        # Try to match hours pattern
        hours_match = re.search(r"(\d+)\s*hours?", time_string.lower())
        if hours_match:
            try:
                return int(hours_match.group(1)) * 60
            except (ValueError, IndexError):
                pass

        # Try to match days pattern
        days_match = re.search(r"(\d+)\s*days?", time_string.lower())
        if days_match:
            try:
                return int(days_match.group(1)) * 24 * 60
            except (ValueError, IndexError):
                pass

        # Default times based on common phrases
        if "within an hour" in time_string.lower():
            return 60
        elif "within hours" in time_string.lower():
            return 180  # 3 hours as a reasonable default
        elif "1-2 business days" in time_string.lower():
            return 36 * 60  # 1.5 days in minutes
        elif "next day" in time_string.lower():
            return 24 * 60

        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
