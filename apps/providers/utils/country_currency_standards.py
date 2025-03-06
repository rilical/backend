"""
Standardized country and currency code mappings for the aggregator.
Uses ISO-3166-1 alpha-2 and alpha-3 for countries and ISO-4217 for currencies.
"""
from typing import Dict, Optional, Tuple

# ISO-3166-1 alpha-2 country codes to full names
ISO_COUNTRY_NAMES = {
    'AE': 'UNITED ARAB EMIRATES',
    'EG': 'EGYPT',
    'GT': 'GUATEMALA',
    'IN': 'INDIA',
    'PK': 'PAKISTAN',
    'PH': 'PHILIPPINES',
    'LK': 'SRI LANKA',
    'BD': 'BANGLADESH',
    'NP': 'NEPAL',
    'US': 'UNITED STATES OF AMERICA',
    'GB': 'UNITED KINGDOM',
    'CA': 'CANADA',
    'AU': 'AUSTRALIA',
    'NZ': 'NEW ZEALAND',
    'SG': 'SINGAPORE',
    'MY': 'MALAYSIA',
    'ID': 'INDONESIA',
    'TH': 'THAILAND',
    'VN': 'VIETNAM',
    'JP': 'JAPAN',
    'KR': 'SOUTH KOREA',
    'SA': 'SAUDI ARABIA',
    'QA': 'QATAR',
    'KW': 'KUWAIT',
    'BH': 'BAHRAIN',
    'OM': 'OMAN',
    'JO': 'JORDAN',
    'LB': 'LEBANON',
    'IQ': 'IRAQ',
    'YE': 'YEMEN',
    'MA': 'MOROCCO',
    'TN': 'TUNISIA',
    'DZ': 'ALGERIA',
    'LY': 'LIBYA',
    'SD': 'SUDAN',
    'KE': 'KENYA',
    'UG': 'UGANDA',
    'TZ': 'TANZANIA',
    'NG': 'NIGERIA',
    'GH': 'GHANA',
    'ZA': 'SOUTH AFRICA',
    'MX': 'MEXICO',
    'BR': 'BRAZIL',
    'AR': 'ARGENTINA',
    'CL': 'CHILE',
    'CO': 'COLOMBIA',
    'PE': 'PERU',
    'VE': 'VENEZUELA',
}

# ISO-3166-1 alpha-3 to alpha-2 mapping
ISO_ALPHA3_TO_ALPHA2 = {
    'USA': 'US',
    'GBR': 'GB',
    'GTM': 'GT',
    'CAN': 'CA',
    'AUS': 'AU',
    'NZL': 'NZ',
    'SGP': 'SG',
    'MYS': 'MY',
    'IDN': 'ID',
    'THA': 'TH',
    'VNM': 'VN',
    'JPN': 'JP',
    'KOR': 'KR',
    'SAU': 'SA',
    'QAT': 'QA',
    'KWT': 'KW',
    'BHR': 'BH',
    'OMN': 'OM',
    'JOR': 'JO',
    'LBN': 'LB',
    'IRQ': 'IQ',
    'YEM': 'YE',
    'MAR': 'MA',
    'TUN': 'TN',
    'DZA': 'DZ',
    'LBY': 'LY',
    'SDN': 'SD',
    'KEN': 'KE',
    'UGA': 'UG',
    'TZA': 'TZ',
    'NGA': 'NG',
    'GHA': 'GH',
    'ZAF': 'ZA',
    'MEX': 'MX',
    'BRA': 'BR',
    'ARG': 'AR',
    'CHL': 'CL',
    'COL': 'CO',
    'PER': 'PE',
    'VEN': 'VE',
    'IND': 'IN',
    'PAK': 'PK',
    'BGD': 'BD',
    'LKA': 'LK',
    'NPL': 'NP',
    'PHL': 'PH',
    'EGY': 'EG',
    'ARE': 'AE',
}

