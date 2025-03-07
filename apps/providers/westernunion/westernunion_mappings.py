"""
Western Union Mappings

This module contains comprehensive mappings for use with the Western Union provider:
- Country to currency mappings
- Supported corridors
- Delivery methods by country
- API configuration settings
- Utility functions for validation and mapping

These mappings are separated from the main implementation to improve maintainability
and make it easier to extend support for additional countries and currencies.
"""

from typing import Dict, List, Tuple, Optional, Set, Any


# =============================================================================
# COUNTRY - CURRENCY MAPPINGS
# =============================================================================

# ISO-3166 Alpha-2 country codes mapped to their main currency (ISO-4217)
COUNTRY_CURRENCY_MAP: Dict[str, str] = {
    # North America
    "US": "USD",  # United States
    "CA": "CAD",  # Canada
    "MX": "MXN",  # Mexico
    "GT": "GTQ",  # Guatemala
    "BZ": "BZD",  # Belize
    "SV": "USD",  # El Salvador
    "HN": "HNL",  # Honduras
    "NI": "NIO",  # Nicaragua
    "CR": "CRC",  # Costa Rica
    "PA": "PAB",  # Panama
    
    # Caribbean
    "CU": "CUP",  # Cuba
    "DO": "DOP",  # Dominican Republic
    "HT": "HTG",  # Haiti
    "JM": "JMD",  # Jamaica
    "PR": "USD",  # Puerto Rico
    "BS": "BSD",  # Bahamas
    "BB": "BBD",  # Barbados
    "TT": "TTD",  # Trinidad and Tobago
    "AG": "XCD",  # Antigua and Barbuda
    "DM": "XCD",  # Dominica
    "GD": "XCD",  # Grenada
    "KN": "XCD",  # Saint Kitts and Nevis
    "LC": "XCD",  # Saint Lucia
    "VC": "XCD",  # Saint Vincent and the Grenadines
    
    # South America
    "AR": "ARS",  # Argentina
    "BO": "BOB",  # Bolivia
    "BR": "BRL",  # Brazil
    "CL": "CLP",  # Chile
    "CO": "COP",  # Colombia
    "EC": "USD",  # Ecuador
    "GY": "GYD",  # Guyana
    "PY": "PYG",  # Paraguay
    "PE": "PEN",  # Peru
    "SR": "SRD",  # Suriname
    "UY": "UYU",  # Uruguay
    "VE": "VES",  # Venezuela
    
    # Western Europe
    "GB": "GBP",  # United Kingdom
    "IE": "EUR",  # Ireland
    "FR": "EUR",  # France
    "DE": "EUR",  # Germany
    "NL": "EUR",  # Netherlands
    "BE": "EUR",  # Belgium
    "LU": "EUR",  # Luxembourg
    "AT": "EUR",  # Austria
    "CH": "CHF",  # Switzerland
    "ES": "EUR",  # Spain
    "PT": "EUR",  # Portugal
    "IT": "EUR",  # Italy
    "MT": "EUR",  # Malta
    "GR": "EUR",  # Greece
    "CY": "EUR",  # Cyprus
    
    # Northern Europe
    "DK": "DKK",  # Denmark
    "FI": "EUR",  # Finland
    "SE": "SEK",  # Sweden
    "NO": "NOK",  # Norway
    "IS": "ISK",  # Iceland
    "EE": "EUR",  # Estonia
    "LV": "EUR",  # Latvia
    "LT": "EUR",  # Lithuania
    
    # Eastern Europe
    "PL": "PLN",  # Poland
    "CZ": "CZK",  # Czech Republic
    "SK": "EUR",  # Slovakia
    "HU": "HUF",  # Hungary
    "RO": "RON",  # Romania
    "BG": "BGN",  # Bulgaria
    "HR": "EUR",  # Croatia
    "SI": "EUR",  # Slovenia
    "RS": "RSD",  # Serbia
    "ME": "EUR",  # Montenegro
    "MK": "MKD",  # North Macedonia
    "AL": "ALL",  # Albania
    "BA": "BAM",  # Bosnia and Herzegovina
    "UA": "UAH",  # Ukraine
    "MD": "MDL",  # Moldova
    "BY": "BYN",  # Belarus
    
    # Russia and Central Asia
    "RU": "RUB",  # Russia
    "KZ": "KZT",  # Kazakhstan
    "UZ": "UZS",  # Uzbekistan
    "TM": "TMT",  # Turkmenistan
    "KG": "KGS",  # Kyrgyzstan
    "TJ": "TJS",  # Tajikistan
    
    # Middle East
    "TR": "TRY",  # Turkey
    "IL": "ILS",  # Israel
    "SA": "SAR",  # Saudi Arabia
    "AE": "AED",  # United Arab Emirates
    "QA": "QAR",  # Qatar
    "KW": "KWD",  # Kuwait
    "BH": "BHD",  # Bahrain
    "OM": "OMR",  # Oman
    "IQ": "IQD",  # Iraq
    "IR": "IRR",  # Iran
    "JO": "JOD",  # Jordan
    "LB": "LBP",  # Lebanon
    "SY": "SYP",  # Syria
    "YE": "YER",  # Yemen
    
    # South Asia
    "IN": "INR",  # India
    "PK": "PKR",  # Pakistan
    "BD": "BDT",  # Bangladesh
    "LK": "LKR",  # Sri Lanka
    "NP": "NPR",  # Nepal
    "BT": "BTN",  # Bhutan
    "MV": "MVR",  # Maldives
    
    # East Asia
    "CN": "CNY",  # China
    "JP": "JPY",  # Japan
    "KR": "KRW",  # South Korea
    "TW": "TWD",  # Taiwan
    "MN": "MNT",  # Mongolia
    "HK": "HKD",  # Hong Kong
    "MO": "MOP",  # Macau
    
    # Southeast Asia
    "PH": "PHP",  # Philippines
    "ID": "IDR",  # Indonesia
    "MY": "MYR",  # Malaysia
    "SG": "SGD",  # Singapore
    "TH": "THB",  # Thailand
    "VN": "VND",  # Vietnam
    "MM": "MMK",  # Myanmar
    "LA": "LAK",  # Laos
    "KH": "KHR",  # Cambodia
    "BN": "BND",  # Brunei
    "TL": "USD",  # Timor-Leste
    
    # Oceania
    "AU": "AUD",  # Australia
    "NZ": "NZD",  # New Zealand
    "PG": "PGK",  # Papua New Guinea
    "FJ": "FJD",  # Fiji
    "SB": "SBD",  # Solomon Islands
    "VU": "VUV",  # Vanuatu
    "WS": "WST",  # Samoa
    "TO": "TOP",  # Tonga
    
    # North Africa
    "EG": "EGP",  # Egypt
    "MA": "MAD",  # Morocco
    "DZ": "DZD",  # Algeria
    "TN": "TND",  # Tunisia
    "LY": "LYD",  # Libya
    
    # Sub-Saharan Africa
    "ZA": "ZAR",  # South Africa
    "NG": "NGN",  # Nigeria
    "KE": "KES",  # Kenya
    "ET": "ETB",  # Ethiopia
    "TZ": "TZS",  # Tanzania
    "UG": "UGX",  # Uganda
    "GH": "GHS",  # Ghana
    "SN": "XOF",  # Senegal
    "CI": "XOF",  # Côte d'Ivoire
    "CM": "XAF",  # Cameroon
    "ZM": "ZMW",  # Zambia
    "ZW": "ZWL",  # Zimbabwe (though USD is commonly used)
    "AO": "AOA",  # Angola
    "MZ": "MZN",  # Mozambique
    "RW": "RWF",  # Rwanda
    "SL": "SLE",  # Sierra Leone
    "ML": "XOF",  # Mali
    "BF": "XOF",  # Burkina Faso
    "NE": "XOF",  # Niger
    "TD": "XAF",  # Chad
    "BJ": "XOF",  # Benin
    "MG": "MGA",  # Madagascar
    "MW": "MWK",  # Malawi
    "LS": "LSL",  # Lesotho
    "NA": "NAD",  # Namibia
    "BW": "BWP",  # Botswana
}

