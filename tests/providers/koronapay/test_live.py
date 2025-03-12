"""
Live API Testing Script for KoronaPay Integration

This script performs real API calls to test the KoronaPay integration.
Tests use amounts under 1000 USD equivalent to ensure better success rates.
"""

import json
import logging
import os
import sys
from datetime import datetime
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from apps.providers.koronapay.exceptions import KoronaPayError
from apps.providers.koronapay.integration import KoronaPayProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_currency(amount, currency):
    """Format currency amount with proper precision."""
    if currency in ["IDR", "VND"]:
        return f"{int(amount):,} {currency}"
    return f"{float(amount):.2f} {currency}"


def log_api_response(response):
    """Log detailed API response information."""
    if isinstance(response, dict):
        logger.debug("API Response Details:")
        for key, value in response.items():
            if key != "success":  # Skip success flag as it's handled separately
                logger.debug(f"  {key}: {value}")


def test_tariffs():
    """Test tariff retrieval for 30 different corridors with amounts under 1000 USD."""
    provider = KoronaPayProvider()

    # Test cases for different corridors (all under 1000 USD equivalent)
    test_cases = [
        # Western Europe to Turkey (6 combinations)
        {
            "sending_country": "DEU",  # Germany
            "receiving_country": "TUR",
            "sending_currency": "EUR",
            "receiving_currency": "TRY",
            "amount": Decimal("50.00"),
            "description": "Germany -> Turkey (EUR->TRY)",
        },
        {
            "sending_country": "FRA",  # France
            "receiving_country": "TUR",
            "sending_currency": "EUR",
            "receiving_currency": "TRY",
            "amount": Decimal("75.00"),
            "description": "France -> Turkey (EUR->TRY)",
        },
        {
            "sending_country": "ITA",  # Italy
            "receiving_country": "TUR",
            "sending_currency": "EUR",
            "receiving_currency": "TRY",
            "amount": Decimal("60.00"),
            "description": "Italy -> Turkey (EUR->TRY)",
        },
        {
            "sending_country": "ESP",  # Spain
            "receiving_country": "TUR",
            "sending_currency": "EUR",
            "receiving_currency": "TRY",
            "amount": Decimal("45.00"),
            "description": "Spain -> Turkey (EUR->TRY)",
        },
        {
            "sending_country": "NLD",  # Netherlands
            "receiving_country": "TUR",
            "sending_currency": "EUR",
            "receiving_currency": "TRY",
            "amount": Decimal("85.00"),
            "description": "Netherlands -> Turkey (EUR->TRY)",
        },
        {
            "sending_country": "BEL",  # Belgium
            "receiving_country": "TUR",
            "sending_currency": "EUR",
            "receiving_currency": "TRY",
            "amount": Decimal("65.00"),
            "description": "Belgium -> Turkey (EUR->TRY)",
        },
        # Northern Europe to Vietnam (6 combinations)
        {
            "sending_country": "SWE",  # Sweden
            "receiving_country": "VNM",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("70.00"),
            "description": "Sweden -> Vietnam (EUR->USD)",
        },
        {
            "sending_country": "DNK",  # Denmark
            "receiving_country": "VNM",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("55.00"),
            "description": "Denmark -> Vietnam (EUR->USD)",
        },
        {
            "sending_country": "NOR",  # Norway
            "receiving_country": "VNM",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("80.00"),
            "description": "Norway -> Vietnam (EUR->USD)",
        },
        {
            "sending_country": "FIN",  # Finland
            "receiving_country": "VNM",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("45.00"),
            "description": "Finland -> Vietnam (EUR->USD)",
        },
        {
            "sending_country": "ISL",  # Iceland
            "receiving_country": "VNM",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("90.00"),
            "description": "Iceland -> Vietnam (EUR->USD)",
        },
        {
            "sending_country": "IRL",  # Ireland
            "receiving_country": "VNM",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("65.00"),
            "description": "Ireland -> Vietnam (EUR->USD)",
        },
        # Western Europe to Philippines (6 combinations)
        {
            "sending_country": "DEU",  # Germany
            "receiving_country": "PHL",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("75.00"),
            "description": "Germany -> Philippines (EUR->USD)",
        },
        {
            "sending_country": "FRA",  # France
            "receiving_country": "PHL",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("85.00"),
            "description": "France -> Philippines (EUR->USD)",
        },
        {
            "sending_country": "ITA",  # Italy
            "receiving_country": "PHL",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("95.00"),
            "description": "Italy -> Philippines (EUR->USD)",
        },
        {
            "sending_country": "ESP",  # Spain
            "receiving_country": "PHL",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("55.00"),
            "description": "Spain -> Philippines (EUR->USD)",
        },
        {
            "sending_country": "NLD",  # Netherlands
            "receiving_country": "PHL",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("65.00"),
            "description": "Netherlands -> Philippines (EUR->USD)",
        },
        {
            "sending_country": "BEL",  # Belgium
            "receiving_country": "PHL",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("45.00"),
            "description": "Belgium -> Philippines (EUR->USD)",
        },
        # Central Europe to Indonesia (6 combinations)
        {
            "sending_country": "CHE",  # Switzerland
            "receiving_country": "IDN",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("80.00"),
            "description": "Switzerland -> Indonesia (EUR->USD)",
        },
        {
            "sending_country": "AUT",  # Austria
            "receiving_country": "IDN",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("70.00"),
            "description": "Austria -> Indonesia (EUR->USD)",
        },
        {
            "sending_country": "CZE",  # Czech Republic
            "receiving_country": "IDN",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("60.00"),
            "description": "Czech Republic -> Indonesia (EUR->USD)",
        },
        {
            "sending_country": "SVK",  # Slovakia
            "receiving_country": "IDN",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("50.00"),
            "description": "Slovakia -> Indonesia (EUR->USD)",
        },
        {
            "sending_country": "HUN",  # Hungary
            "receiving_country": "IDN",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("40.00"),
            "description": "Hungary -> Indonesia (EUR->USD)",
        },
        {
            "sending_country": "SVN",  # Slovenia
            "receiving_country": "IDN",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("45.00"),
            "description": "Slovenia -> Indonesia (EUR->USD)",
        },
        # Southern Europe to Thailand (6 combinations)
        {
            "sending_country": "PRT",  # Portugal
            "receiving_country": "THA",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("75.00"),
            "description": "Portugal -> Thailand (EUR->USD)",
        },
        {
            "sending_country": "ESP",  # Spain
            "receiving_country": "THA",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("85.00"),
            "description": "Spain -> Thailand (EUR->USD)",
        },
        {
            "sending_country": "ITA",  # Italy
            "receiving_country": "THA",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("95.00"),
            "description": "Italy -> Thailand (EUR->USD)",
        },
        {
            "sending_country": "GRC",  # Greece
            "receiving_country": "THA",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("65.00"),
            "description": "Greece -> Thailand (EUR->USD)",
        },
        {
            "sending_country": "HRV",  # Croatia
            "receiving_country": "THA",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("55.00"),
            "description": "Croatia -> Thailand (EUR->USD)",
        },
        {
            "sending_country": "MLT",  # Malta
            "receiving_country": "THA",
            "sending_currency": "EUR",
            "receiving_currency": "USD",
            "amount": Decimal("45.00"),
            "description": "Malta -> Thailand (EUR->USD)",
        },
    ]

    for case in test_cases:
        logger.info("\n" + "=" * 50)
        logger.info(f"Testing: {case['description']}")
        logger.info(
            f"Corridor: {case['sending_country']} ({case['sending_currency']}) -> {case['receiving_country']} ({case['receiving_currency']})"
        )
        logger.info(f"Amount: {format_currency(case['amount'], case['sending_currency'])}")

        try:
            result = provider.get_tariffs(**{k: v for k, v in case.items() if k != "description"})
            if result["success"]:
                logger.info("✓ SUCCESS")
                logger.info("-" * 30)
                logger.info(f"Exchange Rate: {result['exchange_rate']:.4f}")
                logger.info(f"Fee: {format_currency(result['fee'], case['sending_currency'])}")
                logger.info(
                    f"Send Amount: {format_currency(result['sending_amount'], case['sending_currency'])}"
                )
                logger.info(
                    f"Receive Amount: {format_currency(result['receiving_amount'], case['receiving_currency'])}"
                )
                logger.info(
                    f"Total Cost: {format_currency(result['total_cost'], case['sending_currency'])}"
                )
            else:
                logger.error("✗ FAILED")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
                log_api_response(result)
        except Exception as e:
            logger.error("✗ ERROR")
            logger.error(f"Type: {type(e).__name__}")
            logger.error(f"Details: {str(e)}")
            if isinstance(e, KoronaPayError):
                logger.error(f"API Status Code: {getattr(e, 'status_code', 'N/A')}")
                logger.error(f"API Response: {getattr(e, 'response', 'N/A')}")


