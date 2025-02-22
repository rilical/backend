import json
import logging
import os
import random
import time
import uuid
import pprint
from datetime import datetime, UTC
from decimal import Decimal
from typing import Dict, Optional, Any
from urllib.parse import urljoin

import requests

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    WUError,
    WUAuthenticationError,
    WUConnectionError,
    WUValidationError
)

logger = logging.getLogger(__name__)

def log_request_details(logger, method: str, url: str, headers: Dict,
                        params: Dict = None, data: Dict = None):
    logger.debug("\n" + "="*80 + f"\nOUTGOING REQUEST DETAILS:\n{'='*80}")
    logger.debug(f"Method: {method}")
    logger.debug(f"URL: {url}")

    masked_headers = headers.copy()
    sensitive = ['Authorization', 'Cookie', 'X-WU-Correlation-ID', 'X-WU-Transaction-ID']
    for key in sensitive:
        if key in masked_headers:
            masked_headers[key] = '***MASKED***'

    logger.debug("\nHeaders:")
    logger.debug(pprint.pformat(masked_headers))

    if params:
        logger.debug("\nQuery Params:")
        logger.debug(pprint.pformat(params))
    if data:
        logger.debug("\nRequest Body:")
        logger.debug(pprint.pformat(data))

def log_response_details(logger, response):
    logger.debug("\n" + "="*80 + f"\nRESPONSE DETAILS:\n{'='*80}")
    logger.debug(f"Status Code: {response.status_code}")
    logger.debug(f"Reason: {response.reason}")
    logger.debug("\nResponse Headers:")
    logger.debug(pprint.pformat(dict(response.headers)))

    try:
        body = response.json()
        logger.debug("\nJSON Response Body:")
        logger.debug(pprint.pformat(body))
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