# Reverse mapping to get country codes from currency
CURRENCY_COUNTRIES_MAP: Dict[str, List[str]] = {}
for country, currency in COUNTRY_CURRENCY_MAP.items():
    if currency not in CURRENCY_COUNTRIES_MAP:
        CURRENCY_COUNTRIES_MAP[currency] = []
    CURRENCY_COUNTRIES_MAP[currency].append(country)


# =============================================================================
# SUPPORTED CORRIDOR DEFINITIONS
# =============================================================================

# Format: (source_country, source_currency, destination_country, destination_currency)
# This is a representative list, actual support status should be verified with WU's API
SUPPORTED_CORRIDORS: List[Tuple[str, str, str, str]] = [
    # USD from US
    ("US", "USD", "MX", "MXN"),
    ("US", "USD", "CO", "COP"),
    ("US", "USD", "PH", "PHP"),
    ("US", "USD", "IN", "INR"),
    ("US", "USD", "DO", "DOP"),
    ("US", "USD", "GT", "GTQ"),
    ("US", "USD", "JM", "JMD"),
    ("US", "USD", "SV", "USD"),
    ("US", "USD", "HN", "HNL"),
    ("US", "USD", "NI", "NIO"),
    ("US", "USD", "CN", "CNY"),
    ("US", "USD", "NG", "NGN"),
    ("US", "USD", "KE", "KES"),
    
    # EUR from EU countries
    ("DE", "EUR", "TR", "TRY"),
    ("DE", "EUR", "PL", "PLN"),
    ("DE", "EUR", "RO", "RON"),
    ("DE", "EUR", "MA", "MAD"),
    ("FR", "EUR", "MA", "MAD"),
    ("ES", "EUR", "CO", "COP"),
    ("IT", "EUR", "RO", "RON"),

    # GBP from UK
    ("GB", "GBP", "IN", "INR"),
    ("GB", "GBP", "PK", "PKR"),
    ("GB", "GBP", "PH", "PHP"),
    ("GB", "GBP", "NG", "NGN"),
    ("GB", "GBP", "ZA", "ZAR"),
    
    # Other corridors
    ("CA", "CAD", "IN", "INR"),
    ("AU", "AUD", "PH", "PHP"),
    ("SG", "SGD", "ID", "IDR"),
    ("SG", "SGD", "MY", "MYR"),
    ("NO", "NOK", "BN", "BND"),
    ("PL", "PLN", "LT", "EUR"),
    ("TR", "TRY", "PK", "PKR"),
]

