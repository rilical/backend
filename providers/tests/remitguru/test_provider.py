import logging
import sys
from decimal import Decimal

from providers.remitguru.integration import RemitGuruProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("test_remitguru")


def test_get_quote():
    """Test getting quotes for supported and unsupported corridors"""
    with RemitGuruProvider() as provider:
        # Test supported corridor: UK -> India (ONLY SUPPORTED CORRIDOR)
        logger.info("Testing UK -> India corridor (ONLY SUPPORTED CORRIDOR)")
        result = provider.get_quote(
            amount=Decimal("500"),
            source_currency="GBP",
            dest_currency="INR",
            source_country="GB",
            dest_country="IN",
        )
        logger.info(f"Result: {result}")

        # Test unsupported corridor to verify error handling
        logger.info("Testing US -> Pakistan corridor (EXPECTED TO FAIL - NOT SUPPORTED)")
        result = provider.get_quote(
            amount=Decimal("500"),
            source_currency="USD",
            dest_currency="PKR",
            source_country="US",
            dest_country="PK",
        )
        logger.info(f"Result: {result}")


def test_get_exchange_rate():
    """Test the exchange rate method"""
    with RemitGuruProvider() as provider:
        # Test supported corridor (ONLY SUPPORTED CORRIDOR)
        logger.info("Testing GBP -> INR exchange rate (ONLY SUPPORTED CORRIDOR)")
        result = provider.get_exchange_rate(
            send_amount=Decimal("500"),
            send_currency="GBP",
            target_currency="INR",
            receive_country="IN",
        )
        logger.info(f"Result: {result}")

        # Test unsupported corridor to verify error handling
        logger.info("Testing USD -> PKR exchange rate (EXPECTED TO FAIL - NOT SUPPORTED)")
        result = provider.get_exchange_rate(
            send_amount=Decimal("500"), send_currency="USD", target_currency="PKR"
        )
        logger.info(f"Result: {result}")


def test_supported_methods():
    """Test methods that return provider capabilities"""
    with RemitGuruProvider() as provider:
        countries = provider.get_supported_countries()
        currencies = provider.get_supported_currencies()

        logger.info(f"Supported countries: {countries} (Only GB->IN corridor is supported)")
        logger.info(f"Supported currencies: {currencies}")


if __name__ == "__main__":
    logger.info("Starting RemitGuru provider tests...")
    logger.info("NOTE: RemitGuru only supports UK (GBP) to India (INR) corridor")

    # Run all tests
    test_get_quote()
    test_get_exchange_rate()
    test_supported_methods()

    logger.info("Tests completed!")
