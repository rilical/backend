"""
XE Money Transfer (https://www.xe.com/send-money/) integration module for retrieving quotes
and exchange rates.

This module provides an aggregator-ready integration for XE Money Transfer with no fallback or mock data.
If any API call or parsing fails, it returns a standardized aggregator result with success=false.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from ..base.provider import RemittanceProvider
from ..utils.country_currency_standards import get_default_currency_for_country
from .currency_mapping import (
    XE_SUPPORTED_CORRIDORS,
    get_xe_currency_for_country,
    is_xe_corridor_supported,
)
from .exceptions import (
    XEApiError,
    XEConnectionError,
    XECorridorUnsupportedError,
    XEError,
    XEParsingError,
    XEQuoteError,
    XERateLimitError,
    XEResponseError,
    XEValidationError,
)

logger = logging.getLogger(__name__)


class XEProvider(RemittanceProvider):
    """
    Aggregator-ready XE integration with no fallback or mock data.

    Returns aggregator-standard fields:
      {
        "provider_id": "XE",
        "success": True/False,
        "error_message": "...",
        "send_amount": float,
        "source_currency": str,
        "destination_amount": float,
        "destination_currency": str,
        "exchange_rate": float,
        "fee": float,
        "payment_method": str,
        "delivery_method": str,
        "delivery_time_minutes": int,
        "timestamp": "...",
        "raw_response": {...}
      }
    """

    API_BASE_URL = "https://www.xe.com"
    QUOTES_API_URL = "https://launchpad-api.xe.com/v2/quotes"

    # Reference to supported corridors from currency_mapping.py
    SUPPORTED_CORRIDORS = XE_SUPPORTED_CORRIDORS

    def __init__(self, **kwargs):
        super().__init__(name="XE", base_url=self.API_BASE_URL, **kwargs)
        self.session = requests.Session()
        # Set typical headers based on the real curl example
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
                ),
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://www.xe.com",
                "Referer": "https://www.xe.com/",
                "Priority": "u=3, i",
                "X-Correlation-ID": f"XECOM-{uuid.uuid4()}",
                "deviceid": str(uuid.uuid4()),
            }
        )

    def standardize_response(self, local_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local result into aggregator-standard shape:
        - If local_result["success"] is False, just return minimal aggregator error shape
        - Else return aggregator success shape
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        if not local_result.get("success", False):
            # For errors, return a standardized error response
            # Note: For error responses, we only include minimal fields required by the aggregator
            return {
                "provider_id": "XE",
                "success": False,
                "error_message": local_result.get("error_message") or "Unknown XE error",
            }

        # For success responses, return a fully standardized response with all aggregator fields
        standard_response = {
            "provider_id": "XE",
            "success": True,
            "error_message": None,
            "send_amount": local_result.get("send_amount", 0.0),
            "source_currency": str(local_result.get("send_currency", "")).upper(),
            "destination_amount": local_result.get("receive_amount", 0.0),
            "destination_currency": str(local_result.get("receive_currency", "")).upper(),
            "exchange_rate": local_result.get("exchange_rate", 0.0),
            "fee": local_result.get("fee", 0.0),
            "payment_method": local_result.get("payment_method", "BANK_TRANSFER"),
            "delivery_method": local_result.get("delivery_method", "BANK_TRANSFER"),
            "delivery_time_minutes": self._parse_delivery_time(local_result.get("delivery_time")),
            "timestamp": now_iso,
        }

        # If we have rate info (for exchange_rate responses), include it
        # Some aggregator implementations need both "rate" and "exchange_rate"
        if local_result.get("exchange_rate") is not None:
            standard_response["rate"] = local_result.get("exchange_rate")

        # For get_exchange_rate compatibility, also include target_currency
        if local_result.get("receive_currency"):
            standard_response["target_currency"] = str(
                local_result.get("receive_currency", "")
            ).upper()

        # Include the raw response data if available
        if local_result.get("raw_data"):
            standard_response["raw_response"] = local_result.get("raw_data")

        return standard_response

    def _parse_delivery_time(self, time_str: Optional[str]) -> int:
        """
        Convert a textual time like 'Within 1-2 days' to integer minutes if possible.
        Defaults to 1440 (1 day) if not parseable.
        """
        if not time_str:
            return 1440

        t = time_str.lower()
        import re

        # Look for "1-2 days"
        d_match = re.search(r"(\d+)\s*-\s*(\d+)\s*day", t)
        if d_match:
            # average
            d1 = int(d_match.group(1))
            d2 = int(d_match.group(2))
            return int(((d1 + d2) / 2) * 24 * 60)

        # Look for "3 business days"
        d_match2 = re.search(r"(\d+)\s*(?:business\s*)?day", t)
        if d_match2:
            dd = int(d_match2.group(1))
            return dd * 24 * 60

        # Hours
        h_match = re.search(r"(\d+)\s*hour", t)
        if h_match:
            hh = int(h_match.group(1))
            return hh * 60

        # Minutes
        m_match = re.search(r"(\d+)\s*minute", t)
        if m_match:
            return int(m_match.group(1))

        # Instant or same day or "Takes minutes"
        if "instant" in t or "same day" in t or "takes minutes" in t:
            return 60

        # Within 24 hours
        if "within 24 hours" in t:
            return 24 * 60

        # fallback
        return 1440

    def _build_fail(self, msg: str) -> Dict[str, Any]:
        """Helper to build a dict with success=false and error_message=msg."""
        return {"success": False, "error_message": msg}

    def is_corridor_supported(self, send_currency: str, receive_country: str) -> bool:
        """Check if a specific corridor is supported by XE."""
        return is_xe_corridor_supported(send_currency, receive_country)

    def _get_receive_currency(self, country: str) -> Optional[str]:
        """Convert a country code to the corresponding currency code."""
        return get_xe_currency_for_country(country)

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, receive_country: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Aggregator method: get an XE quote with no fallback or mock data.

        If any error occurs, returns aggregator shape with success=false.
        Otherwise returns aggregator success data with all required fields.

        Args:
            send_amount: Amount to send in source currency
            send_currency: Source currency code (e.g., "USD")
            receive_country: Destination country code (e.g., "MX")
            **kwargs: Additional parameters including user_country

        Returns:
            Standardized response dictionary with all aggregator fields
        """
        logger.info(
            f"Getting XE exchange rate for {send_currency} to {receive_country} (Amount: {send_amount})"
        )

        local_fail = self._build_fail("")

        # Basic validation
        if not send_currency or not receive_country:
            local_fail["error_message"] = "Missing send_currency or receive_country"
            return self.standardize_response(local_fail)
        if send_amount <= 0:
            local_fail["error_message"] = f"Invalid send_amount: {send_amount}"
            return self.standardize_response(local_fail)

        # Convert country -> currency
        rcur = self._get_receive_currency(receive_country)
        if not rcur:
            local_fail[
                "error_message"
            ] = f"Unsupported corridor: {send_currency}->{receive_country}"
            return self.standardize_response(local_fail)

        # Format payload based on the real curl example
        payload = {
            "sellCcy": send_currency.upper(),
            "buyCcy": rcur,
            "userCountry": kwargs.get("user_country", "US"),
            "amount": float(send_amount),
            "fixedCcy": send_currency.upper(),
            "countryTo": receive_country.upper(),
        }

        local_ok = {
            "success": True,
            "send_amount": float(send_amount),
            "send_currency": send_currency.upper(),
            "receive_currency": rcur,
            "receive_amount": 0.0,
            "exchange_rate": 0.0,
            "fee": 0.0,
            "delivery_time": "Unknown",
        }

        try:
            logger.info(f"Requesting XE quote: {payload}")
            resp = self.session.post(self.QUOTES_API_URL, json=payload, timeout=30)

            # For debugging - print the response content before raising for status
            logger.debug(f"XE API response status: {resp.status_code}")
            logger.debug(f"XE API response content: {resp.text[:500]}...")

            # Instead of raising for status, handle non-200 responses gracefully
            if resp.status_code != 200:
                logger.error(
                    f"XE API returned non-200 status: {resp.status_code}, response: {resp.text[:200]}..."
                )
                local_fail["error_message"] = f"XE API error: {resp.status_code} response"
                return self.standardize_response(local_fail)

            data = resp.json()
        except requests.RequestException as re:
            logger.error(f"XE request error: {re}", exc_info=True)
            local_fail["error_message"] = f"XE request error: {str(re)}"
            return self.standardize_response(local_fail)
        except ValueError as ve:
            logger.error(f"XE JSON parse error: {ve}", exc_info=True)
            local_fail["error_message"] = f"XE JSON parse error: {str(ve)}"
            return self.standardize_response(local_fail)

        # Parse data
        quote_obj = data.get("quote")
        if not quote_obj:
            logger.error(f"No 'quote' in XE response: {data}")
            local_fail["error_message"] = "Invalid XE response, missing 'quote'"
            return self.standardize_response(local_fail)

        # Check for quote status and error messages
        quote_status = quote_obj.get("quoteStatus")
        if quote_status and quote_status != "Quoted":
            error_msgs = quote_obj.get("errorMessages", {})
            if error_msgs:
                # Format all error messages into a single string
                error_txt = "; ".join([f"{k}: {v}" for k, v in error_msgs.items()])
                local_fail[
                    "error_message"
                ] = f"XE quote failed with status {quote_status}: {error_txt}"
            else:
                local_fail["error_message"] = f"XE quote failed with status {quote_status}"
            return self.standardize_response(local_fail)

        indiv_quotes = quote_obj.get("individualQuotes", [])
        if not indiv_quotes:
            logger.error(f"No 'individualQuotes' in XE response: {quote_obj}")
            local_fail["error_message"] = "No individual quotes in XE response"
            return self.standardize_response(local_fail)

        # pick default or first enabled
        chosen = None
        for iq in indiv_quotes:
            if iq.get("isDefault") and iq.get("isEnabled"):
                chosen = iq
                break
        if not chosen:
            for iq in indiv_quotes:
                if iq.get("isEnabled"):
                    chosen = iq
                    break

        if not chosen:
            logger.error("No valid (default/enabled) quote found in XE response.")
            local_fail["error_message"] = "No valid quote found in 'individualQuotes'"
            return self.standardize_response(local_fail)

        # Extract details
        try:
            rate_val = float(chosen.get("rate", 0.0))
            buy_amt_str = chosen.get("buyAmount", "0").replace(",", "")
            fee_str = chosen.get("transferFee", "0").replace(",", "")
            payment_fee_str = chosen.get("paymentMethodFee", "0").replace(",", "")

            # Get delivery information
            delivery_time = chosen.get("leadTime", "Unknown")
            settlement_method = chosen.get("settlementMethod", "Unknown")
            delivery_method = chosen.get("deliveryMethod", "Unknown")

            buy_amt = float(buy_amt_str)
            fee_val = float(fee_str) + float(payment_fee_str)

            # Map settlement and delivery methods to standard payment and delivery methods
            payment_method_map = {
                "DirectDebit": "BANK_TRANSFER",
                "DebitCard": "DEBIT_CARD",
                "CreditCard": "CREDIT_CARD",
                "BankTransfer": "BANK_TRANSFER",
            }

            delivery_method_map = {
                "BankAccount": "BANK_TRANSFER",
                "CashPayout": "CASH_PICKUP",
                "MobileWallet": "MOBILE_MONEY",
                "FundsOnBalance": "MOBILE_MONEY",
            }

            payment_method = payment_method_map.get(settlement_method, "BANK_TRANSFER")
            actual_delivery_method = delivery_method_map.get(delivery_method, "BANK_TRANSFER")

            local_ok["exchange_rate"] = rate_val
            local_ok["receive_amount"] = buy_amt
            local_ok["fee"] = fee_val
            local_ok["delivery_time"] = delivery_time
            local_ok["payment_method"] = payment_method
            local_ok["delivery_method"] = actual_delivery_method
            local_ok["raw_data"] = data  # store for aggregator
        except Exception as e:
            logger.error(f"Error extracting chosen quote fields: {e}", exc_info=True)
            local_fail["error_message"] = f"Error extracting quote fields: {str(e)}"
            return self.standardize_response(local_fail)

        # Return aggregator success
        return self.standardize_response(local_ok)

    def get_quote(
        self,
        amount=None,
        source_currency=None,
        dest_currency=None,
        source_country=None,
        dest_country=None,
        target_country=None,
        send_amount=None,
        send_currency=None,
        receive_country=None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Alias to get_exchange_rate with aggregator shape.

        Accepts multiple parameter naming conventions for maximum compatibility:
        - Standard parameters: amount, source_currency, dest_country
        - Alias parameters: send_amount, send_currency, receive_country/target_country
        """
        # Use amount if provided, otherwise send_amount
        final_amount = amount if amount is not None else send_amount
        if final_amount is None:
            raise ValueError("Amount is required. Provide 'amount' or 'send_amount'.")

        # Use source_currency if provided, otherwise send_currency
        final_source_currency = source_currency if source_currency is not None else send_currency
        if final_source_currency is None:
            raise ValueError(
                "Source currency is required. Provide 'source_currency' or 'send_currency'."
            )

        # Use target_country if provided, otherwise dest_country, otherwise receive_country
        final_target_country = target_country
        if final_target_country is None:
            final_target_country = dest_country
        if final_target_country is None:
            final_target_country = receive_country
        if final_target_country is None:
            raise ValueError(
                "Target country is required. Provide 'target_country', 'dest_country', or 'receive_country'."
            )

        # Use logging module directly instead of self.logger
        logging.getLogger("apps.providers.xe.integration").info(
            f"get_quote called with normalized parameters: amount={final_amount}, "
            f"source_currency={final_source_currency}, target_country={final_target_country}"
        )

        # Call get_exchange_rate with the properly mapped parameters
        return self.get_exchange_rate(
            send_amount=final_amount,
            send_currency=final_source_currency,
            receive_country=final_target_country,
            **kwargs,
        )

    def close(self):
        """Close the session to release resources."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Support for context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context manager exit."""
        self.close()