def test_quotes():
    """Test quote retrieval with different small amounts."""
    provider = KoronaPayProvider()

    # Test cases for quotes (all under 1000 USD equivalent)
    test_cases = [
        # Send amount tests
        {
            "send_amount": 50.00,
            "send_currency": "EUR",
            "receive_currency": "TRY",
            "send_country": "DEU",
            "receive_country": "TUR",
            "description": "Send EUR 50 from Germany to Turkey",
        },
        {
            "send_amount": 75.00,
            "send_currency": "EUR",
            "receive_currency": "USD",
            "send_country": "SWE",
            "receive_country": "VNM",
            "description": "Send EUR 75 from Sweden to Vietnam",
        },
        # Receive amount tests
        {
            "receive_amount": 1000.00,
            "send_currency": "EUR",
            "receive_currency": "USD",
            "send_country": "POL",
            "receive_country": "PHL",
            "description": "Receive USD 1000 in Philippines from Poland",
        },
        {
            "receive_amount": 2000.00,
            "send_currency": "EUR",
            "receive_currency": "TRY",
            "send_country": "FRA",
            "receive_country": "TUR",
            "description": "Receive TRY 2000 in Turkey from France",
        },
    ]

    for case in test_cases:
        logger.info("\n" + "=" * 50)
        logger.info(f"Testing: {case['description']}")
        direction = "send" if "send_amount" in case else "receive"
        amount = case.get("send_amount" if direction == "send" else "receive_amount")
        currency = case["send_currency" if direction == "send" else "receive_currency"]
        logger.info(f"Type: {direction.title()} Amount Quote")
        logger.info(f"Amount: {format_currency(amount, currency)}")

        try:
            result = provider.get_quote(**{k: v for k, v in case.items() if k != "description"})
            if result["success"]:
                logger.info("✓ SUCCESS")
                logger.info("-" * 30)
                logger.info(
                    f"Send Amount: {format_currency(result['send_amount'], result['send_currency'])}"
                )
                logger.info(
                    f"Receive Amount: {format_currency(result['receive_amount'], result['receive_currency'])}"
                )
                logger.info(f"Exchange Rate: {result['rate']:.4f}")
                logger.info(f"Fee: {format_currency(result['fee'], result['send_currency'])}")
                logger.info(
                    f"Total Cost: {format_currency(result['total_cost'], result['send_currency'])}"
                )
            else:
                logger.error("✗ FAILED")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
                log_api_response(result)
        except Exception as e:
            logger.error("✗ ERROR")
            logger.error(f"Type: {type(e).__name__}")
            logger.error(f"Details: {str(e)}")
            if isinstance(e, KoronaPayError):
                logger.error(f"API Status Code: {getattr(e, 'status_code', 'N/A')}")
                logger.error(f"API Response: {getattr(e, 'response', 'N/A')}")


