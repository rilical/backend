"""
Standardized country and currency mappings for the Placid provider.

This module provides mappings between Placid's internal corridor codes
and standardized ISO country and currency codes used by the aggregator.
"""
from typing import Dict, Optional, List

# Mapping from Placid's corridor codes to ISO standard codes
CORRIDOR_TO_ISO = {
    'PAK': {'country': 'PK', 'currency': 'PKR', 'name': 'Pakistan'},
    'IND': {'country': 'IN', 'currency': 'INR', 'name': 'India'},
    'BGD': {'country': 'BD', 'currency': 'BDT', 'name': 'Bangladesh'},
    'PHL': {'country': 'PH', 'currency': 'PHP', 'name': 'Philippines'},
    'NPL': {'country': 'NP', 'currency': 'NPR', 'name': 'Nepal'},
    'LKA': {'country': 'LK', 'currency': 'LKR', 'name': 'Sri Lanka'},
    'IDN': {'country': 'ID', 'currency': 'IDR', 'name': 'Indonesia'},
    'VNM': {'country': 'VN', 'currency': 'VND', 'name': 'Vietnam'},
}

# Source country codes supported by Placid (ISO-3166 alpha-2)
SUPPORTED_SOURCE_COUNTRIES = {
    'US': {'currency': 'USD', 'name': 'United States'},
    'GB': {'currency': 'GBP', 'name': 'United Kingdom'},
    'CA': {'currency': 'CAD', 'name': 'Canada'},
    'AU': {'currency': 'AUD', 'name': 'Australia'},
    # EU is not a country but Placid uses it for EUR
    'EU': {'currency': 'EUR', 'name': 'Eurozone'},
}

# Mapping from ISO currency code to Placid corridor code
CURRENCY_TO_CORRIDOR = {
    'PKR': 'PAK',
    'INR': 'IND',
    'BDT': 'BGD',
    'PHP': 'PHL',
    'NPR': 'NPL',
    'LKR': 'LKA',
    'IDR': 'IDN',
    'VND': 'VNM',
}

# Payment methods supported by Placid
PAYMENT_METHODS = {
    'bank': 'Bank Transfer',
    'card': 'Card Payment',
    'wallet': 'Digital Wallet',
    'cash': 'Cash Deposit',
}

# Delivery methods supported by Placid
DELIVERY_METHODS = {
    'bank': 'Bank Deposit',
    'cash': 'Cash Pickup',
    'wallet': 'Digital Wallet',
    'door': 'Door Delivery',
}

def get_corridor_from_currency(currency_code: str) -> Optional[str]:
    """Get Placid's corridor code for a given ISO currency code."""
    return CURRENCY_TO_CORRIDOR.get(currency_code.upper())

def get_iso_codes_from_corridor(corridor_code: str) -> Dict[str, str]:
    """Get ISO country and currency codes for a given corridor code."""
    return CORRIDOR_TO_ISO.get(corridor_code.upper(), {})

def get_source_country_currency(country_code: str) -> Optional[str]:
    """Get the currency for a supported source country."""
    country_info = SUPPORTED_SOURCE_COUNTRIES.get(country_code.upper())
    if country_info:
        return country_info.get('currency')
    return None

def get_supported_source_countries() -> List[str]:
    """Get the list of supported source countries in ISO format."""
    return list(SUPPORTED_SOURCE_COUNTRIES.keys())

def get_supported_destination_countries() -> List[str]:
    """Get the list of supported destination countries in ISO format."""
    return [item['country'] for item in CORRIDOR_TO_ISO.values()]

def get_supported_destination_currencies() -> List[str]:
    """Get the list of supported destination currencies in ISO format."""
    return list(CURRENCY_TO_CORRIDOR.keys())

def get_supported_source_currencies() -> List[str]:
    """Get the list of supported source currencies in ISO format."""
    return [item['currency'] for item in SUPPORTED_SOURCE_COUNTRIES.values()] 