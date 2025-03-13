"""
Standardized country and currency code mappings for the aggregator.
Uses ISO-3166-1 alpha-2 and alpha-3 for countries and ISO-4217 for currencies.
"""
from typing import Dict, List, Optional, Tuple

# ISO-3166-1 alpha-2 country codes to full names
ISO_COUNTRY_NAMES = {
    "AE": "UNITED ARAB EMIRATES",
    "EG": "EGYPT",
    "GT": "GUATEMALA",
    "IN": "INDIA",
    "PK": "PAKISTAN",
    "PH": "PHILIPPINES",
    "LK": "SRI LANKA",
    "BD": "BANGLADESH",
    "NP": "NEPAL",
    "US": "UNITED STATES OF AMERICA",
    "GB": "UNITED KINGDOM",
    "CA": "CANADA",
    "AU": "AUSTRALIA",
    "NZ": "NEW ZEALAND",
    "SG": "SINGAPORE",
    "MY": "MALAYSIA",
    "ID": "INDONESIA",
    "TH": "THAILAND",
    "VN": "VIETNAM",
    "JP": "JAPAN",
    "KR": "SOUTH KOREA",
    "SA": "SAUDI ARABIA",
    "QA": "QATAR",
    "KW": "KUWAIT",
    "BH": "BAHRAIN",
    "OM": "OMAN",
    "JO": "JORDAN",
    "LB": "LEBANON",
    "IQ": "IRAQ",
    "YE": "YEMEN",
    "MA": "MOROCCO",
    "TN": "TUNISIA",
    "DZ": "ALGERIA",
    "LY": "LIBYA",
    "SD": "SUDAN",
    "KE": "KENYA",
    "UG": "UGANDA",
    "TZ": "TANZANIA",
    "NG": "NIGERIA",
    "GH": "GHANA",
    "ZA": "SOUTH AFRICA",
    "MX": "MEXICO",
    "BR": "BRAZIL",
    "AR": "ARGENTINA",
    "CL": "CHILE",
    "CO": "COLOMBIA",
    "PE": "PERU",
    "VE": "VENEZUELA",
}

# ISO-3166-1 alpha-3 to alpha-2 mapping
ISO_ALPHA3_TO_ALPHA2 = {
    "USA": "US",
    "GBR": "GB",
    "GTM": "GT",
    "CAN": "CA",
    "AUS": "AU",
    "NZL": "NZ",
    "SGP": "SG",
    "MYS": "MY",
    "IDN": "ID",
    "THA": "TH",
    "VNM": "VN",
    "JPN": "JP",
    "KOR": "KR",
    "SAU": "SA",
    "QAT": "QA",
    "KWT": "KW",
    "BHR": "BH",
    "OMN": "OM",
    "JOR": "JO",
    "LBN": "LB",
    "IRQ": "IQ",
    "YEM": "YE",
    "MAR": "MA",
    "TUN": "TN",
    "DZA": "DZ",
    "LBY": "LY",
    "SDN": "SD",
    "KEN": "KE",
    "UGA": "UG",
    "TZA": "TZ",
    "NGA": "NG",
    "GHA": "GH",
    "ZAF": "ZA",
    "MEX": "MX",
    "BRA": "BR",
    "ARG": "AR",
    "CHL": "CL",
    "COL": "CO",
    "PER": "PE",
    "VEN": "VE",
    "IND": "IN",
    "PAK": "PK",
    "BGD": "BD",
    "LKA": "LK",
    "NPL": "NP",
    "PHL": "PH",
    "EGY": "EG",
    "ARE": "AE",
}

