"""
XE-specific currency and country mappings.

This module provides mappings specifically for XE Money Transfer integration.
It extends the default mappings from utils/country_currency_standards.py.
"""

from typing import Dict, List, Tuple, Optional

from ..utils.country_currency_standards import get_default_currency_for_country

# XE-specific country to currency mappings
# Comprehensive mapping based on XE's supported countries
XE_COUNTRY_TO_CURRENCY = {
    'AD': 'EUR',  # Andorra - Euro
    'AE': 'AED',  # United Arab Emirates - UAE Dirham
    'AF': 'AFN',  # Afghanistan - Afghan Afghani
    'AG': 'XCD',  # Antigua and Barbuda - East Caribbean Dollar
    'AI': 'XCD',  # Anguilla - East Caribbean Dollar
    'AL': 'ALL',  # Albania - Albanian Lek
    'AM': 'AMD',  # Armenia - Armenian Dram
    'AO': 'AOA',  # Angola - Angolan Kwanza
    'AQ': 'USD',  # Antarctica - US Dollar (no official currency)
    'AR': 'ARS',  # Argentina - Argentine Peso
    'AS': 'USD',  # American Samoa - US Dollar
    'AT': 'EUR',  # Austria - Euro
    'AU': 'AUD',  # Australia - Australian Dollar
    'AW': 'AWG',  # Aruba - Aruban Florin
    'AZ': 'AZN',  # Azerbaijan - Azerbaijani Manat
    'BA': 'BAM',  # Bosnia and Herzegovina - Bosnia and Herzegovina Convertible Mark
    'BB': 'BBD',  # Barbados - Barbadian Dollar
    'BD': 'BDT',  # Bangladesh - Bangladeshi Taka
    'BE': 'EUR',  # Belgium - Euro
    'BF': 'XOF',  # Burkina Faso - West African CFA Franc
    'BG': 'BGN',  # Bulgaria - Bulgarian Lev
    'BH': 'BHD',  # Bahrain - Bahraini Dinar
    'BI': 'BIF',  # Burundi - Burundian Franc
    'BJ': 'XOF',  # Benin - West African CFA Franc
    'BM': 'BMD',  # Bermuda - Bermudian Dollar
    'BN': 'BND',  # Brunei - Brunei Dollar
    'BO': 'BOB',  # Bolivia - Bolivian Boliviano
    'BR': 'BRL',  # Brazil - Brazilian Real
    'BS': 'BSD',  # Bahamas - Bahamian Dollar
    'BT': 'BTN',  # Bhutan - Bhutanese Ngultrum
    'BV': 'NOK',  # Bouvet Island - Norwegian Krone
    'BW': 'BWP',  # Botswana - Botswanan Pula
    'BY': 'BYN',  # Belarus - Belarusian Ruble
    'BZ': 'BZD',  # Belize - Belize Dollar
    'CA': 'CAD',  # Canada - Canadian Dollar
    'CD': 'CDF',  # Democratic Republic of the Congo - Congolese Franc
    'CF': 'XAF',  # Central African Republic - Central African CFA Franc
    'CG': 'XAF',  # Republic of the Congo - Central African CFA Franc
    'CH': 'CHF',  # Switzerland - Swiss Franc
    'CI': 'XOF',  # Côte d'Ivoire - West African CFA Franc
    'CK': 'NZD',  # Cook Islands - New Zealand Dollar
    'CL': 'CLP',  # Chile - Chilean Peso
    'CM': 'XAF',  # Cameroon - Central African CFA Franc
    'CN': 'CNY',  # China - Chinese Yuan
    'CO': 'COP',  # Colombia - Colombian Peso
    'CR': 'CRC',  # Costa Rica - Costa Rican Colón
    'CU': 'CUP',  # Cuba - Cuban Peso
    'CV': 'CVE',  # Cape Verde - Cape Verdean Escudo
    'CW': 'ANG',  # Curaçao - Netherlands Antillean Guilder
    'CY': 'EUR',  # Cyprus - Euro
    'CZ': 'CZK',  # Czech Republic - Czech Koruna
    'DE': 'EUR',  # Germany - Euro
    'DJ': 'DJF',  # Djibouti - Djiboutian Franc
    'DK': 'DKK',  # Denmark - Danish Krone
    'DM': 'XCD',  # Dominica - East Caribbean Dollar
    'DO': 'DOP',  # Dominican Republic - Dominican Peso
    'DZ': 'DZD',  # Algeria - Algerian Dinar
    'EC': 'USD',  # Ecuador - US Dollar
    'EE': 'EUR',  # Estonia - Euro
    'EG': 'EGP',  # Egypt - Egyptian Pound
    'EH': 'MAD',  # Western Sahara - Moroccan Dirham
    'ER': 'ERN',  # Eritrea - Eritrean Nakfa
    'ES': 'EUR',  # Spain - Euro
    'ET': 'ETB',  # Ethiopia - Ethiopian Birr
    'FI': 'EUR',  # Finland - Euro
    'FJ': 'FJD',  # Fiji - Fijian Dollar
    'FK': 'FKP',  # Falkland Islands - Falkland Islands Pound
    'FM': 'USD',  # Micronesia - US Dollar
    'FO': 'DKK',  # Faroe Islands - Danish Krone
    'FR': 'EUR',  # France - Euro
    'GA': 'XAF',  # Gabon - Central African CFA Franc
    'GB': 'GBP',  # United Kingdom - British Pound
    'GD': 'XCD',  # Grenada - East Caribbean Dollar
    'GE': 'GEL',  # Georgia - Georgian Lari
    'GF': 'EUR',  # French Guiana - Euro
    'GG': 'GBP',  # Guernsey - British Pound
    'GH': 'GHS',  # Ghana - Ghanaian Cedi
    'GI': 'GIP',  # Gibraltar - Gibraltar Pound
    'GL': 'DKK',  # Greenland - Danish Krone
    'GM': 'GMD',  # Gambia - Gambian Dalasi
    'GN': 'GNF',  # Guinea - Guinean Franc
    'GP': 'EUR',  # Guadeloupe - Euro
    'GQ': 'XAF',  # Equatorial Guinea - Central African CFA Franc
    'GR': 'EUR',  # Greece - Euro
    'GT': 'GTQ',  # Guatemala - Guatemalan Quetzal
    'GU': 'USD',  # Guam - US Dollar
    'GW': 'XOF',  # Guinea-Bissau - West African CFA Franc
    'GY': 'GYD',  # Guyana - Guyanese Dollar
    'HK': 'HKD',  # Hong Kong - Hong Kong Dollar
    'HN': 'HNL',  # Honduras - Honduran Lempira
    'HR': 'EUR',  # Croatia - Euro
    'HT': 'HTG',  # Haiti - Haitian Gourde
    'HU': 'HUF',  # Hungary - Hungarian Forint
    'ID': 'IDR',  # Indonesia - Indonesian Rupiah
    'IE': 'EUR',  # Ireland - Euro
    'IL': 'ILS',  # Israel - Israeli New Shekel
    'IM': 'GBP',  # Isle of Man - British Pound
    'IN': 'INR',  # India - Indian Rupee
    'IO': 'USD',  # British Indian Ocean Territory - US Dollar
    'IQ': 'IQD',  # Iraq - Iraqi Dinar
    'IR': 'IRR',  # Iran - Iranian Rial
    'IS': 'ISK',  # Iceland - Icelandic Króna
    'IT': 'EUR',  # Italy - Euro
    'JE': 'GBP',  # Jersey - British Pound
    'JM': 'JMD',  # Jamaica - Jamaican Dollar
    'JO': 'JOD',  # Jordan - Jordanian Dinar
    'JP': 'JPY',  # Japan - Japanese Yen
    'KE': 'KES',  # Kenya - Kenyan Shilling
    'KG': 'KGS',  # Kyrgyzstan - Kyrgystani Som
    'KH': 'KHR',  # Cambodia - Cambodian Riel
    'KI': 'AUD',  # Kiribati - Australian Dollar
    'KM': 'KMF',  # Comoros - Comorian Franc
    'KN': 'XCD',  # Saint Kitts and Nevis - East Caribbean Dollar
    'KP': 'KPW',  # North Korea - North Korean Won
    'KR': 'KRW',  # South Korea - South Korean Won
    'KW': 'KWD',  # Kuwait - Kuwaiti Dinar
    'KY': 'KYD',  # Cayman Islands - Cayman Islands Dollar
    'KZ': 'KZT',  # Kazakhstan - Kazakhstani Tenge
    'LA': 'LAK',  # Laos - Lao Kip
    'LB': 'LBP',  # Lebanon - Lebanese Pound
    'LC': 'XCD',  # Saint Lucia - East Caribbean Dollar
    'LI': 'CHF',  # Liechtenstein - Swiss Franc
    'LK': 'LKR',  # Sri Lanka - Sri Lankan Rupee
    'LR': 'LRD',  # Liberia - Liberian Dollar
    'LS': 'LSL',  # Lesotho - Lesotho Loti
    'LT': 'EUR',  # Lithuania - Euro
    'LU': 'EUR',  # Luxembourg - Euro
    'LV': 'EUR',  # Latvia - Euro
    'LY': 'LYD',  # Libya - Libyan Dinar
    'MA': 'MAD',  # Morocco - Moroccan Dirham
    'MC': 'EUR',  # Monaco - Euro
    'MD': 'MDL',  # Moldova - Moldovan Leu
    'ME': 'EUR',  # Montenegro - Euro
    'MF': 'EUR',  # Saint Martin - Euro
    'MG': 'MGA',  # Madagascar - Malagasy Ariary
    'MH': 'USD',  # Marshall Islands - US Dollar
    'MK': 'MKD',  # North Macedonia - Macedonian Denar
    'ML': 'XOF',  # Mali - West African CFA Franc
    'MM': 'MMK',  # Myanmar - Myanmar Kyat
    'MN': 'MNT',  # Mongolia - Mongolian Tugrik
    'MO': 'MOP',  # Macau - Macanese Pataca
    'MP': 'USD',  # Northern Mariana Islands - US Dollar
    'MQ': 'EUR',  # Martinique - Euro
    'MR': 'MRU',  # Mauritania - Mauritanian Ouguiya
    'MS': 'XCD',  # Montserrat - East Caribbean Dollar
    'MT': 'EUR',  # Malta - Euro
    'MU': 'MUR',  # Mauritius - Mauritian Rupee
    'MV': 'MVR',  # Maldives - Maldivian Rufiyaa
    'MW': 'MWK',  # Malawi - Malawian Kwacha
    'MX': 'MXN',  # Mexico - Mexican Peso
    'MY': 'MYR',  # Malaysia - Malaysian Ringgit
    'MZ': 'MZN',  # Mozambique - Mozambican Metical
    'NA': 'NAD',  # Namibia - Namibian Dollar
    'NC': 'XPF',  # New Caledonia - CFP Franc
    'NE': 'XOF',  # Niger - West African CFA Franc
    'NF': 'AUD',  # Norfolk Island - Australian Dollar
    'NG': 'NGN',  # Nigeria - Nigerian Naira
    'NI': 'NIO',  # Nicaragua - Nicaraguan Córdoba
    'NL': 'EUR',  # Netherlands - Euro
    'NO': 'NOK',  # Norway - Norwegian Krone
    'NP': 'NPR',  # Nepal - Nepalese Rupee
    'NR': 'AUD',  # Nauru - Australian Dollar
    'NU': 'NZD',  # Niue - New Zealand Dollar
    'NZ': 'NZD',  # New Zealand - New Zealand Dollar
    'OM': 'OMR',  # Oman - Omani Rial
    'PA': 'PAB',  # Panama - Panamanian Balboa
    'PE': 'PEN',  # Peru - Peruvian Sol
    'PF': 'XPF',  # French Polynesia - CFP Franc
    'PG': 'PGK',  # Papua New Guinea - Papua New Guinean Kina
    'PH': 'PHP',  # Philippines - Philippine Peso
    'PK': 'PKR',  # Pakistan - Pakistani Rupee
    'PL': 'PLN',  # Poland - Polish Złoty
    'PM': 'EUR',  # Saint Pierre and Miquelon - Euro
    'PN': 'NZD',  # Pitcairn Islands - New Zealand Dollar
    'PR': 'USD',  # Puerto Rico - US Dollar
    'PS': 'ILS',  # Palestine - Israeli New Shekel
    'PT': 'EUR',  # Portugal - Euro
    'PW': 'USD',  # Palau - US Dollar
    'PY': 'PYG',  # Paraguay - Paraguayan Guaraní
    'QA': 'QAR',  # Qatar - Qatari Riyal
    'RE': 'EUR',  # Réunion - Euro
    'RO': 'RON',  # Romania - Romanian Leu
    'RS': 'RSD',  # Serbia - Serbian Dinar
    'RU': 'RUB',  # Russia - Russian Ruble
    'RW': 'RWF',  # Rwanda - Rwandan Franc
    'SA': 'SAR',  # Saudi Arabia - Saudi Riyal
    'SB': 'SBD',  # Solomon Islands - Solomon Islands Dollar
    'SC': 'SCR',  # Seychelles - Seychellois Rupee
    'SD': 'SDG',  # Sudan - Sudanese Pound
    'SE': 'SEK',  # Sweden - Swedish Krona
    'SG': 'SGD',  # Singapore - Singapore Dollar
    'SH': 'SHP',  # Saint Helena - Saint Helena Pound
    'SI': 'EUR',  # Slovenia - Euro
    'SJ': 'NOK',  # Svalbard and Jan Mayen - Norwegian Krone
    'SK': 'EUR',  # Slovakia - Euro
    'SL': 'SLL',  # Sierra Leone - Sierra Leonean Leone
    'SM': 'EUR',  # San Marino - Euro
    'SN': 'XOF',  # Senegal - West African CFA Franc
    'SO': 'SOS',  # Somalia - Somali Shilling
    'SR': 'SRD',  # Suriname - Surinamese Dollar
    'SS': 'SSP',  # South Sudan - South Sudanese Pound
    'ST': 'STN',  # São Tomé and Príncipe - São Tomé and Príncipe Dobra
    'SV': 'USD',  # El Salvador - US Dollar
    'SX': 'ANG',  # Sint Maarten - Netherlands Antillean Guilder
    'SY': 'SYP',  # Syria - Syrian Pound
    'SZ': 'SZL',  # Eswatini - Swazi Lilangeni
    'TC': 'USD',  # Turks and Caicos Islands - US Dollar
    'TD': 'XAF',  # Chad - Central African CFA Franc
    'TF': 'EUR',  # French Southern and Antarctic Lands - Euro
    'TG': 'XOF',  # Togo - West African CFA Franc
    'TH': 'THB',  # Thailand - Thai Baht
    'TJ': 'TJS',  # Tajikistan - Tajikistani Somoni
    'TK': 'NZD',  # Tokelau - New Zealand Dollar
    'TL': 'USD',  # East Timor - US Dollar
    'TM': 'TMT',  # Turkmenistan - Turkmenistan Manat
    'TN': 'TND',  # Tunisia - Tunisian Dinar
    'TO': 'TOP',  # Tonga - Tongan Paʻanga
    'TR': 'TRY',  # Turkey - Turkish Lira
    'TT': 'TTD',  # Trinidad and Tobago - Trinidad and Tobago Dollar
    'TV': 'AUD',  # Tuvalu - Australian Dollar
    'TW': 'TWD',  # Taiwan - New Taiwan Dollar
    'TZ': 'TZS',  # Tanzania - Tanzanian Shilling
    'UA': 'UAH',  # Ukraine - Ukrainian Hryvnia
    'UG': 'UGX',  # Uganda - Ugandan Shilling
    'US': 'USD',  # United States - US Dollar
    'UY': 'UYU',  # Uruguay - Uruguayan Peso
    'UZ': 'UZS',  # Uzbekistan - Uzbekistani Som
    'VA': 'EUR',  # Vatican City - Euro
    'VC': 'XCD',  # Saint Vincent and the Grenadines - East Caribbean Dollar
    'VE': 'VES',  # Venezuela - Venezuelan Bolívar Soberano
    'VG': 'USD',  # British Virgin Islands - US Dollar
    'VI': 'USD',  # United States Virgin Islands - US Dollar
    'VN': 'VND',  # Vietnam - Vietnamese Dong
    'VU': 'VUV',  # Vanuatu - Vanuatu Vatu
    'WF': 'XPF',  # Wallis and Futuna - CFP Franc
    'WS': 'WST',  # Samoa - Samoan Tala
    'XK': 'EUR',  # Kosovo - Euro
    'YE': 'YER',  # Yemen - Yemeni Rial
    'YT': 'EUR',  # Mayotte - Euro
    'ZA': 'ZAR',  # South Africa - South African Rand
    'ZM': 'ZMW',  # Zambia - Zambian Kwacha
    'ZW': 'ZWL',  # Zimbabwe - Zimbabwean Dollar
}

