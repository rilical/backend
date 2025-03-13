"""
Mapping file for TransferGo provider.

This file centralizes all constants and utility functions related to the TransferGo provider.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

# Import utility functions from core modules
from providers.utils.country_currency_standards import get_country_name
from providers.utils.country_currency_standards import (
    get_default_currency_for_country as get_std_currency_for_country,
)
from providers.utils.country_currency_standards import (
    normalize_country_code,
    validate_corridor,
)

logger = logging.getLogger(__name__)

# API configuration
API_CONFIG = {
    "base_url": "https://my.transfergo.com",
    "api_version": "v1",
    "timeout": 30,
    "user_agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    ),
    "headers": {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Origin": "https://www.transfergo.com",
        "Referer": "https://www.transfergo.com/",
    },
}

# Delivery method mapping (TransferGo → aggregator naming)
DELIVERY_METHODS = {
    "BANK_TRANSFER": "bank_deposit",
    "CASH_PICKUP": "cash_pickup",
    "MOBILE_WALLET": "mobile_wallet",
}

# Payment method mapping (TransferGo → aggregator naming)
PAYMENT_METHODS = {
    "BANK_TRANSFER": "bank_transfer",
    "CARD": "card",
    "WALLET": "e_wallet",
}

# Default values
DEFAULT_VALUES = {
    "payment_method": "bank_transfer",
    "delivery_method": "bank_deposit",
    "delivery_time_minutes": 1440,  # 24 hours in minutes
}

# Comprehensive country to currency mapping
# Based on TransferGo's calculator interface
COUNTRY_CURRENCIES = {
    # Europe
    "AT": "EUR",  # Austria
    "BE": "EUR",  # Belgium
    "BG": ["BGN", "EUR"],  # Bulgaria
    "HR": "EUR",  # Croatia
    "CY": "EUR",  # Cyprus
    "CZ": ["CZK", "EUR"],  # Czech Republic
    "DK": ["DKK", "EUR"],  # Denmark
    "EE": "EUR",  # Estonia
    "FI": "EUR",  # Finland
    "FR": "EUR",  # France
    "DE": "EUR",  # Germany
    "GR": "EUR",  # Greece
    "HU": ["HUF", "EUR"],  # Hungary
    "IS": ["ISK", "EUR"],  # Iceland
    "IE": "EUR",  # Ireland
    "IT": "EUR",  # Italy
    "LV": "EUR",  # Latvia
    "LI": "EUR",  # Liechtenstein
    "LT": "EUR",  # Lithuania
    "LU": "EUR",  # Luxembourg
    "MT": "EUR",  # Malta
    "MC": "EUR",  # Monaco
    "NL": "EUR",  # Netherlands
    "NO": ["NOK", "EUR"],  # Norway
    "PL": ["PLN", "EUR"],  # Poland
    "PT": "EUR",  # Portugal
    "RO": ["RON", "EUR"],  # Romania
    "SM": "EUR",  # San Marino
    "SK": "EUR",  # Slovakia
    "SI": "EUR",  # Slovenia
    "ES": "EUR",  # Spain
    "SE": ["SEK", "EUR"],  # Sweden
    "CH": ["CHF", "EUR"],  # Switzerland
    "GB": ["GBP", "EUR"],  # United Kingdom
    # Other European countries
    "AL": "ALL",  # Albania
    "AD": "EUR",  # Andorra
    "AM": ["AMD", "USD", "EUR"],  # Armenia
    "AZ": ["AZN", "USD", "EUR"],  # Azerbaijan
    "BY": "BYN",  # Belarus
    "BA": "BAM",  # Bosnia and Herzegovina
    "GE": ["GEL", "USD", "EUR"],  # Georgia
    "GI": "GIP",  # Gibraltar
    "VA": "EUR",  # Vatican City
    "XK": "EUR",  # Kosovo
    "MK": "MKD",  # Macedonia
    "MD": ["MDL", "USD", "EUR"],  # Moldova
    "ME": "EUR",  # Montenegro
    "RS": "RSD",  # Serbia
    "TR": "TRY",  # Turkey
    "UA": ["UAH", "EUR", "USD"],  # Ukraine
    # Asia
    "BD": "BDT",  # Bangladesh
    "BT": "BTN",  # Bhutan
    "BN": "BND",  # Brunei Darussalam
    "KH": "KHR",  # Cambodia
    "CN": "USD",  # China
    "HK": ["HKD", "USD"],  # Hong Kong
    "IN": "INR",  # India
    "ID": "IDR",  # Indonesia
    "JP": ["JPY", "USD"],  # Japan
    "KZ": ["KZT", "USD", "EUR"],  # Kazakhstan
    "KG": ["KGS", "USD", "EUR"],  # Kyrgyzstan
    "MY": "MYR",  # Malaysia
    "MV": "MVR",  # Maldives
    "MN": "MNT",  # Mongolia
    "MM": "MMK",  # Myanmar
    "NP": "NPR",  # Nepal
    "PK": "PKR",  # Pakistan
    "PH": "PHP",  # Philippines
    "SG": ["SGD", "USD"],  # Singapore
    "KR": "KRW",  # South Korea
    "LK": "LKR",  # Sri Lanka
    "TW": "TWD",  # Taiwan
    "TJ": ["TJS", "USD", "EUR"],  # Tajikistan
    "TH": ["THB", "USD"],  # Thailand
    "TL": "USD",  # Timor-Leste
    "TM": "TMT",  # Turkmenistan
    "UZ": ["UZS", "USD", "EUR"],  # Uzbekistan
    "VN": "VND",  # Vietnam
    # Middle East
    "BH": ["BHD", "USD"],  # Bahrain
    "IL": "ILS",  # Israel
    "JO": "JOD",  # Jordan
    "KW": ["KWD", "USD"],  # Kuwait
    "LB": "LBP",  # Lebanon
    "OM": ["OMR", "USD"],  # Oman
    "PS": "ILS",  # Palestinian Territory
    "QA": ["QAR", "USD"],  # Qatar
    "SA": ["SAR", "USD"],  # Saudi Arabia
    "AE": "AED",  # United Arab Emirates
    "YE": "YER",  # Yemen
    # Africa
    "DZ": "DZD",  # Algeria
    "AO": "AOA",  # Angola
    "BJ": "XOF",  # Benin
    "BW": "BWP",  # Botswana
    "BF": "XOF",  # Burkina Faso
    "BI": "BIF",  # Burundi
    "CM": "XAF",  # Cameroon
    "CV": "CVE",  # Cape Verde
    "CF": "XAF",  # Central African Republic
    "TD": "XAF",  # Chad
    "KM": "KMF",  # Comoros
    "CG": "XAF",  # Congo
    "CI": "XOF",  # Côte d'Ivoire
    "DJ": "DJF",  # Djibouti
    "EG": "EGP",  # Egypt
    "GQ": "XAF",  # Equatorial Guinea
    "ER": "ERN",  # Eritrea
    "SZ": "SZL",  # Eswatini (Swaziland)
    "ET": "ETB",  # Ethiopia
    "GA": "XAF",  # Gabon
    "GM": "GMD",  # Gambia
    "GH": "GHS",  # Ghana
    "GN": "GNF",  # Guinea
    "GW": "XOF",  # Guinea-Bissau
    "KE": ["KES", "USD"],  # Kenya
    "LS": "LSL",  # Lesotho
    "LR": "LRD",  # Liberia
    "LY": "LYD",  # Libya
    "MG": "MGA",  # Madagascar
    "MW": "MWK",  # Malawi
    "ML": "XOF",  # Mali
    "MR": "MRU",  # Mauritania
    "MU": "MUR",  # Mauritius
    "MA": "MAD",  # Morocco
    "MZ": "MZN",  # Mozambique
    "NA": "NAD",  # Namibia
    "NE": "XOF",  # Niger
    "NG": "NGN",  # Nigeria
    "RW": "RWF",  # Rwanda
    "ST": "STN",  # Sao Tome and Principe
    "SN": "XOF",  # Senegal
    "SC": "SCR",  # Seychelles
    "SL": "SLL",  # Sierra Leone
    "SO": "SOS",  # Somalia
    "ZA": "ZAR",  # South Africa
    "SS": "SSP",  # South Sudan
    "SD": "SDG",  # Sudan
    "TZ": "TZS",  # Tanzania
    "TG": "XOF",  # Togo
    "TN": "TND",  # Tunisia
    "UG": "UGX",  # Uganda
    "ZM": "ZMW",  # Zambia
    "ZW": "ZWL",  # Zimbabwe
    # Americas
    "AR": "ARS",  # Argentina
    "BS": "BSD",  # Bahamas
    "BB": "BBD",  # Barbados
    "BZ": "BZD",  # Belize
    "BM": "BMD",  # Bermuda
    "BO": "BOB",  # Bolivia
    "BR": "BRL",  # Brazil
    "CA": "CAD",  # Canada
    "CL": "CLP",  # Chile
    "CO": "COP",  # Colombia
    "CR": "CRC",  # Costa Rica
    "CU": "CUP",  # Cuba
    "DM": "XCD",  # Dominica
    "DO": "DOP",  # Dominican Republic
    "EC": "USD",  # Ecuador
    "SV": "USD",  # El Salvador
    "GF": "EUR",  # French Guiana
    "GD": "XCD",  # Grenada
    "GP": "EUR",  # Guadeloupe
    "GT": "GTQ",  # Guatemala
    "GY": "GYD",  # Guyana
    "HT": "HTG",  # Haiti
    "HN": "HNL",  # Honduras
    "JM": "JMD",  # Jamaica
    "MQ": "EUR",  # Martinique
    "MX": "MXN",  # Mexico
    "MS": "XCD",  # Montserrat
    "NI": "NIO",  # Nicaragua
    "PA": "USD",  # Panama
    "PY": "PYG",  # Paraguay
    "PE": "PEN",  # Peru
    "PR": "USD",  # Puerto Rico
    "KN": "XCD",  # Saint Kitts and Nevis
    "LC": "XCD",  # Saint Lucia
    "PM": "EUR",  # Saint Pierre and Miquelon
    "VC": "XCD",  # Saint Vincent and the Grenadines
    "SR": "SRD",  # Suriname
    "TT": "TTD",  # Trinidad and Tobago
    "US": "USD",  # United States
    "UY": "UYU",  # Uruguay
    "VE": "VES",  # Venezuela
    "VI": "USD",  # Virgin Islands, U.S.
    "VG": "USD",  # Virgin Islands, British
    "AI": "XCD",  # Anguilla
    "AG": "XCD",  # Antigua and Barbuda
    "AW": "AWG",  # Aruba
    "KY": "KYD",  # Cayman Islands
    "CW": "ANG",  # Curaçao
    # Oceania
    "AU": "AUD",  # Australia
    "CK": "NZD",  # Cook Islands
    "FJ": "FJD",  # Fiji
    "PF": "XPF",  # French Polynesia
    "GU": "USD",  # Guam
    "KI": "AUD",  # Kiribati
    "MH": "USD",  # Marshall Islands
    "FM": "USD",  # Micronesia
    "NR": "AUD",  # Nauru
    "NC": "XPF",  # New Caledonia
    "NZ": ["NZD", "USD"],  # New Zealand
    "NU": "NZD",  # Niue
    "MP": "USD",  # Northern Mariana Islands
    "PW": "USD",  # Palau
    "PG": "PGK",  # Papua New Guinea
    "WS": "WST",  # Samoa
    "SB": "SBD",  # Solomon Islands
    "TO": "TOP",  # Tonga
    "TV": "AUD",  # Tuvalu
    "VU": "VUV",  # Vanuatu
    "WF": "XPF",  # Wallis and Futuna
}

# Simplified country currency lookup for better performance
FLAT_COUNTRY_CURRENCIES = {}
for country, currencies in COUNTRY_CURRENCIES.items():
    if isinstance(currencies, list):
        # If multiple currencies, use the first as primary
        FLAT_COUNTRY_CURRENCIES[country] = currencies[0]
    else:
        FLAT_COUNTRY_CURRENCIES[country] = currencies

# Popular corridors with known good support
# Format: (source_country, source_currency, destination_country, destination_currency)
POPULAR_CORRIDORS = [
    # Europe to Europe
    ("GB", "GBP", "PL", "PLN"),
    ("GB", "GBP", "RO", "RON"),
    ("GB", "GBP", "LT", "EUR"),
    ("DE", "EUR", "PL", "PLN"),
    ("DE", "EUR", "RO", "RON"),
    ("DE", "EUR", "TR", "TRY"),
    ("DE", "EUR", "UA", "UAH"),
    ("ES", "EUR", "RO", "RON"),
    ("IT", "EUR", "RO", "RON"),
    # Europe to Asia
    ("GB", "GBP", "IN", "INR"),
    ("GB", "GBP", "PH", "PHP"),
    ("DE", "EUR", "IN", "INR"),
    ("DE", "EUR", "PH", "PHP"),
    # North America to Asia/Latin America
    ("US", "USD", "IN", "INR"),
    ("US", "USD", "PH", "PHP"),
    ("US", "USD", "MX", "MXN"),
    ("CA", "CAD", "IN", "INR"),
    ("CA", "CAD", "PH", "PHP"),
    # Oceania to Asia
    ("AU", "AUD", "IN", "INR"),
    ("AU", "AUD", "PH", "PHP"),
    # Asia to Asia
    ("SG", "SGD", "IN", "INR"),
    ("SG", "SGD", "PH", "PHP"),
    # Additional popular corridors
    ("DE", "EUR", "TR", "TRY"),
    ("NL", "EUR", "TR", "TRY"),
    ("FR", "EUR", "MA", "MAD"),
    ("ES", "EUR", "MA", "MAD"),
    ("GB", "GBP", "PK", "PKR"),
    ("GB", "GBP", "NG", "NGN"),
    ("GB", "GBP", "KE", "KES"),
    ("GB", "GBP", "ZA", "ZAR"),
    ("GB", "GBP", "GH", "GHS"),
    ("US", "USD", "CO", "COP"),
]

# List of country codes that support cash pickup
CASH_PICKUP_COUNTRIES = [
    "PH",
    "MX",
    "CO",
    "VN",
    "PK",
    "IN",
    "TR",
    "MA",
    "GH",
    "NG",
    "UA",
]

# List of country codes that support mobile wallet
MOBILE_WALLET_COUNTRIES = ["PH", "IN", "KE", "GH", "NG"]

# Country-specific available delivery methods
COUNTRY_DELIVERY_METHODS = {
    "IN": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "mobile_wallet",
            "method_name": "Mobile Wallet",
            "standardized_name": "mobile_wallet",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
    ],
    "PH": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
        {
            "method_code": "mobile_wallet",
            "method_name": "Mobile Wallet",
            "standardized_name": "mobile_wallet",
        },
    ],
    "MX": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
    ],
    "UA": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
    ],
    "TR": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
    ],
    "PK": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
    ],
    "GH": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "mobile_wallet",
            "method_name": "Mobile Wallet",
            "standardized_name": "mobile_wallet",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
    ],
    "NG": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "mobile_wallet",
            "method_name": "Mobile Wallet",
            "standardized_name": "mobile_wallet",
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
        },
    ],
    "KE": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        },
        {
            "method_code": "mobile_wallet",
            "method_name": "Mobile Wallet",
            "standardized_name": "mobile_wallet",
        },
    ],
    "default": [
        {
            "method_code": "bank_deposit",
            "method_name": "Bank Deposit",
            "standardized_name": "bank_deposit",
        }
    ],
}

# Country-specific available payment methods
COUNTRY_PAYMENT_METHODS = {
    "GB": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_transfer",
        },
        {
            "method_code": "card",
            "method_name": "Card Payment",
            "standardized_name": "card",
        },
    ],
    "DE": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_transfer",
        },
        {
            "method_code": "card",
            "method_name": "Card Payment",
            "standardized_name": "card",
        },
    ],
    "US": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_transfer",
        },
        {
            "method_code": "card",
            "method_name": "Card Payment",
            "standardized_name": "card",
        },
    ],
    "default": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_transfer",
        }
    ],
}


def is_corridor_supported(
    source_country: str,
    source_currency: str,
    destination_country: str,
    destination_currency: str,
) -> bool:
    """
    Check if a corridor is supported by TransferGo.

    Args:
        source_country: ISO country code of the source country
        source_currency: ISO currency code of the source currency
        destination_country: ISO country code of the destination country
        destination_currency: ISO currency code of the destination currency

    Returns:
        True if the corridor is supported, False otherwise
    """
    # Normalize country codes
    try:
        source_country = normalize_country_code(source_country)
        destination_country = normalize_country_code(destination_country)
    except Exception as e:
        logger.error(f"Error normalizing country codes: {e}")
        return False

    # Validate source currency for the source country
    source_valid = False
    if source_country in COUNTRY_CURRENCIES:
        country_currencies = COUNTRY_CURRENCIES[source_country]
        if isinstance(country_currencies, list):
            source_valid = source_currency in country_currencies
        else:
            source_valid = source_currency == country_currencies

    if not source_valid:
        return False

    # Validate destination currency for the destination country
    dest_valid = False
    if destination_country in COUNTRY_CURRENCIES:
        country_currencies = COUNTRY_CURRENCIES[destination_country]
        if isinstance(country_currencies, list):
            dest_valid = destination_currency in country_currencies
        else:
            dest_valid = destination_currency == country_currencies

    if not dest_valid:
        return False

    # Check against popular corridors list first (these are known to work well)
    for src_country, src_currency, dst_country, dst_currency in POPULAR_CORRIDORS:
        if (
            source_country == src_country
            and source_currency == src_currency
            and destination_country == dst_country
            and destination_currency == dst_currency
        ):
            return True

    # For other corridors, use more general validation
    # TransferGo generally supports most corridors if both country-currency pairs are valid
    return source_valid and dest_valid


def get_delivery_methods_for_country(country_code: str) -> List[Dict[str, Any]]:
    """
    Get the available delivery methods for a specific country.

    Args:
        country_code: ISO country code

    Returns:
        List of delivery methods with their codes and names
    """
    try:
        normalized_code = normalize_country_code(country_code)
        if normalized_code in COUNTRY_DELIVERY_METHODS:
            return COUNTRY_DELIVERY_METHODS[normalized_code]

        # If not explicitly in our mapping, but country supports cash pickup
        if normalized_code in CASH_PICKUP_COUNTRIES:
            return [
                {
                    "method_code": "bank_deposit",
                    "method_name": "Bank Deposit",
                    "standardized_name": "bank_deposit",
                },
                {
                    "method_code": "cash_pickup",
                    "method_name": "Cash Pickup",
                    "standardized_name": "cash_pickup",
                },
            ]

        # If not explicitly in our mapping, but country supports mobile wallet
        if normalized_code in MOBILE_WALLET_COUNTRIES:
            return [
                {
                    "method_code": "bank_deposit",
                    "method_name": "Bank Deposit",
                    "standardized_name": "bank_deposit",
                },
                {
                    "method_code": "mobile_wallet",
                    "method_name": "Mobile Wallet",
                    "standardized_name": "mobile_wallet",
                },
            ]

        return COUNTRY_DELIVERY_METHODS["default"]
    except Exception:
        return COUNTRY_DELIVERY_METHODS["default"]


def get_payment_methods_for_country(country_code: str) -> List[Dict[str, Any]]:
    """
    Get the available payment methods for a specific country.

    Args:
        country_code: ISO country code

    Returns:
        List of payment methods with their codes and names
    """
    try:
        normalized_code = normalize_country_code(country_code)
        if normalized_code in COUNTRY_PAYMENT_METHODS:
            return COUNTRY_PAYMENT_METHODS[normalized_code]
        return COUNTRY_PAYMENT_METHODS["default"]
    except Exception:
        return COUNTRY_PAYMENT_METHODS["default"]


def get_default_currency_for_country(country_code: str) -> str:
    """
    Get the default currency for a country. First checks the TransferGo-specific mapping,
    then falls back to the standard mapping.

    Args:
        country_code: ISO country code

    Returns:
        ISO currency code or None if not found
    """
    try:
        normalized_code = normalize_country_code(country_code)
        if normalized_code in FLAT_COUNTRY_CURRENCIES:
            return FLAT_COUNTRY_CURRENCIES[normalized_code]
        if normalized_code in COUNTRY_CURRENCIES:
            currencies = COUNTRY_CURRENCIES[normalized_code]
            if isinstance(currencies, list):
                return currencies[0]
            return currencies
        return get_std_currency_for_country(normalized_code)
    except Exception:
        return None


def get_supported_source_countries() -> List[str]:
    """
    Get a list of supported source countries.

    Returns:
        List of ISO country codes
    """
    source_countries = set()

    # Add countries from popular corridors first
    for corridor in POPULAR_CORRIDORS:
        source_countries.add(corridor[0])

    # Add other countries that have valid currencies
    for country, currencies in COUNTRY_CURRENCIES.items():
        if isinstance(currencies, list) and len(currencies) > 0:
            source_countries.add(country)
        elif currencies:
            source_countries.add(country)

    return sorted(list(source_countries))


def get_supported_destination_countries(
    source_country: Optional[str] = None,
) -> List[str]:
    """
    Get a list of supported destination countries for a given source country.
    If source_country is None, returns all destination countries.

    Args:
        source_country: Optional ISO country code of the source country

    Returns:
        List of ISO country codes
    """
    if source_country:
        try:
            normalized_code = normalize_country_code(source_country)
            dest_countries = set()

            # Check popular corridors first
            for src_country, _, dst_country, _ in POPULAR_CORRIDORS:
                if src_country == normalized_code:
                    dest_countries.add(dst_country)

            # If no specific destinations found, return all countries
            # that have valid currencies (TransferGo generally supports
            # transfers between any supported countries)
            if not dest_countries:
                for country in COUNTRY_CURRENCIES.keys():
                    if country != normalized_code:
                        dest_countries.add(country)

            return sorted(list(dest_countries))
        except Exception:
            return []
    else:
        # Return all countries that have valid currencies
        dest_countries = set()
        for country in COUNTRY_CURRENCIES.keys():
            dest_countries.add(country)
        return sorted(list(dest_countries))


def parse_delivery_time(time_string: str) -> Optional[int]:
    """
    Attempt to parse a human-readable time string into minutes.
    Common patterns:
      - "1 hour"
      - "1-2 business days"
      - "Same day"
      - "Instant"

    Args:
        time_string: Human-readable time string

    Returns:
        Integer minutes or None if unknown
    """
    if not time_string:
        return None

    text = time_string.lower()
    # Examples:
    # "within 30 minutes"
    # "1-2 business days"
    # "today", "tomorrow", "same day"

    # If "minutes" in text, parse integer
    if "minutes" in text:
        try:
            num_str = text.split(" minutes")[0].strip()
            num_val = int(num_str.split()[-1])  # last integer
            return num_val
        except (ValueError, IndexError):
            pass

    if "hour" in text:
        try:
            num_str = text.split(" hour")[0].strip()
            num_val = int(num_str.split()[-1])  # last integer
            return num_val * 60
        except (ValueError, IndexError):
            pass

    if "day" in text:
        # Might be "1-2 days"
        if "-" in text:
            # e.g. "1-2" days
            range_part = text.split("day")[0].strip()
            if range_part:
                dash_idx = range_part.find("-")
                if dash_idx != -1:
                    try:
                        min_days = int(range_part[:dash_idx])
                        max_days = int(range_part[dash_idx + 1 :])
                        avg_days = (min_days + max_days) / 2
                        return int(avg_days * 1440)
                    except ValueError:
                        pass
        else:
            # single day
            if text.startswith("1 day"):
                return 24 * 60
            # guess 2 days
            return 48 * 60

    if "same day" in text or "today" in text:
        return 8 * 60  # guess 8 hours

    if "instant" in text or "immediate" in text:
        return 5  # a few minutes

    # fallback
    return DEFAULT_VALUES["delivery_time_minutes"]


def guess_country_for_currency(currency_code: str) -> str:
    """
    Guess a typical from_country for a given currency code.
    E.g., "USD" -> "US", "EUR" -> "DE".

    Args:
        currency_code: ISO currency code

    Returns:
        ISO country code
    """
    if not currency_code:
        return "GB"  # Default fallback

    currency_code = currency_code.upper()

    # Common direct mappings
    direct_mappings = {
        "EUR": "DE",
        "GBP": "GB",
        "USD": "US",
        "CAD": "CA",
        "AUD": "AU",
        "SGD": "SG",
        "HKD": "HK",
        "JPY": "JP",
        "NZD": "NZ",
        "CHF": "CH",
        "SEK": "SE",
        "NOK": "NO",
        "DKK": "DK",
        "PLN": "PL",
        "CZK": "CZ",
        "HUF": "HU",
        "RON": "RO",
        "BGN": "BG",
        "TRY": "TR",
        "UAH": "UA",
        "RUB": "RU",
        "INR": "IN",
        "PHP": "PH",
        "MYR": "MY",
        "THB": "TH",
        "IDR": "ID",
        "ZAR": "ZA",
        "MXN": "MX",
        "BRL": "BR",
        "AED": "AE",
        "SAR": "SA",
        "ILS": "IL",
        "KRW": "KR",
        "CNY": "CN",
    }

    if currency_code in direct_mappings:
        return direct_mappings[currency_code]

    # Create a reverse mapping of currency to country
    reverse_map = {}
    for country, currencies in COUNTRY_CURRENCIES.items():
        if isinstance(currencies, list):
            for currency in currencies:
                if currency not in reverse_map:
                    reverse_map[currency] = country
        elif currencies not in reverse_map:
            reverse_map[currencies] = country

    if currency_code in reverse_map:
        return reverse_map[currency_code]

    # Fallback to GB
    return "GB"