# Currency codes and their numeric mappings
CURRENCY_CODES = {
    "AED": "784",
    "USD": "840",
    "EUR": "978",
    "GBP": "826",
    "GTQ": "320",
    "INR": "356",
    "PKR": "586",
    "BDT": "050",
    "LKR": "144",
    "NPR": "524",
    "PHP": "608",
    "EGP": "818",
    "SAR": "682",
    "QAR": "634",
    "OMR": "512",
    "BHD": "048",
    "KWD": "414",
    "JOD": "400",
    "LBP": "422",
    "IQD": "368",
    "YER": "886",
    "MAD": "504",
    "TND": "788",
    "DZD": "012",
    "MXN": "484",
    "BRL": "986",
    "ARS": "032",
    "CLP": "152",
    "COP": "170",
    "PEN": "604",
    "VES": "928",
    "KES": "404",
    "ETB": "230",
    "SOS": "706",
    "TZS": "834",
    "UGX": "800",
    "RWF": "646",
    "DJF": "262",
    "SDG": "938",
}


def normalize_country_code(country_code: str) -> str:
    """
    Normalize a country code to ISO-3166-1 alpha-2 format.

    Args:
        country_code: A country code in any format (alpha-2, alpha-3, etc.)

    Returns:
        The normalized ISO-3166-1 alpha-2 country code, or the original if not found
    """
    if not country_code:
        return ""

    # Convert to uppercase
    country_code = country_code.strip().upper()

    # If already alpha-2 and valid, return as is
    if country_code in ISO_COUNTRY_NAMES:
        return country_code

    # Check if it's alpha-3 and convert to alpha-2
    if len(country_code) == 3 and country_code in ISO_ALPHA3_TO_ALPHA2:
        return ISO_ALPHA3_TO_ALPHA2[country_code]

    # Special case for Eurozone
    if country_code == "EUR" or country_code == "EURO":
        return "EU"

    # Return original if no mapping found
    return country_code


def validate_corridor(
    source_country: str, source_currency: str, dest_country: str, dest_currency: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate if a corridor (source country/currency to destination country/currency) is valid.

    Args:
        source_country: ISO-3166-1 alpha-2 code for source country
        source_currency: ISO-4217 code for source currency
        dest_country: ISO-3166-1 alpha-2 code for destination country
        dest_currency: ISO-4217 code for destination currency

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if corridor is valid, False otherwise
        - error_message: None if valid, otherwise a string explaining the error
    """
    # Basic validation
    if not source_country:
        return False, "Source country is required"
    if not source_currency:
        return False, "Source currency is required"
    if not dest_country:
        return False, "Destination country is required"
    if not dest_currency:
        return False, "Destination currency is required"

    # Normalize country codes
    source_country = normalize_country_code(source_country)
    dest_country = normalize_country_code(dest_country)

    # Convert currencies to uppercase
    source_currency = source_currency.upper()
    dest_currency = dest_currency.upper()

    # Check if source country is valid
    if source_country != "EU" and source_country not in ISO_COUNTRY_NAMES:
        return False, f"Invalid source country: {source_country}"

    # Check if destination country is valid
    if dest_country != "EU" and dest_country not in ISO_COUNTRY_NAMES:
        return False, f"Invalid destination country: {dest_country}"

    # For now, we don't validate specific corridors
    # This can be expanded later to check if specific country-to-country transfers are supported

    return True, None


def get_country_name(iso_code: str) -> Optional[str]:
    """Convert ISO-3166-1 alpha-2 or alpha-3 country code to full name."""
    code = normalize_country_code(iso_code)
    return ISO_COUNTRY_NAMES.get(code) if code else None


def get_currency_numeric(iso_code: str) -> Optional[str]:
    """Convert ISO-4217 currency code to numeric code."""
    return CURRENCY_CODES.get(iso_code.upper())


def get_default_currency_for_country(country_code: str) -> Optional[str]:
    """
    Get the default currency for a country.

    Args:
        country_code: ISO-3166-1 alpha-2 country code

    Returns:
        ISO-4217 currency code or None if not found
    """
    # Common mappings
    country_to_currency = {
        "US": "USD",
        "GB": "GBP",
        "EU": "EUR",
        "CA": "CAD",
        "AU": "AUD",
        "JP": "JPY",
        "IN": "INR",
        "PK": "PKR",
        "BD": "BDT",
        "PH": "PHP",
        "NP": "NPR",
        "LK": "LKR",
        "ID": "IDR",
        "VN": "VND",
    }

    return country_to_currency.get(normalize_country_code(country_code))
