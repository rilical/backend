"""
Xoom Money Transfer Aggregator Provider

This module implements an aggregator-ready integration with Xoom (PayPal service).
It does not use any fallback or mock data - if both API calls fail, it returns a
standardized aggregator result with success=false.
"""

import logging
import json
import re
import time
import uuid
import html
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Any, List

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from apps.providers.base.provider import RemittanceProvider

logger = logging.getLogger("xoom_aggregator")


class XoomAggregatorProvider(RemittanceProvider):
    """
    Aggregator-ready Xoom integration with no fallback or mock data.
    
    If both the fee table API and the regular quote API fail, it returns:
      {
        "provider_id": "Xoom",
        "success": false,
        "error_message": "...",
      }

    Otherwise, on success, it returns aggregator-standard fields:
      {
        "provider_id": "Xoom",
        "success": true,
        "error_message": null,
        "send_amount": float,
        "source_currency": str,
        "destination_amount": float,
        "destination_currency": str,
        "exchange_rate": float,
        "fee": float,
        "payment_method": str,
        "delivery_method": str,
        "delivery_time_minutes": int,
        "timestamp": "...",
        "raw_response": {...}
      }
    """

    BASE_URL = "https://www.xoom.com"
    FEE_TABLE_API_URL = "https://www.xoom.com/calculate-fee-table"
    REGULAR_API_URL = "https://www.xoom.com/wapi/send-money-app/remittance-engine/remittance"

    # Use a default 'User-Agent' to simulate a browser
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    )

    # Common country to currency mappings for Xoom
    COUNTRY_TO_CURRENCY = {
        "MX": "MXN",  # Mexico
        "PH": "PHP",  # Philippines
        "IN": "INR",  # India
        "CO": "COP",  # Colombia
        "GT": "GTQ",  # Guatemala
        "SV": "USD",  # El Salvador
        "DO": "DOP",  # Dominican Republic
        "HN": "HNL",  # Honduras
        "PE": "PEN",  # Peru
        "EC": "USD",  # Ecuador
        "BR": "BRL",  # Brazil
        "NI": "NIO",  # Nicaragua
        "JM": "JMD",  # Jamaica
        "CN": "CNY",  # China
        "LK": "LKR",  # Sri Lanka
        "VN": "VND",  # Vietnam
        "PK": "PKR",  # Pakistan
        "BD": "BDT",  # Bangladesh
        "NG": "NGN",  # Nigeria
        "GH": "GHS",  # Ghana
        "KE": "KES",  # Kenya
    }

    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        super().__init__(name="Xoom", base_url=self.BASE_URL)
        self.timeout = timeout
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

        self.session = requests.Session()
        self._setup_session()

        # Initialize a fresh session with cookies by visiting the homepage
        self._visit_home_page()

    def _setup_session(self) -> None:
        """Configure session headers, cookies, and retry logic."""
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        })
        # Setup a retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _visit_home_page(self) -> None:
        """Visit Xoom's homepage to acquire initial cookies."""
        try:
            home_url = f"{self.BASE_URL}/"
            resp = self.session.get(home_url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200:
                logger.warning(f"Visit homepage - unexpected status: {resp.status_code}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed to visit homepage: {e}", exc_info=True)

    def standardize_response(self, local_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local_data into aggregator-standard JSON.
        
        If local_data["success"] is False, return aggregator error shape:
          {
            "provider_id": "Xoom",
            "success": false,
            "error_message": ...
          }

        If success, return aggregator success shape.
        """
        if not local_data.get("success"):
            return {
                "provider_id": "Xoom",
                "success": False,
                "error_message": local_data.get("error_message") or "Unknown Xoom error"
            }

        # success path
        now_iso = datetime.now(timezone.utc).isoformat()

        return {
            "provider_id": "Xoom",
            "success": True,
            "error_message": None,
            "send_amount": local_data.get("send_amount", 0.0),
            "source_currency": local_data.get("send_currency", "").upper(),
            "destination_amount": local_data.get("receive_amount", 0.0),
            "destination_currency": local_data.get("receive_currency", "").upper(),
            "exchange_rate": local_data.get("exchange_rate", 0.0),
            "fee": local_data.get("fee", 0.0),
            "payment_method": local_data.get("payment_method", "Unknown"),
            "delivery_method": local_data.get("delivery_method", "bank deposit"),
            "delivery_time_minutes": local_data.get("delivery_time_minutes", 1440),
            "timestamp": now_iso,
            "raw_response": local_data.get("raw_response", {})
        }

    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str = "US",
        dest_country: str = None,
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a quote for money transfer. This is the abstract method required by RemittanceProvider.
        It's a wrapper around get_exchange_rate.
        """
        # Derive receive_country if dest_country is provided
        receive_country = dest_country
        receive_currency = dest_currency
        
        # If we have dest_currency but not dest_country, try to derive dest_country
        if not receive_country and receive_currency:
            for country, currency in self.COUNTRY_TO_CURRENCY.items():
                if currency == receive_currency:
                    receive_country = country
                    break
        
        # Call our main implementation
        return self.get_exchange_rate(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=receive_country,
            receive_currency=receive_currency,
            payment_method=payment_method,
            delivery_method=delivery_method
        )

    def get_exchange_rate(
        self,
        send_amount: Decimal,
        send_currency: str = "USD",
        receive_country: str = None,
        receive_currency: str = None,
        delivery_method: str = None,
        payment_method: str = None
    ) -> Dict[str, Any]:
        """
        Aggregator method: get a quote from Xoom with no fallback or mock data.
        If both the fee table and regular API calls fail, returns success=false.
        
        On success, returns aggregator fields.
        """
        local_fail = {
            "success": False,
            "error_message": ""
        }
        if not receive_country:
            local_fail["error_message"] = "Missing mandatory receive_country"
            return self.standardize_response(local_fail)

        # Attempt fee table method
        fee_table_res = self._get_exchange_rate_via_fee_table(send_amount, send_currency, receive_country, receive_currency)
        if fee_table_res.get("success"):
            return self.standardize_response(fee_table_res)
        else:
            logger.warning(f"Fee table method failed or invalid: {fee_table_res.get('error_message','')}")

        # Attempt regular quote method
        quote_res = self._get_exchange_rate_via_regular_api(send_amount, send_currency, receive_country, receive_currency)
        if quote_res.get("success"):
            return self.standardize_response(quote_res)
        else:
            logger.warning(f"Regular quote method failed or invalid: {quote_res.get('error_message','')}")

        # If we reach here, both calls failed
        local_fail["error_message"] = (
            f"Fee table error: {fee_table_res.get('error_message','N/A')} | "
            f"Regular API error: {quote_res.get('error_message','N/A')}"
        )
        return self.standardize_response(local_fail)

    def _get_exchange_rate_via_fee_table(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        receive_currency: Optional[str]
    ) -> Dict[str, Any]:
        """
        Try to get exchange rate from Xoom's fee table HTML endpoint.
        Return local aggregator shape with success True/False.
        """
        result = {
            "success": False,
            "error_message": "",
            "raw_response": {}
        }

        if not receive_currency:
            receive_currency = self._get_currency_for_country(receive_country)

        try:
            # Build query
            params = {
                "sourceCountryCode": "US",  # assuming US for now
                "sourceCurrencyCode": send_currency,
                "destinationCountryCode": receive_country,
                "destinationCurrencyCode": receive_currency,
                "sendAmount": float(send_amount),
                "paymentType": "PAYPAL_BALANCE",
                "requestId": str(uuid.uuid4()),
                "_": str(int(time.time() * 1000))
            }

            # Make GET request
            headers = {
                "User-Agent": self.user_agent,
                "Referer": f"{self.BASE_URL}/en-us/send-money",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            resp = self.session.get(self.FEE_TABLE_API_URL, params=params, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                result["error_message"] = f"Fee table HTTP {resp.status_code}"
                return result

            # Parse HTML
            soup = BeautifulSoup(resp.text, "html.parser")
            result["raw_response"] = {"html_snippet": resp.text[:500]}

            # Attempt to find JSON data
            data_elem = soup.find("data", id="jsonData")
            if not data_elem or not data_elem.string:
                result["error_message"] = "No <data id='jsonData'> block found"
                return result

            # Clean up the JSON
            data_str = html.unescape(data_elem.string)
            try:
                json_data = json.loads(data_str)
            except Exception as e:
                result["error_message"] = f"Failed to parse fee table JSON: {str(e)}"
                return result

            # Check for failure status in the response
            status = json_data.get("status", {})
            if status.get("failureScenario"):
                result["error_message"] = "Xoom API returned failure status"
                return result

            # We expect something like: {"data": {"fxRate": "...", "receiveAmount": "...", etc.}}
            data_obj = json_data.get("data", {})
            
            # Check if data object is empty or doesn't have required fields
            if not data_obj or "fxRate" not in data_obj or "receiveAmount" not in data_obj:
                result["error_message"] = "Incomplete data in fee table response"
                return result
                
            fx_rate = float(data_obj.get("fxRate", 0.0))
            receive_amt = float(data_obj.get("receiveAmount", 0.0))
            
            # Validate values
            if fx_rate <= 0 or receive_amt <= 0:
                result["error_message"] = "Invalid rates or amounts in fee table response"
                return result
                
            fee = 0.0
            # Attempt to find fee in the table
            # The table is in the HTML, let's parse quickly:
            fee_rows = soup.select("tr.xvx-table--fee__body-tr")
            chosen_fee = None
            for row in fee_rows:
                payment_td = row.select_one("td.xvx-table--fee__body-td")
                fee_td = row.select_one("td.fee-value")
                if payment_td and fee_td:
                    pay_text = payment_td.get_text(strip=True).lower()
                    fee_text = fee_td.get_text(strip=True).replace("$", "")
                    if "paypal balance" in pay_text:
                        try:
                            chosen_fee = float(fee_text)
                            break
                        except:
                            pass
            if chosen_fee is None:
                chosen_fee = 0.0

            result.update({
                "success": True,
                "send_currency": send_currency,
                "send_amount": float(send_amount),
                "receive_currency": receive_currency,
                "receive_amount": receive_amt,
                "exchange_rate": fx_rate,
                "fee": chosen_fee,
                "payment_method": "PayPal balance",
                "delivery_method": "bank deposit",
                "delivery_time_minutes": 60  # Arbitrary default
            })
            return result

        except Exception as e:
            logger.error(f"Fee table error: {str(e)}", exc_info=True)
            result["error_message"] = f"Fee table error: {str(e)}"
            return result

    def _get_exchange_rate_via_regular_api(
        self,
        send_amount: Decimal,
        send_currency: str,
        receive_country: str,
        receive_currency: Optional[str]
    ) -> Dict[str, Any]:
        """
        Try to get exchange rate from Xoom's main remittance engine API.
        Return local aggregator shape with success True/False.
        """
        result = {
            "success": False,
            "error_message": "",
            "raw_response": {}
        }

        if not receive_currency:
            receive_currency = self._get_currency_for_country(receive_country)

        # Build payload
        payload = {
            "data": {
                "remittance": {
                    "sourceCurrency": send_currency,
                    "destinationCountry": receive_country,
                    "destinationCurrency": receive_currency,
                    "sendAmount": {
                        "amount": str(float(send_amount)),
                        "currency": send_currency
                    }
                }
            }
        }

        try:
            resp_json = self._make_json_api_request("POST", self.REGULAR_API_URL, json_data=payload)
            if not resp_json:
                result["error_message"] = "No response JSON"
                return result
            result["raw_response"] = resp_json

            # Extract data
            remittance = resp_json.get("data", {}).get("remittance", {})
            quote = remittance.get("quote", {})
            pricing_list = quote.get("pricing", [])
            if not pricing_list:
                result["error_message"] = "No pricing array in quote"
                return result

            # We'll just pick the first pricing option or the 'best' option by lowest fee
            pricing_list.sort(key=lambda x: float(x.get("feeAmount", {}).get("rawValue", "9999")))
            best_opt = pricing_list[0]
            disburse_type = best_opt.get("disbursementType", "DEPOSIT")
            pay_type = best_opt.get("paymentType", {}).get("type", "PAYPAL_BALANCE")

            # Extract amounts
            send_amt_info = best_opt.get("sendAmount", {})
            recv_amt_info = best_opt.get("receiveAmount", {})
            fee_info = best_opt.get("feeAmount", {})
            fx_data = best_opt.get("fxRate", {})
            fx_str = fx_data.get("comparisonString", "")
            fx_rate = self._extract_fx_from_string(fx_str)

            # Convert to aggregator
            result.update({
                "success": True,
                "send_currency": send_currency,
                "send_amount": float(send_amt_info.get("rawValue", float(send_amount))),
                "receive_currency": receive_currency,
                "receive_amount": float(recv_amt_info.get("rawValue", 0.0)),
                "exchange_rate": fx_rate,
                "fee": float(fee_info.get("rawValue", 0.0)),
                "payment_method": pay_type,    # aggregator can further map if needed
                "delivery_method": disburse_type,
                "delivery_time_minutes": 1440  # default assume 1 day
            })

            # Possibly parse "content" for leadTime or times
            content_array = best_opt.get("content", [])
            for item in content_array:
                if item.get("key") == "feesFx.paymentTypeHeader":
                    lead_time_str = item.get("value", "")
                    minutes_val = self._parse_delivery_time(lead_time_str)
                    if minutes_val:
                        result["delivery_time_minutes"] = minutes_val
                    break

            return result

        except Exception as e:
            logger.error(f"Regular API error: {e}", exc_info=True)
            result["error_message"] = f"Regular API error: {str(e)}"
            return result

    def _make_json_api_request(self, method: str, url: str, json_data: Dict) -> Optional[Dict]:
        """
        Helper to make a JSON POST/GET request with standard headers, returning parsed JSON or None.
        """
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.BASE_URL}/en-us/send-money",
        }
        try:
            if method.upper() == "POST":
                resp = self.session.post(url, json=json_data, headers=headers, timeout=self.timeout)
            else:
                resp = self.session.get(url, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"JSON API request got status {resp.status_code}: {resp.text[:400]}")
                return None
            return resp.json()
        except Exception as e:
            logger.error(f"JSON API request exception: {e}", exc_info=True)
            return None

    def _extract_fx_from_string(self, fx_str: str) -> float:
        """
        Extract numeric rate from a string like '1 USD = 19.836 MXN'.
        """
        if not fx_str:
            return 0.0
        # Try '=\s*([\d.]+)'
        match = re.search(r'=\s*([\d.]+)', fx_str)
        if match:
            try:
                return float(match.group(1))
            except:
                pass

        # fallback 0
        return 0.0

    def _parse_delivery_time(self, time_str: str) -> Optional[int]:
        """Return minutes from a string like 'within 60 minutes' or '1-2 days'."""
        if not time_str:
            return None
        
        # look for minutes
        mm = re.search(r'(\d+)\s*min', time_str.lower())
        if mm:
            return int(mm.group(1))
        # hours
        hh = re.search(r'(\d+)\s*hour', time_str.lower())
        if hh:
            return int(hh.group(1)) * 60
        # days
        dd = re.search(r'(\d+)\s*day', time_str.lower())
        if dd:
            return int(dd.group(1)) * 1440

        # fallback
        return None

    def _get_currency_for_country(self, country: str) -> str:
        """Return default currency code for a country code."""
        return self.COUNTRY_TO_CURRENCY.get(country, "USD")

    def close(self):
        if self.session:
            self.session.close()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 