class WesternUnionProvider(RemittanceProvider):
    BASE_URL = "https://www.westernunion.com"
    START_PAGE_URL = f"{BASE_URL}/us/en/web/send-money/start"
    CATALOG_URL = f"{BASE_URL}/wuconnect/prices/catalog"

    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        super().__init__(name="Western Union", base_url=self.START_PAGE_URL)
        self.logger = logger
        self.timeout = timeout

        self.user_agent = user_agent or os.environ.get(
            "WU_DEFAULT_UA",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        self._session = requests.Session()
        self.correlation_id: str = ""
        self.transaction_id: str = ""
        self._token = None
        self._token_expiry = None

        self.logger.debug(f"Initialized WesternUnionProvider with UA: {self.user_agent}")

    def _initialize_session(self) -> None:
        self.logger.debug("Initializing WU session...")
        self.correlation_id = f"web-{uuid.uuid4()}"
        self.transaction_id = f"{self.correlation_id}-{int(time.time() * 1000)}"

        self._session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Chromium";v="122", "Google Chrome";v="122", "Not(A:Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-WU-Correlation-ID": self.correlation_id,
            "X-WU-Transaction-ID": self.transaction_id,
            "Origin": self.BASE_URL,
            "Referer": self.START_PAGE_URL,
        })

        cookies = {
            "wu_language": "en_US",
            "wu_region": "us",
            "wu_market": "us",
            "SessionId": f"web-{uuid.uuid4()}",
            "WUCountryCookie_": "US",
            "WULanguageCookie_": "en",
            "resolution_height": "900",
            "resolution_width": "1440",
            "is_tablet": "false",
            "is_mobile": "false",
            "wu_cookies_accepted": "true",
            "wu_analytics_enabled": "true",
            "wu_functional_enabled": "true",
            "wu_marketing_enabled": "true",
        }
        for k, v in cookies.items():
            self._session.cookies.set(k, v, domain=".westernunion.com")

        try:
            time.sleep(random.uniform(0.5, 1.5))
            self.logger.debug("GET start page to fetch initial cookies...")

            log_request_details(
                self.logger, "GET", self.START_PAGE_URL,
                dict(self._session.headers)
            )
            resp = self._session.get(
                self.START_PAGE_URL, timeout=self.timeout, allow_redirects=True
            )
            log_response_details(self.logger, resp)
            resp.raise_for_status()

            for cookie in resp.cookies:
                self._session.cookies.set_cookie(cookie)

            time.sleep(random.uniform(1.0, 2.0))

            self.logger.debug("OPTIONS request to ensure CORS for /catalog...")
            options_headers = {
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "content-type,x-wu-correlation-id,x-wu-transaction-id,"
                    "sec-ch-ua,sec-ch-ua-mobile,sec-ch-ua-platform"
                )
            }
            self._session.headers.update(options_headers)

            log_request_details(
                self.logger, "OPTIONS", self.CATALOG_URL,
                dict(self._session.headers)
            )
            opts = self._session.options(
                self.CATALOG_URL,
                timeout=self.timeout
            )
            log_response_details(self.logger, opts)
            opts.raise_for_status()

            for header in options_headers:
                self._session.headers.pop(header, None)

            time.sleep(random.uniform(2.0, 3.0))

            self.logger.debug("Session initialization succeeded.")

        except requests.RequestException as e:
            self.logger.error(f"Failed session init: {e}")
            resp_text = getattr(e.response, 'text', '') if e.response else ''
            self.logger.error(f"Response text: {resp_text}")
            raise WUConnectionError(
                "Could not initialize WU session",
                error_code="INIT_FAILED",
                details={"original_error": str(e)}
            )

    def get_exchange_rate(self,
                          send_amount: Decimal,
                          send_currency: str,
                          receive_country: str,
                          send_country: str = "US"
    ) -> Optional[Dict]:
        if not self._is_token_valid():
            self._refresh_token()

        try:
            catalog_data = self.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
        except (WUError, WUConnectionError, WUValidationError):
            return None

        try:
            best_rate = None
            best_service = None

            for category in catalog_data.get("categories", []):
                if category.get("type") == "bestfx":
                    for svc in category.get("services", []):
                        rate = float(svc.get("fx_rate", 0))
                        if rate > 0 and (best_rate is None or rate > best_rate):
                            best_rate = rate
                            pay_out_val = svc.get("pay_out")
                            pay_in_val = svc.get("pay_in")
                            best_service = self._find_service_group(
                                catalog_data, pay_out_val, pay_in_val
                            )

            if not best_rate:
                for group in catalog_data.get("services_groups", []):
                    for pg in group.get("pay_groups", []):
                        rate = float(pg.get("fx_rate", 0))
                        if rate > 0 and (best_rate is None or rate > best_rate):
                            best_rate = rate
                            best_service = {
                                "name": group.get("service_name", "Unknown"),
                                "fee": float(pg.get("gross_fee", 0)),
                                "receive_amount": float(pg.get("receive_amount", 0)),
                                "delivery_time": f"{group.get('speed_days', 1)} Business Days"
                            }

            if not best_rate or not best_service:
                self.logger.warning("No valid exchange rate found in catalog data")
                return None

            return {
                "provider": self.name,
                "timestamp": datetime.now(UTC).isoformat(),
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_country": receive_country,
                "exchange_rate": best_rate,
                "transfer_fee": best_service["fee"],
                "service_name": best_service["name"],
                "delivery_time": best_service["delivery_time"],
                "receive_amount": best_service["receive_amount"]
            }

        except (TypeError, ValueError, KeyError) as e:
            self.logger.error(f"Error parsing catalog data: {e}")
            raise WUValidationError(
                "Failed to parse catalog response",
                error_code="PARSE_ERROR",
                details={"error": str(e)}
            )

    def get_catalog_data(self,
                         send_amount: Decimal,
                         send_currency: str,
                         receive_country: str,
                         send_country: str = "US",
                         sender_postal_code: Optional[str] = None,
                         sender_city: Optional[str] = None,
                         sender_state: Optional[str] = None
    ) -> Dict:
        self._initialize_session()

        country_to_currency = {
            "US": "USD",
            "GB": "GBP",
            "IN": "INR",
            "EG": "EGP",
            "MX": "MXN",
        }

        payload = {
            "header_reply": {
                "response_type": "not_present",
                "source_app": "defaultSource",
                "correlation_id": self.correlation_id
            },
            "sender": {
                "channel": "WWEB",
                "client": "WUCOM",
                "cty_iso2_ext": send_country,
                "curr_iso3": send_currency,
                "cpc": send_country,
                "funds_in": "*",
                "segment": "N00",
                "send_amount": float(send_amount)
            },
            "receiver": {
                "cty_iso2_ext": receive_country,
                "curr_iso3": country_to_currency.get(receive_country)
            }
        }

        if any([sender_postal_code, sender_city, sender_state]):
            payload["sender"].update({
                "postal_code": sender_postal_code,
                "city": sender_city,
                "state": sender_state
            })

        try:
            log_request_details(
                self.logger, "POST", self.CATALOG_URL,
                dict(self._session.headers),
                data=payload
            )
            response = self._session.post(
                self.CATALOG_URL,
                json=payload,
                timeout=self.timeout
            )
            log_response_details(self.logger, response)
            response.raise_for_status()

            data = response.json()
            if not data.get("services_groups"):
                raise WUValidationError(
                    "Invalid catalog response format",
                    error_code="INVALID_RESPONSE",
                    details={"response": data}
                )
            return data

        except requests.RequestException as e:
            self.logger.error(f"Failed to get catalog data: {e}")
            resp_text = getattr(e.response, 'text', '') if e.response else ''
            self.logger.error(f"Response text: {resp_text}")
            raise WUConnectionError(
                "Failed to get Western Union catalog data",
                error_code="CATALOG_FAILED",
                details={"original_error": str(e)}
            )

    def _find_service_group(self, data, pay_out_val, pay_in_val):
        for group in data.get("services_groups", []):
            if group.get("service") == pay_out_val:
                for pay_group in group.get("pay_groups", []):
                    if pay_group.get("fund_in") == pay_in_val:
                        return {
                            "name": group.get("service_name", "Unknown"),
                            "fee": float(pay_group.get("gross_fee", 0)),
                            "receive_amount": float(pay_group.get("receive_amount", 0)),
                            "delivery_time": f"{group.get('speed_days', 1)} Business Days"
                        }
        return None

    def _is_token_valid(self) -> bool:
        return True

    def _refresh_token(self):
        pass
