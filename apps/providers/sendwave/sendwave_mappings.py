"""
Sendwave-specific mappings for country codes, currency codes, delivery methods,
segment codes, and other configuration specific to the Sendwave API integration.

This module centralizes all the constants and mappings needed for the Sendwave
provider, making it easier to maintain and update.
"""

from typing import Any, Dict, List

# =============================================================================
# SUPPORTED CORRIDORS
# =============================================================================
# List of supported corridors in (source_currency, destination_country) format
SUPPORTED_CORRIDORS = [
    # USD corridors
    ("USD", "PH"),  # US → Philippines
    ("USD", "KE"),  # US → Kenya
    ("USD", "GH"),  # US → Ghana
    ("USD", "UG"),  # US → Uganda
    # EUR corridors
    ("EUR", "PH"),  # EU → Philippines
    ("EUR", "KE"),  # EU → Kenya
    ("EUR", "GH"),  # EU → Ghana
    ("EUR", "UG"),  # EU → Uganda
    # GBP corridors (commonly supported)
    ("GBP", "PH"),  # UK → Philippines
    ("GBP", "KE"),  # UK → Kenya
    ("GBP", "GH"),  # UK → Ghana
    ("GBP", "UG"),  # UK → Uganda
]

# =============================================================================
# COUNTRY TO CURRENCY MAPPINGS
# =============================================================================
# Mapping of country codes to their default currencies
COUNTRY_TO_CURRENCY = {
    "PH": "PHP",  # Philippines
    "KE": "KES",  # Kenya
    "UG": "UGX",  # Uganda
    "GH": "GHS",  # Ghana
}

# =============================================================================
# CURRENCY TO SENDER COUNTRY MAPPINGS
# =============================================================================
# Default sending country for each source currency
CURRENCY_TO_COUNTRY = {
    "USD": "us",
    "EUR": "be",  # Belgium as default for EUR (can be any EU country)
    "GBP": "gb",
    "CAD": "ca",
    "AUD": "au",
}

# =============================================================================
# DELIVERY METHODS AND SEGMENTS
# =============================================================================
# Mapping of country codes to available delivery methods
COUNTRY_DELIVERY_METHODS = {
    "PH": [
        {
            "method_code": "ph_gcash",
            "method_name": "GCash",
            "standardized_name": "mobile_wallet",
            "icon_url": "https://images.ctfassets.net/pqe6664kagrv/23fddzKWOMF477cElhfpt/245ab8a588c9875ed356bd76bb98372f/Union.png",
            "is_default": True,
        },
        {
            "method_code": "ph_bank",
            "method_name": "Bank Account",
            "standardized_name": "bank_deposit",
            "icon_url": "https://images.ctfassets.net/pqe6664kagrv/6B2u8iUQRRVBA9FDfwSSQF/55d7fcebe82af0a84e5600b38d13e90e/Layer_1_78.png",
            "is_default": False,
        },
        {
            "method_code": "ph_cash",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
            "icon_url": "https://images.ctfassets.net/pqe6664kagrv/4LjdwAFIlCezdIheJOF8gP/bacbdc559e6958d48fb8e2cbeb47db3a/Cash-Pickup-icon.png",
            "is_default": False,
        },
    ],
    "KE": [
        {
            "method_code": "ke_mpesa",
            "method_name": "M-Pesa",
            "standardized_name": "mobile_wallet",
            "is_default": True,
        },
        {
            "method_code": "ke_bank",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": False,
        },
    ],
    "GH": [
        {
            "method_code": "gh_momo",
            "method_name": "Mobile Money",
            "standardized_name": "mobile_wallet",
            "is_default": True,
        },
        {
            "method_code": "gh_bank",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": False,
        },
    ],
    "UG": [
        {
            "method_code": "ug_mtn",
            "method_name": "MTN Mobile Money",
            "standardized_name": "mobile_wallet",
            "is_default": True,
        },
        {
            "method_code": "ug_bank",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": False,
        },
    ],
}

# =============================================================================
# API CONFIGURATION
# =============================================================================
# Base URL and endpoints
API_CONFIG = {
    "base_url": "https://app.sendwave.com",
    "pricing_endpoint": "/v2/pricing-public",
    "timeout": 15,  # seconds
    "default_user_agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
    ),
    "origin": "https://www.sendwave.com",
    "referer": "https://www.sendwave.com/",
}

