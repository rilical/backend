"""
XE Money Transfer (https://www.xe.com/send-money/) integration module for retrieving quotes
and exchange rates.
"""

import logging
import json
import uuid
import requests
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

from ..base.provider import RemittanceProvider
from .exceptions import (
    XEError,
    XEConnectionError,
    XEApiError,
    XEValidationError,
    XEResponseError,
    XECorridorUnsupportedError,
    XEQuoteError,
    XEParsingError,
    XERateLimitError
)

logger = logging.getLogger(__name__)

class XEProvider(RemittanceProvider):
    """XE Money Transfer rate provider implementation."""
    
    # XE API endpoints
    API_BASE_URL = "https://www.xe.com"
    MIDMARKET_RATES_URL = "https://www.xe.com/api/protected/midmarket-converter/"
    QUOTES_API_URL = "https://launchpad-api.xe.com/v2/quotes"
    
    # Mapping of ISO country codes to XE's currency codes
    COUNTRY_TO_CURRENCY = {
        'IN': 'INR',  # India - Indian Rupee
        'PH': 'PHP',  # Philippines - Philippine Peso
        'PK': 'PKR',  # Pakistan - Pakistani Rupee
        'US': 'USD',  # United States - US Dollar
        'GB': 'GBP',  # United Kingdom - British Pound
        'CA': 'CAD',  # Canada - Canadian Dollar
        'AU': 'AUD',  # Australia - Australian Dollar
        'MX': 'MXN',  # Mexico - Mexican Peso
        # Add more mappings as needed
    }
    
    # Supported corridors based on testing
    SUPPORTED_CORRIDORS = [
        ('AUD', 'PH'),  # AUD to PH
        ('CAD', 'IN'),  # CAD to IN
        ('EUR', 'PH'),  # EUR to PH
        ('GBP', 'IN'),  # GBP to IN
        ('USD', 'IN'),  # USD to IN
        ('USD', 'PH'),  # USD to PH
        # Add more as they are confirmed
]
    
    def __init__(self, api_key: str = None, **kwargs):
        """
        Initialize the XE provider.
        
        Args:
            api_key: Optional API key (not required for the current implementation)
            **kwargs: Additional arguments
        """
        # Initialize the base class with required parameters
        super().__init__(name="xe", base_url="https://www.xe.com")
        
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://www.xe.com',
            'Referer': 'https://www.xe.com/send-money/'
        })
        
        # Store mid-market rates for quick lookups
        self.midmarket_rates: Dict[str, Decimal] = {}
        
        # Generate a device ID for API requests
        self.device_id = str(uuid.uuid4())
        
        # Attempt to fetch mid-market rates immediately
        self._fetch_midmarket_rates()
        
        # If midmarket rates fetch failed, set some common fallback rates
        # Note: These are just examples and would need to be updated regularly
        if not self.midmarket_rates:
            logger.info("Using fallback mid-market rates")
            self._set_fallback_rates()
    
    def _set_fallback_rates(self) -> None:
        """Set fallback mid-market rates for common currencies."""
        # These are just examples and would need to be updated regularly in a production environment
        fallback_rates = {
            'USD': Decimal('1.0'),
            'EUR': Decimal('0.92'),
            'GBP': Decimal('0.79'),
            'INR': Decimal('83.25'),
            'PHP': Decimal('57.0'),
            'JPY': Decimal('151.0'),
            'CAD': Decimal('1.36'),
            'AUD': Decimal('1.53'),
            'MXN': Decimal('16.80'),
        }
        self.midmarket_rates = fallback_rates
    
    def _fetch_midmarket_rates(self) -> None:
        """Fetch and store mid-market rates from XE's 'protected/midmarket-converter' endpoint."""
        logger.info("Fetching mid-market rates from XE...")
        try:
            # Note: This endpoint appears to require authentication 
            # We'll make the request anyway and handle the fallback if it fails
            resp = self.session.get(self.MIDMARKET_RATES_URL, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            rates_dict = data.get("rates", {})
            count = 0
            for ccy, val in rates_dict.items():
                try:
                    self.midmarket_rates[ccy] = Decimal(str(val))
                    count += 1
                except Exception:
                    logger.warning(f"Failed to parse rate for {ccy}: {val}")
            logger.info(f"XE mid-market rates fetched: {count} rates stored.")
        except requests.HTTPError as exc:
            logger.error(f"HTTP error fetching mid-market rates from XE: {exc}")
            # We'll use fallback rates in this case
        except Exception as ex:
            logger.error(f"Error in mid-market rates fetch: {ex}")
    
    def _get_receive_currency(self, receive_country: str) -> str:
        """
        Get the currency code for a country.
        
        Args:
            receive_country: ISO country code (e.g., 'IN', 'PH')
            
        Returns:
            Currency code (e.g., 'INR', 'PHP')
        """
        return self.COUNTRY_TO_CURRENCY.get(receive_country, 'USD')

    def is_corridor_supported(self, send_currency: str, receive_country: str) -> bool:
        """
        Check if a corridor is supported based on testing.
        
        Args:
            send_currency: Currency code of the sending amount (e.g., 'USD', 'GBP')
            receive_country: ISO country code of the receiving country (e.g., 'IN', 'PH')
            
        Returns:
            True if the corridor is supported, False otherwise
        """
        return (send_currency, receive_country) in self.SUPPORTED_CORRIDORS
    
    def _fetch_quote(self, from_ccy: str, to_ccy: str, send_amount: Decimal,
                    from_country: str, to_country: str) -> Dict[str, Any]:
        """
        Call the XE quotes API endpoint to get a quote.
        
        Args:
            from_ccy: Source currency code (e.g., 'USD')
            to_ccy: Target currency code (e.g., 'INR')
            send_amount: Amount to send
            from_country: ISO country code of the sending country (e.g., 'US')
            to_country: ISO country code of the receiving country (e.g., 'IN')
            
        Returns:
            Dictionary with quote information or error details
        """
        # Build payload
        payload = {
            "sellCcy": from_ccy,
            "buyCcy": to_ccy,
            "userCountry": from_country,  # or maybe "GB", "US", etc.
            "amount": float(send_amount),
            "fixedCcy": from_ccy,
            "countryTo": to_country
        }
        
        # Add correlation ID and device ID for XE's API
        headers = {
            "X-Correlation-ID": f"XECOM-{uuid.uuid4()}",
            "deviceid": str(self.device_id),
        }
        
        result = {
            "success": False,
            "error_message": None
        }
        
        try:
            logger.info(f"Requesting quote from XE API: {from_ccy} -> {to_ccy}, amount={send_amount}")
            
            resp = self.session.post(
                self.QUOTES_API_URL,
                json=payload,
                headers=headers,
                timeout=15
            )
            resp.raise_for_status()
            
            data = resp.json()
            
            if "quote" in data:
                quote = data["quote"]
                quote_id = quote.get("quoteId", "unknown")
                quote_status = quote.get("quoteStatus", "unknown")
                
                logger.info(f"Received XE quote (ID: {quote_id}, Status: {quote_status})")
                
                # Extract rate info from individualQuotes if available
                if "individualQuotes" in quote and len(quote["individualQuotes"]) > 0:
                    first_quote = quote["individualQuotes"][0]
                    provider = first_quote.get("commissionProvider", "XE")
                    sell_amount = first_quote.get("sellAmount", "0").replace(",", "")
                    buy_amount = first_quote.get("buyAmount", "0").replace(",", "")
                    rate = first_quote.get("rate", 0)
                    fee = first_quote.get("transferFee", "0").replace(",", "")
                    payment_fee = first_quote.get("paymentMethodFee", "0").replace(",", "")
                    delivery_eta = first_quote.get("valueDate", "Unknown")
                    
                    # Try to handle formatted string amounts and convert to Decimal
                    try:
                        sell_amount_decimal = Decimal(sell_amount)
                        buy_amount_decimal = Decimal(buy_amount)
                        fee_decimal = Decimal(fee)
                        payment_fee_decimal = Decimal(payment_fee)
                    except (ValueError, InvalidOperation) as e:
                        logger.warning(f"Failed to convert amount string to Decimal: {e}")
                        sell_amount_decimal = send_amount
                        # Fallback to rate if available
                        if rate and isinstance(rate, (int, float, Decimal)):
                            buy_amount_decimal = send_amount * Decimal(str(rate))
                        else:
                            buy_amount_decimal = Decimal("0")
                        fee_decimal = Decimal("0")
                        payment_fee_decimal = Decimal("0")
                    
                    # Calculate total fee
                    total_fee = fee_decimal + payment_fee_decimal
                    
                    # Construct result dictionary
                    result = {
                        "provider": "xe",
                        "provider_name": provider,
                        "quote_id": quote_id,
                        "send_amount": sell_amount_decimal,
                        "send_currency": from_ccy,
                        "receive_amount": buy_amount_decimal,
                        "receive_currency": to_ccy,
                        "rate": Decimal(str(rate)) if rate else (buy_amount_decimal / sell_amount_decimal if sell_amount_decimal else Decimal("0")),
                        "fee": total_fee,
                        "fee_currency": from_ccy,
                        "delivery_estimate": delivery_eta,
                        "success": True
                    }
                else:
                    result["error_message"] = "No quote details found in response"
            else:
                result["error_message"] = "Unexpected response format from XE API - missing 'quote' field"
            
            return result
            
        except requests.HTTPError as e:
            error_msg = f"HTTP error from XE API ({e.response.status_code}): {str(e)}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            raise XEApiError(error_msg) from e
            
        except (json.JSONDecodeError, KeyError) as e:
            error_msg = f"Error parsing XE API response: {str(e)}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            raise XEResponseError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Unexpected error when fetching XE quote: {str(e)}"
            logger.error(error_msg)
            result["error_message"] = error_msg
            raise XEError(error_msg) from e
    
    def get_exchange_rate(self, send_amount: Decimal, send_currency: str, receive_country: str, **kwargs) -> Dict[str, Any]:
        """
        Get the exchange rate from XE for a specific corridor.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency to send from (e.g., 'USD')
            receive_country: Country to receive in (e.g., 'IN')
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing exchange rate information
        """
        logger.info(f"Getting XE exchange rate for {send_currency} to {receive_country} (Amount: {send_amount})")
        
        # Basic result structure
        result = {
            "provider": self.name,
            "send_amount": float(send_amount),
            "send_currency": send_currency,
            "receive_country": receive_country,
            "success": False,
            "error_message": None
        }
        
        # Convert country code to currency if needed
        receive_currency = self._get_receive_currency(receive_country)
        
        if not receive_currency:
            msg = f"Unable to determine currency for country {receive_country}"
            logger.warning(msg)
            result["error_message"] = msg
            raise XECorridorUnsupportedError(msg)
        
        result["receive_currency"] = receive_currency
        
        # Try different methods to get the exchange rate
        try:
            # First, try the direct API quote endpoint
            endpoint_url = self.QUOTES_API_URL
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            # Generate a unique ID for this request
            quote_id = str(uuid.uuid4())
            
            data = {
                "quoteId": quote_id,
                "partnerUserId": quote_id,
                "sellCurrency": send_currency,
                "buyCurrency": receive_currency,
                "sellAmount": str(send_amount),
                "scope": "full"
            }
            
            try:
                response = requests.post(endpoint_url, json=data, headers=headers, timeout=30)
                response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                msg = f"Connection error with XE API: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEConnectionError(msg) from e
            except requests.exceptions.Timeout as e:
                msg = f"Timeout connecting to XE API: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEConnectionError(msg) from e
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
                msg = f"HTTP error from XE API ({status_code}): {e}"
                logger.error(msg)
                result["error_message"] = msg
                if status_code == 429:
                    raise XERateLimitError(msg) from e
                raise XEApiError(msg) from e
            except Exception as e:
                msg = f"Error connecting to XE API: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEError(msg) from e
            
            try:
                data = response.json()
            except ValueError as e:
                msg = f"Failed to parse JSON from XE API: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEParsingError(msg) from e
            
            # Parse the quote data
            quote_obj = data.get("quote", {})
            
            # Check if we got a valid quote
            if not quote_obj:
                msg = "No quote in response"
                logger.error(msg)
                result["error_message"] = msg
                raise XEResponseError(msg)
            
            # Extract individual quotes (different payment methods)
            individual_quotes = quote_obj.get("individualQuotes", [])
            if not individual_quotes:
                msg = "No individual quotes found"
                logger.error(msg)
                result["error_message"] = msg
                raise XEResponseError(msg)
            
            # Find default or first enabled quote
            chosen = None
            for q in individual_quotes:
                if q.get("isDefault", False) and q.get("isEnabled", True):
                    chosen = q
                    break
            
            if not chosen:
                # Fallback to first enabled quote
                for q in individual_quotes:
                    if q.get("isEnabled", False):
                        chosen = q
                        break
            
            if not chosen:
                msg = "No valid quote found in 'individualQuotes'"
                logger.error(msg)
                result["error_message"] = msg
                raise XEQuoteError(msg)
            
            # Extract quote details
            try:
                rate = float(chosen.get("rate", 0.0))
                fee_str = chosen.get("transferFee", "0.00")
                fee = float(fee_str)
                buy_amt_str = chosen.get("buyAmount", "0").replace(",", "")
                buy_amt = float(buy_amt_str)
                
                delivery_time = chosen.get("leadTime", "N/A")
                
                result.update({
                    "success": True,
                    "exchange_rate": rate,
                    "fee": fee,
                    "receive_amount": buy_amt,
                    "delivery_time": delivery_time
                })
                
                # Add raw data for debugging
                if kwargs.get("include_raw_data", False):
                    result["raw_data"] = data
                
                logger.info(f"Successfully retrieved XE quote: {rate} {send_currency}/{receive_currency}")
                return result
            except Exception as e:
                msg = f"Error extracting quote details: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEParsingError(msg) from e
                
        except (XEConnectionError, XEApiError, XEResponseError, XEQuoteError, XEParsingError) as e:
            # These exceptions already set the error message in result
            # Try the fallback method of scraping the website
            logger.warning(f"Direct API failed, trying fallback HTML method: {str(e)}")
            return self._fallback_get_rate_from_website(send_amount, send_currency, receive_currency, result)
        except Exception as e:
            # Catch any other exceptions and try the fallback
            logger.error(f"Unexpected error in XE API request: {str(e)}")
            result["error_message"] = f"Unexpected error: {str(e)}"
            return self._fallback_get_rate_from_website(send_amount, send_currency, receive_currency, result)
    
    def _get_exchange_rate_from_html(self, send_amount: Decimal, send_currency: str, receive_country: str) -> Dict[str, Any]:
        """
        Fallback method to get exchange rate by scraping the XE website.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency code of the sending amount (e.g., 'USD', 'GBP')
            receive_country: ISO country code of the receiving country (e.g., 'IN', 'PH')
            
        Returns:
            Dictionary with exchange rate information
        """
        receive_currency = self._get_receive_currency(receive_country)
        
        # Create a basic result structure
        result = {
            'success': False,
            'error_message': None
        }
        
        try:
            # Create the request URL for quotes
            url = f"{self.API_BASE_URL}/send-money/details"
            
            # Prepare parameters for the GET request
            params = {
                'Amount': str(send_amount),
                'FromCurrency': send_currency,
                'ToCurrency': receive_currency
            }
            
            # Temporarily update headers for HTML request
            original_headers = self.session.headers.copy()
            self.session.headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })
            
            # Make the request
            logger.info(f"Requesting HTML quote for {send_amount} {send_currency} to {receive_country}")
            response = self.session.get(url, params=params)
            
            # Restore original headers
            self.session.headers = original_headers
            
            # Check response status
            if response.status_code == 200:
                # Parse the HTML response
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find the JSON data in various formats
                # Pattern 1: Look for __NEXT_DATA__ script
                next_data = soup.find('script', {'id': '__NEXT_DATA__'})
                if next_data:
                    try:
                        data = json.loads(next_data.string)
                        props = data.get('props', {}).get('pageProps', {})
                        
                        # Check for quote data in different paths
                        quote_data = None
                        if 'quote' in props:
                            quote_data = props['quote']
                        elif 'initialData' in props and 'quote' in props['initialData']:
                            quote_data = props['initialData']['quote']
                        
                        if quote_data:
                            # Find the default individual quote
                            individual_quotes = quote_data.get('individualQuotes', [])
                            default_quote = next((q for q in individual_quotes if q.get('isDefault', False)), None)
                            
                            if default_quote:
                                # Extract relevant information
                                exchange_rate = default_quote.get('rate')
                                receive_amount = float(default_quote.get('buyAmount', '0').replace(',', ''))
                                fee = float(default_quote.get('transferFee', '0'))
                                delivery_time = default_quote.get('leadTime', 'Unknown')
                                
                                # Update the result
                                result.update({
                                    'exchange_rate': exchange_rate,
                                    'receive_amount': receive_amount,
                                    'fee': fee,
                                    'delivery_time': delivery_time,
                                    'success': True,
                                    'raw_data': {'quote': quote_data}
                                })
                                
                                logger.info(f"Successfully retrieved XE quote from HTML: {exchange_rate} {send_currency}/{receive_currency}")
                                return result
                    except Exception as e:
                        logger.error(f"Error parsing __NEXT_DATA__: {str(e)}")
                
                # Pattern 2: Look for window.__INITIAL_STATE__
                state_pattern = r'window\.__INITIAL_STATE__\s*=\s*JSON\.parse\("(.+?)"\);'
                import re
                matches = re.search(state_pattern, response.text)
                if matches:
                    try:
                        json_str = matches.group(1)
                        json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
                        data = json.loads(json_str)
                        
                        # Extract quote data
                        quote_data = data.get('quote', {}).get('quote', {})
                        
                        if quote_data:
                            # Find the default individual quote
                            individual_quotes = quote_data.get('individualQuotes', [])
                            default_quote = next((q for q in individual_quotes if q.get('isDefault', False)), None)
                            
                            if default_quote:
                                # Extract relevant information
                                exchange_rate = default_quote.get('rate')
                                receive_amount = float(default_quote.get('buyAmount', '0').replace(',', ''))
                                fee = float(default_quote.get('transferFee', '0'))
                                delivery_time = default_quote.get('leadTime', 'Unknown')
                                
                                # Update the result
                                result.update({
                                    'exchange_rate': exchange_rate,
                                    'receive_amount': receive_amount,
                                    'fee': fee,
                                    'delivery_time': delivery_time,
                                    'success': True,
                                    'raw_data': {'quote': quote_data}
                                })
                                
                                logger.info(f"Successfully retrieved XE quote from HTML: {exchange_rate} {send_currency}/{receive_currency}")
                                return result
                    except Exception as e:
                        logger.error(f"Error parsing INITIAL_STATE: {str(e)}")
                
                # If we got here, we couldn't find the data
                result['error_message'] = "Could not extract quote data from the HTML"
                result['debug_html'] = response.text[:1000] + "..."
            else:
                logger.error(f"Failed to fetch XE HTML quote. Status code: {response.status_code}")
                result['error_message'] = f"HTTP error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error in HTML fallback: {str(e)}")
            result['error_message'] = f"HTML fallback error: {str(e)}"
        
        return result
    
    def _fallback_get_rate_from_website(self, send_amount: Decimal, send_currency: str, receive_currency: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback method that attempts to get exchange rates by scraping the XE website.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency to send from
            receive_currency: Currency to receive in
            result: Existing result dictionary to update
            
        Returns:
            Updated result dictionary
        """
        logger.info(f"Trying fallback website method for {send_currency} to {receive_currency}")
        
        try:
            url = f"{self.API_BASE_URL}/xemoneytransfer/send"
            params = {
                "Amount": str(send_amount),
                "FromCurrency": send_currency,
                "ToCurrency": receive_currency
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                msg = f"Connection error with XE website: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEConnectionError(msg) from e
            except requests.exceptions.Timeout as e:
                msg = f"Timeout connecting to XE website: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEConnectionError(msg) from e
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
                msg = f"HTTP error from XE website ({status_code}): {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEApiError(msg) from e
            except Exception as e:
                msg = f"Error connecting to XE website: {e}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEError(msg) from e
            
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try to find the JSON data in various formats
                # Pattern 1: Look for __NEXT_DATA__ script
                next_data = soup.find('script', {'id': '__NEXT_DATA__'})
                if next_data:
                    try:
                        data = json.loads(next_data.string)
                        props = data.get('props', {}).get('pageProps', {})
                        
                        # Check for quote data in different paths
                        quote_data = None
                        if 'quote' in props:
                            quote_data = props['quote']
                        elif 'initialData' in props and 'quote' in props['initialData']:
                            quote_data = props['initialData']['quote']
                        
                        if quote_data:
                            # Find the default individual quote
                            individual_quotes = quote_data.get('individualQuotes', [])
                            default_quote = next((q for q in individual_quotes if q.get('isDefault', False)), None)
                            
                            if default_quote:
                                # Extract relevant information
                                exchange_rate = default_quote.get('rate')
                                receive_amount = float(default_quote.get('buyAmount', '0').replace(',', ''))
                                fee = float(default_quote.get('transferFee', '0'))
                                delivery_time = default_quote.get('leadTime', 'Unknown')
                                
                                # Update the result
                                result.update({
                                    'exchange_rate': exchange_rate,
                                    'receive_amount': receive_amount,
                                    'fee': fee,
                                    'delivery_time': delivery_time,
                                    'success': True,
                                    'raw_data': {'quote': quote_data}
                                })
                                
                                logger.info(f"Successfully retrieved XE quote from HTML: {exchange_rate} {send_currency}/{receive_currency}")
                                return result
                    except Exception as e:
                        logger.error(f"Error parsing __NEXT_DATA__: {str(e)}")
                        raise XEParsingError(f"Error parsing __NEXT_DATA__: {str(e)}") from e
                
                # Pattern 2: Look for window.__INITIAL_STATE__
                state_pattern = r'window\.__INITIAL_STATE__\s*=\s*JSON\.parse\("(.+?)"\);'
                import re
                matches = re.search(state_pattern, response.text)
                if matches:
                    try:
                        json_str = matches.group(1)
                        # Handle escaped quotes and other characters
                        json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
                        data = json.loads(json_str)
                        
                        # Extract quote data
                        quote_data = data.get('quote', {})
                        if quote_data:
                            rate = float(quote_data.get('rate', 0))
                            fee = float(quote_data.get('fee', 0))
                            
                            # Calculate receive amount
                            receive_amount = (float(send_amount) - fee) * rate
                            
                            result.update({
                                'exchange_rate': rate,
                                'receive_amount': receive_amount,
                                'fee': fee,
                                'delivery_time': quote_data.get('deliveryTime', 'Unknown'),
                                'success': True,
                                'raw_data': {'quote': quote_data}
                            })
                            
                            logger.info(f"Successfully retrieved XE quote from __INITIAL_STATE__: {rate} {send_currency}/{receive_currency}")
                            return result
                    except Exception as e:
                        logger.error(f"Error parsing __INITIAL_STATE__: {str(e)}")
                        raise XEParsingError(f"Error parsing __INITIAL_STATE__: {str(e)}") from e
                
                # Pattern 3: Look for specific HTML elements
                try:
                    rate_element = soup.select_one("[data-test='exchange-rate']")
                    if rate_element:
                        rate_text = rate_element.text.strip()
                        # Extract the numeric rate from text like "1 USD = 83.27 INR"
                        import re
                        rate_match = re.search(r'1\s+[A-Z]{3}\s*=\s*(\d+(?:\.\d+)?)', rate_text)
                        if rate_match:
                            rate = float(rate_match.group(1))
                            
                            # Try to find fee element
                            fee_element = soup.select_one("[data-test='fee']")
                            fee = 0.0
                            if fee_element:
                                fee_text = fee_element.text.strip()
                                fee_match = re.search(r'(\d+(?:\.\d+)?)', fee_text)
                                if fee_match:
                                    fee = float(fee_match.group(1))
                            
                            # Calculate receive amount
                            receive_amount = float(send_amount) * rate - fee
                            
                            result.update({
                                'exchange_rate': rate,
                                'receive_amount': receive_amount,
                                'fee': fee,
                                'delivery_time': 'Unknown',
                                'success': True
                            })
                            
                            logger.info(f"Successfully retrieved XE quote from HTML elements: {rate} {send_currency}/{receive_currency}")
                            return result
                except Exception as e:
                    logger.error(f"Error parsing HTML elements: {str(e)}")
                    raise XEParsingError(f"Error parsing HTML elements: {str(e)}") from e
                
                # If we reach here, we couldn't find the data in any expected format
                msg = "Could not extract exchange rate from HTML response"
                logger.error(msg)
                result["error_message"] = msg
                return result
                
            except XEParsingError as e:
                # Propagate specific parsing errors
                raise
            except Exception as e:
                msg = f"Error parsing XE website response: {str(e)}"
                logger.error(msg)
                result["error_message"] = msg
                raise XEParsingError(msg) from e
                
        except Exception as e:
            # Catch all other exceptions
            logger.error(f"Fallback method failed: {str(e)}")
            if not result.get("error_message"):
                result["error_message"] = f"Fallback method failed: {str(e)}"
            return result
        
        return result
    
    def get_quote(self, amount: Decimal, source_currency: str, target_country: str, **kwargs) -> Dict[str, Any]:
        """
        Get a quote for a money transfer.
        
        Args:
            amount: Amount to send
            source_currency: Currency code of the sending amount (e.g., 'USD', 'GBP')
            target_country: ISO country code of the receiving country (e.g., 'IN', 'PH')
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with quote information
        """
        # Delegate to get_exchange_rate as they're essentially the same for XE
        return self.get_exchange_rate(
            send_amount=amount,
            send_currency=source_currency,
            receive_country=target_country,
            **kwargs
        )
    
    def get_supported_countries(self, base_currency: str = None) -> List[str]:
        """
        Get a list of supported receiving countries for a given base currency.
        
        Args:
            base_currency: Base currency code (e.g., 'USD', 'GBP')
            
        Returns:
            List of supported receiving country codes
        """
        if not base_currency:
            # Return all unique target countries from supported corridors
            return sorted(set(country for _, country in self.SUPPORTED_CORRIDORS))
        
        # Return only countries supported for the given base currency
        return sorted(set(country for currency, country in self.SUPPORTED_CORRIDORS if currency == base_currency)) 