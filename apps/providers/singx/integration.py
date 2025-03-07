"""
SingX API Integration Module

This module provides integration with the SingX remittance service.
It supports money transfers from Singapore to various countries with multiple payment methods.

Features:
- Exchange rate retrieval
- Fee calculation
- Quote generation
- Multiple corridors support
- Various payment methods (SWIFT, Cash Pickup, Wallet)

API Documentation:
Base URL: https://api.singx.co
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    SingXError,
    SingXAuthError,
    SingXAPIError,
    SingXValidationError,
    SingXCorridorError,
    SingXQuoteError,
    SingXRateError
)

# Import SingX-specific mappings
from apps.providers.singx.singx_mappings import (
    COUNTRY_CODES,
    SUPPORTED_CORRIDORS,
    API_CONFIG,
    DEFAULT_VALUES,
    is_corridor_supported,
    get_delivery_methods_for_country,
    get_payment_methods_for_country,
    get_country_uuid,
    is_country_supported,
    get_default_currency_for_country
)

logger = logging.getLogger(__name__)

class SingXProvider(RemittanceProvider):
    """
    Aggregator-ready SingX integration.
    
    - No fallback or mock data is used: if the SingX API call fails or 
      the corridor is unsupported, returns success=False with an error_message.
    - If successful, returns aggregator-standard quote fields.
    
    Usage:
        singx = SingXProvider()
        quote = singx.get_quote(
            amount=Decimal("1000"),
            source_currency="SGD",
            destination_currency="INR",
            source_country="SG",
            destination_country="IN"
        )
    """

    # Base URL for SingX
    BASE_URL = API_CONFIG["base_url"]
    
    # API version and paths
    API_VERSION = API_CONFIG["api_version"]
    
    # Mapping from 2-letter country code to SingX internal UUID
    COUNTRY_CODES = COUNTRY_CODES
    
    # Default values
    DEFAULT_PAYMENT_METHOD = DEFAULT_VALUES["payment_method"]
    DEFAULT_DELIVERY_METHOD = DEFAULT_VALUES["delivery_method"]
    DEFAULT_DELIVERY_TIME = DEFAULT_VALUES["delivery_time_minutes"]

    def __init__(self, name="singx", base_url: Optional[str] = None, config: Optional[Dict] = None):
        """
        Initialize the aggregator-ready SingX provider.
        
        Args:
            name: Provider identifier
            base_url: Optional URL override
            config: Optional configuration dict
        """
        super().__init__(name=name, base_url=base_url or self.BASE_URL)
        self.config = config or {}
        self.session = self._setup_session()
        self.logger = logging.getLogger(f"providers.{name}")
        self.logger.debug("Initialized SingX provider")

    def _setup_session(self) -> requests.Session:
        """
        Create and configure a requests Session with standard headers.
        
        Returns:
            Configured requests Session
        """
        session = requests.Session()
        session.headers.update(API_CONFIG["headers"])
        return session

    def standardize_response(
        self,
        raw_result: Dict[str, Any],
        provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Convert local result dictionary into aggregator's standard shape.
        
        Args:
            raw_result: Provider-specific response
            provider_specific_data: Whether to include raw provider data
            
        Returns:
            Standardized response dictionary
        """
        now_ts = datetime.utcnow().isoformat()
        output = {
            "provider_id": self.name,
            "success": raw_result.get("success", False),
            "error_message": raw_result.get("error_message"),
            "send_amount": raw_result.get("send_amount", 0.0),
            "source_currency": raw_result.get("source_currency", "").upper(),
            "destination_amount": raw_result.get("destination_amount", 0.0),
            "destination_currency": raw_result.get("destination_currency", "").upper(),
            "exchange_rate": raw_result.get("exchange_rate"),
            "fee": raw_result.get("fee", 0.0),
            "payment_method": raw_result.get("payment_method", self.DEFAULT_PAYMENT_METHOD),
            "delivery_method": raw_result.get("delivery_method", self.DEFAULT_DELIVERY_METHOD),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes", self.DEFAULT_DELIVERY_TIME),
            "timestamp": raw_result.get("timestamp", now_ts),
        }
        
        # Include available delivery and payment methods if present
        if "available_delivery_methods" in raw_result:
            self.logger.debug(f"Preserving {len(raw_result['available_delivery_methods'])} delivery methods in standardized response")
            output["available_delivery_methods"] = raw_result["available_delivery_methods"]
            
        if "available_payment_methods" in raw_result:
            self.logger.debug(f"Preserving {len(raw_result['available_payment_methods'])} payment methods in standardized response")
            output["available_payment_methods"] = raw_result["available_payment_methods"]
        
        if provider_specific_data and "raw_response" in raw_result:
            output["raw_response"] = raw_result["raw_response"]
        
        return output

    def validate_country(self, country_code: str) -> str:
        """
        Validate a country code and return SingX's internal UUID.
        
        Args:
            country_code: Two-letter country code (e.g., "SG")
            
        Returns:
            SingX's internal UUID for the country
            
        Raises:
            SingXValidationError: If the country is not supported
        """
        country_uuid = get_country_uuid(country_code)
        if not country_uuid:
            raise SingXValidationError(f"Unsupported or unknown country code: {country_code}")
        return country_uuid

    def validate_corridor(
        self,
        source_country: str,
        source_currency: str,
        destination_country: str,
        destination_currency: str
    ) -> bool:
        """
        Validate if a corridor is supported.
        
        Args:
            source_country: Source country code (e.g., "SG")
            source_currency: Source currency code (e.g., "SGD")
            destination_country: Destination country code (e.g., "IN")
            destination_currency: Destination currency code (e.g., "INR")
            
        Returns:
            True if the corridor is supported
            
        Raises:
            SingXCorridorError: If the corridor is not supported
        """
        if not is_corridor_supported(source_country, source_currency, destination_country, destination_currency):
            raise SingXCorridorError(
                f"Unsupported corridor: {source_country}({source_currency}) to {destination_country}({destination_currency})"
            )
        return True

    def handle_singx_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle the raw SingX API response, raise errors if unsuccessful.
        
        Args:
            response: Response from SingX API
            
        Returns:
            JSON data from the response
            
        Raises:
            SingXAPIError: If the response indicates an error
        """
        if response.status_code != 200:
            msg = (
                f"SingX API request failed (HTTP {response.status_code}): "
                f"{response.text[:200]} ..."
            )
            raise SingXAPIError(msg)

        try:
            data = response.json()
        except json.JSONDecodeError:
            raise SingXAPIError("Invalid JSON response from SingX")

        # Check if there are known error fields in the response
        if "errors" in data and data["errors"]:
            # Example: data["errors"] might be a list of error strings
            msg = data["errors"][0] if isinstance(data["errors"], list) and data["errors"] else "SingX API error"
            raise SingXAPIError(msg)

        return data

    def build_request_body(
        self,
        send_country: str,
        send_currency: str,
        receive_country: str,
        receive_currency: str,
        amount_str: str,
        flow_type: str = "Send",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build the JSON payload for SingX exchange/quote requests.
        
        Args:
            send_country: Source country code (e.g., "SG")
            send_currency: Source currency code (e.g., "SGD")
            receive_country: Destination country code (e.g., "IN")
            receive_currency: Destination currency code (e.g., "INR")
            amount_str: Amount as a string
            flow_type: "Send" or "Receive"
            **kwargs: Additional parameters
            
        Returns:
            Request body as a dictionary
        """
        # Some optional flags for advanced usage
        swift = kwargs.get("swift", False)
        cash_pickup = kwargs.get("cash_pickup", False)
        wallet = kwargs.get("wallet", False)
        business = kwargs.get("business", False)

        body = {
            "fromCurrency": send_currency.upper(),
            "toCurrency": receive_currency.upper(),
            "amount": amount_str,
            "type": flow_type,    # "Send" or "Receive"
            "swift": swift,
            "cashPickup": cash_pickup,
            "wallet": wallet,
            "business": business
        }
        return body

    def get_quote(
        self,
        amount: Optional[Decimal] = None,
        receive_amount: Optional[Decimal] = None,
        source_currency: str = "SGD",
        destination_currency: str = "INR",
        source_country: str = "SG",
        destination_country: str = "IN",
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote from SingX for either send_amount or receive_amount.
        No fallback data if it fails, returns success=False + error_message.
        
        Args:
            amount: Amount to send
            receive_amount: Amount to receive
            source_currency: Source currency code (e.g., "SGD")
            destination_currency: Destination currency code (e.g., "INR")
            source_country: Source country code (e.g., "SG")
            destination_country: Destination country code (e.g., "IN")
            payment_method: Payment method
            delivery_method: Delivery method
            **kwargs: Additional parameters
            
        Returns:
            Standardized quote dictionary
        """
        # Normalize inputs
        source_country = source_country.upper()
        destination_country = destination_country.upper()
        source_currency = source_currency.upper()
        destination_currency = destination_currency.upper()
        
        if not payment_method:
            payment_method = self.DEFAULT_PAYMENT_METHOD
        if not delivery_method:
            delivery_method = self.DEFAULT_DELIVERY_METHOD
        
        # Default currency if not provided
        if not source_currency and source_country:
            source_currency = get_default_currency_for_country(source_country)
        if not destination_currency and destination_country:
            destination_currency = get_default_currency_for_country(destination_country)
        
        # Basic result for aggregator
        base_result = {
            "success": False,
            "error_message": None,
            "send_amount": float(amount or 0.0),
            "source_currency": source_currency,
            "destination_currency": destination_currency,
            "payment_method": payment_method,
            "delivery_method": delivery_method,
            "delivery_time_minutes": self.DEFAULT_DELIVERY_TIME
        }

        # Ensure either amount or receive_amount is provided
        if not amount and not receive_amount:
            msg = "Either 'amount' or 'receive_amount' must be provided"
            base_result["error_message"] = msg
            return self.standardize_response(base_result)

        try:
            # Validate inputs
            if not is_country_supported(source_country):
                raise SingXValidationError(f"Unsupported source country: {source_country}")
            if not is_country_supported(destination_country):
                raise SingXValidationError(f"Unsupported destination country: {destination_country}")
            
            # Validate corridor
            self.validate_corridor(source_country, source_currency, destination_country, destination_currency)

            # Get available delivery methods for this destination
            available_delivery_methods = get_delivery_methods_for_country(destination_country)
            if available_delivery_methods:
                base_result["available_delivery_methods"] = available_delivery_methods
            
            # Get available payment methods for this source
            available_payment_methods = get_payment_methods_for_country(source_country)
            if available_payment_methods:
                base_result["available_payment_methods"] = available_payment_methods
            
            # Determine if we need any special flags based on the delivery method
            cash_pickup = False
            wallet = False
            
            if delivery_method == "cash_pickup":
                cash_pickup = True
            elif delivery_method == "mobile_wallet":
                wallet = True

            # Prepare request body
            # type="Send" if we have a send_amount, otherwise "Receive"
            flow_type = "Send" if amount else "Receive"
            # Use str of either amount or receive_amount
            amt_str = str(amount if amount else receive_amount)

            body = self.build_request_body(
                send_country=source_country,
                send_currency=source_currency,
                receive_country=destination_country,
                receive_currency=destination_currency,
                amount_str=amt_str,
                flow_type=flow_type,
                cash_pickup=cash_pickup,
                wallet=wallet,
                **kwargs
            )

            # Construct the endpoint URL
            endpoint = f"{self.base_url}/{self.API_VERSION}/{source_country}/exchange"
            
            # Make the API call
            self.logger.debug(f"Sending request to {endpoint} with body: {body}")
            resp = self.session.post(endpoint, json=body, timeout=API_CONFIG["timeout"])
            data = self.handle_singx_response(resp)
            self.logger.debug(f"Received response: {data}")

            # Check if data has required fields
            if not all(k in data for k in ("sendAmount", "receiveAmount", "singxFee", "exchangeRate")):
                msg = "Missing required fields (sendAmount/receiveAmount/singxFee/exchangeRate) in SingX response"
                base_result["error_message"] = msg
                return self.standardize_response(base_result)

            # Mark success, fill aggregator fields
            base_result.update({
                "success": True,
                "send_amount": float(data["sendAmount"]),
                "destination_amount": float(data["receiveAmount"]),
                "fee": float(data["singxFee"]),
                "exchange_rate": float(data["exchangeRate"]),
                "timestamp": datetime.utcnow().isoformat(),
                "raw_response": data
            })

            # Include quote ID if available
            if "quote" in data:
                base_result["quote_id"] = data["quote"]

            self.logger.info(
                f"SingX quote success: {base_result['send_amount']} {source_currency} → "
                f"{base_result['destination_amount']} {destination_currency} "
                f"(rate={base_result['exchange_rate']}, fee={base_result['fee']})"
            )

            return self.standardize_response(base_result, provider_specific_data=True)

        except (SingXValidationError, SingXAPIError, SingXCorridorError) as sx_err:
            msg = f"SingX error: {sx_err}"
            self.logger.error(msg, exc_info=True)
            base_result["error_message"] = str(sx_err)
            return self.standardize_response(base_result)

        except Exception as e:
            msg = f"Unexpected error in SingX quote: {e}"
            self.logger.error(msg, exc_info=True)
            base_result["error_message"] = str(e)
            return self.standardize_response(base_result)

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_country: str,
        send_currency: str,
        receive_country: str,
        receive_currency: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Legacy aggregator method for retrieving an exchange rate from SingX.
        
        Args:
            send_amount: Amount to send
            send_country: Source country code (e.g., "SG")
            send_currency: Source currency code (e.g., "SGD")
            receive_country: Destination country code (e.g., "IN")
            receive_currency: Destination currency code (e.g., "INR")
            **kwargs: Additional parameters
            
        Returns:
            Standardized quote dictionary
        """
        return self.get_quote(
            amount=send_amount,
            source_currency=send_currency,
            destination_currency=receive_currency,
            source_country=send_country,
            destination_country=receive_country,
            **kwargs
        )

    def close(self):
        """Close the session if needed."""
        if self.session:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Legacy class name for backward compatibility
class SingXAggregatorProvider(SingXProvider):
    """Legacy class name for backward compatibility."""
    pass 