"""
SingX-specific mappings for country codes, currency codes, delivery methods,
and other configuration needed for the SingX API integration.

This module centralizes all constants and mappings needed for the SingX
provider, making maintenance and updates easier.
"""

from typing import Any, Dict, List

# =============================================================================
# COUNTRY MAPPINGS
# =============================================================================
# Mapping from 2-letter country code to SingX internal UUID
COUNTRY_CODES = {
    "SG": "59C3BBD2-5D26-4A47-8FC1-2EFA628049CE",  # Singapore
    "IN": "A5001AED-DDA1-4296-8312-223D383F96F5",  # India
    "PH": "B6112BFE-E482-4507-9423-334D385F96F6",  # Philippines
    "ID": "C7223CFF-F593-5618-0534-445E496G07G7",  # Indonesia
    "MY": "D8334DGG-G604-6729-1645-556F507H18H8",  # Malaysia
    "HK": "E9445EHH-H715-7830-2756-667G618I29I9",  # Hong Kong
    "AU": "F0556FII-I826-8941-3867-778H729J30J0",  # Australia
}

# =============================================================================
# SUPPORTED CORRIDORS
# =============================================================================
# Supported currency corridors in (source_country, source_currency, destination_country, destination_currency) format
SUPPORTED_CORRIDORS = [
    # Singapore outbound
    ("SG", "SGD", "IN", "INR"),  # Singapore to India
    ("SG", "SGD", "PH", "PHP"),  # Singapore to Philippines
    ("SG", "SGD", "ID", "IDR"),  # Singapore to Indonesia
    ("SG", "SGD", "MY", "MYR"),  # Singapore to Malaysia
    ("SG", "SGD", "HK", "HKD"),  # Singapore to Hong Kong
    ("SG", "SGD", "AU", "AUD"),  # Singapore to Australia
    # Australia outbound
    ("AU", "AUD", "SG", "SGD"),  # Australia to Singapore
    ("AU", "AUD", "IN", "INR"),  # Australia to India
    # Hong Kong outbound
    ("HK", "HKD", "SG", "SGD"),  # Hong Kong to Singapore
    ("HK", "HKD", "IN", "INR"),  # Hong Kong to India
]

# =============================================================================
# DELIVERY METHODS
# =============================================================================
# Mapping of countries to available delivery methods
COUNTRY_DELIVERY_METHODS = {
    "IN": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": True,
        },
        {
            "method_code": "wallet",
            "method_name": "Mobile Wallet",
            "standardized_name": "mobile_wallet",
            "is_default": False,
        },
    ],
    "PH": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": True,
        },
        {
            "method_code": "cash_pickup",
            "method_name": "Cash Pickup",
            "standardized_name": "cash_pickup",
            "is_default": False,
        },
        {
            "method_code": "wallet",
            "method_name": "Mobile Wallet",
            "standardized_name": "mobile_wallet",
            "is_default": False,
        },
    ],
    "ID": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": True,
        }
    ],
    "MY": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": True,
        }
    ],
    "HK": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": True,
        }
    ],
    "AU": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": True,
        }
    ],
    "SG": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_deposit",
            "is_default": True,
        }
    ],
}

# =============================================================================
# PAYMENT METHODS
# =============================================================================
# Mapping of countries to available payment methods
COUNTRY_PAYMENT_METHODS = {
    "SG": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_transfer",
            "is_default": True,
        }
    ],
    "AU": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_transfer",
            "is_default": True,
        }
    ],
    "HK": [
        {
            "method_code": "bank_transfer",
            "method_name": "Bank Transfer",
            "standardized_name": "bank_transfer",
            "is_default": True,
        }
    ],
}

# =============================================================================
# API CONFIGURATION
# =============================================================================
API_CONFIG = {
    "base_url": "https://api.singx.co",
    "api_version": "central/landing/fx",
    "timeout": 15,
    "headers": {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15"
        ),
        "Origin": "https://www.singx.co",
        "Referer": "https://www.singx.co/",
    },
}

