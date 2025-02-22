"""Ria Money Transfer provider implementation."""
import json
import logging
import os
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, Optional

import requests

from apps.providers.base.provider import RemittanceProvider

# ------------------------------------------------------------------------------
# 1) LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)

class RiaInitializationError(Exception):
    """Raised when session initialization fails for Ria."""

class RiaCatalogError(Exception):
    """Raised when we fail to get or parse the Ria catalog data."""

# ------------------------------------------------------------------------------
# 2) RIA PROVIDER
# ------------------------------------------------------------------------------
class RiaProvider(RemittanceProvider):
    """
    Ria Money Transfer provider implementation using direct API requests.
    Stores a requests.Session for persistent cookies/headers.
    """
    
    BASE_URL = "https://www.riamoneytransfer.com"
    API_BASE_URL = "https://public.riamoneytransfer.com"
    START_PAGE_URL = f"{BASE_URL}/en-us/send-money"
    CALCULATOR_URL = f"{API_BASE_URL}/MoneyTransferCalculator/Calculate"
    
    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        """Initialize the Ria provider with session + default headers."""
        super().__init__(name="Ria", base_url=self.START_PAGE_URL)
        
        self.user_agent = user_agent or os.environ.get(
            "RIA_DEFAULT_UA",
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/18.3 Safari/605.1.15"
            )
        )
        
        self.logger = logger
        self.logger.debug("Creating RiaProvider instance...")
        
        self._session = requests.Session()
        self.timeout = timeout
        
        # Keep placeholders for session IDs
        self.session_id = str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())
        
        # Track the send amount/currency for building payloads
        self.send_amount: Optional[Decimal] = None
        self.send_currency: Optional[str] = None
        
        self.logger.debug(f"Initialized RiaProvider with UA: {self.user_agent}")
    
    # --------------------------------------------------------------------------
    # 2.1) SESSION INITIALIZATION
    # --------------------------------------------------------------------------
    def _initialize_session(self) -> None:
        """
        Initialize the session with headers/cookies and do a basic GET/OPTIONS
        to ensure we have a valid session context.
        """
        self.logger.debug("Initializing Ria session...")
        
        # Common headers
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": self.user_agent,
            "Origin": self.BASE_URL,
            "Referer": self.START_PAGE_URL,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "AppType": "2",
            "AppVersion": "4.0",
            "Client-Type": "PublicSite",
            "CultureCode": "en-US"
        })
        
        # Basic cookies
        cookies = {
            "SessionId": self.session_id,
            "CorrelationId": self.correlation_id,
            "CultureCode": "en-US",
            "Client-Type": "PublicSite"
        }
        
        for k, v in cookies.items():
            self._session.cookies.set(k, v, domain=".riamoneytransfer.com")
        
        try:
            self.logger.debug("GET start page to fetch initial cookies...")
            resp = self._session.get(self.START_PAGE_URL, timeout=self.timeout)
            resp.raise_for_status()
            
            self.logger.debug("OPTIONS request to ensure CORS for calculator...")
            opts = self._session.options(self.CALCULATOR_URL, timeout=self.timeout)
            opts.raise_for_status()
            
            self.logger.debug("Session initialization succeeded.")
            
        except requests.RequestException as e:
            self.logger.error(f"Failed session init: {e}")
            raise RiaInitializationError("Could not initialize Ria session") from e
    
    # --------------------------------------------------------------------------
    # 2.2) GET CATALOG DATA
    # --------------------------------------------------------------------------
    def get_catalog_data(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        send_country: str = "US",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> Dict:
        """
        Retrieves the Ria catalog data (fees, exchange rates, etc.) for the given
        send amount/currency and receive country.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency code to send (e.g. "USD", "CAD")
            receive_country: Country code to receive in (e.g. "MX", "IN")
            send_country: Country code sending from (e.g. "US", "CA")
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Dictionary containing the catalog data with fees and exchange rates
        """
        # Store for potential further usage
        self.send_amount = send_amount
        self.send_currency = send_currency
        
        # (Re)initialize session
        self._initialize_session()
        
        payload = {
            "transferDetails": {
                "selections": {
                    "countryTo": receive_country,
                    "stateTo": None,
                    "currencyTo": None,  # Will be determined by API
                    "currencyFrom": send_currency,
                    "paymentMethod": "DebitCard",
                    "deliveryMethod": "BankDeposit",
                    "amountFrom": float(send_amount),
                    "amountTo": None,
                    "agentToId": None,
                    "agentToLocationId": None,
                    "promoCode": None,
                    "promoId": 0,
                    "transferReason": None,
                    "shouldCalcAmountFrom": False,
                    "shouldCalcVariableRates": True,
                    "countryFrom": send_country
                }
            }
        }
        
        for attempt in range(1, max_retries + 1):
            self.logger.info(f"Catalog data request attempt {attempt}/{max_retries}")
            
            try:
                resp = self._session.post(
                    self.CALCULATOR_URL,
                    json=payload,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                
                data = resp.json()
                if "model" not in data or "transferDetails" not in data["model"]:
                    err_msg = "Invalid response format"
                    self.logger.error(f"Catalog error: {err_msg}")
                    continue
                
                return data
                
            except (requests.RequestException, ValueError) as e:
                self.logger.error(f"Error retrieving catalog data: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                    continue
                else:
                    raise RiaCatalogError("Max retries reached for Ria catalog data") from e
        
        raise RiaCatalogError("Failed to get valid catalog data")
    
    # --------------------------------------------------------------------------
    # 2.3) GET EXCHANGE RATE
    # --------------------------------------------------------------------------
    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        send_country: str = "US",
    ) -> Optional[Dict]:
        """
        Retrieve exchange rate info from the catalog data.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency code to send (e.g. "USD", "CAD")
            receive_country: Country code to receive in (e.g. "MX", "IN")
            send_country: Country code sending from (e.g. "US", "CA")
            
        Returns:
            Dictionary with exchange rate info or None if not found
        """
        try:
            catalog = self.get_catalog_data(
                send_amount,
                send_currency,
                receive_country,
                send_country=send_country
            )
        except (RiaInitializationError, RiaCatalogError) as e:
            self.logger.error(f"Cannot retrieve exchange rate: {e}")
            return None
        
        try:
            transfer_details = catalog["model"]["transferDetails"]
            calculations = transfer_details["calculations"]
            
            # Find the best rate from variable rates
            best_rate = None
            best_method = None
            
            for rate_info in calculations.get("variableRates", []):
                rate = float(rate_info.get("exchangeRate", 0))
                if best_rate is None or rate > best_rate:
                    best_rate = rate
                    best_method = rate_info
            
            if not best_rate:
                best_rate = float(calculations.get("exchangeRate", 0))
                best_method = {
                    "value": calculations.get("deliveryMethod", "BankDeposit"),
                    "payAgentName": calculations.get("payAgentName", "")
                }
            
            # Return a standard schema with timezone-aware timestamp
            result = {
                "provider": self.name,
                "timestamp": datetime.now(UTC).isoformat(),
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_country": receive_country,
                "exchange_rate": best_rate,
                "transfer_fee": float(calculations.get("transferFee", 0)),
                "service_name": f"{best_method['value']} - {best_method['payAgentName']}".strip(" -"),
                "delivery_time": "0-1 Business Days",  # Default as not provided in API
                "receive_amount": float(calculations.get("amountTo", 0))
            }
            
            self.logger.info(
                f"Found best rate: {best_rate} with fee: {result['transfer_fee']}"
            )
            return result
            
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Error parsing exchange rate data: {e}")
            return None
    
    # --------------------------------------------------------------------------
    # 2.4) TRANSACTION METHODS (STUBS)
    # --------------------------------------------------------------------------
    def create_transaction(self, **kwargs) -> Optional[Dict]:
        """
        Create a new money transfer transaction.
        This is a stub implementation - not yet implemented.
        """
        self.logger.warning("create_transaction() not implemented for Ria.")
        return None

    def get_transaction_status(self, tracking_number: str) -> Optional[Dict]:
        """
        Get the status of an existing transaction.
        This is a stub implementation - not yet implemented.
        """
        self.logger.warning("get_transaction_status() not implemented for Ria.")
        return None
    
    # --------------------------------------------------------------------------
    # 2.5) CONTEXT MANAGER
    # --------------------------------------------------------------------------
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the underlying session on exit."""
        self._session.close()