# Most common source currencies supported by XE
XE_COMMON_SOURCE_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'NZD', 'JPY', 'CHF', 'SGD', 'HKD'
]

# Extended list of known supported corridors for XE
# Format: (source_currency, target_country)
XE_SUPPORTED_CORRIDORS = [
    # USD corridors
    ("USD", "IN"),  # USD to India
    ("USD", "PH"),  # USD to Philippines
    ("USD", "PK"),  # USD to Pakistan
    ("USD", "MX"),  # USD to Mexico
    ("USD", "DE"),  # USD to Germany
    ("USD", "FR"),  # USD to France
    ("USD", "ES"),  # USD to Spain
    ("USD", "IT"),  # USD to Italy
    ("USD", "AU"),  # USD to Australia
    ("USD", "GB"),  # USD to UK
    ("USD", "CA"),  # USD to Canada
    ("USD", "NZ"),  # USD to New Zealand
    ("USD", "SG"),  # USD to Singapore
    ("USD", "AE"),  # USD to UAE
    ("USD", "ZA"),  # USD to South Africa
    ("USD", "KE"),  # USD to Kenya
    ("USD", "NG"),  # USD to Nigeria
    ("USD", "CN"),  # USD to China
    ("USD", "JP"),  # USD to Japan
    ("USD", "KR"),  # USD to South Korea
    ("USD", "TH"),  # USD to Thailand
    ("USD", "VN"),  # USD to Vietnam
    ("USD", "ID"),  # USD to Indonesia
    ("USD", "MY"),  # USD to Malaysia
    ("USD", "TR"),  # USD to Turkey
    ("USD", "BR"),  # USD to Brazil
    ("USD", "CO"),  # USD to Colombia
    
    # EUR corridors
    ("EUR", "PH"),  # EUR to Philippines
    ("EUR", "IN"),  # EUR to India
    ("EUR", "PK"),  # EUR to Pakistan
    ("EUR", "MX"),  # EUR to Mexico
    ("EUR", "US"),  # EUR to USA
    ("EUR", "GB"),  # EUR to UK
    ("EUR", "CA"),  # EUR to Canada
    ("EUR", "AU"),  # EUR to Australia
    ("EUR", "NZ"),  # EUR to New Zealand
    ("EUR", "ZA"),  # EUR to South Africa
    ("EUR", "AE"),  # EUR to UAE
    
    # GBP corridors
    ("GBP", "IN"),  # GBP to India
    ("GBP", "PK"),  # GBP to Pakistan
    ("GBP", "PH"),  # GBP to Philippines
    ("GBP", "MX"),  # GBP to Mexico
    ("GBP", "DE"),  # GBP to Germany
    ("GBP", "US"),  # GBP to USA
    ("GBP", "CA"),  # GBP to Canada
    ("GBP", "AU"),  # GBP to Australia
    ("GBP", "NZ"),  # GBP to New Zealand
    ("GBP", "AE"),  # GBP to UAE
    
    # CAD corridors
    ("CAD", "IN"),  # CAD to India
    ("CAD", "PK"),  # CAD to Pakistan
    ("CAD", "PH"),  # CAD to Philippines
    ("CAD", "US"),  # CAD to USA
    ("CAD", "GB"),  # CAD to UK
    ("CAD", "AU"),  # CAD to Australia
    ("CAD", "NZ"),  # CAD to New Zealand
    
    # AUD corridors
    ("AUD", "IN"),  # AUD to India
    ("AUD", "PH"),  # AUD to Philippines
    ("AUD", "PK"),  # AUD to Pakistan
    ("AUD", "US"),  # AUD to USA
    ("AUD", "GB"),  # AUD to UK
    ("AUD", "CA"),  # AUD to Canada
    ("AUD", "NZ"),  # AUD to New Zealand
    
    # NZD corridors
    ("NZD", "IN"),  # NZD to India
    ("NZD", "PH"),  # NZD to Philippines
    ("NZD", "AU"),  # NZD to Australia
    ("NZD", "GB"),  # NZD to UK
    ("NZD", "US"),  # NZD to USA
]

