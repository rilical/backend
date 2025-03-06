"""
InstaRem Money Transfer Integration (Aggregator-Ready)

This module implements the integration with InstaRem for retrieving
money transfer quotes and returning standardized data for an aggregator.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from apps.providers.instarem.exceptions import InstaRemApiError

logger = logging.getLogger(__name__)

class InstaRemProvider(RemittanceProvider):
    """
    Integration with InstaRem's public transaction computed-value endpoint.
    Provides aggregator-ready responses.
    
    Example usage:
        provider = InstaRemProvider()
        quote = provider.get_quote(
            amount=Decimal("1000.00"),
            source_currency="USD",
            dest_currency="INR",
            source_country="US",
            dest_country="IN"
        )
    """

    BASE_URL = "https://www.instarem.com"
    PAYMENT_METHOD_ENDPOINT = "/api/v1/public/payment-method/fee"
    QUOTE_ENDPOINT = "/api/v1/public/transaction/computed-value"
    
    # Example: Delivery methods for aggregator usage (customize as needed)
    DELIVERY_METHODS = {
        "BankDeposit": {
            "id": 58,
            "name": "Bank Deposit",
            "description": "Direct deposit to bank account",
            "estimated_minutes": 60
        },
        "InstantTransfer": {
            "id": 95,
            "name": "Instant Transfer",
            "description": "Instant deposit to bank account",
            "estimated_minutes": 15
        },
        "PesoNet": {
            "id": 96,
            "name": "PesoNet",
            "description": "PesoNet transfer (Philippines)",
            "estimated_minutes": 120
        }
    }

    def __init__(self, name="instarem"):
        """Initialize the InstaRem provider with aggregator-friendly defaults."""
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()

        # Set browser-like headers
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.3 Safari/605.1.15"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.instarem.com/en-us/",
            "X-Requested-With": "XMLHttpRequest",
            "Priority": "u=3, i"
        })

        # Setup retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.logger = logging.getLogger(f"providers.{name}")

    def get_delivery_methods(
        self,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str
    ) -> List[Dict[str, Any]]:
        """
        Return a list of delivery methods for aggregator usage.
        Example includes BankDeposit, InstantTransfer, etc.
        """
        methods = []
        for method_key, method_info in self.DELIVERY_METHODS.items():
            methods.append({
                "id": method_info["id"],
                "name": method_info["name"],
                "type": method_key,
                "estimated_minutes": method_info["estimated_minutes"],
                "description": method_info["description"],
                "is_default": (method_key == "BankDeposit")
            })
        return methods

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str,
        dest_country: str,
        delivery_method: Optional[str] = None,
        payment_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a standardized quote for a money transfer from InstaRem.

        Args:
            amount: Decimal, amount to send
            source_currency: source currency code (ISO-4217), e.g. "USD"
            dest_currency: target currency code (ISO-4217), e.g. "INR"
            source_country: Source country code (e.g. "US")
            dest_country: Destination country code (e.g. "IN")
            delivery_method: aggregator passes e.g. "BankDeposit"
            payment_method: aggregator passes e.g. "BankTransfer"
            **kwargs: Additional flags, e.g. include_raw=True

        Returns:
            Dictionary containing standardized aggregator fields
        """
        # Prepare local raw result dict with aggregator-friendly fields
        raw_result = {
            "success": False,
            "send_amount": float(amount),
            "source_currency": source_currency.upper(),
            "destination_currency": dest_currency.upper(),
            "exchange_rate": None,
            "fee": None,
            "destination_amount": None,
            "total_cost": None,
            "error_message": None,
            "delivery_method": delivery_method,
            "payment_method": payment_method,
            "delivery_time_minutes": None  # We'll fill if the API returns an estimate
        }

        try:
            # First, get available payment methods
            payment_params = {
                "source_currency": source_currency.upper(),
                "source_amount": str(amount),
                "destination_currency": dest_currency.upper(),
                "country_code": source_country.upper()
            }
            
            self.logger.info(f"Requesting payment methods from InstaRem with params: {payment_params}")
            
            payment_response = self.session.get(
                f"{self.BASE_URL}{self.PAYMENT_METHOD_ENDPOINT}",
                params=payment_params,
                timeout=30
            )
            payment_response.raise_for_status()
            
            payment_data = payment_response.json()
            self.logger.info(f"InstaRem payment methods response: {payment_data}")
            
            if not payment_data.get("success", False) or not payment_data.get("data"):
                error_msg = payment_data.get("message", "Failed to get payment methods from InstaRem")
                raw_result["error_message"] = error_msg
                return self.standardize_response(raw_result, provider_specific_data=kwargs.get("include_raw", False))
            
            # Use the first payment method by default (usually ACH/Direct Debit - key 58)
            instarem_bank_account_id = payment_data["data"][0]["key"]
            
            # Prepare quote parameters
            quote_params = {
                "source_currency": source_currency.upper(),
                "destination_currency": dest_currency.upper(),
                "instarem_bank_account_id": instarem_bank_account_id,
                "country_code": source_country.upper(),
                "source_amount": str(amount)
            }

            self.logger.info(f"Requesting quote from InstaRem with params: {quote_params}")

            # GET from the InstaRem QUOTE_ENDPOINT with query parameters (not POST with JSON)
            response = self.session.get(
                f"{self.BASE_URL}{self.QUOTE_ENDPOINT}",
                params=quote_params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info(f"InstaRem quote response: {data}")

            # If aggregator wants to see the raw API data
            if kwargs.get("include_raw", False):
                raw_result["raw_response"] = data

            # Check if the API returned an error or success is false
            if not data.get("success", False):
                raw_result["error_message"] = data.get("message", "Unknown error from InstaRem")
                return self.standardize_response(raw_result, provider_specific_data=kwargs.get("include_raw", False))

            # Extract main data - now comes in a nested 'data' object
            quote_data = data.get("data", {})
            if not quote_data:
                raw_result["error_message"] = "No quote data returned from InstaRem"
                return self.standardize_response(raw_result, provider_specific_data=kwargs.get("include_raw", False))

            # Parse exchange values from the actual response structure
            fx_rate = Decimal(str(quote_data.get("fx_rate", 0)))
            
            # Fee might be a combination of multiple fee types
            transaction_fee = Decimal(str(quote_data.get("transaction_fee_amount", 0)))
            payment_method_fee = Decimal(str(quote_data.get("payment_method_fee_amount", 0)))
            payout_method_fee = Decimal(str(quote_data.get("payout_method_fee_amount", 0)))
            total_fee = transaction_fee + payment_method_fee + payout_method_fee
            
            destination_amount = Decimal(str(quote_data.get("destination_amount", 0)))
            source_amount = Decimal(str(quote_data.get("gross_source_amount", 0)))

            raw_result["success"] = True
            raw_result["exchange_rate"] = float(fx_rate)
            raw_result["fee"] = float(total_fee)
            raw_result["send_amount"] = float(source_amount)
            raw_result["destination_amount"] = float(destination_amount)
            raw_result["total_cost"] = float(source_amount + total_fee)

            # Delivery time isn't explicitly provided in the response,
            # Could default to a standard value or use delivery method info
            
        except requests.RequestException as exc:
            error_msg = f"Request error: {exc}"
            logger.error(error_msg)
            raw_result["error_message"] = error_msg
        except (ValueError, KeyError, TypeError) as exc:
            error_msg = f"Response parsing error: {exc}"
            logger.error(error_msg)
            raw_result["error_message"] = error_msg
        except Exception as exc:
            error_msg = f"Unexpected error: {exc}"
            logger.error(error_msg)
            raw_result["error_message"] = error_msg

        return self.standardize_response(raw_result, provider_specific_data=kwargs.get("include_raw", False))

    def get_exchange_rate(
        self,
        source_currency: str,
        target_currency: str,
        source_country: str,
        target_country: str,
        amount: Decimal = Decimal("1000")
    ) -> Dict[str, Any]:
        """
        Get aggregator-friendly dictionary with minimal fields for exchange rate tests.
        
        Args:
            source_currency: ISO-4217 currency code (e.g., "USD")
            target_currency: ISO-4217 currency code (e.g., "INR")
            source_country: ISO-3166 country code (e.g., "US")
            target_country: ISO-3166 country code (e.g., "IN")
            amount: Amount to convert (defaults to 1000)
            
        Returns:
            Dictionary with fields: success, error_message, rate, etc.
        """
        try:
            # We'll call get_quote with include_raw=True, then unify fields
            quote = self.get_quote(
                amount=amount,
                source_currency=source_currency,
                dest_currency=target_currency,
                source_country=source_country,
                dest_country=target_country,
                include_raw=True
            )
            # aggregator typically wants "rate" (not just "exchange_rate")
            # We'll build a small dict capturing the essential fields
            rate_info = {
                "success": quote.get("success", False),
                "error_message": quote.get("error_message"),
                "source_currency": quote.get("source_currency", ""),
                "target_currency": quote.get("destination_currency", ""),
                # aggregator expects "rate" to check in tests:
                "rate": quote.get("exchange_rate"),
                "fee": quote.get("fee"),
                "timestamp": datetime.now().isoformat()
            }
            return self.standardize_response(raw_result=rate_info)
        except Exception as exc:
            error_msg = f"Exchange rate error: {exc}"
            logger.error(error_msg)
            return self.standardize_response(raw_result={
                "success": False,
                "error_message": error_msg,
                "source_currency": source_currency.upper(),
                "target_currency": target_currency.upper()
            })

    def standardize_response(self, raw_result: Dict[str, Any], provider_specific_data: bool = False) -> Dict[str, Any]:
        """
        Convert the local raw_result dict into aggregator-standard shape.
        aggregator might check keys like:
          - provider_id
          - success
          - error_message
          - send_amount
          - source_currency
          - destination_amount
          - destination_currency
          - exchange_rate
          - fee
          - rate
          - target_currency
          - timestamp
        """
        # aggregator might want both "exchange_rate" and "rate" to unify references
        # for get_exchange_rate vs get_quote calls:
        final_exchange_rate = raw_result.get("exchange_rate")  # from a quote
        final_rate = raw_result.get("rate")                    # from an exchange rate call
        if final_rate is None:
            final_rate = final_exchange_rate  # fallback

        # aggregator might also want "target_currency" in get_exchange_rate calls
        final_target_currency = raw_result.get("target_currency") or raw_result.get("destination_currency", "")

        # Build the aggregator-standard output
        standardized = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),

            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("source_currency", ""),
            "destination_amount": raw_result.get("destination_amount"),
            "destination_currency": raw_result.get("destination_currency", ""),
            "exchange_rate": final_exchange_rate,

            # aggregator specifically looks for "rate" in get_exchange_rate tests
            "rate": final_rate,
            "target_currency": final_target_currency,

            "fee": raw_result.get("fee"),
            "payment_method": raw_result.get("payment_method"),
            "delivery_method": raw_result.get("delivery_method"),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes"),

            "timestamp": raw_result.get("timestamp", datetime.now().isoformat()),
        }

        # If aggregator wants raw, attach it
        if provider_specific_data and "raw_response" in raw_result:
            standardized["raw_response"] = raw_result["raw_response"]

        return standardized

    def close(self):
        """Close the underlying HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 