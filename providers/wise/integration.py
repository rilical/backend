"""
Wise Money Transfer Integration (formerly TransferWise)

This module implements the integration with Wise (TransferWise) money transfer API.
It is designed to be aggregator-ready, with no fallback data.

Key features:
- Uses public unauthenticated API endpoints when possible
- Aggregator-standard responses for all methods
- Proper error handling and logging
- Follows best practices for API integration

PAYMENT METHODS (pay_in types):
------------------------------
- BANK_TRANSFER: Regular bank transfer
- CARD: Debit or credit card payment
- SWIFT: SWIFT transfer
- BALANCE: Wise account balance

DELIVERY METHODS (pay_out types):
--------------------------------
- BANK_TRANSFER: Bank account deposit
- SWIFT: SWIFT transfer to bank account
- CASH_PICKUP: Cash pickup (where available)
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from providers.base.provider import RemittanceProvider

from .exceptions import (
    WiseAuthenticationError,
    WiseConnectionError,
    WiseError,
    WiseRateLimitError,
    WiseValidationError,
)

logger = logging.getLogger(__name__)


class WiseProvider(RemittanceProvider):
    """
    Aggregator-ready integration for Wise (TransferWise) with no fallback data.

    Returns standardized responses in all cases:
    - On success: All required aggregator fields with live data from Wise API
    - On failure: Proper error details with no fallback data

    Uses unauthenticated endpoints when possible to avoid API key requirements.
    """

    BASE_URL = "https://api.transferwise.com"
    QUOTES_ENDPOINT = "/v3/quotes/"
    PROFILES_ENDPOINT = "/v1/profiles"

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    )

    # Delivery time estimates in minutes
    DELIVERY_TIME_ESTIMATES = {
        "INSTANT": 5,  # Nearly instant
        "SAME_DAY": 180,  # Same day (roughly 3 hours)
        "NEXT_DAY": 1440,  # Next day (24 hours)
        "STANDARD": 2880,  # 2 days
        "DEFAULT": 1440,  # Default fallback
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the Wise provider.

        Args:
            api_key: API key for authenticating with Wise (optional for some endpoints)
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        super().__init__(name="wise", base_url=self.BASE_URL, **kwargs)
        self.logger = logger
        self.timeout = timeout

        self.user_agent = user_agent or os.environ.get("WISE_DEFAULT_UA", self.DEFAULT_USER_AGENT)

        self.api_key = api_key or os.environ.get("WISE_API_KEY")
        self._session = requests.Session()
        self.request_id = str(uuid.uuid4())
        self._initialize_session()

    def _initialize_session(self) -> None:
        """Set up the HTTP session with default headers and retry strategy."""
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": self.user_agent,
                "X-Request-ID": self.request_id,
            }
        )

        if self.api_key:
            self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})

        # Configure retry strategy for better reliability
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)

    def standardize_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local result dictionary into aggregator-friendly response.

        Args:
            result: Raw provider result dictionary

        Returns:
            Standardized response dictionary
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # If success is false or missing, return error response
        success = bool(result.get("success", False))
        if not success:
            return {
                "provider_id": self.name,
                "success": False,
                "error_message": result.get("error_message") or "Unknown Wise error",
            }

        # Return success response with all required fields
        return {
            "provider_id": self.name,
            "success": True,
            "error_message": None,
            "send_amount": result.get("send_amount", 0.0),
            "source_currency": str(result.get("source_currency", "")).upper(),
            "destination_amount": result.get("destination_amount", 0.0),
            "destination_currency": str(result.get("destination_currency", "")).upper(),
            "exchange_rate": result.get("exchange_rate", 0.0),
            "fee": result.get("fee", 0.0),
            "payment_method": result.get("payment_method", "BANK_TRANSFER"),
            "delivery_method": result.get("delivery_method", "BANK_TRANSFER"),
            "delivery_time_minutes": result.get(
                "delivery_time_minutes", self.DELIVERY_TIME_ESTIMATES["DEFAULT"]
            ),
            "timestamp": result.get("timestamp", now_iso),
            "raw_response": result.get("raw_response"),
        }

    def get_quote(
        self,
        amount: Optional[Decimal] = None,
        source_currency: str = "USD",
        destination_currency: str = None,
        source_country: str = "US",
        dest_country: str = None,
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer (aggregator-standard method).

        Args:
            amount: Amount to send
            source_currency: Source currency code
            destination_currency: Destination currency code
            source_country: Source country code
            dest_country: Destination country code
            payment_method: Payment method
            delivery_method: Delivery method

        Returns:
            Standardized response with quote information
        """
        aggregator_fail = {"success": False, "error_message": None}

        # Validate required parameters
        if amount is None:
            aggregator_fail["error_message"] = "Amount is required"
            return self.standardize_response(aggregator_fail)

        if not source_currency:
            aggregator_fail["error_message"] = "Source currency is required"
            return self.standardize_response(aggregator_fail)

        if not destination_currency:
            aggregator_fail["error_message"] = "Destination currency is required"
            return self.standardize_response(aggregator_fail)

        # Validate amount
        if amount <= 0:
            aggregator_fail["error_message"] = f"Invalid amount: {amount}"
            return self.standardize_response(aggregator_fail)

        try:
            # Get quote data from Wise API using unauthenticated endpoint
            quote_data = self._create_unauthenticated_quote(
                source_currency=source_currency,
                target_currency=destination_currency,
                source_amount=float(amount),
            )

            # Validate quote data
            if not quote_data.get("paymentOptions"):
                aggregator_fail["error_message"] = "No payment options available for this corridor"
                return self.standardize_response(aggregator_fail)

            # Find best payment option based on requested methods
            best_option = self._find_best_payment_option(
                quote_data,
                payment_method=payment_method,
                delivery_method=delivery_method,
            )

            if not best_option:
                aggregator_fail["error_message"] = "No suitable payment option found"
                return self.standardize_response(aggregator_fail)

            # Extract data from the quote and option
            exchange_rate = float(quote_data.get("rate", 0.0))
            fee = float(best_option.get("fee", {}).get("total", 0.0))
            target_amount = float(best_option.get("targetAmount", 0.0))

            # Determine payment and delivery methods
            pay_in = best_option.get("payIn")
            pay_out = best_option.get("payOut")

            # Standardize delivery time estimate
            delivery_time_minutes = self._estimate_delivery_time(best_option)

            # Create success response
            aggregator_ok = {
                "success": True,
                "send_amount": float(amount),
                "source_currency": source_currency,
                "destination_amount": target_amount,
                "destination_currency": destination_currency,
                "exchange_rate": exchange_rate,
                "fee": fee,
                "payment_method": pay_in,
                "delivery_method": pay_out,
                "delivery_time_minutes": delivery_time_minutes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": quote_data,
            }

            return self.standardize_response(aggregator_ok)

        except WiseAuthenticationError as e:
            aggregator_fail["error_message"] = f"Authentication error: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except WiseRateLimitError as e:
            aggregator_fail["error_message"] = f"Rate limit exceeded: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except WiseValidationError as e:
            aggregator_fail["error_message"] = f"Validation error: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except WiseConnectionError as e:
            aggregator_fail["error_message"] = f"Connection error: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except WiseError as e:
            aggregator_fail["error_message"] = f"Wise error: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except requests.RequestException as e:
            aggregator_fail["error_message"] = f"Request error: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except Exception as e:
            logger.error(f"Unexpected error in get_quote: {e}", exc_info=True)
            aggregator_fail["error_message"] = f"Unexpected error: {str(e)}"
            return self.standardize_response(aggregator_fail)

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, receive_currency: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Get exchange rate information for a specific currency pair.

        Args:
            send_amount: Amount to send
            send_currency: Source currency code
            receive_currency: Destination currency code
            **kwargs: Additional parameters

        Returns:
            Standardized response with exchange rate information
        """
        # Simply delegate to get_quote which handles all the details
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            destination_currency=receive_currency,
            **kwargs,
        )

    def _create_unauthenticated_quote(
        self,
        source_currency: str,
        target_currency: str,
        source_amount: float = None,
        target_amount: float = None,
    ) -> Dict[str, Any]:
        """
        Create an unauthenticated quote from Wise API.
        This endpoint doesn't require authentication.

        Args:
            source_currency: Source currency code
            target_currency: Target currency code
            source_amount: Amount to send (or None if using target_amount)
            target_amount: Amount to receive (or None if using source_amount)

        Returns:
            Raw quote data from Wise API

        Raises:
            WiseError: If API call fails
        """
        # Build request payload
        payload = {
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sourceAmount": source_amount,
            "targetAmount": target_amount,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            # Make API request to unauthenticated endpoint
            url = urljoin(self.BASE_URL, self.QUOTES_ENDPOINT)

            logger.debug(f"Creating unauthenticated Wise quote: {payload}")

            # Create a new session without auth headers for this request
            session = requests.Session()
            session.headers.update(
                {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": self.user_agent,
                }
            )

            response = session.post(url, json=payload, timeout=self.timeout)

            # Handle different status codes
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 422:
                raise WiseValidationError(
                    "Invalid parameters",
                    details={"status_code": 422, "body": response.text},
                )
            elif response.status_code == 429:
                raise WiseRateLimitError("Rate limit exceeded", details={"status_code": 429})
            else:
                # Handle all other errors
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = error_data["errors"][0].get("message", error_msg)
                except (ValueError, KeyError, IndexError):
                    error_msg = response.text[:100] if response.text else error_msg

                raise WiseError(
                    f"API error: {error_msg}",
                    details={"status_code": response.status_code},
                )

        except requests.RequestException as e:
            raise WiseConnectionError(f"Connection error: {str(e)}")

    def _create_quote(
        self,
        source_currency: str,
        target_currency: str,
        source_amount: float = None,
        target_amount: float = None,
    ) -> Dict[str, Any]:
        """
        Create an authenticated quote from Wise API.
        This endpoint requires an API key.

        Args:
            source_currency: Source currency code
            target_currency: Target currency code
            source_amount: Amount to send (or None if using target_amount)
            target_amount: Amount to receive (or None if using source_amount)

        Returns:
            Raw quote data from Wise API

        Raises:
            WiseError: If API call fails
        """
        # Check if API key is available
        if not self.api_key:
            raise WiseAuthenticationError("No API key provided")

        # Build request payload
        payload = {
            "sourceCurrency": source_currency,
            "targetCurrency": target_currency,
            "sourceAmount": source_amount,
            "targetAmount": target_amount,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            # Make API request
            url = urljoin(self.BASE_URL, self.QUOTES_ENDPOINT)

            logger.debug(f"Creating authenticated Wise quote: {payload}")
            response = self._session.post(url, json=payload, timeout=self.timeout)

            # Handle different status codes
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 401:
                raise WiseAuthenticationError("Authentication failed", details={"status_code": 401})
            elif response.status_code == 422:
                raise WiseValidationError(
                    "Invalid parameters",
                    details={"status_code": 422, "body": response.text},
                )
            elif response.status_code == 429:
                raise WiseRateLimitError("Rate limit exceeded", details={"status_code": 429})
            else:
                # Handle all other errors
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = error_data["errors"][0].get("message", error_msg)
                except (ValueError, KeyError, IndexError):
                    error_msg = response.text[:100] if response.text else error_msg

                raise WiseError(
                    f"API error: {error_msg}",
                    details={"status_code": response.status_code},
                )

        except requests.RequestException as e:
            raise WiseConnectionError(f"Connection error: {str(e)}")

    def _find_best_payment_option(
        self,
        quote_data: Dict[str, Any],
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best payment option from quote data.

        Args:
            quote_data: Quote data from Wise API
            payment_method: Preferred payment method (optional)
            delivery_method: Preferred delivery method (optional)

        Returns:
            Best payment option or None if not found
        """
        # Get all payment options
        payment_options = quote_data.get("paymentOptions", [])

        # Filter out disabled options
        valid_options = [opt for opt in payment_options if not opt.get("disabled")]

        if not valid_options:
            return None

        # Apply payment method filter if specified
        if payment_method:
            payment_method = payment_method.upper()
            filtered_by_payment = [
                opt for opt in valid_options if opt.get("payIn", "").upper() == payment_method
            ]
            if filtered_by_payment:
                valid_options = filtered_by_payment

        # Apply delivery method filter if specified
        if delivery_method:
            delivery_method = delivery_method.upper()
            filtered_by_delivery = [
                opt for opt in valid_options if opt.get("payOut", "").upper() == delivery_method
            ]
            if filtered_by_delivery:
                valid_options = filtered_by_delivery

        if not valid_options:
            return None

        # Sort by fee (lowest first)
        sorted_options = sorted(
            valid_options,
            key=lambda opt: float(opt.get("fee", {}).get("total", float("inf"))),
        )

        return sorted_options[0] if sorted_options else None

    def _estimate_delivery_time(self, payment_option: Dict[str, Any]) -> int:
        """
        Convert delivery time estimate to minutes.

        Args:
            payment_option: Payment option data

        Returns:
            Estimated delivery time in minutes
        """
        # Try to get formatted delivery time
        delivery_text = payment_option.get("formattedEstimatedDelivery", "").lower()

        # Handle common patterns
        if not delivery_text:
            return self.DELIVERY_TIME_ESTIMATES["DEFAULT"]

        if "instant" in delivery_text:
            return self.DELIVERY_TIME_ESTIMATES["INSTANT"]

        if (
            "today" in delivery_text
            or "within hours" in delivery_text
            or "same day" in delivery_text
        ):
            return self.DELIVERY_TIME_ESTIMATES["SAME_DAY"]

        if "tomorrow" in delivery_text or "next day" in delivery_text or "1 day" in delivery_text:
            return self.DELIVERY_TIME_ESTIMATES["NEXT_DAY"]

        if "days" in delivery_text:
            # Try to extract number of days
            import re

            day_match = re.search(r"(\d+)(?:-\d+)?\s*(?:business)?\s*days?", delivery_text)
            if day_match:
                days = int(day_match.group(1))
                return days * 24 * 60  # Convert days to minutes

        # Default fallback
        return self.DELIVERY_TIME_ESTIMATES["DEFAULT"]

    def get_corridors(self) -> Dict[str, Any]:
        """
        Get available corridors from Wise API.

        Returns:
            Standardized response with corridor information
        """
        aggregator_fail = {"success": False, "error_message": None}

        # Validate API key
        if not self.api_key:
            aggregator_fail["error_message"] = "No Wise API key provided"
            return self.standardize_response(aggregator_fail)

        try:
            # Get profile ID (required for corridors)
            profile_id = self._get_profile_id()
            if not profile_id:
                aggregator_fail["error_message"] = "Could not retrieve profile ID"
                return self.standardize_response(aggregator_fail)

            # Get corridors
            url = urljoin(self.BASE_URL, f"/v1/profiles/{profile_id}/available-currencies")
            response = self._session.get(url, timeout=self.timeout)

            if response.status_code != 200:
                aggregator_fail[
                    "error_message"
                ] = f"Failed to get corridors: HTTP {response.status_code}"
                return self.standardize_response(aggregator_fail)

            data = response.json()

            # Extract corridor information
            corridors = []
            for source_currency in data:
                source_code = source_currency.get("code")
                for target in source_currency.get("targetCurrencies", []):
                    corridors.append({"source_currency": source_code, "target_currency": target})

            # Create success response
            aggregator_ok = {
                "success": True,
                "corridors": corridors,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_response": data,
            }

            return self.standardize_response(aggregator_ok)

        except WiseError as e:
            aggregator_fail["error_message"] = f"Wise error: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except requests.RequestException as e:
            aggregator_fail["error_message"] = f"Request error: {str(e)}"
            return self.standardize_response(aggregator_fail)
        except Exception as e:
            logger.error(f"Unexpected error in get_corridors: {e}", exc_info=True)
            aggregator_fail["error_message"] = f"Unexpected error: {str(e)}"
            return self.standardize_response(aggregator_fail)

    def _get_profile_id(self) -> Optional[str]:
        """
        Get the profile ID for the authenticated user.

        Returns:
            Profile ID or None if not found
        """
        try:
            url = urljoin(self.BASE_URL, self.PROFILES_ENDPOINT)
            response = self._session.get(url, timeout=self.timeout)

            if response.status_code != 200:
                logger.error(f"Failed to get profile: HTTP {response.status_code}")
                return None

            profiles = response.json()

            # Find personal profile (usually the first one)
            for profile in profiles:
                if profile.get("type") == "personal":
                    return profile.get("id")

            # Fallback to any profile
            if profiles:
                return profiles[0].get("id")

            return None

        except Exception as e:
            logger.error(f"Error getting profile ID: {e}")
            return None

    def close(self):
        """Close the session and clean up resources."""
        if self._session:
            try:
                self._session.close()
            except:
                pass

    def __enter__(self):
        """Support for context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context manager exit."""
        self.close()
