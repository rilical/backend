"""
Intermex-specific mapping utilities.

This module provides mapping functions to convert between standardized formats
and Intermex's specific requirements for country codes, currencies, and other values.
"""

from typing import Dict, Optional, Tuple

from providers.utils.country_currency_standards import normalize_country_code

# Intermex-specific country code mappings
# Maps ISO-3166-1 alpha-2 codes to Intermex country codes
COUNTRY_MAPPINGS = {
    # Source countries
    "US": "USA",  # United States
    "USA": "USA",  # United States (alternate)
    # Destination countries
    # North America
    "MX": "MX",  # Mexico
    "MEX": "MX",  # Mexico (alternate)
    # Central America
    "GU": "GU",  # Guatemala
    "GTM": "GU",  # Guatemala (alternate)
    "SA": "SA",  # El Salvador
    "SV": "SA",  # El Salvador (alternate)
    "HO": "HO",  # Honduras
    "HN": "HO",  # Honduras (alternate)
    "NI": "NI",  # Nicaragua
    "NIC": "NI",  # Nicaragua (alternate)
    "CR": "CR",  # Costa Rica
    "CRI": "CR",  # Costa Rica (alternate)
    "PA": "PA",  # Panama
    "PAN": "PA",  # Panama (alternate)
    # South America
    "CL": "CL",  # Colombia
    "CO": "CL",  # Colombia (alternate)
    "PE": "PE",  # Peru
    "PER": "PE",  # Peru (alternate)
    "EC": "EC",  # Ecuador
    "ECU": "EC",  # Ecuador (alternate)
    "BO": "BO",  # Bolivia
    "BOL": "BO",  # Bolivia (alternate)
    "AR": "AR",  # Argentina
    "ARG": "AR",  # Argentina (alternate)
    "BR": "BR",  # Brazil
    "BRA": "BR",  # Brazil (alternate)
    "UY": "UY",  # Uruguay
    "URY": "UY",  # Uruguay (alternate)
    "PY": "PY",  # Paraguay
    "PRY": "PY",  # Paraguay (alternate)
    "VE": "VE",  # Venezuela
    "VEN": "VE",  # Venezuela (alternate)
    # Caribbean
    "DO": "DO",  # Dominican Republic
    "DOM": "DO",  # Dominican Republic (alternate)
    "HT": "HT",  # Haiti
    "HTI": "HT",  # Haiti (alternate)
    "JM": "JM",  # Jamaica
    "JAM": "JM",  # Jamaica (alternate)
    "CU": "CU",  # Cuba
    "CUB": "CU",  # Cuba (alternate)
    # Europe
    "ES": "ES",  # Spain
    "ESP": "ES",  # Spain (alternate)
    "PT": "PT",  # Portugal
    "PRT": "PT",  # Portugal (alternate)
    "IT": "IT",  # Italy
    "ITA": "IT",  # Italy (alternate)
    "FR": "FR",  # France
    "FRA": "FR",  # France (alternate)
    "DE": "DE",  # Germany
    "DEU": "DE",  # Germany (alternate)
    "GB": "GB",  # United Kingdom
    "GBR": "GB",  # United Kingdom (alternate)
    "RO": "RO",  # Romania
    "ROU": "RO",  # Romania (alternate)
    "PL": "PL",  # Poland
    "POL": "PL",  # Poland (alternate)
    "HU": "HU",  # Hungary
    "HUN": "HU",  # Hungary (alternate)
    "CZ": "CZ",  # Czech Republic
    "CZE": "CZ",  # Czech Republic (alternate)
    "SK": "SK",  # Slovakia
    "SVK": "SK",  # Slovakia (alternate)
    "BG": "BG",  # Bulgaria
    "BGR": "BG",  # Bulgaria (alternate)
    "HR": "HR",  # Croatia
    "HRV": "HR",  # Croatia (alternate)
    "SI": "SI",  # Slovenia
    "SVN": "SI",  # Slovenia (alternate)
    "EE": "EE",  # Estonia
    "EST": "EE",  # Estonia (alternate)
    "LV": "LV",  # Latvia
    "LVA": "LV",  # Latvia (alternate)
    "LT": "LT",  # Lithuania
    "LTU": "LT",  # Lithuania (alternate)
    "CY": "CY",  # Cyprus
    "CYP": "CY",  # Cyprus (alternate)
    "MT": "MT",  # Malta
    "MLT": "MT",  # Malta (alternate)
    "GR": "GR",  # Greece
    "GRC": "GR",  # Greece (alternate)
    "IE": "IE",  # Ireland
    "IRL": "IE",  # Ireland (alternate)
    "DK": "DK",  # Denmark
    "DNK": "DK",  # Denmark (alternate)
    "SE": "SE",  # Sweden
    "SWE": "SE",  # Sweden (alternate)
    "FI": "FI",  # Finland
    "FIN": "FI",  # Finland (alternate)
    "NO": "NO",  # Norway
    "NOR": "NO",  # Norway (alternate)
    "IS": "IS",  # Iceland
    "ISL": "IS",  # Iceland (alternate)
    "CH": "CH",  # Switzerland
    "CHE": "CH",  # Switzerland (alternate)
    "AT": "AT",  # Austria
    "AUT": "AT",  # Austria (alternate)
    "BE": "BE",  # Belgium
    "BEL": "BE",  # Belgium (alternate)
    "NL": "NL",  # Netherlands
    "NLD": "NL",  # Netherlands (alternate)
    "LU": "LU",  # Luxembourg
    "LUX": "LU",  # Luxembourg (alternate)
}

