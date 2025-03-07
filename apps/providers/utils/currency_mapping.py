"""
Currency and country code mappings for remittance providers.
"""

# ISO 4217 currency codes mapped to their common names
CURRENCY_NAMES = {
    'USD': 'US Dollar',
    'EUR': 'Euro',
    'GBP': 'British Pound',
    'CAD': 'Canadian Dollar',
    'AUD': 'Australian Dollar',
    'JPY': 'Japanese Yen',
    'INR': 'Indian Rupee',
    'CNY': 'Chinese Yuan',
    'MXN': 'Mexican Peso',
    'BRL': 'Brazilian Real',
}

# ISO 3166-1 alpha-2 country codes mapped to their common names
COUNTRY_NAMES = {
    'US': 'United States',
    'GB': 'United Kingdom',
    'CA': 'Canada',
    'AU': 'Australia',
    'JP': 'Japan',
    'IN': 'India',
    'CN': 'China',
    'MX': 'Mexico',
    'BR': 'Brazil',
    'DE': 'Germany',
}

# Common currency codes for each country
COUNTRY_CURRENCIES = {
    'US': ['USD'],
    'GB': ['GBP'],
    'CA': ['CAD'],
    'AU': ['AUD'],
    'JP': ['JPY'],
    'IN': ['INR'],
    'CN': ['CNY'],
    'MX': ['MXN'],
    'BR': ['BRL'],
    'DE': ['EUR'],
}

def get_currency_name(currency_code: str) -> str:
    """Get the common name for a currency code."""
    return CURRENCY_NAMES.get(currency_code.upper(), currency_code)

def get_country_name(country_code: str) -> str:
    """Get the common name for a country code."""
    return COUNTRY_NAMES.get(country_code.upper(), country_code)

def get_country_currencies(country_code: str) -> list:
    """Get the list of currencies commonly used in a country."""
    return COUNTRY_CURRENCIES.get(country_code.upper(), []) 