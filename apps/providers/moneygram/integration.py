import json
import logging
import os
import time
import uuid
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, Optional, Any
import random
import pprint
import re
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

class MGError(Exception):
    """Generic MoneyGram error."""

class MoneyGramProvider:
    """
    Provider for MoneyGram's public API endpoints.
    """
    
    BASE_URL = "https://www.moneygram.com"
    START_PAGE_PATH = "/mgo/us/en/"  # appended to BASE_URL
    API_BASE_URL = "https://consumerapi.moneygram.com"
    FEE_LOOKUP_PATH = "/services/capi/api/v1/sendMoney/feeLookup"
    
    def __init__(self, timeout: int = 30):
        self.logger = logger
        self.session = requests.Session()
        self.timeout = timeout
        self.session_id = f"web-{uuid.uuid4()}"
        self.logger.info("Initialized MoneyGram provider.")
    
    def _init_session(self) -> None:
        """
        Initialize a new session with required headers and attempt
        to handle Incapsula/in-cap cookies. Also parse utmvc= if present.
        """
        # Recreate session so each test is fresh
        self.session = requests.Session()
        
        # Potential Incapsula placeholders; these might help but may not be strictly necessary
        incap_session = str(random.randint(100000, 999999))
        visid_incap = ''.join(random.choices('0123456789abcdef', k=32))
        
        # Some initial cookies (these can be optional)
        self.session.cookies.set(
            "visid_incap_1212967", visid_incap,
            domain=".moneygram.com", path="/"
        )
        self.session.cookies.set(
            "incap_ses_1244_1212967", incap_session,
            domain=".moneygram.com", path="/"
        )
        self.session.cookies.set(
            "MGUserConsent", "true",
            domain=".moneygram.com", path="/"
        )
        
        # Headers
        self.session.headers.update({
            # Latest stable Chrome on Windows
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            
            # Updated client hints for Chrome 121
            "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            
            # Additional security headers
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-User": "?1",
            
            # MoneyGram specific headers
            "clientKey": (
                "Basic V0VCX2VkYjI0ZDc5LTA0ODItNDdlMi1hNmQ2LTc4ZGY5YzI4MmM0ZTo1"
                "MTNlMTEyOS0yZTJmLTRlYmUtYjkwMi02YTVkMGViMDNjZjc="
            ),
            "locale-header": "en_US",
            "X-MG-Web-Client": "web",
            "X-MG-Session-ID": str(uuid.uuid4()),
            
            # Additional headers that might help
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            
            # Standard headers
            "Origin": "https://www.moneygram.com",
            "Referer": "https://www.moneygram.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })

        # Add additional cookies that might help with browser verification
        self.session.cookies.update({
            "mgui_cookie_policy": "accepted",
            "mgui_cookie_marketing": "accepted",
            "mgui_cookie_analytics": "accepted",
            "mgui_cookie_functional": "accepted",
            "mgui_cookie_strictly": "accepted"
        })

        start_page_url = urljoin(self.BASE_URL, self.START_PAGE_PATH)
        try:
            self.logger.info(f"[Session Init] GET {start_page_url}")
            resp = self.session.get(
                start_page_url,
                timeout=self.timeout,
                allow_redirects=True
            )
            resp.raise_for_status()
            
            # Parse Set-Cookie header for utmvc cookie
            raw_set_cookie = resp.headers.get("Set-Cookie", "")
            if "utmvc=" in raw_set_cookie:
                match = re.search(r"utmvc=([^;]+)", raw_set_cookie)
                if match:
                    utmvc_val = match.group(1)
                    self.session.cookies.set(
                        "utmvc",
                        utmvc_val,
                        domain=".moneygram.com",
                        path="/"
                    )
            
            # Add a short random delay
            time.sleep(random.uniform(1, 2))
            
            # Make a second request to complete any potential challenge
            self.logger.info(f"[Session Init] Second GET {start_page_url}")
            resp = self.session.get(
                start_page_url,
                timeout=self.timeout,
                allow_redirects=True
            )
            resp.raise_for_status()
            
            # Another short delay
            time.sleep(random.uniform(0.5, 1))
            
        except requests.RequestException as e:
            self.logger.error(f"Init session failed: {e}")
            if e.response is not None:
                self.logger.error(f"Status code: {e.response.status_code}")
                self.logger.error(f"Body: {e.response.text[:1000]} ...")
            raise MGError("Session init failed.")
    
    def get_catalog_data(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        send_country: str,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> Dict[str, Any]:
        """Get catalog data for sending money between countries."""
        self._init_session()

        fee_lookup_url = urljoin(self.API_BASE_URL, self.FEE_LOOKUP_PATH)
        params = {
            "sendAmount": str(send_amount),
            "senderCurrency": send_currency,
            "receiveCountry": receive_country,
            "senderCountry": send_country,
            "channel": "web",
            "locale": "en_US"
        }

        for attempt in range(max_retries):
            try:
                self.logger.info(f"GET {fee_lookup_url} (attempt {attempt + 1}/{max_retries})")
                self.logger.debug(f"Params: {params}")
                
                r = self.session.get(
                    fee_lookup_url,
                    params=params,
                    timeout=self.timeout
                )
                r.raise_for_status()
                
                data = r.json()
                self.logger.debug(f"Response: {data}")
                
                if "paymentOptions" not in data:
                    raise MGError("No payment options in response")
                    
                return data

            except (requests.RequestException, json.JSONDecodeError) as e:
                self.logger.error(f"Fee lookup failed (attempt {attempt + 1}): {e}")
                if hasattr(e, "response") and e.response is not None:
                    self.logger.error(f"Status code: {e.response.status_code}")
                    self.logger.error(f"Body: {e.response.text[:1000]} ...")
                
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                    
                raise MGError("Could not get fee data after retries")
    
    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        send_country: str = "USA",
    ) -> Optional[Dict]:
        """
        Return a simplified best exchange-rate result from the first paymentOption found.
        """
        try:
            data = self.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
        except MGError as e:
            self.logger.error(f"Cannot retrieve exchange rate: {e}")
            return None
        
        best_option = None
        best_rate = 0
        
        for pmt in data.get("paymentOptions", []):
            for grp in pmt.get("receiveGroups", []):
                label = grp.get("receiveGroupLabel", "Unknown")
                for opt in grp.get("receiveOptions", []):
                    rate = float(opt.get("exchangeRate", 0))
                    if rate > best_rate:
                        best_rate = rate
                        best_option = {
                            "group": label,
                            "description": opt.get("description", ""),
                            "exchange_rate": rate,
                            "fee": float(opt.get("sendFees", 0)),
                            "receive_amount": float(opt.get("receiveAmount", 0)),
                            "delivery_time": opt.get("estimatedDeliveryDate", ""),
                        }
        
        if not best_option:
            self.logger.warning("No valid exchange rate found.")
            return None
        
        # Build standard structure
        return {
            "provider": "MoneyGram",
            "timestamp": datetime.now(UTC).isoformat(),
            "send_amount": float(send_amount),
            "send_currency": send_currency,
            "receive_country": receive_country,
            **best_option
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    mg = MoneyGramProvider()

    try:
        data = mg.get_catalog_data(Decimal("100"), "USD", "MEX", "USA")
        print("US->MEX catalog data:", json.dumps(data, indent=2))
    except MGError as e:
        print(f"Failed: {e}")