def test_exchange_rates():
    """Test exchange rate retrieval for different currency pairs."""
    provider = KoronaPayProvider()

    # Test cases for exchange rates
    test_cases = [
        # EUR to TRY from different countries
        {
            "send_currency": "EUR",
            "receive_currency": "TRY",
            "send_country": "DEU",
            "receive_country": "TUR",
            "description": "EUR/TRY Rate (Germany -> Turkey)",
        },
        {
            "send_currency": "EUR",
            "receive_currency": "TRY",
            "send_country": "FRA",
            "receive_country": "TUR",
            "description": "EUR/TRY Rate (France -> Turkey)",
        },
        # EUR to USD for different Asian countries
        {
            "send_currency": "EUR",
            "receive_currency": "USD",
            "send_country": "SWE",
            "receive_country": "VNM",
            "description": "EUR/USD Rate (Sweden -> Vietnam)",
        },
        {
            "send_currency": "EUR",
            "receive_currency": "USD",
            "send_country": "POL",
            "receive_country": "PHL",
            "description": "EUR/USD Rate (Poland -> Philippines)",
        },
        {
            "send_currency": "EUR",
            "receive_currency": "USD",
            "send_country": "CZE",
            "receive_country": "THA",
            "description": "EUR/USD Rate (Czech Republic -> Thailand)",
        },
    ]

    for case in test_cases:
        logger.info("\n" + "=" * 50)
        logger.info(f"Testing: {case['description']}")
        logger.info(f"Pair: {case['send_currency']}/{case['receive_currency']}")
        logger.info(f"Route: {case['send_country']} -> {case['receive_country']}")

        try:
            result = provider.get_exchange_rate(
                **{k: v for k, v in case.items() if k != "description"}
            )
            if result["success"]:
                logger.info("✓ SUCCESS")
                logger.info("-" * 30)
                logger.info(f"Rate: {result['rate']:.4f}")
                logger.info(f"Fee: {format_currency(result['fee'], case['send_currency'])}")
                logger.info(f"Timestamp: {result['timestamp']}")
            else:
                logger.error("✗ FAILED")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
                log_api_response(result)
        except Exception as e:
            logger.error("✗ ERROR")
            logger.error(f"Type: {type(e).__name__}")
            logger.error(f"Details: {str(e)}")
            if isinstance(e, KoronaPayError):
                logger.error(f"API Status Code: {getattr(e, 'status_code', 'N/A')}")
                logger.error(f"API Response: {getattr(e, 'response', 'N/A')}")


def main():
    """Run all live API tests."""
    logger.info("\nKoronaPay Live API Tests")
    logger.info("=" * 50)
    logger.info("Testing with amounts under 1000 USD equivalent")
    logger.info("Timestamp: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 50)

    try:
        logger.info("\n1. Testing Tariffs")
        logger.info("-" * 20)
        test_tariffs()

        logger.info("\n2. Testing Quotes")
        logger.info("-" * 20)
        test_quotes()

        logger.info("\n3. Testing Exchange Rates")
        logger.info("-" * 20)
        test_exchange_rates()

        logger.info("\n" + "=" * 50)
        logger.info("All tests completed!")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
