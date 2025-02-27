"""
Intermex Money Transfer Integration

This module implements the integration with Intermex Money Transfer API.
Intermex offers money transfer services to various countries with multiple payment options.

PAYMENT METHODS:
---------------------------------
- Debit Card (SenderPaymentMethodId=3): Primary method for payments
- Credit Card (SenderPaymentMethodId=4): Alternative payment method

DELIVERY METHODS:
---------------------------------
- Bank Deposit (DeliveryType=W): Direct to bank account
- Cash Pickup (other DeliveryType values): Available in some corridors

Important API notes:
1. The API requires a subscription key in the header (Ocp-Apim-Subscription-Key)
2. Exchange rates vary by delivery method and payment method
3. The API supports both calculating by send amount and by receive amount
"""

import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, Optional, Any, List, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    IntermexError,
    IntermexAuthenticationError,
    IntermexConnectionError,
    IntermexValidationError,
    IntermexRateLimitError
)

logger = logging.getLogger(__name__)


def log_request_details(logger, method: str, url: str, headers: Dict,
                      params: Dict = None, data: Dict = None):
    logger.debug("\n" + "="*80 + f"\nOUTGOING REQUEST DETAILS:\n{'='*80}")
    logger.debug(f"Method: {method}")
    logger.debug(f"URL: {url}")

    masked_headers = headers.copy()
    sensitive = ['Authorization', 'Cookie', 'Ocp-Apim-Subscription-Key']
    for key in sensitive:
        if key in masked_headers:
            masked_headers[key] = '***MASKED***'

    logger.debug("\nHeaders:")
    logger.debug(json.dumps(dict(masked_headers), indent=2))

    if params:
        logger.debug("\nQuery Params:")
        logger.debug(json.dumps(params, indent=2))
    if data:
        logger.debug("\nRequest Body:")
        logger.debug(json.dumps(data, indent=2))


def log_response_details(logger, response):
    logger.debug("\n" + "="*80 + f"\nRESPONSE DETAILS:\n{'='*80}")
    logger.debug(f"Status Code: {response.status_code}")
    logger.debug(f"Reason: {response.reason}")
    logger.debug("\nResponse Headers:")
    logger.debug(json.dumps(dict(response.headers), indent=2))

    try:
        body = response.json()
        logger.debug("\nJSON Response Body:")
        logger.debug(json.dumps(body, indent=2))
    except ValueError:
        body = response.text
        content_type = response.headers.get('content-type', '').lower()
        if 'html' in content_type:
            logger.debug("\nHTML Response (truncated):")
            logger.debug(body[:500] + '...' if len(body) > 500 else body)
        else:
            logger.debug("\nPlain Text Response:")
            logger.debug(body[:1000] + '...' if len(body) > 1000 else body)

    logger.debug("="*80)


