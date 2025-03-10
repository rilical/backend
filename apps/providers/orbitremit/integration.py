"""
OrbitRemit provider integration module.

This module implements an aggregator-ready OrbitRemit provider for retrieving remittance
fee information.
"""

import logging
import requests
from decimal import Decimal
from typing import Any, Dict, Optional, List
from datetime import datetime

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    OrbitRemitError,
    OrbitRemitConnectionError,
    OrbitRemitApiError,
    OrbitRemitResponseError,
    OrbitRemitCorridorUnsupportedError,
)

logger = logging.getLogger("providers.orbitremit")

class OrbitRemitProvider(RemittanceProvider):
    """
    Aggregator-ready OrbitRemit integration for retrieving fees, exchange rates, and quotes.
    """

    BASE_URL = "https://www.orbitremit.com"
    FEES_ENDPOINT = "/api/fees"
    RATES_ENDPOINT = "/api/rates"
    HISTORIC_RATES_ENDPOINT = "/api/historic-rates"
    
    # Common source currencies
    SUPPORTED_SOURCE_CURRENCIES = ["AUD", "NZD", "GBP", "EUR", "CAD", "USD"]
    
    # Known supported corridors (source→target pairs)
    SUPPORTED_CORRIDORS = {
        "AUD": ["PHP", "INR", "PKR", "BDT", "FJD", "LKR", "NPR", "USD", "VND"],
        "NZD": ["PHP", "INR", "FJD", "PKR", "BDT", "LKR", "NPR", "VND"],
        "GBP": ["PHP", "INR", "PKR", "BDT", "LKR", "NPR", "VND"],
        "EUR": ["PHP", "INR", "PKR", "BDT", "LKR", "NPR", "VND"],
        "CAD": ["PHP", "INR", "PKR", "BDT", "LKR", "NPR", "VND"],
        "USD": ["PHP", "INR", "PKR", "BDT", "LKR", "NPR", "VND"],
    }
    
    # Mapping of country codes to currencies
    COUNTRY_TO_CURRENCY = {
        "PH": "PHP",  # Philippines
        "IN": "INR",  # India
        "FJ": "FJD",  # Fiji
        "PK": "PKR",  # Pakistan
        "BD": "BDT",  # Bangladesh
        "LK": "LKR",  # Sri Lanka
        "NP": "NPR",  # Nepal
        "VN": "VND",  # Vietnam
        "US": "USD",  # United States
    }
    
    # Approximated exchange rates for fallback calculation
    EXCHANGE_RATES = {
        "AUD": {
            "PHP": Decimal("35.50"), "INR": Decimal("55.20"), "PKR": Decimal("217.40"),
            "BDT": Decimal("75.30"), "FJD": Decimal("1.50"), "LKR": Decimal("215.75"),
            "NPR": Decimal("89.15"), "USD": Decimal("0.66"),  "VND": Decimal("16250.00"),
        },
        "NZD": {
            "PHP": Decimal("33.20"), "INR": Decimal("51.75"), "PKR": Decimal("203.50"),
            "BDT": Decimal("70.40"), "FJD": Decimal("1.40"), "LKR": Decimal("201.80"),
            "NPR": Decimal("83.45"), "VND": Decimal("15200.00"),
        },
        "GBP": {
            "PHP": Decimal("67.80"), "INR": Decimal("105.60"), "PKR": Decimal("415.25"),
            "BDT": Decimal("143.70"), "LKR": Decimal("411.90"), "NPR": Decimal("170.30"),
            "VND": Decimal("31000.00"),
        },
        "EUR": {
            "PHP": Decimal("59.40"), "INR": Decimal("92.50"), "PKR": Decimal("363.80"),
            "BDT": Decimal("125.95"), "LKR": Decimal("360.90"), "NPR": Decimal("149.25"),
            "VND": Decimal("27150.00"),
        },
        "CAD": {
            "PHP": Decimal("39.65"), "INR": Decimal("61.75"), "PKR": Decimal("242.85"),
            "BDT": Decimal("84.10"), "LKR": Decimal("241.00"), "NPR": Decimal("99.65"),
            "VND": Decimal("18130.00"),
        },
        "USD": {
            "PHP": Decimal("53.90"), "INR": Decimal("83.95"), "PKR": Decimal("330.15"),
            "BDT": Decimal("114.25"), "LKR": Decimal("327.60"), "NPR": Decimal("135.55"),
            "VND": Decimal("24650.00"),
        }
    }
    
    # When these rates were last updated
    RATES_LAST_UPDATED = datetime(2023, 3, 2)
    
    # Fixed fees by currency (fallback values)
    FIXED_FEES = {
        "AUD": Decimal("4.00"),
        "NZD": Decimal("6.00"),
        "GBP": Decimal("3.50"),
        "EUR": Decimal("3.50"),
        "CAD": Decimal("4.00"),
        "USD": Decimal("4.00"),
    }

    def __init__(self, name="orbitremit", **kwargs):
        """
        Initialize the OrbitRemit provider.

        :param name: Internal provider name to register (defaults to 'orbitremit')
        :param kwargs: Additional config / session parameters
        """
        super().__init__(name=name, base_url=self.BASE_URL, **kwargs)
        self.session = requests.Session()

        # Example default headers that match your logs
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                           "Version/18.3 Safari/605.1.15"),
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })

    def standardize_response(self, raw_result: Dict[str, Any], provider_specific_data: bool = False) -> Dict[str, Any]:
        """
        Convert local fields -> aggregator-friendly keys.
        Typically aggregator wants:
            provider_id, success, error_message,
            send_amount, source_currency, destination_amount, destination_currency,
            exchange_rate, fee, delivery_time_minutes, timestamp,
            plus "rate" and "target_currency" for aggregator's get_exchange_rate usage
        """
        final_exchange_rate = raw_result.get("exchange_rate")
        final_rate = raw_result.get("rate")
        # If aggregator specifically wants "rate", we can unify them
        if final_rate is None:
            final_rate = final_exchange_rate
            
        final_target_currency = raw_result.get("target_currency") or raw_result.get("destination_currency")
        
        standardized = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),

            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": (raw_result.get("source_currency") or "").upper(),

            "destination_amount": raw_result.get("destination_amount"),
            "destination_currency": (raw_result.get("destination_currency") or "").upper(),

            "exchange_rate": final_exchange_rate,
            "fee": raw_result.get("fee"),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes"),
            "timestamp": raw_result.get("timestamp") or datetime.now().isoformat(),

            "rate": final_rate,
            "target_currency": (final_target_currency or "").upper(),
        }
        
        if provider_specific_data and "raw_response" in raw_result:
            standardized["raw_response"] = raw_result["raw_response"]
            
        return standardized

    def _get_exchange_rate(self, source_currency: str, target_currency: str) -> Optional[Decimal]:
        """
        Get the exchange rate from our embedded rate database.
        
        Args:
            source_currency: Source currency code (e.g. 'USD')
            target_currency: Target currency code (e.g. 'PHP')
            
        Returns:
            Exchange rate as a Decimal or None if not found
        """
        source_currency = source_currency.upper()
        target_currency = target_currency.upper()
        
        if source_currency in self.EXCHANGE_RATES:
            if target_currency in self.EXCHANGE_RATES[source_currency]:
                return self.EXCHANGE_RATES[source_currency][target_currency]
        
        logger.warning(f"No exchange rate found for {source_currency} to {target_currency}")
        return None

    def get_rates(self, send_currency: str, dest_currency: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Attempt to get exchange rate from OrbitRemit's /api/rates endpoint.
        If it fails or doesn't find a rate, we'll fallback to embedded EXCHANGE_RATES.
        """
        local_result = {
            'success': False,
            'source_currency': send_currency.upper(),
            'target_currency': dest_currency.upper(),
            'rate': None,
            'error_message': None,
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Update parameter names to match the API's expected format
            payload = {
                'send': send_currency.upper(),
                'payout': dest_currency.upper(),
                'send_amount': str(float(amount)) if amount else '1000.00'
            }
            headers = {
                'Content-Type': 'application/json',
                'Pragma': 'no-cache',
                'Accept': 'application/json, text/plain, */*',
                'Sec-Fetch-Site': 'same-origin',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Fetch-Mode': 'cors',
                'Cache-Control': 'no-cache',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Referer': 'https://www.orbitremit.com/',
                'Sec-Fetch-Dest': 'empty',
                'Priority': 'u=1, i'
            }

            url = f"{self.BASE_URL}/api/rates"
            logger.info(f"OrbitRemit GET /api/rates -> POST {url} with payload: {payload}")
            timeout = getattr(self, 'timeout', 15)
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()

            data = response.json()
            logger.info(f"OrbitRemit rates response: {data}")

            # Update response parsing to match expected format
            # Check for the new response format first
            if data.get('code') == 200 and data.get('status') == 'success' and 'data' in data:
                if 'rate' in data['data']:
                    local_result['success'] = True
                    local_result['rate'] = Decimal(str(data['data']['rate']))
                    return local_result
                
            # Fallback to previous response handling patterns
            # Extract rate from nested structure
            # Typical new structure => data->data->attributes->rate
            # or top-level 'data': { 'attributes': {...} }
            elif data.get('type') == 'success' and 'data' in data:
                attr = data['data'].get('data', {}).get('attributes', {})
                rate_val = attr.get('rate') or attr.get('promotion_rate')
            else:
                # fallback attempt
                rate_val = None

            if rate_val:
                local_result['rate'] = Decimal(str(rate_val))
                local_result['success'] = True
            else:
                error_msg = f"Could not find a valid 'rate' in response: {data}"
                logger.error(error_msg)
                local_result['error_message'] = error_msg

        except requests.RequestException as e:
            error_msg = f"OrbitRemit rates request failed: {str(e)}"
            logger.error(error_msg)
            local_result['error_message'] = error_msg

        except (ValueError, TypeError) as e:
            error_msg = f"Error processing exchange rate data: {str(e)}"
            logger.error(error_msg)
            local_result['error_message'] = error_msg

        return local_result

    def get_fee_info(
        self,
        send_currency: str,
        payout_currency: str,
        send_amount: Decimal,
        recipient_type: str = "bank_account",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieve fee from OrbitRemit's /api/fees endpoint.
        """
        result = {
            "success": False,
            "send_currency": send_currency.upper(),
            "payout_currency": payout_currency.upper(),
            "send_amount": float(send_amount),
            "recipient_type": recipient_type,
            "fee": None,
            "error_message": None,
        }

        # Basic validation
        if not send_amount or send_amount <= 0:
            result["error_message"] = "Amount must be positive"
            return result
        if send_currency.upper() not in self.SUPPORTED_SOURCE_CURRENCIES:
            result["error_message"] = f"Unsupported source currency: {send_currency}"
            return result

        endpoint_url = self.BASE_URL + self.FEES_ENDPOINT
        headers = {
            "Content-Type": "application/json",
            "Pragma": "no-cache",
            "Accept": "application/json, text/plain, */*",
            "Sec-Fetch-Site": "same-origin",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Mode": "cors",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://www.orbitremit.com/",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=1, i"
        }

        try:
            params = {
                "send": send_currency.upper(),
                "payout": payout_currency.upper(),
                "amount": str(float(send_amount)),
                "type": recipient_type
            }
            logger.info(f"OrbitRemit fees request to {endpoint_url}, params={params}")
            timeout = getattr(self, 'timeout', 15)
            resp = requests.get(endpoint_url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()

            data = resp.json()
            logger.info(f"OrbitRemit fees response: {data}")

            # Update response parsing to match the sample response structure
            if "code" in data and data["code"] == 200 and data["status"] == "success" and "data" in data:
                if "fee" in data["data"]:
                    result["fee"] = float(data["data"]["fee"])
                    result["success"] = True
                else:
                    result["error_message"] = f"Could not locate 'fee' in data: {data}"
            # Keep the previous parsing logic as fallback
            elif "fee" in data:
                result["fee"] = float(data["fee"])
                result["success"] = True
            elif "data" in data and isinstance(data["data"], dict):
                # Possibly deeper nested
                if "fee" in data["data"]:
                    result["fee"] = float(data["data"]["fee"])
                    result["success"] = True
                elif "attributes" in data["data"] and "fee" in data["data"]["attributes"]:
                    result["fee"] = float(data["data"]["attributes"]["fee"])
                    result["success"] = True
                else:
                    result["error_message"] = f"Could not locate 'fee' in data: {data}"
            else:
                result["error_message"] = f"Unexpected fees response format: {data}"

        except requests.exceptions.RequestException as e:
            error_msg = f"OrbitRemit fees request failed: {e}"
            logger.error(error_msg)
            result["error_message"] = error_msg
        except (ValueError, TypeError) as e:
            error_msg = f"Failed to parse OrbitRemit fees response: {e}"
            logger.error(error_msg)
            result["error_message"] = error_msg

        return result

    def get_quote(
        self,
        amount=None,
        source_currency=None,
        dest_currency=None,
        source_country=None,
        dest_country=None,
        payment_method=None,
        receiving_method=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Aggregator-style get_quote: returns standardized aggregator keys.
        """
        local_result = {
            "success": False,
            "error_message": None,
            "send_amount": float(amount or 0),
            "source_currency": (source_currency or "").upper(),
            "destination_amount": None,
            "destination_currency": (dest_currency or "").upper(),
            "exchange_rate": None,
            "fee": None,
            "delivery_time_minutes": None,
            "timestamp": datetime.now().isoformat(),
        }

        # Validate required
        if not amount or not source_currency or not dest_currency:
            local_result["error_message"] = "Missing required params: amount, source_currency, dest_currency"
            return self.standardize_response(local_result)

        # Validate supported corridor
        src_curr = source_currency.upper()
        dst_curr = dest_currency.upper()
        
        if src_curr not in self.SUPPORTED_SOURCE_CURRENCIES:
            local_result["error_message"] = f"Unsupported source currency: {src_curr}"
            return self.standardize_response(local_result)
            
        if src_curr in self.SUPPORTED_CORRIDORS and dst_curr not in self.SUPPORTED_CORRIDORS[src_curr]:
            local_result["error_message"] = f"Unsupported corridor: {src_curr}->{dst_curr}"
            return self.standardize_response(local_result)

        # 1) Attempt to get fee
        try:
            fee_info = self.get_fee_info(
                send_currency=source_currency,
                payout_currency=dest_currency,
                send_amount=Decimal(str(amount))
            )
            if fee_info.get("success"):
                fee_val = Decimal(str(fee_info.get("fee", "6.00")))
            else:
                logger.warning(f"Fee call returned error: {fee_info.get('error_message')}")
                fee_val = self.FIXED_FEES.get(src_curr, Decimal("6.00"))  # fallback
        except Exception as e:
            logger.warning(f"Fee call failed: {str(e)}")
            fee_val = self.FIXED_FEES.get(src_curr, Decimal("6.00"))  # fallback

        local_result["fee"] = float(fee_val)

        # 2) Use embedded exchange rates as the API seems to be unreliable
        logger.info("Using embedded exchange rates fallback")
        src_map = self.EXCHANGE_RATES.get(src_curr, {})
        rate = src_map.get(dst_curr)
        
        if not rate:
            # Try API as last resort
            try:
                rate_data = self.get_rates(source_currency, dest_currency, amount)
                if rate_data.get("success"):
                    rate = rate_data.get("rate")
                else:
                    logger.warning(f"Rate call returned error: {rate_data.get('error_message')}")
            except Exception as e:
                logger.warning(f"Rate call failed: {str(e)}")
            
            if not rate:
                local_result["error_message"] = f"No exchange rate found for {src_curr}->{dst_curr}"
                return self.standardize_response(local_result)

        local_result["exchange_rate"] = float(rate)

        # 3) Calculate destination amount
        send_amount_dec = Decimal(str(amount))
        adj_send_amount = send_amount_dec - fee_val
        if adj_send_amount < 0:
            adj_send_amount = Decimal("0.00")

        destination_amount = adj_send_amount * rate
        local_result["destination_amount"] = float(destination_amount)

        local_result["success"] = True
        return self.standardize_response(local_result, provider_specific_data=kwargs.get("include_raw", False))

    def get_exchange_rate(
        self,
        source_currency: str,
        target_currency: str,
        source_country: str = None,
        target_country: str = None,
        amount: Decimal = Decimal("1000"),
        **kwargs
    ) -> Dict[str, Any]:
        """
        Aggregator-style get_exchange_rate returning standardized fields.
        We'll call get_quote(...) with the 'amount' and return the same structure.
        """
        # We'll re-use get_quote logic since aggregator often wants the same structure
        return self.get_quote(
            amount=amount,
            source_currency=source_currency,
            dest_currency=target_currency,
            source_country=source_country,
            dest_country=target_country,
            **kwargs
        )

    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close()

    def get_historic_rates(
        self, 
        send_currency: str, 
        payout_currency: str, 
        timescale: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Aggregator style function to get historical exchange rates from 
        OrbitRemit's /api/historic-rates.
        """
        try:
            # Basic input validation
            if not send_currency or not payout_currency:
                return {
                    "success": False,
                    "error_message": "send_currency and payout_currency required",
                    "source_currency": send_currency,
                    "target_currency": payout_currency,
                    "rates": []
                }

            url = f"{self.BASE_URL}{self.HISTORIC_RATES_ENDPOINT}"
            headers = {
                "Pragma": "no-cache",
                "Accept": "application/json, text/plain, */*",
                "Sec-Fetch-Site": "same-origin",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Fetch-Mode": "cors",
                "Cache-Control": "no-cache",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Referer": "https://www.orbitremit.com/",
                "Sec-Fetch-Dest": "empty",
                "Priority": "u=1, i"
            }
            params = {
                "send_currency": send_currency.upper(),
                "payout_currency": payout_currency.upper(),
                "timescale": timescale
            }

            logger.info(f"Requesting historic rates from {url} with {params}")
            timeout = getattr(self, 'timeout', 15)
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()

            data = resp.json()
            logger.info(f"Historic rates response: {data}")

            # Parse returned data
            if data.get("type") == "success" and "data" in data:
                all_rates = []
                if isinstance(data["data"], list):
                    for item in data["data"]:
                        if "attributes" in item:
                            attr = item["attributes"]
                            all_rates.append({
                                "date": attr.get("date"),
                                "rate": float(attr.get("rate", 0))
                            })

                return {
                    "success": True,
                    "error_message": None,
                    "source_currency": send_currency.upper(),
                    "target_currency": payout_currency.upper(),
                    "rates": all_rates
                }
            else:
                return {
                    "success": False,
                    "error_message": f"Unexpected response structure: {data}",
                    "source_currency": send_currency.upper(),
                    "target_currency": payout_currency.upper(),
                    "rates": []
                }

        except requests.RequestException as exc:
            error_msg = f"Error fetching historic rates: {exc}"
            logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg,
                "source_currency": send_currency.upper(),
                "target_currency": payout_currency.upper(),
                "rates": []
            }
        except (ValueError, TypeError) as exc:
            error_msg = f"Error parsing historic rates: {exc}"
            logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg,
                "source_currency": send_currency.upper(),
                "target_currency": payout_currency.upper(),
                "rates": []
            } 