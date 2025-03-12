"""
KoronaPay provider mappings.
Contains currency and country ID mappings for the KoronaPay API.
"""

# Currency mappings (ISO-4217 -> KoronaPay internal ID)
CURRENCY_IDS = {
    "EUR": "978",  # Euro
    "USD": "840",  # US Dollar
    "TRY": "949",  # Turkish Lira
    "IDR": "360",  # Indonesian Rupiah
    "GBP": "826",  # British Pound
    "PLN": "985",  # Polish Zloty
    "CZK": "203",  # Czech Koruna
    "HUF": "348",  # Hungarian Forint
    "RON": "946",  # Romanian Leu
    "BGN": "975",  # Bulgarian Lev
    "HRK": "191",  # Croatian Kuna
    "DKK": "208",  # Danish Krone
    "SEK": "752",  # Swedish Krona
    "NOK": "578",  # Norwegian Krone
    "VND": "704",  # Vietnamese Dong
    "PHP": "608",  # Philippine Peso
    "THB": "764",  # Thai Baht
    "MYR": "458",  # Malaysian Ringgit
}

# Country mappings (ISO-3166-1 alpha-3 -> KoronaPay internal ID)
# Note: KoronaPay uses the same 3-character codes as ISO-3166-1 alpha-3
COUNTRY_IDS = {
    # Source Countries (Europe)
    "AUT": "AUT",  # Austria
    "BEL": "BEL",  # Belgium
    "BGR": "BGR",  # Bulgaria
    "HRV": "HRV",  # Croatia
    "CYP": "CYP",  # Cyprus
    "CZE": "CZE",  # Czech Republic
    "DNK": "DNK",  # Denmark
    "EST": "EST",  # Estonia
    "FIN": "FIN",  # Finland
    "FRA": "FRA",  # France
    "DEU": "DEU",  # Germany
    "GRC": "GRC",  # Greece
    "HUN": "HUN",  # Hungary
    "ISL": "ISL",  # Iceland
    "IRL": "IRL",  # Ireland
    "ITA": "ITA",  # Italy
    "LVA": "LVA",  # Latvia
    "LIE": "LIE",  # Liechtenstein
    "LTU": "LTU",  # Lithuania
    "LUX": "LUX",  # Luxembourg
    "MLT": "MLT",  # Malta
    "NLD": "NLD",  # Netherlands
    "NOR": "NOR",  # Norway
    "POL": "POL",  # Poland
    "PRT": "PRT",  # Portugal
    "ROU": "ROU",  # Romania
    "SVK": "SVK",  # Slovakia
    "SVN": "SVN",  # Slovenia
    "ESP": "ESP",  # Spain
    "SWE": "SWE",  # Sweden
    "GBR": "GBR",  # United Kingdom
    # Destination Countries
    "IDN": "IDN",  # Indonesia
    "TUR": "TUR",  # Turkey
    "VNM": "VNM",  # Vietnam
    "PHL": "PHL",  # Philippines
    "THA": "THA",  # Thailand
    "MYS": "MYS",  # Malaysia
}

# Payment method mappings
PAYMENT_METHODS = {"debit_card": "debitCard", "bank_account": "bankAccount"}

# Receiving method mappings
RECEIVING_METHODS = {"cash": "cash", "card": "card"}


def get_currency_id(currency_code: str) -> str:
    """Get KoronaPay internal currency ID from ISO-4217 code."""
    return CURRENCY_IDS.get(currency_code.upper())


def get_country_id(country_code: str) -> str:
    """Get KoronaPay internal country ID from ISO-3166-1 alpha-3 code."""
    return COUNTRY_IDS.get(country_code.upper())


def get_payment_method(method: str) -> str:
    """Get KoronaPay internal payment method ID."""
    return PAYMENT_METHODS.get(method.lower())


def get_receiving_method(method: str) -> str:
    """Get KoronaPay internal receiving method ID."""
    return RECEIVING_METHODS.get(method.lower())


def get_supported_currencies() -> list:
    """Get list of supported ISO-4217 currency codes."""
    return list(CURRENCY_IDS.keys())


def get_supported_countries() -> list:
    """Get list of supported ISO-3166-1 alpha-3 country codes."""
    return list(COUNTRY_IDS.keys())


def get_supported_payment_methods() -> list:
    """Get list of supported payment methods."""
    return list(PAYMENT_METHODS.keys())


def get_supported_receiving_methods() -> list:
    """Get list of supported receiving methods."""
    return list(RECEIVING_METHODS.keys())
