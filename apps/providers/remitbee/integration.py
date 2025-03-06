"""
Remitbee Money Transfer Integration

This module implements the integration with Remitbee, a digital money transfer service
that offers competitive rates for international remittances.

The integration uses Remitbee's public quote API to fetch exchange rates and fees
for international money transfers.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional
from pathlib import Path
import os
import random

import requests
from bs4 import BeautifulSoup

from apps.providers.base.provider import RemittanceProvider
from apps.providers.remitbee.exceptions import (
    RemitbeeError,
    RemitbeeConnectionError,
    RemitbeeApiError,
    RemitbeeValidationError
)

# Setup logging
logger = logging.getLogger(__name__)


class RemitbeeProvider(RemittanceProvider):
    """
    Integration with Remitbee's public quote API.
    
    This class implements a client for Remitbee's API to retrieve
    exchange rates and fees for international money transfers.
    
    Example usage:
        provider = RemitbeeProvider()
        result = provider.get_exchange_rate(
            send_amount=Decimal("1000.00"),
            send_currency="CAD",
            receive_country="IN"
        )
    """
    
    BASE_URL = "https://api.remitbee.com"
    QUOTE_ENDPOINT = "/public-services/calculate-money-transfer"
    
    # Path to the countries data file (relative to this file)
    COUNTRIES_DATA_FILE = "countries_data.json"
    
    # Common user agents to rotate and appear more like a browser
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0"
    ]
    
    def __init__(self, countries_html_file: Optional[str] = None):
        """
        Initialize the RemitbeeProvider.
        
        Args:
            countries_html_file: Optional path to an HTML file containing Remitbee country data.
                                 If not provided, will use a cached JSON file if available.
        """
        super().__init__(name="Remitbee", base_url=self.BASE_URL)
        
        # Dictionary to map country codes to country IDs
        self.country_data = {}
        
        # Load country data
        if countries_html_file and os.path.exists(countries_html_file):
            # Parse from HTML file
            self.country_data = self._load_from_html(countries_html_file)
            # Cache the data for future use
            self._save_country_data()
        else:
            # Try to load from cached JSON
            self._load_country_data()
            
        # Create a session for persistent connections and cookies
        self.session = requests.Session()
        # Set a random user agent
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS)
        })
    
    def _load_from_html(self, html_file: str) -> Dict[str, Dict]:
        """
        Parse the Remitbee HTML to extract country and currency information.
        
        Args:
            html_file: Path to HTML file containing Remitbee country dropdown data.
        
        Returns:
            Dictionary mapping country codes to country data dictionaries.
        """
        logger.info(f"Parsing Remitbee HTML from: {html_file}")
        country_data = {}
        
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html = f.read()

            soup = BeautifulSoup(html, "html.parser")
            
            # Find all <li> elements with data-item attribute
            li_tags = soup.find_all("li", attrs={"data-item": True})
            
            for li in li_tags:
                data_item_str = li["data-item"]  # raw JSON in attribute
                try:
                    item_json = json.loads(data_item_str)
                except json.JSONDecodeError:
                    continue  # skip if invalid
                
                # Extract relevant fields
                country_id = item_json.get("country_id")
                country_name = item_json.get("country_to")
                currency_name = item_json.get("currency_name")
                currency_code = item_json.get("currency_code")
                rate = item_json.get("rate")
                iso2 = item_json.get("iso2")
                iso3 = item_json.get("iso3")
                special_rate = item_json.get("special_rate")
                
                if not (country_id and iso2 and currency_code):
                    continue  # Skip entries missing required fields
                
                # Store in our data structure
                # We'll use ISO2 country code as the key
                country_data[iso2] = {
                    "country_id": country_id,
                    "country_name": country_name,
                    "currency_name": currency_name,
                    "currency_code": currency_code,
                    "rate": rate,
                    "iso2": iso2,
                    "iso3": iso3,
                    "special_rate": special_rate
                }
            
            logger.info(f"Extracted {len(country_data)} countries from Remitbee HTML")
            
        except Exception as e:
            logger.error(f"Error parsing Remitbee HTML: {str(e)}")
            raise RemitbeeError(f"Failed to parse Remitbee HTML: {str(e)}")
        
        return country_data
    
    def _save_country_data(self):
        """Save country data to a JSON file for future use."""
        try:
            data_file = Path(__file__).parent / self.COUNTRIES_DATA_FILE
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(self.country_data, f, indent=2)
            logger.info(f"Saved Remitbee country data to {data_file}")
        except Exception as e:
            logger.warning(f"Could not save Remitbee country data: {str(e)}")
    
    def _load_country_data(self):
        """Load country data from a JSON file."""
        try:
            data_file = Path(__file__).parent / self.COUNTRIES_DATA_FILE
            if data_file.exists():
                with open(data_file, "r", encoding="utf-8") as f:
                    self.country_data = json.load(f)
                logger.info(f"Loaded {len(self.country_data)} Remitbee countries from {data_file}")
            else:
                logger.warning(f"Remitbee country data file {data_file} not found")
        except Exception as e:
            logger.warning(f"Could not load Remitbee country data: {str(e)}")
    
    def get_quote(
        self, 
        country_id: int,
        currency_code: str,
        amount: Decimal,
        is_special_rate: bool = False,
        include_timeline: bool = True
    ) -> Dict[str, Any]:
        """
        Call Remitbee's calculate-money-transfer API to get a quote.
        
        Args:
            country_id: Destination country ID (from Remitbee's country list)
            currency_code: Destination currency code
            amount: Amount to send (in CAD, as Remitbee is Canada-based)
            is_special_rate: Whether to use special rate (if available)
            include_timeline: Whether to include delivery timeline in response
            
        Returns:
            Dictionary with exchange rate, fees, and other details
        
        Raises:
            RemitbeeConnectionError: If connection to API fails
            RemitbeeApiError: If API returns an error
        """
        url = f"{self.BASE_URL}{self.QUOTE_ENDPOINT}"
        
        # Enhanced browser-like headers to avoid 403 errors
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.remitbee.com",
            "Referer": "https://www.remitbee.com/send-money",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Updated payload format based on the example script
        payload = {
            "transfer_amount": f"{amount:.2f}",
            "country_id": country_id,
            "currency_code": currency_code,
            "include_timeline": include_timeline,
            "is_special_rate": is_special_rate,
            # Additional fields observed from browser requests
            "source_currency": "CAD",
            "source_country": "CA"
        }
        
        logger.debug(f"Requesting Remitbee quote: {payload}")
        
        try:
            # First visit the Remitbee homepage to get cookies
            self.session.get("https://www.remitbee.com/", timeout=20)
            
            # Now make the API request using the session
            response = self.session.post(url, headers=headers, json=payload, timeout=20)
            
            # Log response headers for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 403:
                logger.warning("Received 403 Forbidden from Remitbee API. The API may require additional authentication.")
                # Try to get the response content for debugging
                try:
                    error_content = response.text
                    logger.debug(f"403 Response content: {error_content}")
                except:
                    pass
                raise RemitbeeApiError("Access forbidden by Remitbee API. The API may require browser authentication.")
            
            response.raise_for_status()  # Raise for other 4XX/5XX status codes
            
            try:
                data = response.json()
                logger.debug(f"Remitbee quote response: {json.dumps(data, indent=2)}")
                return data
            except json.JSONDecodeError:
                # If not JSON, try to return the text content for debugging
                logger.error(f"Response was not valid JSON: {response.text[:200]}...")
                raise RemitbeeApiError(f"Invalid JSON response from Remitbee API")
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while getting Remitbee quote: {str(e)}")
            raise RemitbeeConnectionError(f"Failed to connect to Remitbee API: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout while getting Remitbee quote: {str(e)}")
            raise RemitbeeConnectionError(f"Remitbee API request timed out: {str(e)}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error while getting Remitbee quote: {str(e)}")
            raise RemitbeeApiError(f"Remitbee API returned error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while getting Remitbee quote: {str(e)}")
            raise RemitbeeError(f"Error getting Remitbee quote: {str(e)}")
    
    def get_exchange_rate(
        self, 
        send_amount: Decimal, 
        send_currency: str, 
        receive_country: str
    ) -> Optional[Dict]:
        """
        Get exchange rate and fees for a money transfer.
        
        Args:
            send_amount: Amount to send (in CAD, as Remitbee is primarily Canadian)
            send_currency: Source currency code (typically 'CAD')
            receive_country: Destination country code (e.g. 'IN')
            
        Returns:
            Dictionary containing rate information or None if failed
        """
        # Validate input
        if not isinstance(send_amount, Decimal):
            raise RemitbeeValidationError("send_amount must be a Decimal")
        
        if send_currency != "CAD":
            logger.warning(f"Remitbee primarily supports CAD as source currency, not {send_currency}")
        
        # Convert country code to uppercase
        receive_country = receive_country.upper()
        
        # Get country details from our country data
        country_data = self.country_data.get(receive_country)
        if not country_data:
            logger.error(f"Country code {receive_country} not found in Remitbee data")
            return None
        
        country_id = country_data["country_id"]
        currency_code = country_data["currency_code"]
        
        try:
            # Call the Remitbee API to get a quote
            quote_data = self.get_quote(
                country_id=country_id,
                currency_code=currency_code,
                amount=send_amount,
                is_special_rate=False  # Set to True if you want to use special rates
            )
            
            # Check if there's an error message in the response
            if "message" in quote_data and "unable to find" in quote_data["message"].lower():
                logger.warning(f"Remitbee does not support this corridor: {quote_data['message']}")
                return {
                    "provider": self.name,
                    "send_amount": float(send_amount),
                    "send_currency": send_currency,
                    "receive_currency": currency_code,
                    "receive_country": receive_country,
                    "receive_country_name": country_data["country_name"],
                    "error": quote_data["message"],
                    "supported": False,
                    "raw_json": quote_data
                }
            
            # Parse the response based on the observed structure
            # Remitbee response structure:
            # - rate: exchange rate (float)
            # - receiving_amount: amount recipient gets (string with commas)
            # - transfer_amount: amount being sent (string with commas)
            # - payment_types: array of payment methods, each with fees
            
            # Get the first payment type with lowest fee for default
            fee = "0.00"
            delivery_hours = 0
            if "payment_types" in quote_data and quote_data["payment_types"]:
                payment_type = quote_data["payment_types"][0]  # Default to first payment type
                fee = payment_type.get("fees", "0.00")
                
                # Get delivery time from timeline if available
                if "timeline" in payment_type and "settlement_timeline" in payment_type["timeline"]:
                    delivery_hours = payment_type["timeline"]["settlement_timeline"].get("predicted_minutes", 0) / 60
            
            # Clean the receiving amount (remove commas)
            receive_amount_str = quote_data.get("receiving_amount", "0.00").replace(",", "")
            
            # Parse the response into our standard format
            result = {
                "provider": self.name,
                "send_amount": float(send_amount),
                "send_currency": send_currency,
                "receive_currency": currency_code,
                "receive_country": receive_country,
                "receive_country_name": country_data["country_name"],
                "exchange_rate": quote_data.get("rate"),
                "receive_amount": float(receive_amount_str) if receive_amount_str else None,
                "fee": float(fee) if fee else 0.0,
                "delivery_time": delivery_hours,
                "supported": True,
                "raw_json": quote_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting Remitbee exchange rate: {str(e)}")
            return None
    
    def get_supported_countries(self) -> List[Dict]:
        """
        Get a list of countries supported by Remitbee.
        
        Returns:
            List of dictionaries containing country information
        """
        return list(self.country_data.values()) 