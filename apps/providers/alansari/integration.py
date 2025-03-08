"""
Al Ansari Exchange provider integration module.
"""

import logging
import requests
import json
from decimal import Decimal
from typing import Any, Dict, Optional, List
from datetime import datetime
import re

from apps.providers.base.provider import RemittanceProvider
from .exceptions import (
    AlAnsariError,
    AlAnsariAuthError,
    AlAnsariConnectionError,
    AlAnsariSecurityTokenError,
)

logger = logging.getLogger(__name__)

class AlAnsariProvider(RemittanceProvider):
    BASE_URL = "https://alansariexchange.com/wp-admin/admin-ajax.php"
    WEBSITE_URL = "https://alansariexchange.com/"

    CURRENCY_ID_MAPPING = {
        'AED': '91',
        'INR': '27',
        'LKR': '30',
        'BDT': '31',
        'PKR': '28',
        'PHP': '29',
        'USD': '92',
        'EGP': '19',
        'JOD': '20',
        'NPR': '98',
        'AUD': '41',
        'BHD': '23',
        'CAD': '37',
        'CHF': '33',
        'EUR': '75',
        'GBP': '13',
        'HKD': '54',
        'IDR': '58',
        'IQD': '18',
        'JPY': '40',
        'KWD': '22',
        'LBP': '17',
        'MAD': '31',
        'MYR': '44',
        'NZD': '73',
        'OMR': '21',
        'QAR': '24',
        'SAR': '25',
        'SGD': '39',
        'THB': '38',
        'TND': '57',
        'YER': '30'
    }

    COUNTRY_ID_MAPPING = {
        'AFGHANISTAN': '69',
        'ALBANIA': '104',
        'ALGERIA': '105',
        'ANDORRA': '146',
        'ANGOLA': '147',
        'ARGENTINA': '107',
        'ARMENIA': '148',
        'AUSTRALIA': '41',
        'AUSTRIA': '43',
        'AZERBAIJAN': '149',
        'BAHAMAS': '109',
        'BAHRAIN': '23',
        'BANGLADESH': '59',
        'BARBADOS': '111',
        'BELARUS': '150',
        'BELGIUM': '34',
        'BELIZE': '110',
        'BENIN': '151',
        'BERMUDA': '112',
        'BHUTAN': '113',
        'BOLIVIA': '225',
        'BOSNIA AND HERZEGOVINA': '152',
        'BOTSWANA': '114',
        'BRAZIL': '64',
        'BRUNEI': '55',
        'BULGARIA': '89',
        'BURKINA FASO': '153',
        'BURUNDI': '154',
        'CAMBODIA': '155',
        'CAMEROON': '83',
        'CANADA': '37',
        'CAPE VERDE': '156',
        'CAYMAN ISLANDS': '118',
        'CENTRAL AFRICAN REPUBLIC': '157',
        'CHAD': '116',
        'CHILE': '117',
        'CHINA': '90',
        'COLOMBIA': '120',
        'COMOROS': '158',
        'CONGO': '119',
        'COSTA RICA': '121',
        'COTE D IVOIRE': '161',
        'CROATIA': '162',
        'CUBA': '122',
        'CURACAO': '199',
        'CYPRUS': '47',
        'CZECH REPUBLIC': '67',
        'DENMARK': '50',
        'DJIBOUTI': '163',
        'DOMINICA': '164',
        'DOMINICAN REPUBLIC': '165',
        'EAST TIMOR': '166',
        'ECUADOR': '123',
        'EGYPT': '19',
        'EL SALVADOR': '167',
        'ERITREA': '132',
        'ESTONIA': '168',
        'ETHIOPIA': '71',
        'FALKLAND ISLANDS': '74',
        'FIJI': '169',
        'FINLAND': '53',
        'FRANCE': '15',
        'GABON': '170',
        'GAMBIA': '140',
        'GEORGIA': '171',
        'GERMANY': '14',
        'GHANA': '141',
        'GIBRALTAR': '142',
        'GREECE': '46',
        'GRENADA': '172',
        'GUATEMALA': '173',
        'GUINEA': '174',
        'GUINEA BISSAU': '175',
        'GUYANA': '143',
        'HAITI': '144',
        'HONDURAS': '145',
        'HONG KONG': '54',
        'HUNGARY': '93',
        'ICELAND': '177',
        'INDIA': '26',
        'INDONESIA': '58',
        'IRAQ': '18',
        'IRELAND': '29',
        'ITALY': '32',
        'JAMAICA': '179',
        'JAPAN': '40',
        'JORDAN': '20',
        'KAZAKHSTAN': '79',
        'KENYA': '62',
        'KIRIBATI': '180',
        'KOSOVO': '181',
        'KUWAIT': '22',
        'KYRGYZSTAN': '182',
        'LAOS': '183',
        'LATVIA': '184',
        'LEBANON': '17',
        'LESOTHO': '185',
        'LIBERIA': '133',
        'LIECHTENSTEIN': '186',
        'LITHUANIA': '187',
        'LUXEMBOURG': '96',
        'MACEDONIA': '189',
        'MADAGASCAR': '190',
        'MALAWI': '191',
        'MALAYSIA': '44',
        'MALDIVES': '124',
        'MALI': '192',
        'MALTA': '65',
        'MARSHALL ISLANDS': '193',
        'MAURITANIA': '129',
        'MAURITIUS': '61',
        'MEXICO': '125',
        'MICRONESIA': '194',
        'MOLDOVA': '195',
        'MONACO': '126',
        'MONGOLIA': '130',
        'MONTENEGRO': '196',
        'MOROCCO': '31',
        'MOZAMBIQUE': '197',
        'NAMIBIA': '131',
        'NAURU': '198',
        'NEPAL': '98',
        'NETHERLANDS': '35',
        'NEW ZEALAND': '73',
        'NICARAGUA': '137',
        'NIGER': '138',
        'NIGERIA': '88',
        'NORWAY': '51',
        'OMAN': '21',
        'PAKISTAN': '27',
        'PALAU': '201',
        'PALESTINE': '68',
        'PANAMA': '97',
        'PAPUA NEW GUINEA': '202',
        'PARAGUAY': '203',
        'PERU': '76',
        'PHILIPPINES': '49',
        'POLAND': '77',
        'PORTUGAL': '78',
        'PUERTO RICO': '139',
        'QATAR': '24',
        'REPUBLIC OF CONGO': '160',
        'ROMANIA': '94',
        'RUSSIA': '63',
        'RWANDA': '204',
        'SAINT KITTS AND NEVIS': '205',
        'SAINT LUCIA': '206',
        'SAINT VINCENT AND THE GRENADINES': '207',
        'SAMOA': '208',
        'SAN MARINO': '209',
        'SAO TOME AND PRINCIPE': '210',
        'SAUDI ARABIA': '25',
        'SENEGAL': '127',
        'SERBIA': '211',
        'SEYCHELLES': '80',
        'SIERRA LEONE': '212',
        'SINGAPORE': '39',
        'SLOVAKIA': '70',
        'SLOVENIA': '213',
        'SOLOMON ISLANDS': '214',
        'SOMALIA': '81',
        'SOUTH AFRICA': '72',
        'SOUTH KOREA': '52',
        'SPAIN': '42',
        'SRI LANKA': '60',
        'SURINAME': '99',
        'SWAZILAND': '216',
        'SWEDEN': '48',
        'SWITZERLAND': '33',
        'TAIWAN': '56',
        'TAJIKISTAN': '217',
        'TANZANIA': '82',
        'THAILAND': '38',
        'TOGO': '219',
        'TONGA': '220',
        'TRINIDAD AND TOBAGO': '221',
        'TUNISIA': '57',
        'TURKEY': '36',
        'TUVALU': '222',
        'UGANDA': '84',
        'UKRAINE': '101',
        'UNITED ARAB EMIRATES': '91',
        'UNITED KINGDOM': '13',
        'UNITED STATES OF AMERICA': '92',
        'URUGUAY': '100',
        'UZBEKISTAN': '227',
        'VANUATU': '223',
        'VATICAN CITY STATE': '176',
        'VENEZUELA': '224',
        'VIETNAM': '102',
        'YEMEN': '30',
        'ZAMBIA': '86',
        'ZIMBABWE': '134'
    }

    def __init__(self, name="alansari", base_url=None, config: Optional[Dict] = None):
        """Initialize the Al Ansari Exchange provider."""
        super().__init__(name=name, base_url=base_url or self.BASE_URL)
        self.config = config or {}
        self.session = requests.Session()
        self.security_token = None
        self._setup_session()

    def _setup_session(self):
        """Configure session headers."""
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
            )
        })

    def fetch_security_token(self) -> str:
        """
        Fetch security token from Al Ansari website by parsing the homepage HTML.
        The token is embedded in JavaScript as ajax_nonce.
        """
        try:
            response = self.session.get(
                self.WEBSITE_URL,
                timeout=30
            )
            if response.status_code != 200:
                raise AlAnsariAuthError(
                    f"Failed to get security token: HTTP {response.status_code}"
                )
            
            # Extract the ajax_nonce token from the JavaScript in the HTML
            pattern = r'var CC_Ajax_Object\s*=\s*{"ajax_url":[^,]*,"ajax_nonce":"([a-zA-Z0-9]+)"}'
            match = re.search(pattern, response.text)
            
            if not match:
                raise AlAnsariAuthError(
                    "Failed to extract security token from website"
                )
            
            token = match.group(1)
            if not token:
                raise AlAnsariAuthError(
                    "Empty security token extracted from website"
                )
            
            logger.info(f"Successfully extracted security token: {token}")
            return token
        except requests.RequestException as e:
            raise AlAnsariConnectionError(
                f"Connection error fetching security token: {str(e)}"
            ) from e
        except Exception as e:
            raise AlAnsariSecurityTokenError(
                f"Unexpected error fetching security token: {str(e)}"
            ) from e

    def standardize_response(
        self,
        raw_result: Dict[str, Any],
        provider_specific_data: bool = False
    ) -> Dict[str, Any]:
        """
        Standardize the response shape for aggregator consumption.
        
        Follows the structure defined in RemittanceProvider base class
        to ensure consistent response format across all providers.
        
        Args:
            raw_result: Provider-specific response dictionary
            provider_specific_data: Whether to include raw provider data
            
        Returns:
            Dictionary with standardized fields for the aggregator
        """
        # Ensure required keys exist with proper formatting
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
            "payment_method": raw_result.get("payment_method", "cash"),
            "delivery_method": raw_result.get("delivery_method", "cash"),
            "delivery_time_minutes": raw_result.get("delivery_time_minutes", 1440),  # Default to 24 hours
            "timestamp": raw_result.get("timestamp", datetime.now().isoformat()),
        }

        # Include raw API response if requested and available
        if provider_specific_data and "raw_response" in raw_result:
            output["raw_response"] = raw_result["raw_response"]

        return output
    
    def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        dest_currency: str,
        source_country: str,
        dest_country: str,
        payment_method: Optional[str] = None,
        delivery_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get a standardized quote from Al Ansari.
        Uses the convert_action API endpoint.
        
        Args:
            amount: Amount to send
            source_currency: Source currency code (e.g., "AED")
            dest_currency: Destination currency code (e.g., "INR")
            source_country: Source country code or name (e.g., "UNITED ARAB EMIRATES")
            dest_country: Destination country code or name (e.g., "INDIA")
            payment_method: Method of payment (default: "cash")
            delivery_method: Method of delivery (default: "cash")
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with standardized quote information
        """
        # Initialize result with default values
        quote_result = {
            "provider_id": "alansari",
            "success": False,
            "error_message": None,
            "send_amount": float(amount),
            "source_currency": source_currency.upper(),
            "destination_amount": None,
            "destination_currency": dest_currency.upper(),
            "exchange_rate": None,
            "fee": 0.0,
            "payment_method": payment_method or "cash",
            "delivery_method": delivery_method or "cash",
            "delivery_time_minutes": None,
            "timestamp": datetime.now().isoformat()
        }

        # Validate amount
        if amount <= 0:
            quote_result["error_message"] = f"Invalid amount: {amount}. Amount must be greater than zero."
            return quote_result

        try:
            # Always fetch a fresh security token for each request
            self.security_token = self.fetch_security_token()

            # Get currency IDs from mappings
            source_currency_id = self.CURRENCY_ID_MAPPING.get(source_currency.upper())
            dest_currency_id = self.CURRENCY_ID_MAPPING.get(dest_currency.upper())
            
            if not source_currency_id or not dest_currency_id:
                quote_result["error_message"] = f"Unsupported currency: {source_currency if not source_currency_id else dest_currency}"
                return quote_result

            # Transaction type - BT for Bank Transfer
            # This matches what's in the curl example
            trtype = "BT"  
            
            # Prepare request data - match the format from the curl example
            data = {
                "action": "convert_action",
                "currfrom": source_currency_id,
                "currto": dest_currency_id,
                "cntcode": dest_currency_id,  # In the example, this is the same as currto
                "amt": str(float(amount)),  # Convert to float then string for proper formatting
                "security": self.security_token,
                "trtype": trtype
            }

            # Add required headers based on the curl request
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://alansariexchange.com/",
                "Origin": "https://alansariexchange.com"
            }

            response = self.session.post(
                self.BASE_URL, 
                data=data, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                quote_result["error_message"] = (
                    f"Al Ansari API responded with HTTP {response.status_code}"
                )
                return quote_result

            try:
                ansari_json = response.json()
            except Exception as e:
                quote_result["error_message"] = f"Failed to parse JSON response: {str(e)}"
                return quote_result
                
            # For debugging
            if kwargs.get("include_raw", False):
                quote_result["raw_response"] = ansari_json
                
            # Check for successful response based on sample in README
            if ansari_json.get("status_msg") == "SUCCESS":
                quote_result["success"] = True
                
                # Extract values from the response
                if "amount" in ansari_json:
                    try:
                        quote_result["destination_amount"] = float(ansari_json["amount"].replace(",", ""))
                    except (ValueError, TypeError):
                        quote_result["error_message"] = "Invalid amount value in response"
                        quote_result["success"] = False
                        return quote_result
                
                if "get_rate" in ansari_json:
                    try:
                        quote_result["exchange_rate"] = float(ansari_json["get_rate"].replace(",", ""))
                    except (ValueError, TypeError):
                        quote_result["exchange_rate"] = quote_result["destination_amount"] / float(amount) if quote_result["destination_amount"] and float(amount) != 0 else None
            else:
                quote_result["error_message"] = ansari_json.get("message", "Unknown error from Al Ansari")
                quote_result["success"] = False
                
            return self.standardize_response(quote_result, provider_specific_data=kwargs.get("include_raw", False))
                
        except requests.RequestException as e:
            quote_result["error_message"] = f"Connection error: {str(e)}"
            return quote_result
        except Exception as e:
            quote_result["error_message"] = f"Unexpected error: {str(e)}"
            return quote_result

    def get_exchange_rate(
        self,
        source_currency: str,
        dest_currency: str,
        source_country: str = "UNITED ARAB EMIRATES",
        dest_country: str = "INDIA",
        amount: Decimal = Decimal("1000")
    ) -> Dict[str, Any]:
        """
        Get simplified dictionary with exchange rate + fee (if successful).
        
        Args:
            source_currency: Source currency code (e.g., "AED")
            dest_currency: Destination currency code (e.g., "INR")
            source_country: Source country name in uppercase (default: "UNITED ARAB EMIRATES")
            dest_country: Destination country name in uppercase (default: "INDIA")
            amount: Amount to send (default: 1000)
            
        Returns:
            Dictionary with exchange rate information
        """
        quote = self.get_quote(
            amount=amount,
            source_currency=source_currency,
            dest_currency=dest_currency,
            source_country=source_country,
            dest_country=dest_country
        )
        
        # No need to transform, simply return the quote which is already standardized
        return quote

    def get_supported_countries(self) -> List[str]:
        """Returns a list of all mapped countries (uppercase)."""
        return list(self.COUNTRY_ID_MAPPING.keys())

    def get_supported_currencies(self) -> List[str]:
        """Returns a list of all mapped ISO currency codes."""
        return list(self.CURRENCY_ID_MAPPING.keys())

    def get_supported_payment_methods(self) -> List[str]:
        """Returns a list of supported payment methods."""
        return ["cash", "bank_transfer", "debit_card", "credit_card"]

    def get_supported_receiving_methods(self) -> List[str]:
        """Returns a list of supported receiving methods."""
        return ["cash", "bank_deposit", "mobile_wallet"]

    def close(self):
        """Close the session if it exists."""
        if self.session:
            self.session.close()
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()