# Common send countries (for reference)
COMMON_SEND_COUNTRIES = [
    "US", "GB", "DE", "FR", "IT", "ES", "CA", "AU", "SG", "AE", "SA", "NO", "SE"
]

# Common receive countries (for reference)
COMMON_RECEIVE_COUNTRIES = [
    "MX", "IN", "PH", "CO", "DO", "GT", "CN", "NG", "KE", "TR", "RO", "MA", "PK", 
    "ID", "MY", "BR", "VN", "UA", "EG", "JM", "BN", "LT"
]


# =============================================================================
# DELIVERY METHODS
# =============================================================================

# Maps Western Union internal service codes to descriptive names
DELIVERY_SERVICE_CODES = {
    "000": "CASH_PICKUP",          # Money in Minutes / Cash pickup
    "001": "ACCOUNT_DEPOSIT",      # Direct to Bank / Bank deposit
    "002": "ACCOUNT_DEPOSIT",      # Economy service to bank
    "100": "CASH_HOME_DELIVERY",   # Cash delivery to door
    "050": "MOBILE_MONEY",         # Mobile money
    "060": "WALLET_ACCOUNT",       # Mobile wallet
    "115": "UPI",                  # UPI (India-specific)
    "080": "PREPAID_CARD"          # Western Union prepaid card
}

# Maps Western Union internal payment codes to descriptive names
PAYMENT_METHOD_CODES = {
    "CC": "CREDITCARD",       # Credit card
    "DC": "DEBITCARD",        # Debit card
    "BA": "BANKACCOUNT",      # Bank account / ACH / direct debit
    "CA": "CASH",             # Cash at agent location
    "EB": "ONLINE_BANKING",   # Online banking
    "GP": "GIROPAY",          # Giropay (Germany)
    "TR": "TRUSTLY",          # Trustly (EU)
    "TK": "TRUSTLY",          # Trustly alias
    "SO": "SOFORT"            # Sofort (EU)
}