# =============================================================================
# DEFAULT VALUES
# =============================================================================
# Default values for various fields
DEFAULT_VALUES = {
    "payment_method": "debitCard",
    "delivery_method": "mobileWallet",
    "delivery_time_minutes": 60,  # 1 hour
    "fee": 0.0,  # Sendwave typically has zero fees
}

# =============================================================================
# EXCHANGE RATE INFORMATION
# =============================================================================
# Sample exchange rates (These are for reference only and should be fetched from the API)
SAMPLE_EXCHANGE_RATES = {
    "USD-PHP": {
        "base_rate": 55.02,
        "effective_rate": 57.05574,  # with discounts applied
        "discounts": [
            {
                "code": "intro-rate-us-ph",
                "description": "Intro Rate Discount",
                "value": 9.50,
            },
            {"code": "slp-gb-ph-gcash", "description": "Exchange Rate", "value": 9.01},
        ],
    },
    "EUR-PHP": {
        "base_rate": 59.64,
        "effective_rate": 61.51866,  # with discounts applied
        "discounts": [
            {"code": "slp-gb-ph-gcash", "description": "Exchange Rate", "value": 9.00},
            {
                "code": "intro-rate-eu1-ph",
                "description": "Intro Rate Discount",
                "value": 6.75,
            },
        ],
    },
    "GBP-PHP": {
        "base_rate": 71.51,
        "effective_rate": 73.834075,  # with discounts applied
        "discounts": [
            {
                "code": "intro-rate-gb-ph",
                "description": "Intro Rate Discount",
                "value": 7.25,
            },
            {"code": "slp-gb-ph-gcash", "description": "Exchange Rate", "value": 9.00},
        ],
    },
}


def get_segment_name_for_delivery_method(country_code: str, delivery_method: str) -> str:
    """
    Get the appropriate segment name for a country and delivery method.

    Args:
        country_code: Two-letter country code (e.g., "PH")
        delivery_method: Standardized delivery method (e.g., "mobile_wallet")

    Returns:
        Segment name to use in the API call (e.g., "ph_gcash")
    """
    methods = COUNTRY_DELIVERY_METHODS.get(country_code.upper(), [])

    # Try to find a matching method
    for method in methods:
        if method["standardized_name"] == delivery_method:
            return method["method_code"]

    # If no match found, return the default method for that country
    for method in methods:
        if method.get("is_default", False):
            return method["method_code"]

    # If no default method found, return the first method if available
    if methods:
        return methods[0]["method_code"]

    # If no methods at all, build a sensible default
    if country_code.upper() == "PH":
        return "ph_gcash"
    elif country_code.upper() == "KE":
        return "ke_mpesa"
    elif country_code.upper() == "GH":
        return "gh_momo"
    elif country_code.upper() == "UG":
        return "ug_mtn"

    # Fallback to empty string if nothing else works
    return ""


def get_send_country_for_currency(currency_code: str, default_country: str = None) -> str:
    """
    Get the appropriate sender country ISO code based on source currency.

    Args:
        currency_code: Source currency code (e.g., "USD", "EUR")
        default_country: Optional source country code to override defaults

    Returns:
        Lower case ISO2 country code
    """
    if default_country:
        return default_country.lower()

    return CURRENCY_TO_COUNTRY.get(currency_code.upper(), "us")


def is_corridor_supported(send_currency: str, receive_country: str) -> bool:
    """
    Check if a corridor is in the SUPPORTED_CORRIDORS list.

    Args:
        send_currency: Source currency code (e.g., "USD")
        receive_country: Destination country code (e.g., "PH")

    Returns:
        True if the corridor is supported
    """
    return (send_currency.upper(), receive_country.upper()) in SUPPORTED_CORRIDORS


def get_delivery_methods_for_country(country_code: str) -> List[Dict[str, Any]]:
    """
    Get available delivery methods for a specific country.

    Args:
        country_code: Two-letter country code (e.g., "PH")

    Returns:
        List of delivery method dictionaries
    """
    return COUNTRY_DELIVERY_METHODS.get(country_code.upper(), [])
