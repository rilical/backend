"""
Mukuru country and currency mappings

This file contains mappings between country codes and currencies for Mukuru integration.
"""

from typing import Dict, Any, Optional

# Country to currency code mappings
# This is a fallback in case the API call to get_recipient_countries fails
COUNTRY_TO_CURRENCY = {
    'ZA': 'ZAR',  # South Africa
    'ZW': 'USD',  # Zimbabwe
    'GH': 'GHS',  # Ghana
    'NG': 'NGN',  # Nigeria
    'ML': 'XOF',  # Mali
    'MZ': 'MZN',  # Mozambique
    'KE': 'KES',  # Kenya
    'MW': 'MWK',  # Malawi
    'BW': 'BWP',  # Botswana
    'SZ': 'SZL',  # Eswatini
    'LS': 'LSL',  # Lesotho
    'RW': 'RWF',  # Rwanda
    'UG': 'UGX',  # Uganda
    'GB': 'GBP',  # United Kingdom
    'ZM': 'ZMW',  # Zambia
    'AO': 'AOA',  # Angola
    'ET': 'ETB',  # Ethiopia
    'TZ': 'TZS',  # Tanzania
    'CD': 'CDF',  # DR Congo
    'SO': 'SOS',  # Somalia
}

# Currency ID mappings for specific corridors
# Format: (from_country, to_country, [delivery_method]) -> currency_id
CURRENCY_ID_MAPPING = {
    # South Africa to Zimbabwe
    ('ZA', 'ZW'): 18,  # Default USD Cash
    ('ZA', 'ZW', 'wallet'): 1693,  # USD Mukuru Wallet (from HTML: data-iso="USD" data-is-send="false")
    ('ZA', 'ZW', 'cash'): 18,  # Cash USD (from HTML: data-iso="USD" data-is-send="true")
    ('ZA', 'ZW', 'bank'): 1691,  # Bank deposit USD
    ('ZA', 'ZW', 'CASH_ZAR'): 31,  # Cash ZAR (from HTML: data-iso="ZAR" data-is-send="true")
    
    # Other corridors
    ('ZA', 'MZ'): 37,  # Mozambique MZN
    ('ZA', 'MW'): 68,  # Malawi MWK
    ('ZA', 'BW'): 78,  # Botswana BWP
    ('ZA', 'LS'): 35,  # Lesotho LSL
    ('ZA', 'SZ'): 41,  # Eswatini SZL
    ('ZA', 'ZM'): 112,  # Zambia ZMW
    ('ZA', 'GH'): 20,  # Ghana GHS
    ('ZA', 'NG'): 21,  # Nigeria NGN
}

# Supported corridors based on Mukuru's typical operations
SUPPORTED_CORRIDORS = [
    ('ZA', 'ZW'),  # South Africa -> Zimbabwe
    ('ZA', 'MZ'),  # South Africa -> Mozambique
    ('ZA', 'MW'),  # South Africa -> Malawi
    ('ZA', 'BW'),  # South Africa -> Botswana
    ('ZA', 'LS'),  # South Africa -> Lesotho
    ('ZA', 'SZ'),  # South Africa -> Eswatini
    ('ZA', 'ZM'),  # South Africa -> Zambia
    ('ZA', 'GH'),  # South Africa -> Ghana
    ('ZA', 'NG'),  # South Africa -> Nigeria
    ('GB', 'ZW'),  # United Kingdom -> Zimbabwe
    ('GB', 'ZA'),  # United Kingdom -> South Africa
    ('ZA', 'KE'),  # South Africa -> Kenya
    ('ZA', 'RW'),  # South Africa -> Rwanda
    ('ZA', 'UG'),  # South Africa -> Uganda
    ('ZA', 'AO'),  # South Africa -> Angola
    ('ZA', 'ET'),  # South Africa -> Ethiopia
    ('ZA', 'TZ'),  # South Africa -> Tanzania
    ('ZA', 'CD'),  # South Africa -> DR Congo
    ('ZA', 'SO'),  # South Africa -> Somalia
]

# Payment methods
PAYMENT_METHODS = {
    'bank': 'Bank Transfer',
    'card': 'Card Payment',
    'cash': 'Cash Deposit',
}

# Delivery methods
DELIVERY_METHODS = {
    'cash': 'Cash Pickup',
    'bank': 'Bank Deposit',
    'wallet': 'Mukuru Wallet',
    'mobile_money': 'Mobile Money',
}

def update_country_currency_mapping(api_response: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Update the COUNTRY_TO_CURRENCY mapping with data from the API response.
    
    Args:
        api_response: The response data from the API's get_recipient_countries endpoint
        
    Returns:
        The updated mapping dictionary
    """
    if not api_response or not isinstance(api_response, dict):
        return COUNTRY_TO_CURRENCY.copy()
        
    updated_mapping = COUNTRY_TO_CURRENCY.copy()
    
    # If we have API data, update our mapping
    for country_code, info in api_response.items():
        if isinstance(info, dict) and 'currency_market_iso' in info:
            currency_code = info['currency_market_iso']
            if currency_code:
                updated_mapping[country_code] = currency_code
    
    return updated_mapping 

def extract_currency_ids_from_html(html_content: str) -> Dict:
    """
    Extract currency IDs from Mukuru HTML form data.
    
    The function parses the HTML content to find currency ID options like:
    <option value="18" data-iso="USD" data-is-send="true" data-show-fee="1">Cash USD</option>
    
    Args:
        html_content: The HTML content of the form
        
    Returns:
        Dictionary mapping currency information to IDs
    """
    import re
    
    currency_ids = {}
    
    # Look for option elements in the currency_id select
    pattern = r'<option\s+value="(\d+)"\s+data-iso="([^"]+)"\s+data-is-send="([^"]+)"\s+data-show-fee="[^"]+">(.*?)</option>'
    matches = re.findall(pattern, html_content)
    
    for match in matches:
        currency_id, iso_code, is_send, label = match
        
        # Extract the delivery method from the label
        delivery_method = label.strip().lower()
        if "cash" in delivery_method:
            method_type = "cash"
        elif "wallet" in delivery_method:
            method_type = "wallet"
        elif "bank" in delivery_method:
            method_type = "bank"
        else:
            method_type = "other"
            
        # Create a unique key for this currency option
        key = (iso_code, method_type, is_send == "true")
        currency_ids[key] = int(currency_id)
    
    return currency_ids 