"""
Standardized country and currency mappings for the Placid provider.

This module provides mappings between Placid's internal corridor codes
and standardized ISO country and currency codes used by the aggregator.
"""
from typing import Dict, Optional, List
from apps.providers.utils.country_currency_standards import ISO_COUNTRY_NAMES, ISO_ALPHA3_TO_ALPHA2

# Mapping from Placid's corridor codes to ISO standard codes
CORRIDOR_TO_ISO = {
    # Asia
    'PAK': {'country': 'PK', 'currency': 'PKR', 'name': 'Pakistan'},
    'IND': {'country': 'IN', 'currency': 'INR', 'name': 'India'},
    'BGD': {'country': 'BD', 'currency': 'BDT', 'name': 'Bangladesh'},
    'BAN': {'country': 'BD', 'currency': 'BDT', 'name': 'Bangladesh'},
    'PHL': {'country': 'PH', 'currency': 'PHP', 'name': 'Philippines'},
    'PHX': {'country': 'PH', 'currency': 'PHP', 'name': 'Philippines'},
    'NPL': {'country': 'NP', 'currency': 'NPR', 'name': 'Nepal'},
    'NEP': {'country': 'NP', 'currency': 'NPR', 'name': 'Nepal'},
    'LKA': {'country': 'LK', 'currency': 'LKR', 'name': 'Sri Lanka'},
    'SLK': {'country': 'LK', 'currency': 'LKR', 'name': 'Sri Lanka'},
    'IDN': {'country': 'ID', 'currency': 'IDR', 'name': 'Indonesia'},
    'INDON': {'country': 'ID', 'currency': 'IDR', 'name': 'Indonesia'},
    'VNM': {'country': 'VN', 'currency': 'VND', 'name': 'Vietnam'},
    'CHN': {'country': 'CN', 'currency': 'CNY', 'name': 'China'},
    'THA': {'country': 'TH', 'currency': 'THB', 'name': 'Thailand'},
    'MYX': {'country': 'MY', 'currency': 'MYR', 'name': 'Malaysia'},
    'JPN': {'country': 'JP', 'currency': 'JPY', 'name': 'Japan'},
    'KOR': {'country': 'KR', 'currency': 'KRW', 'name': 'South Korea'},
    'SGP': {'country': 'SG', 'currency': 'SGD', 'name': 'Singapore'},
    
    # Europe
    'AUT': {'country': 'AT', 'currency': 'EUR', 'name': 'Austria'},
    'BEL': {'country': 'BE', 'currency': 'EUR', 'name': 'Belgium'},
    'DEU': {'country': 'DE', 'currency': 'EUR', 'name': 'Germany'},
    'ESP': {'country': 'ES', 'currency': 'EUR', 'name': 'Spain'},
    'EST': {'country': 'EE', 'currency': 'EUR', 'name': 'Estonia'},
    'FIND': {'country': 'FI', 'currency': 'EUR', 'name': 'Finland'},
    'FRA': {'country': 'FR', 'currency': 'EUR', 'name': 'France'},
    'GRC': {'country': 'GR', 'currency': 'EUR', 'name': 'Greece'},
    'IRL': {'country': 'IE', 'currency': 'EUR', 'name': 'Ireland'},
    'ITAL': {'country': 'IT', 'currency': 'EUR', 'name': 'Italy'},
    'LTU': {'country': 'LT', 'currency': 'EUR', 'name': 'Lithuania'},
    'LUX': {'country': 'LU', 'currency': 'EUR', 'name': 'Luxembourg'},
    'LVA': {'country': 'LV', 'currency': 'EUR', 'name': 'Latvia'},
    'MLT': {'country': 'MT', 'currency': 'EUR', 'name': 'Malta'},
    'NLD': {'country': 'NL', 'currency': 'EUR', 'name': 'Netherlands'},
    'PRT': {'country': 'PT', 'currency': 'EUR', 'name': 'Portugal'},
    'SVK': {'country': 'SK', 'currency': 'EUR', 'name': 'Slovakia'},
    'SVN': {'country': 'SI', 'currency': 'EUR', 'name': 'Slovenia'},
    'HRV': {'country': 'HR', 'currency': 'EUR', 'name': 'Croatia'},
    'CYP': {'country': 'CY', 'currency': 'EUR', 'name': 'Cyprus'},
    'UK': {'country': 'GB', 'currency': 'GBP', 'name': 'United Kingdom'},
    'CHE': {'country': 'CH', 'currency': 'CHF', 'name': 'Switzerland'},
    'NOR': {'country': 'NO', 'currency': 'NOK', 'name': 'Norway'},
    'SWE': {'country': 'SE', 'currency': 'SEK', 'name': 'Sweden'},
    'DNK': {'country': 'DK', 'currency': 'DKK', 'name': 'Denmark'},
    'POL': {'country': 'PL', 'currency': 'PLN', 'name': 'Poland'},
    
    # Africa
    'CIV': {'country': 'CI', 'currency': 'XOF', 'name': 'Côte d\'Ivoire'},
    'CMR': {'country': 'CM', 'currency': 'XAF', 'name': 'Cameroon'},
    'GHA': {'country': 'GH', 'currency': 'GHS', 'name': 'Ghana'},
    'KEN': {'country': 'KE', 'currency': 'KES', 'name': 'Kenya'},
    'SEN': {'country': 'SN', 'currency': 'XOF', 'name': 'Senegal'},
    'TZA': {'country': 'TZ', 'currency': 'TZS', 'name': 'Tanzania'},
    'UGA': {'country': 'UG', 'currency': 'UGX', 'name': 'Uganda'},
    'NGA': {'country': 'NG', 'currency': 'NGN', 'name': 'Nigeria'},
    'ZAF': {'country': 'ZA', 'currency': 'ZAR', 'name': 'South Africa'},
    'MAR': {'country': 'MA', 'currency': 'MAD', 'name': 'Morocco'},
    'EGY': {'country': 'EG', 'currency': 'EGP', 'name': 'Egypt'},
    
    # North America
    'USA': {'country': 'US', 'currency': 'USD', 'name': 'United States'},
    'CAN': {'country': 'CA', 'currency': 'CAD', 'name': 'Canada'},
    'MEX': {'country': 'MX', 'currency': 'MXN', 'name': 'Mexico'},
    
    # South America
    'BRA': {'country': 'BR', 'currency': 'BRL', 'name': 'Brazil'},
    'ARG': {'country': 'AR', 'currency': 'ARS', 'name': 'Argentina'},
    'COL': {'country': 'CO', 'currency': 'COP', 'name': 'Colombia'},
    'CHL': {'country': 'CL', 'currency': 'CLP', 'name': 'Chile'},
    'PER': {'country': 'PE', 'currency': 'PEN', 'name': 'Peru'},
    
    # Oceania
    'AUS': {'country': 'AU', 'currency': 'AUD', 'name': 'Australia'},
    'NZL': {'country': 'NZ', 'currency': 'NZD', 'name': 'New Zealand'},
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
    # Asia
    'PKR': 'PAK',
    'INR': 'IND',
    'BDT': 'BAN',
    'PHP': 'PHX',
    'NPR': 'NEP',
    'LKR': 'SLK',
    'IDR': 'INDON',
    'VND': 'VNM',
    'CNY': 'CHN',
    'THB': 'THA',
    'MYR': 'MYX',
    'JPY': 'JPN',
    'KRW': 'KOR',
    'SGD': 'SGP',
    
    # Europe
    'EUR': 'DEU',  # Using Germany as primary for EUR
    'GBP': 'UK',
    'CHF': 'CHE',
    'NOK': 'NOR',
    'SEK': 'SWE',
    'DKK': 'DNK',
    'PLN': 'POL',
    
    # Africa
    'XOF': 'SEN',  # Using Senegal as primary for XOF
    'XAF': 'CMR',
    'GHS': 'GHA',
    'KES': 'KEN',
    'TZS': 'TZA',
    'UGX': 'UGA',
    'NGN': 'NGA',
    'ZAR': 'ZAF',
    'MAD': 'MAR',
    'EGP': 'EGY',
    
    # North America
    'USD': 'USA',
    'CAD': 'CAN',
    'MXN': 'MEX',
    
    # South America
    'BRL': 'BRA',
    'ARS': 'ARG',
    'COP': 'COL',
    'CLP': 'CHL',
    'PEN': 'PER',
    
    # Oceania
    'AUD': 'AUS',
    'NZD': 'NZL',
}

# Payment methods supported by Placid
PAYMENT_METHODS = {
    'bank': 'Bank Transfer',
    'card': 'Card Payment',
    'wallet': 'Digital Wallet',
    'cash': 'Cash Deposit',
    'CC': 'Credit/Debit Card',
    'BA': 'Bank Account',
    'PM': 'Payment Method',
}

# Delivery methods supported by Placid
DELIVERY_METHODS = {
    'bank': 'Bank Deposit',
    'cash': 'Cash Pickup',
    'wallet': 'Digital Wallet',
    'door': 'Door Delivery',
}

# Enhanced utility functions that leverage internal mappings
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