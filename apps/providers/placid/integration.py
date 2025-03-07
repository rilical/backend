"""
Placid provider integration module.

This module implements the Placid provider for retrieving remittance
exchange rates and fees.
"""

import logging
import requests
import re
import time
from decimal import Decimal
from typing import Any, Dict, Optional, List

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    PlacidError,
    PlacidConnectionError,
    PlacidApiError,
    PlacidResponseError,
    PlacidCorridorUnsupportedError,
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
    
    # Corridor mappings: corridor code -> { currency, name }
    CORRIDOR_MAPPING = {
        'PAK': {'currency': 'PKR', 'name': 'Pakistan'},
        'IND': {'currency': 'INR', 'name': 'India'},
        'BGD': {'currency': 'BDT', 'name': 'Bangladesh'},
        'PHL': {'currency': 'PHP', 'name': 'Philippines'},
        'NPL': {'currency': 'NPR', 'name': 'Nepal'},
        'LKA': {'currency': 'LKR', 'name': 'Sri Lanka'},
        'IDN': {'currency': 'IDR', 'name': 'Indonesia'},
        'VNM': {'currency': 'VND', 'name': 'Vietnam'},
    }
    
    # Reverse mapping: currency -> corridor code
    CURRENCY_TO_CORRIDOR = {
        'PKR': 'PAK',
        'INR': 'IND',
        'BDT': 'BGD',
        'PHP': 'PHL',
        'NPR': 'NPL',
        'LKR': 'LKA',
        'IDR': 'IDN',
        'VND': 'VNM',
    }

    def __init__(self, name="placid", **kwargs):
        """
        Initialize the Placid provider.
        """
        super().__init__(name=name, base_url=self.BASE_URL)
        self.session = requests.Session()

        # Default headers to mimic typical browser traffic
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.3 Safari/605.1.15"
            ),
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        
        self.logger = logging.getLogger(f"providers.{name}")

    def standardize_response(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local result dictionary into aggregator-friendly keys.
        """
        final_exchange_rate = raw_data.get("exchange_rate", 0.0)
        final_rate = raw_data.get("rate", final_exchange_rate)
        final_target_currency = raw_data.get("destination_currency") or raw_data.get("target_currency")

        standardized = {
            "provider_id": self.name,
            "success": raw_data.get("success", False),
            "error_message": raw_data.get("error_message"),
            
            "send_amount": raw_data.get("send_amount", 0.0),
            "source_currency": raw_data.get("source_currency", "").upper(),
            
            "destination_amount": raw_data.get("receive_amount", 0.0),
            "destination_currency": (raw_data.get("target_currency") or raw_data.get("destination_currency") or "").upper(),
            
            "exchange_rate": final_exchange_rate,
            "fee": raw_data.get("fee", 0.0),
            "timestamp": raw_data.get("timestamp"),
            "rate": final_rate,
            "target_currency": (final_target_currency or "").upper(),
        }
        return standardized

    def get_exchange_rate_for_corridor(
        self,
        corridor_val: str,
        rndval: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal method that calls Placid's POST endpoint to fetch the corridor info.
        """
        if not corridor_val:
            return {
                "success": False,
                "corridor_val": corridor_val,
                "rate": 0.0,
                "error_message": "No corridor specified"
            }
        
        corridor_val = corridor_val.strip().upper()
        # If no rndval given, use a timestamp
        if not rndval:
            rndval = str(int(time.time() * 1000))

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
        try:
            resp = self.session.post(url, params=query_params, data=data, timeout=15)
            resp.raise_for_status()
            content = resp.text

            # Check corridor presence
            if corridor_val not in content:
                # Might be an unsupported corridor or changed internal logic
                if "|//|" in content:
                    # Possibly a generic response with no specific corridor info
                    return {
                        "success": True,
                        "corridor_val": corridor_val,
                        "rate": 0.0,
                        "raw_data": content,
                        "error_message": f"No specific corridor data for {corridor_val}"
                    }
                else:
                    raise PlacidCorridorUnsupportedError(f"Corridor {corridor_val} not found in response")

            # corridor -> currency
            if corridor_val in self.CORRIDOR_MAPPING:
                currency_code = self.CORRIDOR_MAPPING[corridor_val]["currency"]
            else:
                # If corridor is not recognized, treat corridor_val as currency
                currency_code = corridor_val

            # Attempt to parse an exchange rate
            pattern = rf"(\d+[\.,]?\d*)\s*{currency_code}"
            match = re.search(pattern, content)
            if match:
                rate_str = match.group(1).replace(",", "")
                rate = float(rate_str)
                return {
                    "success": True,
                    "corridor_val": corridor_val,
                    "rate": rate,
                    "raw_data": content
                }
            else:
                raise PlacidResponseError(f"Exchange rate for {currency_code} not found in response")

        except requests.RequestException as e:
            raise PlacidConnectionError(f"Connection error to Placid: {str(e)}")
        except PlacidError:
            # re-raise known Placid exceptions
            raise
        except Exception as e:
            raise PlacidApiError(f"Unexpected Placid error: {str(e)}")

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Attempt to get a quote from Placid for amount in source_currency -> target_currency.
        """
        local_res = {
            "success": False,
            "source_currency": source_currency.upper(),
            "target_currency": target_currency.upper(),
            "send_amount": float(amount),
            "exchange_rate": 0.0,
            "receive_amount": 0.0,
            "error_message": None
        }

        # Basic validations
        if amount <= 0:
            local_res["error_message"] = "Invalid amount: must be > 0"
            return local_res
        
        valid_source_currencies = ["USD", "GBP", "EUR", "CAD", "AUD"]
        if local_res["source_currency"] not in valid_source_currencies:
            local_res["error_message"] = (
                f"Unsupported source currency: {local_res['source_currency']}. "
                f"Supported are: {', '.join(valid_source_currencies)}"
            )
            return local_res

        # Derive corridor from target_currency if known
        corridor_val = self.CURRENCY_TO_CORRIDOR.get(local_res["target_currency"])
        if not corridor_val:
            # Not recognized
            local_res["error_message"] = f"Unsupported target currency {local_res['target_currency']} for Placid"
            return local_res

        # Get rate
        try:
            corridor_res = self.get_exchange_rate_for_corridor(corridor_val=corridor_val)
            if not corridor_res["success"]:
                local_res["error_message"] = corridor_res.get("error_message", "Unknown corridor error")
                return local_res
            
            rate = corridor_res.get("rate", 0.0)
            if rate <= 0:
                local_res["error_message"] = corridor_res.get("error_message", "No positive rate found")
                return local_res

            # Success
            local_res["exchange_rate"] = rate
            local_res["receive_amount"] = float(amount) * rate
            local_res["success"] = True
            return local_res

        except PlacidError as e:
            local_res["error_message"] = str(e)
            return local_res
        except Exception as e:
            logger.error(f"Unexpected error in get_quote: {e}")
            local_res["error_message"] = f"Unexpected error: {str(e)}"
            return local_res

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        target_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get exchange rate for the specified amount, currencies and countries.
        """
        # get a local quote
        local_quote = self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            target_currency=target_currency,
            **kwargs
        )
        # Convert local dict to aggregator standard
        aggregator_res = self.standardize_response({
            "success": local_quote["success"],
            "error_message": local_quote["error_message"],
            "source_currency": local_quote["source_currency"],
            "target_currency": local_quote["target_currency"],
            "send_amount": local_quote["send_amount"],
            "exchange_rate": local_quote["exchange_rate"],
            "receive_amount": local_quote["receive_amount"],
            "timestamp": kwargs.get("timestamp"),
        })
        return aggregator_res

    def get_supported_countries(self) -> List[str]:
        """Return list of supported countries."""
        return ["US", "GB", "EU", "CA", "AU"]

    def get_supported_currencies(self) -> List[str]:
        """Return list of supported currencies."""
        return list(self.CURRENCY_TO_CORRIDOR.keys()) + ["USD", "GBP", "EUR", "CAD", "AUD"]

    def close(self):
        """Close the session if it's open."""
        if self.session:
            self.session.close()
            self.session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 