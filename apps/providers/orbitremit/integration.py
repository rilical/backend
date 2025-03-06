"""
OrbitRemit provider integration module.

This module implements the OrbitRemit provider for retrieving remittance
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
    OrbitRemit integration for retrieving fees, exchange rates, and quotes.
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
    
    # Approximated exchange rates for calculation purposes
    # These would ideally be updated regularly from an exchange rate API
    # Format: source_currency -> target_currency -> rate
    EXCHANGE_RATES = {
        "AUD": {
            "PHP": Decimal("35.50"),    # 1 AUD = 35.50 PHP
            "INR": Decimal("55.20"),    # 1 AUD = 55.20 INR
            "PKR": Decimal("217.40"),   # 1 AUD = 217.40 PKR
            "BDT": Decimal("75.30"),    # 1 AUD = 75.30 BDT
            "FJD": Decimal("1.50"),     # 1 AUD = 1.50 FJD
            "LKR": Decimal("215.75"),   # 1 AUD = 215.75 LKR
            "NPR": Decimal("89.15"),    # 1 AUD = 89.15 NPR
            "USD": Decimal("0.66"),     # 1 AUD = 0.66 USD
            "VND": Decimal("16250.00"), # 1 AUD = 16250.00 VND
        },
        "NZD": {
            "PHP": Decimal("33.20"),    # 1 NZD = 33.20 PHP
            "INR": Decimal("51.75"),    # 1 NZD = 51.75 INR
            "PKR": Decimal("203.50"),   # 1 NZD = 203.50 PKR
            "BDT": Decimal("70.40"),    # 1 NZD = 70.40 BDT
            "FJD": Decimal("1.40"),     # 1 NZD = 1.40 FJD
            "LKR": Decimal("201.80"),   # 1 NZD = 201.80 LKR
            "NPR": Decimal("83.45"),    # 1 NZD = 83.45 NPR
            "VND": Decimal("15200.00"), # 1 NZD = 15200.00 VND
        },
        "GBP": {
            "PHP": Decimal("67.80"),    # 1 GBP = 67.80 PHP
            "INR": Decimal("105.60"),   # 1 GBP = 105.60 INR
            "PKR": Decimal("415.25"),   # 1 GBP = 415.25 PKR
            "BDT": Decimal("143.70"),   # 1 GBP = 143.70 BDT
            "LKR": Decimal("411.90"),   # 1 GBP = 411.90 LKR
            "NPR": Decimal("170.30"),   # 1 GBP = 170.30 NPR
            "VND": Decimal("31000.00"), # 1 GBP = 31000.00 VND
        },
        "EUR": {
            "PHP": Decimal("59.40"),    # 1 EUR = 59.40 PHP
            "INR": Decimal("92.50"),    # 1 EUR = 92.50 INR
            "PKR": Decimal("363.80"),   # 1 EUR = 363.80 PKR
            "BDT": Decimal("125.95"),   # 1 EUR = 125.95 BDT
            "LKR": Decimal("360.90"),   # 1 EUR = 360.90 LKR
            "NPR": Decimal("149.25"),   # 1 EUR = 149.25 NPR
            "VND": Decimal("27150.00"), # 1 EUR = 27150.00 VND
        },
        "CAD": {
            "PHP": Decimal("39.65"),    # 1 CAD = 39.65 PHP
            "INR": Decimal("61.75"),    # 1 CAD = 61.75 INR
            "PKR": Decimal("242.85"),   # 1 CAD = 242.85 PKR
            "BDT": Decimal("84.10"),    # 1 CAD = 84.10 BDT
            "LKR": Decimal("241.00"),   # 1 CAD = 241.00 LKR
            "NPR": Decimal("99.65"),    # 1 CAD = 99.65 NPR
            "VND": Decimal("18130.00"), # 1 CAD = 18130.00 VND
        },
        "USD": {
            "PHP": Decimal("53.90"),    # 1 USD = 53.90 PHP
            "INR": Decimal("83.95"),    # 1 USD = 83.95 INR
            "PKR": Decimal("330.15"),   # 1 USD = 330.15 PKR
            "BDT": Decimal("114.25"),   # 1 USD = 114.25 BDT
            "LKR": Decimal("327.60"),   # 1 USD = 327.60 LKR
            "NPR": Decimal("135.55"),   # 1 USD = 135.55 NPR
            "VND": Decimal("24650.00"), # 1 USD = 24650.00 VND
        }
    }
    
    # When these rates were last updated
    RATES_LAST_UPDATED = datetime(2023, 3, 2)

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
        Convert local result dict into standardized format.
        """
        final_exchange_rate = raw_result.get("exchange_rate")
        final_rate = raw_result.get("rate")
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
            
            "delivery_time_minutes": None,
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

    def get_rates(self, send_currency, dest_currency, amount=None):
        """Get the exchange rate for a currency pair."""
        try:
            payload = {
                'send_currency': send_currency,
                'payout_currency': dest_currency,
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
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Referer': 'https://www.orbitremit.com/',
                'Sec-Fetch-Dest': 'empty',
                'Priority': 'u=1, i'
            }

            url = f"{self.BASE_URL}/api/rates"
            
            logging.info(f"Request to {url} with params: {payload}")
            # Use a default timeout of 15 seconds if self.timeout isn't available
            timeout = getattr(self, 'timeout', 15)
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()

            logging.info(f"Response from {url}: {response.text}")
            data = response.json()
            
            # Extract rate from the nested structure
            try:
                # Handle the new nested response format
                if data.get('type') == 'success' and 'data' in data:
                    attributes = data.get('data', {}).get('data', {}).get('attributes', {})
                    rate = attributes.get('rate') or attributes.get('promotion_rate')
                elif 'data' in data and 'attributes' in data.get('data', {}).get('data', {}):
                    attributes = data.get('data', {}).get('data', {}).get('attributes', {})
                    rate = attributes.get('rate') or attributes.get('promotion_rate')
                else:
                    rate = None
                
                if rate:
                    rate_value = Decimal(str(rate))
                    return {
                        'success': True,
                        'source_currency': send_currency,
                        'target_currency': dest_currency,
                        'rate': rate_value,
                        'error_message': None,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    error_msg = f"Could not find rate in response: {data}"
                    logging.error(error_msg)
                    return {
                        'success': False,
                        'source_currency': send_currency,
                        'target_currency': dest_currency,
                        'rate': None,
                        'error_message': error_msg,
                        'timestamp': datetime.now().isoformat()
                    }
            except (KeyError, TypeError) as e:
                error_msg = f"Error extracting rate from response: {e}. Response: {data}"
                logging.error(error_msg)
                return {
                    'success': False,
                    'source_currency': send_currency,
                    'target_currency': dest_currency,
                    'rate': None,
                    'error_message': error_msg,
                    'timestamp': datetime.now().isoformat()
                }
                
        except requests.RequestException as e:
            error_msg = f"Error fetching exchange rate: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'source_currency': send_currency,
                'target_currency': dest_currency,
                'rate': None,
                'error_message': error_msg,
                'timestamp': datetime.now().isoformat()
            }
        except (ValueError, TypeError) as e:
            error_msg = f"Error processing exchange rate data: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'source_currency': send_currency,
                'target_currency': dest_currency,
                'rate': None,
                'error_message': error_msg,
                'timestamp': datetime.now().isoformat()
            }

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
        # Validate inputs
        send_currency = send_currency.upper()
        payout_currency = payout_currency.upper()
        
        result = {
            "success": False,
            "send_currency": send_currency,
            "payout_currency": payout_currency,
            "send_amount": float(send_amount),
            "recipient_type": recipient_type,
            "fee": None,
            "error_message": None,
        }
        
        # Basic validation
        if not send_amount or send_amount <= 0:
            result["error_message"] = "Amount must be positive"
            return result
            
        if not send_currency:
            result["error_message"] = "Send currency cannot be empty"
            return result
            
        if not payout_currency:
            result["error_message"] = "Payout currency cannot be empty"
            return result

        endpoint_url = self.BASE_URL + self.FEES_ENDPOINT

        # Set headers to match the curl example
        headers = {
            "Content-Type": "application/json",
            "Pragma": "no-cache",
            "Accept": "application/json, text/plain, */*",
            "Sec-Fetch-Site": "same-origin",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Mode": "cors",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer": "https://www.orbitremit.com/",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=1, i"
        }
        
        try:
            # Construct the query parameters
            params = {
                "send_currency": send_currency,
                "payout_currency": payout_currency,
                "amount": str(float(send_amount)),
                "recipient_type": recipient_type
            }
            
            # Add any additional parameters from kwargs
            params.update({k: v for k, v in kwargs.items() if k not in params})
            
            logging.info(f"OrbitRemit fees request: {endpoint_url}, {params}")
            
            # Use a default timeout of 15 seconds if self.timeout isn't available
            timeout = getattr(self, 'timeout', 15)
            resp = requests.get(endpoint_url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            
            logging.info(f"OrbitRemit fees response: {resp.text}")
            data = resp.json()
            
            # Check if the response contains fee information
            # The structure might be different than expected, but we'll try common patterns
            if "fee" in data:
                # Direct fee property
                fee_value = float(data["fee"])
                result["fee"] = Decimal(str(fee_value))
                result["success"] = True
            elif "data" in data and isinstance(data["data"], dict):
                # Nested data structure
                if "fee" in data["data"]:
                    fee_value = float(data["data"]["fee"])
                    result["fee"] = Decimal(str(fee_value))
                    result["success"] = True
                elif "attributes" in data["data"] and "fee" in data["data"]["attributes"]:
                    fee_value = float(data["data"]["attributes"]["fee"])
                    result["fee"] = Decimal(str(fee_value))
                    result["success"] = True
            else:
                result["error_message"] = f"Could not find fee in response: {data}"
                
        except requests.exceptions.RequestException as e:
            error_msg = f"OrbitRemit fees request failed: {e}"
            logging.error(error_msg)
            result["error_message"] = error_msg
            
        except (ValueError, TypeError) as e:
            error_msg = f"Failed to parse OrbitRemit fees response: {e}"
            logging.error(error_msg)
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
    ):
        """Get a standardized quote for a money transfer."""
        try:
            # Validate required parameters
            if not amount or not source_currency or not dest_currency:
                return {
                    'provider_id': self.name,
                    'success': False,
                    'error_message': 'Missing required parameters: amount, source_currency, dest_currency',
                }
            
            # Try to get fee information, but use fallback if it fails
            try:
                fee_info = self.get_fee_info(
                    send_currency=source_currency,
                    payout_currency=dest_currency,
                    send_amount=Decimal(str(amount))
                )
                if fee_info.get('success'):
                    fee = fee_info.get('fee', Decimal('6.00'))
                else:
                    # Fall back to fixed fee
                    fee = Decimal('6.00')  # Default fee if not available
            except Exception as e:
                logging.warning(f"Fee API call failed: {str(e)}")
                fee = Decimal('6.00')  # Default fee
            
            # Try to get exchange rate, but use fallback if it fails
            try:
                rate_info = self.get_rates(source_currency, dest_currency, amount)
                if rate_info.get('success'):
                    rate = rate_info.get('rate')
                else:
                    # Fall back to embedded rates
                    rate = None
            except Exception as e:
                logging.warning(f"Rate API call failed: {str(e)}")
                rate = None
            
            # If we couldn't get a rate from the API, use the embedded rates
            if not rate:
                logging.info("Using embedded exchange rates")
                # Get the nested dictionary for the source currency
                source_rates = self.EXCHANGE_RATES.get(source_currency.upper(), {})
                # Get the rate for the destination currency
                rate = source_rates.get(dest_currency.upper())
                
                if not rate:
                    return {
                        'provider_id': self.name,
                        'success': False,
                        'error_message': f'No exchange rate found for {source_currency} to {dest_currency}',
                    }
            
            # Calculate destination amount
            send_amount = Decimal(str(amount))
            destination_amount = (send_amount - fee) * rate
            
            # Build the response
            return {
                'provider_id': self.name,
                'success': True,
                'error_message': None,
                'send_amount': float(send_amount),
                'source_currency': source_currency,
                'destination_amount': float(destination_amount),
                'destination_currency': dest_currency,
                'exchange_rate': float(rate),
                'fee': float(fee),
                'delivery_time_minutes': None,
                'timestamp': datetime.now().isoformat(),
                'rate': float(rate),
                'target_currency': dest_currency,
            }
            
        except Exception as e:
            logging.error(f"Error getting quote: {str(e)}")
            return {
                'provider_id': self.name,
                'success': False,
                'error_message': f"Failed to get quote: {str(e)}",
            }

    def get_exchange_rate(
        self,
        source_currency: str,
        target_currency: str,
        source_country: str = None,
        target_country: str = None,
        amount: Decimal = Decimal("1000")
    ) -> Dict[str, Any]:
        """
        Get exchange rate for a currency pair.
        """
        local_result = {
            "success": False,
            "send_amount": float(amount),
            "source_currency": source_currency.upper(),
            "destination_currency": target_currency.upper(),
            "exchange_rate": None,
            "error_message": None,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Get rates from the live API
        rate_data = self.get_rates(
            source_currency,
            target_currency,
            amount
        )
        
        local_result["success"] = rate_data["success"]
        local_result["exchange_rate"] = rate_data.get("rate")
        local_result["error_message"] = rate_data.get("error_message")
        
        return self.standardize_response(local_result)
        
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
        """Get historical exchange rates from OrbitRemit API."""
        try:
            # Validate input parameters
            if not send_currency or not payout_currency:
                return {
                    "success": False,
                    "source_currency": send_currency,
                    "target_currency": payout_currency,
                    "rates": [],
                    "error_message": "Send currency and payout currency must be provided",
                }
                
            # Set parameters for the request
            params = {
                "send_currency": send_currency.upper(),
                "payout_currency": payout_currency.upper(),
                "timescale": timescale
            }
            
            # Set headers to match the curl example
            headers = {
                "Pragma": "no-cache",
                "Accept": "application/json, text/plain, */*",
                "Sec-Fetch-Site": "same-origin",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Sec-Fetch-Mode": "cors",
                "Cache-Control": "no-cache",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Referer": "https://www.orbitremit.com/",
                "Sec-Fetch-Dest": "empty",
                "Priority": "u=1, i"
            }
            
            url = f"{self.BASE_URL}{self.HISTORIC_RATES_ENDPOINT}"
            
            logging.info(f"Request to {url} with params: {params}")
            # Use a default timeout of 15 seconds if self.timeout isn't available
            timeout = getattr(self, 'timeout', 15)
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            logging.info(f"Response from {url}: {response.text}")
            data = response.json()
            
            # Extract rates from response
            try:
                if data.get("type") == "success" and "data" in data:
                    # Process the historical rates data
                    rates = []
                    if isinstance(data["data"], list):
                        for item in data["data"]:
                            if "attributes" in item:
                                attributes = item["attributes"]
                                rate_info = {
                                    "date": attributes.get("date"),
                                    "rate": float(attributes.get("rate", 0)),
                                }
                                rates.append(rate_info)
                    
                    return {
                        "success": True,
                        "source_currency": send_currency,
                        "target_currency": payout_currency,
                        "rates": rates,
                        "error_message": None,
                    }
                else:
                    return {
                        "success": False,
                        "source_currency": send_currency,
                        "target_currency": payout_currency,
                        "rates": [],
                        "error_message": f"Unexpected response format: {data}",
                    }
            except (KeyError, ValueError, TypeError) as e:
                return {
                    "success": False,
                    "source_currency": send_currency,
                    "target_currency": payout_currency, 
                    "rates": [],
                    "error_message": f"Error parsing response: {e}"
                }
                
        except requests.RequestException as e:
            return {
                "success": False,
                "source_currency": send_currency,
                "target_currency": payout_currency,
                "rates": [],
                "error_message": f"Error fetching historic rates: {str(e)}"
            } 