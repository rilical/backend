"""
Dahabshiil provider integration module.
"""

import logging
import requests
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime

from apps.providers.base.provider import RemittanceProvider
from .exceptions import DahabshiilApiError

logger = logging.getLogger(__name__)

class DahabshiilProvider(RemittanceProvider):
    """
    Provider implementation for Dahabshiil, an international remittance service.
    """

    BASE_URL = "https://apigw-us.dahabshiil.com/remit/transaction"
    GET_CHARGES_ENDPOINT = "/get-charges-anonymous"

    def __init__(self, name="dahabshiil"):
        """Initialize the Dahabshiil provider."""
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.3 Safari/605.1.15"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Origin": "https://www.dahabshiil.com"
        })
        
        self.logger = logging.getLogger(f"providers.{name}")

    def get_delivery_methods(
        self,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str
    ) -> List[Dict[str, Any]]:
        """
        Return the list of delivery methods (bank deposit, mobile wallet, etc.).
        For simplicity, we'll let the aggregator handle method selection.
        """
        return []

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
        Get a quote for a money transfer from Dahabshiil.

        Args:
            amount: Amount to send (Decimal)
            source_currency: Source currency code (e.g., "USD")
            dest_currency: Destination currency code (e.g., "KES")
            source_country: Source country code (e.g., "US")
            dest_country: Destination country code (e.g., "KE")
            delivery_method: Method of delivery (ignored here)
            payment_method: Method of payment (ignored here)
            **kwargs: Additional parameters (e.g. include_raw=True)

        Returns:
            Dictionary containing aggregator-standard quote information.
        """
        # Local dictionary for initial result
        quote_result = {
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
        }
        
        try:
            # Build query params as you described for the GET request
            params = {
                "source_country_code": source_country.upper(),
                "destination_country_iso2": dest_country.upper(),
                "amount_type": "SOURCE",
                "amount": str(amount),
                "destination_currency": dest_currency.upper(),
                "type": "Mobile Transfer"  # default to "Mobile Transfer"
            }
            
            self.logger.info(f"Dahabshiil request: {params}")

            # Perform the GET request
            response = self.session.get(
                f"{self.BASE_URL}{self.GET_CHARGES_ENDPOINT}",
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.logger.info(f"Dahabshiil response: {data}")

            # Example success structure: 
            # {"status": "Success", "code": 200, "data": {"charges": {...}}}
            if (
                data.get("status") == "Success"
                and data.get("code") == 200
                and "data" in data
                and "charges" in data["data"]
            ):
                charges = data["data"]["charges"]

                send_amount = Decimal(str(charges.get("source_amount", amount)))
                exchange_rate = Decimal(str(charges.get("rate", 0)))
                fee = Decimal(str(charges.get("commission", 0)))
                receive_amount = Decimal(str(charges.get("destination_amount", 0)))
                total_cost = send_amount + fee

                quote_result.update({
                    "success": True,
                    "exchange_rate": float(exchange_rate),
                    "fee": float(fee),
                    "destination_amount": float(receive_amount),
                    "total_cost": float(total_cost),
                })

                # If aggregator wants raw response for debugging
                if kwargs.get("include_raw", False):
                    quote_result["raw_response"] = data
            else:
                # Fallback error if not success or missing data
                error_msg = data.get("message", "Unknown error from Dahabshiil")
                quote_result["error_message"] = error_msg

        except requests.exceptions.RequestException as exc:
            error_msg = f"Network/Request error: {exc}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg

        except (ValueError, KeyError, TypeError) as exc:
            error_msg = f"Response parsing error: {exc}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg

        except Exception as exc:
            error_msg = f"Unexpected error: {exc}"
            self.logger.error(error_msg)
            quote_result["error_message"] = error_msg

        # If aggregator specifically wants the unstandardized data with raw...
        if kwargs.get("include_raw", False):
            # Return the aggregator-ready dictionary but let them see raw
            return self.standardize_response(
                raw_result=quote_result,
                provider_specific_data=True
            )
        else:
            # Return aggregator-ready dictionary
            return self.standardize_response(raw_result=quote_result)

    def get_exchange_rate(
        self,
        source_currency: str,
        target_currency: str,
        source_country: str,
        target_country: str,
        amount: Decimal = Decimal("1000")
    ) -> Dict[str, Any]:
        """
        Get current exchange rate for a currency pair using `get_quote`.

        The aggregator typically expects:
        {
          "success": bool,
          "error_message": str|None,
          "source_currency": ...,
          "target_currency": ...,
          "rate": float|None,
          "fee": float|None,
          "timestamp": iso-string,
          "provider_id": "dahabshiil"
        }
        """
        try:
            # We'll call get_quote with include_raw=True, then re-map fields
            quote = self.get_quote(
                amount=amount,
                source_currency=source_currency,
                dest_currency=target_currency,
                source_country=source_country,
                dest_country=target_country,
                include_raw=True
            )
            # Now build a minimal dict with aggregator's expected get_exchange_rate fields
            # note aggregator looks for "rate" not "exchange_rate"
            rate_info = {
                "success": quote.get("success", False),
                "error_message": quote.get("error_message"),
                "source_currency": quote.get("source_currency", ""),
                "target_currency": quote.get("destination_currency", ""),
                "rate": quote.get("exchange_rate"),
                "fee": quote.get("fee"),
                # aggregator also expects a timestamp
                "timestamp": datetime.now().isoformat()
            }
            return self.standardize_response(raw_result=rate_info)
        except Exception as exc:
            logger.error(f"Failed to get exchange rate: {exc}", exc_info=True)
            # Return aggregator shape with error
            error_result = {
                "success": False,
                "error_message": str(exc),
                "source_currency": source_currency,
                "target_currency": target_currency,
                "rate": None,
                "fee": None,
                "timestamp": datetime.now().isoformat()
            }
            return self.standardize_response(raw_result=error_result)

    def standardize_response(self, raw_result=None, provider_specific_data=False) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator usage.

        We pass in raw_result containing keys like:
          - "success", "error_message", "send_amount", "source_currency", ...
          - "exchange_rate", "fee", "destination_amount", "total_cost", ...
          - "rate" (for get_exchange_rate)
          - Possibly "raw_response" if include_raw=True
        """
        if raw_result is None:
            raw_result = {}

        # aggregator expects "rate" in get_exchange_rate responses,
        # plus "exchange_rate" for quote, so we'll unify them:
        # "rate" = raw_result.get("exchange_rate") or raw_result.get("rate")
        final_rate = raw_result.get("rate")
        if final_rate is None:  # fallback
            final_rate = raw_result.get("exchange_rate")

        # aggregator also wants "target_currency" instead of just "destination_currency"
        final_target_currency = raw_result.get("target_currency")
        if not final_target_currency:
            final_target_currency = raw_result.get("destination_currency", "")

        # Build the aggregator-standard dictionary
        standardized = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),

            # For quotes
            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("source_currency", ""),
            "destination_amount": raw_result.get("destination_amount"),
            "destination_currency": raw_result.get("destination_currency", ""),
            "exchange_rate": raw_result.get("exchange_rate"),

            # For aggregator's get_exchange_rate test
            "rate": final_rate,
            "target_currency": final_target_currency,

            "fee": raw_result.get("fee"),
            "payment_method": raw_result.get("payment_method"),
            "delivery_method": raw_result.get("delivery_method"),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes"),
            "timestamp": raw_result.get("timestamp", datetime.now().isoformat()),
        }

        # Include raw response if requested
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