# Maps countries to their available delivery methods
# This is indicative and may vary; actual availability should be verified with the API
COUNTRY_DELIVERY_METHODS: Dict[str, List[str]] = {
    # Default delivery methods for all countries if not specified
    "DEFAULT": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    
    # North America
    "MX": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "GT": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "SV": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "HN": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "NI": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "CR": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "PA": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    
    # Caribbean & Latin America
    "DO": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "JM": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "CO": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "PE": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "EC": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    
    # Asia
    "PH": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "IN": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "UPI", "MOBILE_MONEY"],
    "CN": ["ACCOUNT_DEPOSIT"],
    "ID": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "VN": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "BD": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "NP": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "PK": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "LK": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "MY": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "TH": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "SG": ["ACCOUNT_DEPOSIT"],
    "BN": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    
    # Africa
    "NG": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "KE": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "GH": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "ZA": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "ET": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "UG": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "TZ": ["CASH_PICKUP", "ACCOUNT_DEPOSIT", "MOBILE_MONEY"],
    "MA": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "EG": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    
    # Europe
    "TR": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "PL": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "RO": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "UA": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "RS": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "BA": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "BG": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "AL": ["CASH_PICKUP", "ACCOUNT_DEPOSIT"],
    "LT": ["ACCOUNT_DEPOSIT"]
}

# Maps Western Union delivery methods to standardized aggregator delivery methods
DELIVERY_METHOD_TO_AGGREGATOR = {
    "CASH_PICKUP": "cashPickup",
    "ACCOUNT_DEPOSIT": "bankDeposit",
    "MOBILE_MONEY": "mobileWallet", 
    "WALLET_ACCOUNT": "mobileWallet",
    "CASH_HOME_DELIVERY": "cashDelivery",
    "UPI": "digitalWallet",
    "PREPAID_CARD": "prepaidCard"
}

# Maps Western Union payment methods to standardized aggregator payment methods
PAYMENT_METHOD_TO_AGGREGATOR = {
    "CREDITCARD": "creditCard",
    "DEBITCARD": "debitCard",
    "BANKACCOUNT": "bankAccount",
    "CASH": "cash",
    "ONLINE_BANKING": "onlineBanking",
    "GIROPAY": "giropay",
    "TRUSTLY": "trustly",
    "SOFORT": "sofort"
}


# =============================================================================
# API CONFIGURATION
# =============================================================================

API_CONFIG = {
    "BASE_URL": "https://www.westernunion.com",
    "START_PAGE_URL": "https://www.westernunion.com/us/en/web/send-money/start",
    "CATALOG_URL": "https://www.westernunion.com/wuconnect/prices/catalog",
    "DEFAULT_TIMEOUT": 30,
    "DEFAULT_USER_AGENT": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "HEADERS": {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.westernunion.com",
        "Referer": "https://www.westernunion.com/us/en/web/send-money/start"
    },
    "DEFAULT_COOKIES": {
        "wu_language": "en_US",
        "wu_region": "us",
        "wu_market": "us",
        "WUCountryCookie_": "US",
        "WULanguageCookie_": "en",
        "resolution_height": "800",
        "resolution_width": "1280",
        "wu_cookies_accepted": "true"
    }
}