# Common currency codes and their numeric mappings
CURRENCY_CODES = {
    'AED': '784',  # UAE Dirham
    'USD': '840',  # US Dollar
    'EUR': '978',  # Euro
    'GBP': '826',  # British Pound
    'GTQ': '320',  # Guatemalan Quetzal
    'INR': '356',  # Indian Rupee
    'PKR': '586',  # Pakistani Rupee
    'BDT': '050',  # Bangladeshi Taka
    'LKR': '144',  # Sri Lankan Rupee
    'NPR': '524',  # Nepalese Rupee
    'PHP': '608',  # Philippine Peso
    'EGP': '818',  # Egyptian Pound
    'SAR': '682',  # Saudi Riyal
    'QAR': '634',  # Qatari Riyal
    'OMR': '512',  # Omani Rial
    'BHD': '048',  # Bahraini Dinar
    'KWD': '414',  # Kuwaiti Dinar
    'JOD': '400',  # Jordanian Dinar
    'LBP': '422',  # Lebanese Pound
    'IQD': '368',  # Iraqi Dinar
    'YER': '886',  # Yemeni Rial
    'MAD': '504',  # Moroccan Dirham
    'TND': '788',  # Tunisian Dinar
    'DZD': '012',  # Algerian Dinar
    'MXN': '484',  # Mexican Peso
    'BRL': '986',  # Brazilian Real
    'ARS': '032',  # Argentine Peso
    'CLP': '152',  # Chilean Peso
    'COP': '170',  # Colombian Peso
    'PEN': '604',  # Peruvian Sol
    'VES': '928',  # Venezuelan Bolívar
    
    # East African currencies
    'KES': '404',  # Kenyan Shilling
    'ETB': '230',  # Ethiopian Birr
    'SOS': '706',  # Somali Shilling
    'TZS': '834',  # Tanzanian Shilling
    'UGX': '800',  # Ugandan Shilling
    'RWF': '646',  # Rwandan Franc
    'DJF': '262',  # Djibouti Franc
    'SDG': '938',  # Sudanese Pound
}

def normalize_country_code(country_code: str) -> Optional[str]:
    """
    Convert country code to ISO-3166-1 alpha-2 format.
    Handles both alpha-2 and alpha-3 codes.
    
    Args:
        country_code: Country code in either alpha-2 or alpha-3 format
        
    Returns:
        Alpha-2 country code if valid, None otherwise
    """
    code = country_code.upper()
    if len(code) == 2:
        return code if code in ISO_COUNTRY_NAMES else None
    elif len(code) == 3:
        return ISO_ALPHA3_TO_ALPHA2.get(code)
    return None

def validate_corridor(
    source_country: str,
    source_currency: str,
    dest_country: str,
    dest_currency: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate a corridor using ISO standards.
    
    Args:
        source_country: Source country code (ISO-3166-1 alpha-2 or alpha-3)
        source_currency: Source currency code (ISO-4217)
        dest_country: Destination country code (ISO-3166-1 alpha-2 or alpha-3)
        dest_currency: Destination currency code (ISO-4217)
        
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    source_country = normalize_country_code(source_country)
    dest_country = normalize_country_code(dest_country)
    source_currency = source_currency.upper()
    dest_currency = dest_currency.upper()
    
    if not source_country:
        return False, f"Invalid source country code: {source_country}"
        
    if not dest_country:
        return False, f"Invalid destination country code: {dest_country}"
        
    if source_currency not in CURRENCY_CODES:
        return False, f"Invalid source currency code: {source_currency}"
        
    if dest_currency not in CURRENCY_CODES:
        return False, f"Invalid destination currency code: {dest_currency}"
        
    return True, None

def get_country_name(iso_code: str) -> Optional[str]:
    """Convert ISO-3166-1 alpha-2 or alpha-3 country code to full name."""
    code = normalize_country_code(iso_code)
    return ISO_COUNTRY_NAMES.get(code) if code else None

def get_currency_numeric(iso_code: str) -> Optional[str]:
    """Convert ISO-4217 currency code to numeric code."""
    return CURRENCY_CODES.get(iso_code.upper()) 