class IntermexProvider(RemittanceProvider):
    BASE_URL = "https://api.imxi.com"
    PRICING_ENDPOINT = "/pricing/api/v2/feesrates"
    
    DEFAULT_STYLE_ID = 3
    DEFAULT_TRAN_TYPE_ID = 3
    DEFAULT_CHANNEL_ID = 1
    DEFAULT_PARTNER_ID = 1
    DEFAULT_LANGUAGE_ID = 1
    
    PAYMENT_METHODS = {
        "DebitCard": 3,
        "CreditCard": 4
    }
    
    DELIVERY_METHODS = {
        "BankDeposit": "W"
    }
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30, user_agent: Optional[str] = None):
        super().__init__(name="Intermex", base_url=self.BASE_URL)
        self.logger = logger
        self.timeout = timeout
        
        self.user_agent = user_agent or os.environ.get(
            "INTERMEX_DEFAULT_UA",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
        )
        
        self.api_key = api_key or os.environ.get("INTERMEX_API_KEY", "2162a586e2164623a1cd9b6b2d300b4c")
        self._session = requests.Session()
        self.request_id = str(uuid.uuid4())
        self._initialize_session()
        
        self.logger.debug(f"Initialized IntermexProvider with UA: {self.user_agent}")
        
    def _initialize_session(self) -> None:
        self.logger.debug("Initializing Intermex session...")
        
        self._session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "User-Agent": self.user_agent,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Dest": "empty",
            "Priority": "u=3, i",
            "PartnerId": str(self.DEFAULT_PARTNER_ID),
            "ChannelId": str(self.DEFAULT_CHANNEL_ID),
            "LanguageId": str(self.DEFAULT_LANGUAGE_ID),
            "Origin": "https://www.intermexonline.com",
            "Referer": "https://www.intermexonline.com/"
        })
        
        if self.api_key:
            self._session.headers.update({
                "Ocp-Apim-Subscription-Key": self.api_key
            })
            
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("https://", adapter)
        
    def get_exchange_rate(self,
                         send_amount: Decimal,
                         send_currency: str,
                         receive_country: str,
                         receive_currency: Optional[str] = None,
                         send_country: str = "USA",
                         send_state: str = "PA",
                         payment_method: str = "CreditCard",
                         delivery_method: str = "BankDeposit") -> Optional[Dict]:
        country_to_currency = {
            "USA": "USD",
            "TUR": "TRY",
            "MEX": "MXN",
            "COL": "COP", 
            "PHL": "PHP",
            "GTM": "GTQ",
            "SLV": "USD",
            "HND": "HNL",
            "ECU": "USD",
            "DOM": "DOP",
            "NIC": "NIO",
            "PER": "PEN",
            "AD": "EUR",
            "AR": "ARS",
            "AT": "EUR",
            "BE": "EUR",
            "BO": "BOB",
            "BR": "BRL",
            "BG": "BGN",
            "CM": "XAF",
            "CH": "CLP",
            "CR": "CRC",
            "CI": "XOF",
            "HRV": "EUR",
            "CY": "EUR",
            "CZ": "CZK",
            "DK": "DKK",
            "EGY": "EGP",
            "EE": "EUR",
            "ET": "ETB",
            "FIN": "EUR",
            "FRA": "EUR",
            "DEU": "EUR",
            "GH": "GHS",
            "GRC": "EUR",
            "HT": "HTG",
            "HU": "HUF",
            "ISL": "ISK",
            "IND": "INR",
            "IT": "EUR",
            "JA": "JMD",
            "KE": "KES",
            "LV": "EUR",
            "LIE": "CHF",
            "LTU": "EUR",
            "LUX": "EUR",
            "MLT": "EUR",
            "MCO": "EUR",
            "NLD": "EUR",
            "NG": "NGN",
            "NOR": "NOK",
            "PK": "PKR",
            "PA": "PAB",
            "PE": "PEN",
            "PH": "PHP",
            "PL": "PLN",
            "PRT": "EUR",
            "IRL": "EUR",
            "RP": "DOP",
            "RO": "RON",
            "ROU": "RON",
            "SMR": "EUR",
            "SN": "XOF",
            "SVK": "EUR",
            "SVN": "EUR",
            "ESP": "EUR",
            "SE": "SEK",
            "CHE": "CHF",
            "TH": "THB",
            "VN": "VND",
            "VAT": "EUR",
        }
        
        if not receive_currency:
            receive_currency = country_to_currency.get(receive_country)
            if not receive_currency:
                self.logger.warning(f"No default currency for country {receive_country}")
                return None
        
        payment_method_id = self.PAYMENT_METHODS.get(payment_method, 4)
        
        delivery_type = self.DELIVERY_METHODS.get(delivery_method, "W")
                
        try:
            params = {
                "DestCountryAbbr": receive_country,
                "DestCurrency": receive_currency,
                "OriCountryAbbr": send_country,
                "OriStateAbbr": send_state,
                "StyleId": self.DEFAULT_STYLE_ID,
                "TranTypeId": self.DEFAULT_TRAN_TYPE_ID,
                "DeliveryType": delivery_type,
                "OriCurrency": send_currency,
                "ChannelId": self.DEFAULT_CHANNEL_ID,
                "OriAmount": float(send_amount),
                "DestAmount": 0,
                "SenderPaymentMethodId": payment_method_id
            }
            
            url = f"{self.BASE_URL}{self.PRICING_ENDPOINT}"
            
            log_request_details(self.logger, "GET", url, self._session.headers, params)
            
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            log_response_details(self.logger, response)
            
            if response.status_code != 200:
                error_message = f"Failed to get exchange rate: {response.status_code}"
                if response.status_code == 401:
                    raise IntermexAuthenticationError(error_message)
                elif response.status_code == 400:
                    raise IntermexValidationError(error_message)
                elif response.status_code == 429:
                    raise IntermexRateLimitError("Rate limit exceeded")
                else:
                    raise IntermexError(error_message)
            
            data = response.json()
            
            payment_methods = data.get("paymentMethods", [])
            available_payment_methods = [
                {"id": pm.get("senderPaymentMethodId"), "name": pm.get("senderPaymentMethodName"), "fee": pm.get("feeAmount")}
                for pm in payment_methods if pm.get("isAvailable")
            ]
            
            return {
                "provider": self.name,
                "timestamp": datetime.now(UTC).isoformat(),
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_country": receive_country,
                "receive_currency": receive_currency,
                "exchange_rate": float(data.get("rate", 0)),
                "transfer_fee": float(data.get("feeAmount", 0)),
                "payment_method": payment_method,
                "payment_method_id": payment_method_id,
                "delivery_method": delivery_method,
                "delivery_time": "24-48 hours",
                "receive_amount": float(data.get("destAmount", 0)),
                "available_payment_methods": available_payment_methods,
                "total_amount": float(data.get("totalAmount", 0))
            }
                
        except (IntermexError, IntermexConnectionError, IntermexValidationError) as e:
            self.logger.error(f"Error getting Intermex exchange rate: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in Intermex exchange rate: {e}")
            return None
            
    def get_payment_methods(self, source_country: str = "USA", target_country: str = "TUR") -> List[Dict]:
        try:
            test_amount = Decimal("100.00")
            
            params = {
                "DestCountryAbbr": target_country,
                "OriCountryAbbr": source_country,
                "OriStateAbbr": "PA",
                "StyleId": self.DEFAULT_STYLE_ID,
                "TranTypeId": self.DEFAULT_TRAN_TYPE_ID,
                "DeliveryType": "W",
                "OriCurrency": "USD",
                "ChannelId": self.DEFAULT_CHANNEL_ID,
                "OriAmount": float(test_amount),
                "DestAmount": 0,
                "SenderPaymentMethodId": 4
            }
            
            url = f"{self.BASE_URL}{self.PRICING_ENDPOINT}"
            
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get payment methods: {response.status_code}")
                return []
            
            data = response.json()
            
            payment_methods = data.get("paymentMethods", [])
            return [
                {
                    "id": pm.get("senderPaymentMethodId"),
                    "name": pm.get("senderPaymentMethodName"),
                    "fee": pm.get("feeAmount"),
                    "available": pm.get("isAvailable", False)
                }
                for pm in payment_methods
            ]
                
        except Exception as e:
            self.logger.error(f"Error getting payment methods: {e}")
            return []
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close() 