# =============================================================================
# DEFAULT VALUES
# =============================================================================
DEFAULT_VALUES = {
    "payment_method": "bankTransfer",
    "delivery_method": "bankDeposit",
    "delivery_time_minutes": 1440,  # 24 hours in minutes
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def is_corridor_supported(
    source_country: str,
    source_currency: str,
    destination_country: str,
    destination_currency: str,
) -> bool:
    """
    Check if a specific corridor is supported.

    Args:
        source_country: Source country code (e.g., "SG")
        source_currency: Source currency code (e.g., "SGD")
        destination_country: Destination country code (e.g., "IN")
        destination_currency: Destination currency code (e.g., "INR")

    Returns:
        True if the corridor is supported
    """
    corridor = (
        source_country.upper(),
        source_currency.upper(),
        destination_country.upper(),
        destination_currency.upper(),
    )
    return corridor in SUPPORTED_CORRIDORS


def get_delivery_methods_for_country(country_code: str) -> List[Dict[str, Any]]:
    """
    Get available delivery methods for a specific country.

    Args:
        country_code: Two-letter country code (e.g., "IN")

    Returns:
        List of delivery method dictionaries
    """
    return COUNTRY_DELIVERY_METHODS.get(country_code.upper(), [])


def get_payment_methods_for_country(country_code: str) -> List[Dict[str, Any]]:
    """
    Get available payment methods for a specific country.

    Args:
        country_code: Two-letter country code (e.g., "SG")

    Returns:
        List of payment method dictionaries
    """
    return COUNTRY_PAYMENT_METHODS.get(country_code.upper(), [])


def get_country_uuid(country_code: str) -> str:
    """
    Get SingX's internal UUID for a country code.

    Args:
        country_code: Two-letter country code (e.g., "SG")

    Returns:
        SingX's internal UUID for the country or None if not found
    """
    return COUNTRY_CODES.get(country_code.upper())


def is_country_supported(country_code: str) -> bool:
    """
    Check if a country is supported by SingX.

    Args:
        country_code: Two-letter country code (e.g., "SG")

    Returns:
        True if the country is supported
    """
    return country_code.upper() in COUNTRY_CODES


def get_supported_countries() -> List[str]:
    """
    Get all supported country codes.

    Returns:
        List of supported country codes
    """
    return list(COUNTRY_CODES.keys())


def get_supported_source_countries() -> List[str]:
    """
    Get all supported source country codes.

    Returns:
        List of supported source country codes
    """
    return list(set(corridor[0] for corridor in SUPPORTED_CORRIDORS))


def get_supported_destination_countries(
    source_country: str = None, source_currency: str = None
) -> List[str]:
    """
    Get all supported destination country codes, optionally filtered by source country and currency.

    Args:
        source_country: Source country code (e.g., "SG")
        source_currency: Source currency code (e.g., "SGD")

    Returns:
        List of supported destination country codes
    """
    if source_country and source_currency:
        source_country = source_country.upper()
        source_currency = source_currency.upper()
        return list(
            set(
                corridor[2]
                for corridor in SUPPORTED_CORRIDORS
                if corridor[0] == source_country and corridor[1] == source_currency
            )
        )
    elif source_country:
        source_country = source_country.upper()
        return list(
            set(corridor[2] for corridor in SUPPORTED_CORRIDORS if corridor[0] == source_country)
        )
    else:
        return list(set(corridor[2] for corridor in SUPPORTED_CORRIDORS))


def get_default_currency_for_country(country_code: str) -> str:
    """
    Get the default currency for a country.

    Args:
        country_code: Two-letter country code (e.g., "SG")

    Returns:
        Three-letter currency code (e.g., "SGD")
    """
    country_to_currency = {
        "SG": "SGD",
        "IN": "INR",
        "PH": "PHP",
        "ID": "IDR",
        "MY": "MYR",
        "HK": "HKD",
        "AU": "AUD",
    }
    return country_to_currency.get(country_code.upper())
