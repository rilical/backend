"""
Placid provider integration module.

This module implements the Placid provider for retrieving remittance
exchange rates and fees.
"""

import datetime
import logging
import re
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

import requests

from providers.base.provider import RemittanceProvider
from providers.utils.country_currency_standards import (
    normalize_country_code,
    validate_corridor,
)

from .exceptions import (
    PlacidApiError,
    PlacidConnectionError,
    PlacidCorridorUnsupportedError,
    PlacidError,
    PlacidResponseError,
)
from .mapping import (
    CORRIDOR_TO_ISO,
    CURRENCY_TO_CORRIDOR,
    get_corridor_from_currency,
    get_iso_codes_from_corridor,
    get_supported_destination_countries,
    get_supported_destination_currencies,
    get_supported_source_countries,
    get_supported_source_currencies,
)

logger = logging.getLogger(__name__)


class PlacidProvider(RemittanceProvider):
    """
    Aggregator-ready Placid Provider Integration WITHOUT any mock-data fallback.

    Provides methods to fetch exchange rates and quotes from Placid's internal
    corridors. If a corridor is unsupported or an error occurs, returns an error.
    """

    BASE_URL = "https://www.placid.net"
    ENDPOINT = "/conf/sqls/pstRqstNS.php"

    # Default payment/delivery methods and estimated delivery time (minutes)
    DEFAULT_PAYMENT_METHOD = "bank"
    DEFAULT_DELIVERY_METHOD = "bank"
    DEFAULT_DELIVERY_TIME = 1440  # 24 hours in minutes

    def __init__(self, name="placid", **kwargs):
        """
        Initialize the Placid provider.
        """
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()

        # Default headers to mimic typical browser traffic
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/18.3 Safari/605.1.15"
                ),
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        )

        self.logger = logging.getLogger(f"providers.{name}")

    def standardize_response(
        self, raw_result: Dict[str, Any], provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator consumption.

        Follows the structure defined in RemittanceProvider base class
        to ensure consistent response format across all providers.
        """
        # Ensure required keys exist with proper formatting
        output = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("source_currency", "").upper(),
            "destination_amount": raw_result.get("receive_amount", 0.0),
            "destination_currency": raw_result.get("destination_currency", "").upper(),
            "exchange_rate": raw_result.get("exchange_rate"),
            "fee": raw_result.get("fee", 0.0),
            "payment_method": raw_result.get("payment_method", self.DEFAULT_PAYMENT_METHOD),
            "delivery_method": raw_result.get("delivery_method", self.DEFAULT_DELIVERY_METHOD),
            "delivery_time_minutes": raw_result.get(
                "delivery_time_minutes", self.DEFAULT_DELIVERY_TIME
            ),
            "timestamp": raw_result.get("timestamp", datetime.datetime.now().isoformat()),
        }

        if provider_specific_data and "raw_response" in raw_result:
            output["raw_response"] = raw_result["raw_response"]

        return output

    def get_exchange_rate_for_corridor(
        self, corridor_val: str, rndval: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal method that calls Placid's POST endpoint to fetch the corridor info.
        If the corridor is unsupported or an error occurs, returns an error response.
        No fallback to mock data is provided.
        """
        if not corridor_val:
            return {
                "success": False,
                "corridor_val": corridor_val,
                "rate": 0.0,
                "error_message": "No corridor specified",
            }

        corridor_val = corridor_val.strip().upper()
        # If no rndval given, use a timestamp
        if not rndval:
            rndval = str(int(time.time() * 1000))

        # Get the ISO currency code for this corridor for error messaging
        currency_code = None
        if corridor_val in CORRIDOR_TO_ISO:
            currency_code = CORRIDOR_TO_ISO[corridor_val]["currency"]
        else:
            # If corridor is not recognized, treat corridor_val as currency
            currency_code = corridor_val
            logger.warning(
                f"Using corridor_val {corridor_val} as currency code (not found in mapping)"
            )

        # Prepare query params
        query_params = {
            "TaskType": "ChgContIndx",
            "Val1": corridor_val,
            "Val2": "NIL",
            "Val3": "NIL",
            "Val4": "NIL",
            "Val5": "NIL",
            "Val6": "NIL",
        }
        data = {"rndval": rndval}

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Accept": "*/*",
            "Sec-Fetch-Site": "same-origin",
            "Origin": "https://www.placid.net",
            "Referer": "https://www.placid.net/",
        }

        try:
            logger.info(
                f"Requesting Placid corridor info for {corridor_val} with URL: {url}, params: {query_params}"
            )
            resp = self.session.post(
                url, params=query_params, data=data, headers=headers, timeout=15
            )
            resp.raise_for_status()
            content = resp.text
            logger.debug(f"Placid response for {corridor_val}: {content}")

            # Check corridor presence
            if corridor_val not in content:
                # Might be an unsupported corridor or changed internal logic
                if "|//|" in content:
                    # Possibly a generic response with no specific corridor info
                    logger.warning(
                        f"Corridor code {corridor_val} not found in response, but pipe-delimited data exists"
                    )
                    return {
                        "success": False,
                        "corridor_val": corridor_val,
                        "rate": 0.0,
                        "raw_response": content,
                        "error_message": f"No specific corridor data for {corridor_val}",
                    }
                else:
                    logger.error(f"Corridor {corridor_val} not found in response: {content}")
                    raise PlacidCorridorUnsupportedError(
                        f"Corridor {corridor_val} not found in response"
                    )

            # Parse pipe-delimited response
            # Format typically: COUNTRY_CODE|//|COUNTRY_NAME|//|CURRENCY|//|OTHER_DATA|//|...|//|RATE|//|...
            if "|//|" in content:
                parts = content.split("|//|")

                # Look for rate in the parts
                for i, part in enumerate(parts):
                    # Try to find a number that could be an exchange rate (typically after PLAC marker)
                    if i > 0 and "PLAC" in parts[i - 1]:
                        try:
                            # Extract the first number after PLAC
                            rate_match = re.search(r"(\d+[\.,]?\d*)", part)
                            if rate_match:
                                rate_str = rate_match.group(1).replace(",", ".")
                                rate = float(rate_str)
                                logger.info(
                                    f"Successfully extracted rate {rate} for {corridor_val} from pipe-delimited data"
                                )
                                return {
                                    "success": True,
                                    "corridor_val": corridor_val,
                                    "rate": rate,
                                    "raw_response": content,
                                }
                        except Exception as e:
                            logger.warning(f"Error parsing rate from part {part}: {str(e)}")

            # No rate found in response
            logger.error(f"No rate found in response for {corridor_val}")
            raise PlacidResponseError(f"Failed to extract rate from response: {content[:200]}")

        except requests.RequestException as e:
            logger.error(f"Connection error when fetching rate for {corridor_val}: {str(e)}")
            raise PlacidConnectionError(f"Connection error: {str(e)}")

        except PlacidError as e:
            logger.error(f"Placid provider error for {corridor_val}: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching rate for {corridor_val}: {str(e)}")
            raise PlacidApiError(f"API error: {str(e)}")

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
        Get a standardized quote for money transfer between currencies.

        This implements the abstract method from RemittanceProvider.
        """
        source_currency = source_currency.upper()
        dest_currency = dest_currency.upper()
        source_country = normalize_country_code(source_country)
        dest_country = normalize_country_code(dest_country)

        local_res = {
            "success": False,
            "source_currency": source_currency,
            "destination_currency": dest_currency,
            "send_amount": float(amount),
            "exchange_rate": 0.0,
            "receive_amount": 0.0,
            "error_message": None,
            "payment_method": payment_method or self.DEFAULT_PAYMENT_METHOD,
            "delivery_method": delivery_method or self.DEFAULT_DELIVERY_METHOD,
            "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Basic validations
        if amount <= 0:
            local_res["error_message"] = "Invalid amount: must be > 0"
            return self.standardize_response(local_res)

        # Enhanced corridor validation with better country support
        # Special case handling for EUR destination currency - all Eurozone countries valid
        if dest_currency == "EUR" and dest_country in [
            "AT",
            "BE",
            "DE",
            "ES",
            "EE",
            "FI",
            "FR",
            "GR",
            "IE",
            "IT",
            "LT",
            "LU",
            "LV",
            "MT",
            "NL",
            "PT",
            "SK",
            "SI",
            "CY",
            "HR",
        ]:
            # Eurozone country with EUR is valid - skip specific validation
            pass
        else:
            # Use generic validation first to ensure country codes are valid
            is_valid, error_message = validate_corridor(
                source_country=source_country,
                source_currency=source_currency,
                dest_country=dest_country,
                dest_currency=dest_currency,
            )

            if not is_valid:
                local_res["error_message"] = error_message
                return self.standardize_response(local_res)

            # Now check if source country is specifically supported by Placid
            valid_source_countries = get_supported_source_countries()
            if source_country not in valid_source_countries:
                local_res["error_message"] = f"Unsupported source country: {source_country}"
                return self.standardize_response(local_res)

        # Check if source currency is supported by Placid
        valid_source_currencies = get_supported_source_currencies()
        if source_currency not in valid_source_currencies:
            local_res["error_message"] = (
                f"Unsupported source currency: {source_currency}. "
                f"Supported are: {', '.join(valid_source_currencies)}"
            )
            return self.standardize_response(local_res)

        # Derive corridor from destination currency using Placid-specific mapping
        corridor_val = get_corridor_from_currency(dest_currency)
        if not corridor_val:
            # Not recognized
            local_res[
                "error_message"
            ] = f"Unsupported destination currency {dest_currency} for Placid"
            return self.standardize_response(local_res)

        # Get rate
        try:
            corridor_res = self.get_exchange_rate_for_corridor(corridor_val=corridor_val)
            if not corridor_res["success"]:
                local_res["error_message"] = corridor_res.get(
                    "error_message", "Unknown corridor error"
                )
                return self.standardize_response(local_res)

            rate = corridor_res.get("rate", 0.0)
            if rate <= 0:
                local_res["error_message"] = corridor_res.get(
                    "error_message", "No positive rate found"
                )
                return self.standardize_response(local_res)

            # Success
            local_res["exchange_rate"] = rate
            local_res["receive_amount"] = float(amount) * rate
            local_res["success"] = True

            # Apply standardization and return
            return self.standardize_response(local_res)

        except PlacidError as e:
            local_res["error_message"] = str(e)
            return self.standardize_response(local_res)
        except Exception as e:
            logger.error(f"Unexpected error in get_quote: {e}")
            local_res["error_message"] = f"Unexpected error: {str(e)}"
            return self.standardize_response(local_res)

    def get_exchange_rate(
        self, send_amount: Decimal, send_currency: str, target_currency: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy method for getting exchange rate - convert to standardized quote format.

        This method is being kept for backward compatibility. For new code,
        use get_quote instead which provides the standardized response.
        """
        # Derive countries from currencies if not provided
        source_country = kwargs.get(
            "source_country", "US"
        )  # Default to US for backward compatibility
        dest_country = kwargs.get("dest_country")

        # Try to find destination country from target currency
        if not dest_country:
            corridor = get_corridor_from_currency(target_currency)
            if corridor and corridor in CORRIDOR_TO_ISO:
                dest_country = CORRIDOR_TO_ISO[corridor]["country"]

        # If still not found, use a placeholder
        if not dest_country:
            dest_country = "XX"  # Placeholder for unknown

        # Call the standardized get_quote method
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            dest_currency=target_currency,
            source_country=source_country,
            dest_country=dest_country,
            payment_method=kwargs.get("payment_method"),
            delivery_method=kwargs.get("delivery_method"),
        )

    def get_supported_countries(self) -> List[str]:
        """Return list of supported countries in ISO alpha-2 format."""
        source_countries = get_supported_source_countries()
        dest_countries = get_supported_destination_countries()
        return sorted(list(set(source_countries + dest_countries)))

    def get_supported_currencies(self) -> List[str]:
        """Return list of supported currencies in ISO format."""
        source_currencies = get_supported_source_currencies()
        dest_currencies = get_supported_destination_currencies()
        return sorted(list(set(source_currencies + dest_currencies)))

    def close(self):
        """Close the session if it's open."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
