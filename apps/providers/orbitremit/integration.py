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
    Example of adding OrbitRemit integration for retrieving fees or quotes.
    
    Observed usage from logs:
      GET /api/fees?send=AUD&payout=PHP&amount=200000&type=bank_account

    The JSON response might look like:
    {
      "code": 200,
      "status": "success",
      "data": {
        "fee": "0.00",
        "send_currency": "AUD",
        "payout_currency": "PHP",
        "send_amount": "200000",
        "recipient_type": "bank_account"
      }
    }
    """

    BASE_URL = "https://www.orbitremit.com"
    FEES_ENDPOINT = "/api/fees"
    
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

    def get_exchange_rate(
        self, 
        send_amount: Decimal, 
        send_currency: str, 
        receive_country: str
    ) -> Optional[Dict]:
        """
        Get exchange rate and fees for a money transfer.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency code to send (e.g. 'USD')
            receive_country: Destination country code (e.g. 'PH')
            
        Returns:
            Dictionary containing rate information or None if failed
        """
        # Convert country code to currency
        if receive_country.upper() in self.COUNTRY_TO_CURRENCY:
            payout_currency = self.COUNTRY_TO_CURRENCY[receive_country.upper()]
        else:
            logger.warning(f"Unknown country code: {receive_country}, cannot determine currency")
            return None
        
        # Get fee info using the fee_info method
        fee_info = self.get_fee_info(
            send_currency=send_currency,
            payout_currency=payout_currency,
            send_amount=send_amount,
        )
        
        # Get the exchange rate from our embedded rate database
        exchange_rate = self._get_exchange_rate(send_currency.upper(), payout_currency)
        
        # Calculate the target amount if we have an exchange rate
        target_amount = None
        if exchange_rate:
            # Deduct the fee from the send amount
            fee = Decimal(str(fee_info.get("fee", 0)))
            adjusted_send_amount = send_amount - fee
            
            # Calculate the target amount
            target_amount = adjusted_send_amount * exchange_rate
        
        if fee_info["success"]:
            return {
                "provider": self.name,
                "source_amount": float(send_amount),
                "source_currency": send_currency.upper(),
                "target_currency": payout_currency,
                "fee": fee_info.get("fee", 0),
                "rate": float(exchange_rate) if exchange_rate else None,
                "target_amount": float(target_amount) if target_amount else None,
                "corridor": f"{send_currency.upper()}-{payout_currency}",
                "success": True,
                "rate_source": "OrbitRemit estimated rates",
                "rate_timestamp": self.RATES_LAST_UPDATED.isoformat(),
            }
        else:
            # Return None or a dictionary with error information
            return {
                "provider": self.name,
                "success": False,
                "error_message": fee_info.get("error_message", "Failed to get exchange rate information"),
            }

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

    def get_fee_info(
        self,
        send_currency: str,
        payout_currency: str,
        send_amount: Decimal,
        recipient_type: str = "bank_account",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieve the fee / quote from OrbitRemit, e.g.:

        GET /api/fees
          ?send=AUD
          &payout=PHP
          &amount=200000
          &type=bank_account

        Example usage:
            result = provider.get_fee_info(
                send_currency="AUD",
                payout_currency="PHP",
                send_amount=Decimal("200000"),
                recipient_type="bank_account",
            )

        :return: Dictionary with keys: success, fee, send_currency, payout_currency, etc.
        """
        # Validate inputs
        send_currency = send_currency.upper()
        payout_currency = payout_currency.upper()
        
        result = {
            "provider": self.name,
            "success": False,
            "send_currency": send_currency,
            "payout_currency": payout_currency,
            "send_amount": float(send_amount),
            "recipient_type": recipient_type,
            "fee": None,
            "raw_data": None,
            "error_message": None,
        }
        
        # Input validation
        if not send_amount or send_amount <= 0:
            result["error_message"] = "Amount must be positive"
            return result
            
        if not send_currency:
            result["error_message"] = "Send currency cannot be empty"
            return result
            
        if not payout_currency:
            result["error_message"] = "Payout currency cannot be empty"
            return result
            
        if send_currency not in self.SUPPORTED_SOURCE_CURRENCIES:
            result["error_message"] = f"Invalid source currency. Supported currencies: {', '.join(self.SUPPORTED_SOURCE_CURRENCIES)}"
            return result
            
        # Check if corridor is supported
        if send_currency in self.SUPPORTED_CORRIDORS:
            if payout_currency not in self.SUPPORTED_CORRIDORS[send_currency]:
                result["error_message"] = f"Unsupported corridor: {send_currency} to {payout_currency}"
                return result
        else:
            # If source currency not found in supported corridors, indicate that
            result["error_message"] = f"Source currency {send_currency} is not supported"
            return result

        endpoint_url = self.base_url + self.FEES_ENDPOINT

        # Convert Decimal to string
        send_amount_str = f"{send_amount:.2f}"

        # Construct query parameters
        params = {
            "send": send_currency,       # e.g. 'AUD'
            "payout": payout_currency,   # e.g. 'PHP'
            "amount": send_amount_str,   # e.g. '200000'
            "type": recipient_type,      # e.g. 'bank_account'
        }

        logger.debug(f"OrbitRemit GET: {endpoint_url} params={params}")

        try:
            resp = self.session.get(endpoint_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            # Store raw data for debugging
            result["raw_data"] = data
            
            logger.debug(f"OrbitRemit response: {data}")

            # Check if we have a "success" code
            if data.get("status") == "success" and isinstance(data.get("data"), dict):
                fee_data = data["data"]
                # Example structure:
                # {
                #   "fee": "0.00",
                #   "send_currency": "AUD",
                #   "payout_currency": "PHP",
                #   "send_amount": "200000",
                #   "recipient_type": "bank_account"
                # }

                fee_str = fee_data.get("fee", "0.00")
                fee_val = float(fee_str)

                result.update({
                    "success": True,
                    "fee": fee_val,
                })
            else:
                msg = f"OrbitRemit returned unexpected response: {data}"
                logger.error(msg)
                result["error_message"] = msg
        except requests.exceptions.JSONDecodeError as e:
            error_msg = f"Failed to parse OrbitRemit response as JSON: {e}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            raise OrbitRemitResponseError(error_msg) from e
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error when accessing OrbitRemit API: {e}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            raise OrbitRemitConnectionError(error_msg) from e
        except requests.exceptions.RequestException as e:
            error_msg = f"OrbitRemit request failed: {e}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            raise OrbitRemitApiError(error_msg) from e

        return result

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for converting an amount from one currency to another.
        This provides the standard interface expected by the remittance comparison system.

        Args:
            amount: The amount to convert
            source_currency: The source currency code (e.g. "AUD")
            target_currency: The target currency code (e.g. "PHP")
            **kwargs: Additional parameters for the API call

        Returns:
            A dictionary containing:
            - success: Boolean indicating success or failure
            - source_amount: Original amount in source currency
            - target_amount: Converted amount in target currency
            - fee: Fee charged for the conversion (if available)
            - rate: Exchange rate used (if available/calculated)
            - source_currency: Source currency code
            - target_currency: Target currency code
            - error_message: Error message if the quote failed
        """
        source_currency = source_currency.upper()
        target_currency = target_currency.upper()
        
        result = {
            "provider": self.name,
            "success": False,
            "source_amount": float(amount),
            "target_amount": None,
            "fee": None,
            "rate": None,
            "source_currency": source_currency,
            "target_currency": target_currency,
            "error_message": None,
        }
        
        # Call get_fee_info to get the fee
        fee_info = self.get_fee_info(
            send_currency=source_currency,
            payout_currency=target_currency,
            send_amount=amount,
            **kwargs
        )
        
        # Update result with fee info
        result["success"] = fee_info["success"]
        result["fee"] = fee_info.get("fee")
        result["error_message"] = fee_info.get("error_message")
        
        # Get the exchange rate from our embedded rate database
        if result["success"]:
            exchange_rate = self._get_exchange_rate(source_currency, target_currency)
            
            if exchange_rate:
                result["rate"] = float(exchange_rate)
                
                # Calculate the target amount
                fee = Decimal(str(result["fee"] or 0))
                adjusted_amount = amount - fee
                target_amount = adjusted_amount * exchange_rate
                result["target_amount"] = float(target_amount)
                
                # Add rate source information
                result["rate_source"] = "OrbitRemit estimated rates"
                result["rate_timestamp"] = self.RATES_LAST_UPDATED.isoformat()
            else:
                result["error_message"] = f"Exchange rate not available for {source_currency} to {target_currency}"
        
        return result 