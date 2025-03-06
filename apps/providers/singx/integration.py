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

logger = logging.getLogger(__name__)

class SingXProvider(RemittanceProvider):
    """
    SingX integration for retrieving fees, exchange rates, and quotes.
    
    Supported Payment Methods:
    - Bank Transfer (default)
    - SWIFT Transfer
    - Cash Pickup
    - Wallet Transfer
    
    Supported Corridors:
    - Singapore (SGD) to:
        - India (INR)
        - Philippines (PHP)
        - Indonesia (IDR)
        - Malaysia (MYR)
        - And more...
    """
    
    BASE_URL = "https://api.singx.co"
    API_VERSION = "central/landing/fx"
    
    # Country codes mapping
    COUNTRY_CODES = {
        "SG": "59C3BBD2-5D26-4A47-8FC1-2EFA628049CE",  # Singapore
        "IN": "A5001AED-DDA1-4296-8312-223D383F96F5",  # India
        "PH": "B6112BFE-E482-4507-9423-334D385F96F6",  # Philippines
        "ID": "C7223CFF-F593-5618-0534-445E496G07G7",  # Indonesia
        "MY": "D8334DGG-G604-6729-1645-556F507H18H8",  # Malaysia
    }
    
    def __init__(self, config=None):
        """Initialize the SingX provider."""
        super().__init__(name="singx", base_url=self.BASE_URL)
        self.config = config or {}
        self.session = self._setup_session()
    
    def _setup_session(self) -> requests.Session:
        """Set up a requests session with default headers."""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
            "Origin": "https://www.singx.co",
            "Referer": "https://www.singx.co/"
        })
        return session
    
    def _validate_country(self, country_code: str) -> str:
        """Validate and return the country UUID."""
        country_id = self.COUNTRY_CODES.get(country_code.upper())
        if not country_id:
            raise SingXValidationError(f"Unsupported country: {country_code}")
        return country_id
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        try:
            data = response.json()
            
            if response.status_code == 200:
                if data.get("errors"):
                    raise SingXAPIError(
                        message=data["errors"][0] if data["errors"] else "API Error",
                        status_code=response.status_code,
                        response=data
                    )
                return data
            
            elif response.status_code == 401:
                raise SingXAuthError(
                    message="Authentication failed",
                    status_code=response.status_code,
                    response=data
                )
            
            else:
                raise SingXAPIError(
                    message=f"API request failed with status {response.status_code}",
                    status_code=response.status_code,
                    response=data
                )
                
        except json.JSONDecodeError:
            raise SingXAPIError(
                message="Invalid JSON response",
                status_code=response.status_code,
                response=response.text
            )
    
    def get_exchange_rate(
        self,
        send_country: str,
        send_currency: str,
        receive_country: str,
        receive_currency: str,
        amount: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get the exchange rate for a currency pair.
        
        Args:
            send_country: Source country code (e.g., 'SG')
            send_currency: Source currency code (e.g., 'SGD')
            receive_country: Destination country code (e.g., 'IN')
            receive_currency: Destination currency code (e.g., 'INR')
            amount: Optional amount to get specific rate tier
            
        Returns:
            Dict containing exchange rate details
        """
        try:
            # Validate countries
            from_country_id = self._validate_country(send_country)
            to_country_id = self._validate_country(receive_country)
            
            # Prepare request data
            data = {
                "fromCurrency": send_currency,
                "toCurrency": receive_currency,
                "amount": str(amount) if amount else "1000.00",
                "type": "Send",
                "swift": kwargs.get("swift", False),
                "cashPickup": kwargs.get("cash_pickup", False),
                "wallet": kwargs.get("wallet", False),
                "business": kwargs.get("business", False)
            }
            
            # Make API request
            response = self.session.post(
                f"{self.BASE_URL}/{self.API_VERSION}/{send_country}/exchange",
                json=data
            )
            
            result = self._handle_response(response)
            
            return {
                "success": True,
                "source_country": send_country,
                "source_currency": send_currency,
                "target_country": receive_country,
                "target_currency": receive_currency,
                "rate": result["exchangeRate"],
                "fee": result["singxFee"],
                "quote_id": result["quote"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get exchange rate: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_quote(
        self,
        send_amount: Optional[Decimal] = None,
        receive_amount: Optional[Decimal] = None,
        send_currency: str = "SGD",
        receive_currency: str = "INR",
        send_country: str = "SG",
        receive_country: str = "IN",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for money transfer.
        
        Args:
            send_amount: Amount to send (optional)
            receive_amount: Amount to receive (optional)
            send_currency: Source currency code
            receive_currency: Target currency code
            send_country: Source country code
            receive_country: Target country code
            
        Returns:
            Dict containing quote details
        """
        try:
            # Validate that either send or receive amount is provided
            if not send_amount and not receive_amount:
                raise SingXValidationError("Either send_amount or receive_amount must be provided")
            
            # Prepare request data
            data = {
                "fromCurrency": send_currency,
                "toCurrency": receive_currency,
                "amount": str(send_amount if send_amount else receive_amount),
                "type": "Send" if send_amount else "Receive",
                "swift": kwargs.get("swift", False),
                "cashPickup": kwargs.get("cash_pickup", False),
                "wallet": kwargs.get("wallet", False),
                "business": kwargs.get("business", False)
            }
            
            # Make API request
            response = self.session.post(
                f"{self.BASE_URL}/{self.API_VERSION}/{send_country}/exchange",
                json=data
            )
            
            result = self._handle_response(response)
            
            return {
                "success": True,
                "send_amount": result["sendAmount"],
                "receive_amount": result["receiveAmount"],
                "fee": result["singxFee"],
                "rate": result["exchangeRate"],
                "total_cost": result["totalPayable"],
                "quote_id": result["quote"],
                "send_currency": send_currency,
                "receive_currency": receive_currency,
                "provider": "singx",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_fees(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_currency: str,
        send_country: str = "SG",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get fees for a transfer.
        
        Args:
            send_amount: Amount to send
            send_currency: Source currency code
            receive_currency: Target currency code
            send_country: Source country code
            
        Returns:
            Dict containing fee details
        """
        try:
            # Get quote to calculate fees
            quote = self.get_quote(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_currency=receive_currency,
                send_country=send_country,
                **kwargs
            )
            
            if not quote["success"]:
                raise SingXQuoteError(quote.get("error", "Failed to get quote"))
            
            return {
                "success": True,
                "transfer_fee": quote["fee"],
                "total_fee": quote["fee"],  # SingX combines all fees
                "fee_currency": send_currency
            }
            
        except Exception as e:
            logger.error(f"Failed to get fees: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 