# Intermex-specific payment method mappings
PAYMENT_METHODS = {
    "debitCard": 3,
    "creditCard": 4,
    "bankAccount": 1,
    "cash": 2,
    "ACH": 5,
    "wireTransfer": 6,
}

# Intermex-specific delivery method mappings
DELIVERY_METHODS = {
    "bankDeposit": {
        "tranTypeId": 3,
        "deliveryType": "W",  # W for wire transfer
        "tranTypeName": "Bank Deposit",
    },
    "cashPickup": {
        "tranTypeId": 1,
        "deliveryType": "W",  # W for wire transfer
        "tranTypeName": "Cash Pickup",
    },
    "mobileWallet": {
        "tranTypeId": 4,
        "deliveryType": "W",  # W for wire transfer
        "tranTypeName": "Mobile Wallet",
    },
    "homeDelivery": {
        "tranTypeId": 5,
        "deliveryType": "W",  # W for wire transfer
        "tranTypeName": "Home Delivery",
    },
}


def map_country_code(country_code: str) -> Optional[str]:
    """
    Map a standardized country code to Intermex's format.

    Args:
        country_code: ISO-3166-1 alpha-2 or alpha-3 country code

    Returns:
        Intermex country code if valid, None otherwise
    """
    # First normalize to ISO-3166-1 alpha-2
    normalized_code = normalize_country_code(country_code)
    if not normalized_code:
        return None

    # Then map to Intermex format
    return COUNTRY_MAPPINGS.get(normalized_code)


def map_payment_method(payment_method: str) -> Optional[int]:
    """
    Map a standardized payment method to Intermex's format.

    Args:
        payment_method: Standardized payment method name

    Returns:
        Intermex payment method ID if valid, None otherwise
    """
    return PAYMENT_METHODS.get(payment_method)


def map_delivery_method(delivery_method: str) -> Optional[Dict]:
    """
    Map a standardized delivery method to Intermex's format.

    Args:
        delivery_method: Standardized delivery method name

    Returns:
        Dictionary containing Intermex delivery method details if valid, None otherwise
    """
    return DELIVERY_METHODS.get(delivery_method)


def validate_corridor(
    source_country: str, source_currency: str, dest_country: str, dest_currency: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate if a corridor is supported by Intermex.

    Args:
        source_country: Source country code
        source_currency: Source currency code
        dest_country: Destination country code
        dest_currency: Destination currency code

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    # Map country codes to Intermex format
    mapped_source = map_country_code(source_country)
    mapped_dest = map_country_code(dest_country)

    if not mapped_source:
        return False, f"Unsupported source country: {source_country}"

    if not mapped_dest:
        return False, f"Unsupported destination country: {dest_country}"

    # Validate currencies
    if source_currency.upper() != "USD":
        return False, f"Unsupported source currency: {source_currency}"

    # Map of supported destination currencies by country
    supported_dest_currencies = {
        # North America
        "MX": "MXN",  # Mexico
        # Central America
        "GU": "GTQ",  # Guatemala
        "SA": "USD",  # El Salvador (USD corridor)
        "HO": "HNL",  # Honduras
        "NI": "NIO",  # Nicaragua
        "CR": "CRC",  # Costa Rica
        "PA": "PAB",  # Panama
        # South America
        "CL": "COP",  # Colombia
        "PE": "PEN",  # Peru
        "EC": "USD",  # Ecuador (USD corridor)
        "BO": "BOB",  # Bolivia
        "AR": "ARS",  # Argentina
        "BR": "BRL",  # Brazil
        "UY": "UYU",  # Uruguay
        "PY": "PYG",  # Paraguay
        "VE": "VES",  # Venezuela
        # Caribbean
        "DO": "DOP",  # Dominican Republic
        "HT": "HTG",  # Haiti
        "JM": "JMD",  # Jamaica
        "CU": "CUP",  # Cuba
        # Europe
        "ES": "EUR",  # Spain
        "PT": "EUR",  # Portugal
        "IT": "EUR",  # Italy
        "FR": "EUR",  # France
        "DE": "EUR",  # Germany
        "GB": "GBP",  # United Kingdom
        "RO": "RON",  # Romania
        "PL": "PLN",  # Poland
        "HU": "HUF",  # Hungary
        "CZ": "CZK",  # Czech Republic
        "SK": "EUR",  # Slovakia
        "BG": "BGN",  # Bulgaria
        "HR": "EUR",  # Croatia
        "SI": "EUR",  # Slovenia
        "EE": "EUR",  # Estonia
        "LV": "EUR",  # Latvia
        "LT": "EUR",  # Lithuania
        "CY": "EUR",  # Cyprus
        "MT": "EUR",  # Malta
        "GR": "EUR",  # Greece
        "IE": "EUR",  # Ireland
        "DK": "DKK",  # Denmark
        "SE": "SEK",  # Sweden
        "FI": "EUR",  # Finland
        "NO": "NOK",  # Norway
        "IS": "ISK",  # Iceland
        "CH": "CHF",  # Switzerland
        "AT": "EUR",  # Austria
        "BE": "EUR",  # Belgium
        "NL": "EUR",  # Netherlands
        "LU": "EUR",  # Luxembourg
    }

    expected_currency = supported_dest_currencies.get(mapped_dest)
    if not expected_currency or dest_currency.upper() != expected_currency:
        return False, f"Invalid currency pair: {source_currency} to {dest_currency}"

    return True, None
