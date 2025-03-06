"""
Sendwave (Wave) Integration

This module integrates with Sendwave's public endpoint to retrieve
pricing and quote information for remittances.
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, Any, Optional, List

# Import your base provider abstract/parent
from apps.providers.base.provider import RemittanceProvider
from apps.providers.sendwave.exceptions import (
    SendwaveError,
    SendwaveConnectionError,
    SendwaveApiError,
    SendwaveValidationError,
    SendwaveResponseError,
    SendwaveCorridorUnsupportedError
)

logger = logging.getLogger(__name__)


class WaveProvider(RemittanceProvider):
    """
    Wave (Sendwave) provider integration.

    Example usage:

        wave = WaveProvider()
        quote = wave.get_exchange_rate(
            send_amount=Decimal("500"),
            send_currency="USD",
            receive_country="PH"  # Philippines
        )
    """

    # Base URL for Sendwave's public pricing
    BASE_URL = "https://app.sendwave.com"
    PRICING_ENDPOINT = "/v2/pricing-public"

    # A small mapping of country code → default currency
    # so that we can guess the `receiveCurrency` if needed
    COUNTRY_TO_CURRENCY = {
        "PH": "PHP",  # Philippines
        "KE": "KES",  # Kenya
        "UG": "UGX",  # Uganda
        "GH": "GHS",  # Ghana
        # etc.
    }

    # If your code uses corridors:
    SUPPORTED_CORRIDORS = [
        ("USD", "PH"),  # e.g. US → Philippines
        ("USD", "KE"),  # e.g. US → Kenya
        # add more as tested
    ]

    def __init__(self, name="sendwave", base_url: Optional[str] = None, **kwargs):
        """
        Initialize Wave (Sendwave) provider.
        :param name: internal provider name
        :param base_url: override for base URL
        :param kwargs: optional additional config
        """
        super().__init__(name=name, base_url=base_url or self.BASE_URL)
        self.session = requests.Session()
        # Optionally set default headers, e.g. "User-Agent"
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.sendwave.com",
            "Referer": "https://www.sendwave.com/"
        })

    def is_corridor_supported(self, send_currency: str, receive_country: str) -> bool:
        """Check if a corridor is in our SUPPORTED_CORRIDORS list."""
        return (send_currency, receive_country) in self.SUPPORTED_CORRIDORS

    def get_supported_countries(self, base_currency: str = None) -> List[str]:
        """
        Return a list of receiving countries we know are supported,
        optionally filtered by base_currency.
        """
        if base_currency is None:
            # Return all
            return sorted(set(c for (cur, c) in self.SUPPORTED_CORRIDORS))
        else:
            return sorted(c for (cur, c) in self.SUPPORTED_CORRIDORS if cur == base_currency)

    def _get_receive_currency(self, country_code: str) -> str:
        """
        Return the wave 'receiveCurrency' for a given country code,
        using our simple lookup or fallback to 'USD'.
        """
        return self.COUNTRY_TO_CURRENCY.get(country_code, "USD")

    def get_exchange_rate(self, send_amount: Decimal, send_currency: str, receive_country: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a pricing quote from Sendwave for the corridor send_currency -> receive_country,
        sending `send_amount`.
        """
        logger.info(f"Requesting Sendwave quote: {send_currency} to {receive_country} for {send_amount} {send_currency}")

        # Basic result structure
        result = {
            "provider": self.name,
            "send_amount": float(send_amount),
            "send_currency": send_currency,
            "receive_country": receive_country,
            "success": False,
            "error_message": None
        }

        if not self.is_corridor_supported(send_currency, receive_country):
            msg = f"Corridor not in SUPPORTED_CORRIDORS: {send_currency}->{receive_country}"
            logger.warning(msg)
            result["error_message"] = msg
            raise SendwaveCorridorUnsupportedError(msg)

        # In wave's public pricing, you pass "receiveCurrency" as well
        receive_currency = self._get_receive_currency(receive_country)

        # Build the query params based on the example
        # e.g.   amountType=SEND&receiveCurrency=PHP&segmentName=ph_gcash
        #        amount=500&sendCurrency=USD&sendCountryIso2=us&receiveCountryIso2=ph

        # "segmentName" might be something you vary by corridor: e.g. "ph_gcash", "ph_bank", etc.
        # This example uses 'ph_gcash' for the Philippines → GCash corridor
        # If you want a bank deposit or other method, segmentName could differ.
        # We'll keep this minimal for demonstration.
        segment_name = kwargs.get("segment_name", "ph_gcash" if receive_country == "PH" else "")

        # If the user is in the US, wave uses sendCountryIso2=us
        # If the user is in the UK, wave uses sendCountryIso2=gb, etc.
        # We'll guess "us" for USD unless the user sets override in kwargs.
        send_country_iso2 = kwargs.get("send_country_iso2", "us")

        # The final URL
        endpoint_url = f"{self.base_url}{self.PRICING_ENDPOINT}"

        params = {
            "amountType": "SEND",
            "receiveCurrency": receive_currency,
            "segmentName": segment_name,
            "amount": str(send_amount),
            "sendCurrency": send_currency,
            "sendCountryIso2": send_country_iso2,
            "receiveCountryIso2": receive_country.lower()  # 'ph', 'ke', etc.
        }

        try:
            resp = self.session.get(endpoint_url, params=params, timeout=15)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            msg = f"HTTP error fetching wave quote: {exc}"
            logger.error(msg)
            result["error_message"] = msg
            raise SendwaveApiError(msg) from exc
        except requests.ConnectionError as exc:
            msg = f"Connection error fetching wave quote: {exc}"
            logger.error(msg)
            result["error_message"] = msg
            raise SendwaveConnectionError(msg) from exc
        except Exception as e:
            msg = f"Error requesting wave quote: {e}"
            logger.error(msg)
            result["error_message"] = msg
            raise SendwaveError(msg) from e

        # Parse JSON
        try:
            data = resp.json()  # Typically an object with e.g. "receiveAmount", "exchangeRate", "fees", etc.
        except ValueError as ve:
            msg = f"Invalid JSON response from wave: {ve}"
            logger.error(msg)
            result["error_message"] = msg
            raise SendwaveResponseError(msg) from ve

        # Inspect the structure. The actual Sendwave response looks like:
        #   {
        #     "baseExchangeRate": "55.80",
        #     "baseFeeAmount": "0.00",
        #     "baseFeeRateBps": 0,
        #     "baseSendAmount": "500.0",
        #     "campaignsApplied": [...],
        #     "effectiveExchangeRate": "57.864600",
        #     "effectiveFeeAmount": "0.00",
        #     "effectiveFeeRateBps": 0,
        #     "effectiveSendAmount": "500.0",
        #     ...
        #   }

        # Check for required fields in the actual response format
        if "effectiveExchangeRate" not in data or "effectiveSendAmount" not in data:
            msg = "Missing required fields in Sendwave response"
            logger.error(msg)
            result["error_message"] = msg
            raise SendwaveResponseError(msg)

        # Extract the values from the response
        exchange_rate = float(data["effectiveExchangeRate"])
        fee = float(data.get("effectiveFeeAmount", 0.0))
        send_amount = float(data["effectiveSendAmount"])
        
        # Calculate receive amount based on exchange rate and send amount
        receive_amount = send_amount * exchange_rate
        
        # Check if there's any campaign/promotion info
        promotions = []
        if "campaignsApplied" in data and data["campaignsApplied"]:
            for campaign in data["campaignsApplied"]:
                promotions.append({
                    "code": campaign.get("code", ""),
                    "description": campaign.get("description", ""),
                    "value": campaign.get("sendCurrencyValue", "0")
                })

        result.update({
            "receive_currency": receive_currency,
            "exchange_rate": exchange_rate,
            "fee": fee,
            "receive_amount": receive_amount,
            "promotions": promotions,
            "raw_data": data,
            "success": True
        })

        logger.info(
            f"Sendwave quote success: {send_amount} {send_currency} => {receive_amount} {receive_currency} "
            f"(rate={exchange_rate}, fee={fee})"
        )
        return result 