# Default values
DEFAULT_VALUES = {
    "DEFAULT_PAYMENT_METHOD": "bankAccount",
    "DEFAULT_DELIVERY_METHOD": "bankDeposit",
    "DEFAULT_DELIVERY_TIME_MINUTES": 1440  # 1 day in minutes
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_corridor_supported(source_country: str, destination_country: str,
                         source_currency: Optional[str] = None,
                         destination_currency: Optional[str] = None) -> bool:
    """
    Check if a corridor is supported by Western Union.
    
    Args:
        source_country: The sending country code (ISO 3166-1 alpha-2)
        destination_country: The receiving country code
        source_currency: Optional source currency code
        destination_currency: Optional destination currency code
        
    Returns:
        True if the corridor is supported, False otherwise
    """
    # Normalize inputs
    source_country = source_country.upper()
    destination_country = destination_country.upper()
    
    # If currencies not provided, use defaults from the mapping
    if not source_currency and source_country in COUNTRY_CURRENCY_MAP:
        source_currency = COUNTRY_CURRENCY_MAP[source_country]
    if not destination_currency and destination_country in COUNTRY_CURRENCY_MAP:
        destination_currency = COUNTRY_CURRENCY_MAP[destination_country]
    
    # Both countries must have known currencies
    if not source_currency or not destination_currency:
        return False
    
    # Check if the corridor is in our predefined list
    source_currency = source_currency.upper()
    destination_currency = destination_currency.upper()
    
    # Direct check against supported corridors
    if (source_country, source_currency, destination_country, destination_currency) in SUPPORTED_CORRIDORS:
        return True
    
    # More advanced check: check if the corridor is commonly supported
    # This is a best guess and actual API calls should be made to confirm
    if source_country in COMMON_SEND_COUNTRIES and destination_country in COMMON_RECEIVE_COUNTRIES:
        return True
    
    return False


def get_delivery_methods_for_country(country_code: str) -> List[str]:
    """
    Get available delivery methods for a given country.
    
    Args:
        country_code: The country code (ISO 3166-1 alpha-2)
        
    Returns:
        List of delivery methods available for the country
    """
    country_code = country_code.upper()
    return COUNTRY_DELIVERY_METHODS.get(country_code, COUNTRY_DELIVERY_METHODS["DEFAULT"])


def get_aggregator_delivery_method(wu_delivery_method: str) -> str:
    """
    Map a Western Union delivery method to the standardized aggregator format.
    
    Args:
        wu_delivery_method: The Western Union delivery method
        
    Returns:
        The corresponding aggregator delivery method
    """
    return DELIVERY_METHOD_TO_AGGREGATOR.get(wu_delivery_method, "bankDeposit")


def get_aggregator_payment_method(wu_payment_method: str) -> str:
    """
    Map a Western Union payment method to the standardized aggregator format.
    
    Args:
        wu_payment_method: The Western Union payment method
        
    Returns:
        The corresponding aggregator payment method
    """
    return PAYMENT_METHOD_TO_AGGREGATOR.get(wu_payment_method, "bankAccount")


def get_country_for_currency(currency_code: str) -> List[str]:
    """
    Find countries that use a given currency.
    
    Args:
        currency_code: The currency code (ISO 4217)
        
    Returns:
        List of country codes using the currency
    """
    return CURRENCY_COUNTRIES_MAP.get(currency_code.upper(), [])


def get_service_code_for_delivery_method(delivery_method: str) -> str:
    """
    Map aggregator delivery method to Western Union service code.
    
    Args:
        delivery_method: The aggregator delivery method
        
    Returns:
        The Western Union service code or None if not found
    """
    # Reverse the delivery method mapping
    reverse_map = {v: k for k, v in DELIVERY_METHOD_TO_AGGREGATOR.items()}
    wu_delivery_method = reverse_map.get(delivery_method)
    
    if not wu_delivery_method:
        return "000"  # Default to cash pickup service code
    
    # Find the service code
    for code, method in DELIVERY_SERVICE_CODES.items():
        if method == wu_delivery_method:
            return code
    
    return "000"  # Default if no match found


def get_payment_code_for_payment_method(payment_method: str) -> str:
    """
    Map aggregator payment method to Western Union payment code.
    
    Args:
        payment_method: The aggregator payment method
        
    Returns:
        The Western Union payment code or None if not found
    """
    # Reverse the payment method mapping
    reverse_map = {v: k for k, v in PAYMENT_METHOD_TO_AGGREGATOR.items()}
    wu_payment_method = reverse_map.get(payment_method)
    
    if not wu_payment_method:
        return "BA"  # Default to bank account
    
    # Find the payment code
    for code, method in PAYMENT_METHOD_CODES.items():
        if method == wu_payment_method:
            return code
    
    return "BA"  # Default if no match found 