def get_xe_currency_for_country(country_code: str) -> Optional[str]:
    """
    Get the currency for a country using XE-specific mappings.
    Falls back to default mappings if not found in XE-specific mapping.
    
    Args:
        country_code: ISO-3166-1 alpha-2 country code
        
    Returns:
        ISO-4217 currency code or None if not found
    """
    # First try XE-specific mapping
    country_code = country_code.upper()
    currency = XE_COUNTRY_TO_CURRENCY.get(country_code)
    
    # If not found, fall back to default mapping
    if not currency:
        currency = get_default_currency_for_country(country_code)
        
    return currency

def is_xe_corridor_supported(source_currency: str, target_country: str) -> bool:
    """
    Check if a specific corridor is supported by XE.
    
    Args:
        source_currency: Source currency code (e.g., 'USD')
        target_country: Target country code (e.g., 'IN')
        
    Returns:
        True if the corridor is supported, False otherwise
    """
    source_currency = source_currency.upper()
    target_country = target_country.upper()
    
    # Check if it's in our known list of supported corridors
    if (source_currency, target_country) in XE_SUPPORTED_CORRIDORS:
        return True
    
    # For common source currencies, we'll assume most countries are supported
    if source_currency in XE_COMMON_SOURCE_CURRENCIES and target_country in XE_COUNTRY_TO_CURRENCY:
        # In a real implementation, you might want to add exceptions here
        # For example, certain sanctioned countries might not be supported
        return True
    
    return False 