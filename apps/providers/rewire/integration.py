"""
Rewire Integration

This module implements the integration with Rewire's public endpoints
to fetch exchange rates, fees, and supported corridors.
"""

import logging
import json
import requests
from decimal import Decimal
from typing import Dict, Any, List, Optional

# Import the base provider class
from apps.providers.base import RemittanceProvider
from apps.providers.rewire.exceptions import (
    RewireError,
    RewireConnectionError,
    RewireApiError,
    RewireResponseError,
    RewireCorridorUnsupportedError,
    RewireRateLimitError,
)

logger = logging.getLogger(__name__)


class RewireProvider(RemittanceProvider):
    """
    Provider implementation for Rewire, which offers cross-border
    money transfer services.

    Example usage:

        rewire = RewireProvider()
        quote = rewire.get_exchange_rate(
            send_amount=Decimal("500"),
            send_country="IL",       # e.g. 'IL' (Israel) or 'GB' (UK)
            send_currency="ILS",
            receive_currency="PHP"
        )
    """

    # Public Rewire endpoints
    RATES_URL = "https://api.rewire.to/services/rates/v3/jsonp"
    PRICING_URL = "https://lights.rewire.to/public/public-pricing"
    
    # Mapping of ISO country codes to currencies
    COUNTRY_TO_CURRENCY = {
        'IL': 'ILS',  # Israel - Israeli Shekel
        'GB': 'GBP',  # United Kingdom - British Pound
        'DE': 'EUR',  # Germany - Euro
        'FR': 'EUR',  # France - Euro
        'IT': 'EUR',  # Italy - Euro
        'ES': 'EUR',  # Spain - Euro
        'US': 'USD',  # United States - US Dollar
        'IN': 'INR',  # India - Indian Rupee
        'PH': 'PHP',  # Philippines - Philippine Peso
        'CN': 'CNY',  # China - Chinese Yuan
        'JP': 'JPY',  # Japan - Japanese Yen
        'CA': 'CAD',  # Canada - Canadian Dollar
        'AU': 'AUD',  # Australia - Australian Dollar
    }
    
    # Default corridors based on common Rewire usage
    SUPPORTED_CORRIDORS = [
        # From -> To
        ('IL', 'PHP'),
        ('IL', 'INR'),
        ('IL', 'CNY'),
        ('GB', 'PHP'),
        ('GB', 'INR'),
        ('DE', 'PHP'),
        ('DE', 'INR'),
        # Add more as discovered
    ]

    def __init__(self, name="rewire", **kwargs):
        """
        Initialize the Rewire provider.
        :param name: internal provider name
        :param kwargs: additional config
        """
        super().__init__(name=name, base_url=None, **kwargs)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
            ),
            "Accept": "*/*",
            "Origin": "https://www.rewire.com",
            "Referer": "https://www.rewire.com/"
        })

        # We will store rates & fees in memory
        self.cached_rates: Dict[str, Dict[str, Dict[str, float]]] = {}
        self.cached_fees: Dict[str, Any] = {}
        self.last_fetch_timestamp = 0

    def fetch_rates(self) -> Dict[str, Any]:
        """
        Fetch the main JSON from Rewire's `services/rates/v3/jsonp`
        which typically has structure:

        {
          "id": "...",
          "mid": false,
          "timestamp": 1740954759287,
          "rates": {
              "IL": { "NGN": {"buy": 0.00068, "sell": 1483.21 }, ... },
              "GB": { ... },
              "DE": { ... },
              ...
          },
          "geoLocation": "US"
        }

        We'll parse it and store the rates into self.cached_rates in a
        normalized manner: self.cached_rates[send_country][receive_currency] = { 'buy': ..., 'sell': ... }
        """
        logger.info("Fetching Rewire rates from %s", self.RATES_URL)
        
        try:
            resp = self.session.get(self.RATES_URL, timeout=15)
            resp.raise_for_status()
            
            try:
                data = resp.json()  # This should parse the JSON object
                
                # Check if the response has the expected structure
                if "rates" not in data:
                    raise RewireResponseError("Invalid response format: 'rates' field missing")
                
                # Store the rates
                self.cached_rates = data.get("rates", {})
                self.last_fetch_timestamp = data.get("timestamp", 0)
                
                logger.debug("Got rates for %d countries", len(self.cached_rates))
                # Log some sample rates for debugging
                for country in list(self.cached_rates.keys())[:2]:
                    sample_currencies = list(self.cached_rates[country].keys())[:3]
                    logger.debug("Sample rates for %s: %s", country, 
                                 {c: self.cached_rates[country][c] for c in sample_currencies})
                
                return data
                
            except json.JSONDecodeError as e:
                raise RewireResponseError(f"Failed to parse JSON response: {str(e)}")
                
        except requests.exceptions.RequestException as e:
            logger.error("Connection error fetching Rewire rates: %s", str(e))
            raise RewireConnectionError(f"Failed to connect to Rewire API: {str(e)}")

    def fetch_pricing(self) -> Dict[str, Any]:
        """
        Fetch the public-pricing from Rewire for fees or
        differentialFxFee data.
        
        Note: As of March 2025, this endpoint returns a 500 error.
        
        Returns:
            Empty dictionary since the API is not working
        """
        logger.info("Attempting to fetch Rewire public pricing from %s", self.PRICING_URL)
        logger.warning("Note: The pricing API currently returns a 500 error (as of March 2025)")
        
        # Return empty dictionary since we know this call will fail
        self.cached_fees = {}
        return {}
        
        # Keeping the original implementation commented out for future reference
        """
        try:
            resp = self.session.get(self.PRICING_URL, timeout=15)
            resp.raise_for_status()
            
            try:
                data = resp.json()
                logger.debug("Got pricing for %d currencies", len(data))
                
                # Store the data
                self.cached_fees = data
                return data
                
            except json.JSONDecodeError as e:
                raise RewireResponseError(f"Failed to parse JSON pricing data: {str(e)}")
                
        except requests.exceptions.RequestException as e:
            logger.error("Connection error fetching Rewire pricing: %s", str(e))
            raise RewireConnectionError(f"Failed to connect to Rewire pricing API: {str(e)}")
        """

    def _ensure_rates_loaded(self):
        """Helper to ensure we have recent rates cached."""
        if not self.cached_rates:
            self.fetch_rates()

    def _get_receive_currency(self, receive_country: str) -> str:
        """Get the currency code for a receive country."""
        return self.COUNTRY_TO_CURRENCY.get(receive_country, "USD")
        
    def _get_fee_for_corridor(self, send_currency: str, receive_currency: str, send_amount: float) -> float:
        """
        Calculate the fee for a specific corridor and amount.
        
        Note: As of March 2025, the pricing API returns a 500 error,
        so we use a static fee structure as a fallback.
        
        Args:
            send_currency: The currency code of the sending country (e.g., 'ILS', 'GBP')
            receive_currency: The currency code of the receiving country (e.g., 'PHP', 'INR')
            send_amount: The amount to send
            
        Returns:
            The fee amount in send_currency
        """
        # Define a basic static fee structure as a fallback
        # This is a temporary solution until the API is working
        static_fees = {
            "ILS": {
                "PHP": 5.0,  # 5 ILS fee
                "INR": 5.0,
                "NGN": 10.0,
                "CNY": 10.0,
                "default": 5.0,
            },
            "GBP": {
                "PHP": 2.0,  # 2 GBP fee
                "INR": 2.0,
                "default": 2.0,
            },
            "EUR": {
                "PHP": 2.5,  # 2.5 EUR fee
                "INR": 2.5,
                "default": 2.5,
            },
            "USD": {
                "default": 3.0,  # 3 USD fee
            },
        }
        
        # Apply static fee as a fallback
        if send_currency in static_fees:
            if receive_currency in static_fees[send_currency]:
                return static_fees[send_currency][receive_currency]
            else:
                return static_fees[send_currency].get("default", 0.0)
                
        # Default to zero fee if no static fee defined
        return 0.0
        
        # NOTE: The code below attempts to use the pricing API,
        # but it's currently returning a 500 error.
        # This code is kept for reference until the API is working again.
        """
        # Ensure we have pricing data
        if not self.cached_fees:
            try:
                self.fetch_pricing()
            except Exception as e:
                logger.warning("Failed to fetch pricing data: %s", str(e))
                return 0.0
        
        # Check if we have fee data for this corridor
        if send_currency not in self.cached_fees:
            logger.debug("No fee data for send currency %s", send_currency)
            return 0.0
            
        if receive_currency not in self.cached_fees.get(send_currency, {}):
            logger.debug("No fee data for corridor %s to %s", send_currency, receive_currency)
            return 0.0
            
        # Find the applicable fee tier
        tiers = self.cached_fees[send_currency][receive_currency]
        for tier in tiers:
            if tier.get("from", 0) <= send_amount <= tier.get("to", float('inf')):
                # Get the base fee
                fee = tier.get("price", 0)
                
                # Add differential FX fee if applicable
                diff_fee_pct = tier.get("differentialFxFee", 0)
                if diff_fee_pct > 0:
                    diff_fee = send_amount * diff_fee_pct
                    fee += diff_fee
                    
                logger.debug("Found fee for %s %s to %s: %s", 
                           send_amount, send_currency, receive_currency, fee)
                return fee
                
        logger.debug("No matching fee tier found for amount %s %s", send_amount, send_currency)
        return 0.0  # Default to zero fee if no tier matches
        """

    def is_corridor_supported(self, send_country: str, receive_country: str) -> bool:
        """
        Check if a specific corridor is supported based on our predefined list 
        or by verifying in the rates data.
        
        Args:
            send_country: ISO country code of the sending country (e.g., 'IL', 'GB')
            receive_country: ISO country code of the receiving country (e.g., 'PH', 'IN')
            
        Returns:
            True if the corridor is supported, False otherwise
        """
        # First check our predefined list for common corridors
        if (send_country, receive_country) in self.SUPPORTED_CORRIDORS:
            return True
            
        # If not in the predefined list, check the rates data
        self._ensure_rates_loaded()
        
        if send_country not in self.cached_rates:
            logger.debug("Send country %s not found in rates data", send_country)
            return False
            
        # Convert country to currency for receive side
        receive_currency = self._get_receive_currency(receive_country)
        
        # Check if the receive currency is available for this send country
        if receive_currency in self.cached_rates.get(send_country, {}):
            # Add to supported corridors for future reference
            self.SUPPORTED_CORRIDORS.append((send_country, receive_country))
            return True
            
        return False

    def get_supported_countries(self, base_currency: str = None) -> List[str]:
        """
        Return a list of sending country codes from the rates data,
        or optionally filter if we only want ones that support `base_currency`.
        The Rewire rates data is structured by sending country code (IL, GB, DE, etc.).
        
        Args:
            base_currency: Optional currency code to filter by
            
        Returns:
            List of country codes
        """
        self._ensure_rates_loaded()
        countries = list(self.cached_rates.keys())  # e.g. ["IL", "GB", "DE", "IT", ...]
        countries.sort()

        # If you want to filter by currency, you'd check if that
        # base currency is in any of the "buy" or "sell" pairs.
        if base_currency:
            filtered_countries = []
            for country in countries:
                currencies = self.cached_rates.get(country, {})
                if base_currency in currencies:
                    filtered_countries.append(country)
            return filtered_countries

        return countries

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_country: str,
        send_currency: str,
        receive_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Return an exchange rate + fee for send_country -> receive_currency,
        referencing the 'buy' or 'sell' rate from the Rewire JSON.

        For Rewire, if the user is sending from IL (Israel) with currency "ILS",
        we might look up:  self.cached_rates["IL"]["PHP"].{'buy','sell'}

        Usually:
         - "buy" indicates how many local currency units you get for 1 unit of `receive_currency`.
         - "sell" is how many local currency units you pay for 1 unit of `receive_currency`.
        
        Args:
            send_amount: The amount to send in the source currency
            send_country: ISO country code of the sending country (e.g., 'IL', 'GB')  
            send_currency: The currency code of the sending country (e.g., 'ILS', 'GBP')
            receive_currency: The currency code of the receiving country (e.g., 'PHP', 'INR')
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with exchange rate information
        """
        self._ensure_rates_loaded()

        result = {
            "provider": self.name,
            "send_amount": float(send_amount),
            "send_country": send_country,
            "send_currency": send_currency,
            "receive_currency": receive_currency,
            "success": False,
            "error_message": None
        }

        # Validate if we have that send_country in the rates
        if send_country not in self.cached_rates:
            msg = f"No rates found for send country '{send_country}' in Rewire data."
            logger.error(msg)
            result["error_message"] = msg
            return result

        # Validate if we have the desired receive_currency
        country_rates = self.cached_rates[send_country]
        if receive_currency not in country_rates:
            msg = f"No rates for {receive_currency} from {send_country} in Rewire data."
            logger.error(msg)
            result["error_message"] = msg
            return result

        # Extract rate information
        rewire_rate = country_rates[receive_currency]  # e.g. {"buy": 0.017..., "sell": 58.345...}
        
        # For Rewire, "sell" rate represents how many units of send_currency for 1 unit of receive_currency
        sell_rate = rewire_rate.get("sell", 0)
        if sell_rate == 0:
            msg = "Sell rate is 0—invalid or corridor not available."
            logger.error(msg)
            result["error_message"] = msg
            return result

        # Calculate receive amount based on sell rate
        # If sending 500 ILS and rate is 58.34558 ILS per 1 PHP, then:
        # 500 ILS / 58.34558 = ~8.57 PHP
        receive_amount = float(send_amount) / sell_rate

        # Calculate fee if applicable
        fee = self._get_fee_for_corridor(send_currency, receive_currency, float(send_amount))

        # Return the final result
        result.update({
            "exchange_rate": 1.0 / sell_rate,  # the ratio of 1 send_currency to get X receive_currency
            "receive_amount": receive_amount,
            "fee": fee,
            "success": True,
        })
        return result

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        target_country: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for a money transfer.
        
        Args:
            amount: Amount to send
            source_currency: Currency code of the sending amount (e.g., 'ILS', 'GBP')
            target_country: ISO country code of the receiving country (e.g., 'PH', 'IN')
                           or currency code (e.g., 'PHP', 'INR')
            **kwargs: Additional parameters including send_country
            
        Returns:
            Dictionary with quote information
        """
        # Extract send_country from kwargs to avoid passing it twice
        send_country = kwargs.pop("send_country", None)
        
        # If send_country is not provided, try to infer it from source_currency
        if not send_country:
            # Try to infer send_country from currency
            for country, currency in self.COUNTRY_TO_CURRENCY.items():
                if currency == source_currency:
                    send_country = country
                    break
            
            # If still not found, use a default
            if not send_country:
                # Default to IL (Israel) for ILS, GB for GBP, etc.
                country_map = {
                    "ILS": "IL",
                    "GBP": "GB",
                    "EUR": "DE",
                    "USD": "US",
                }
                send_country = country_map.get(source_currency, "IL")  # Default to Israel
        
        # Check if the send_country is in the rates data
        self._ensure_rates_loaded()
        if send_country not in self.cached_rates:
            # If not found, try to find another country that uses the same currency
            alt_country = None
            for country in self.cached_rates.keys():
                if self.COUNTRY_TO_CURRENCY.get(country) == source_currency:
                    alt_country = country
                    logger.info(f"Using alternative country {alt_country} for currency {source_currency}")
                    break
            
            if alt_country:
                send_country = alt_country
            else:
                # If no alternative found, return an error
                return {
                    "provider": self.name,
                    "send_amount": float(amount),
                    "send_country": send_country,
                    "send_currency": source_currency,
                    "receive_currency": target_country,
                    "success": False,
                    "error_message": f"No rates found for send country '{send_country}' in Rewire data."
                }
        
        # Convert target_country to receive_currency if needed
        receive_currency = target_country
        # If target_country looks like a country code (2 letters), convert to currency
        if len(target_country) == 2 and target_country.isalpha():
            receive_currency = self._get_receive_currency(target_country)
        
        return self.get_exchange_rate(
            send_amount=amount,
            send_country=send_country,
            send_currency=source_currency,
            receive_currency=receive_currency,
            **kwargs
        ) 