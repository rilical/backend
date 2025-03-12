#!/usr/bin/env python
"""
Comprehensive test suite for KoronaPay integration.
Tests various scenarios including supported corridors, payment methods, and error cases.
"""

import logging
import sys
import unittest
from decimal import Decimal
from typing import Any, Dict

from apps.providers.koronapay.exceptions import (
    KoronaPayAPIError,
    KoronaPayError,
    KoronaPayValidationError,
)
from apps.providers.koronapay.integration import KoronaPayProvider
from apps.providers.koronapay.mapping import (
    get_supported_countries,
    get_supported_currencies,
    get_supported_payment_methods,
    get_supported_receiving_methods,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestKoronaPayIntegration(unittest.TestCase):
    """Test suite for KoronaPay integration."""

    def setUp(self):
        """Set up test environment."""
        self.provider = KoronaPayProvider()

        # Test data
        self.test_amount = Decimal("100.00")
        self.test_amounts = [
            Decimal("50.00"),
            Decimal("100.00"),
            Decimal("500.00"),
            Decimal("1000.00"),
        ]

        # Known working corridor
        self.working_corridor = {
            "send_country": "ESP",
            "receive_country": "TUR",
            "send_currency": "EUR",
            "receive_currency": "TRY",
        }

    def test_working_corridor(self):
        """Test the known working corridor (Spain to Turkey)."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount), **self.working_corridor
        )

        self.assertTrue(quote["success"])
        self.assertEqual(quote["send_currency"], "EUR")
        self.assertEqual(quote["receive_currency"], "TRY")
        self.assertGreater(quote["exchange_rate"], 0)
        self.assertGreater(quote["fee"], 0)
        self.assertGreater(quote["receive_amount"], 0)
        self.assertIsNone(quote["delivery_time_minutes"])
        self.assertIsNone(quote["error_message"])

    def test_different_amounts(self):
        """Test quotes with different amounts."""
        for amount in self.test_amounts:
            quote = self.provider.get_quote(
                send_amount=float(amount), **self.working_corridor
            )

            self.assertTrue(quote["success"])
            self.assertEqual(quote["send_amount"], float(amount))
            self.assertGreater(quote["receive_amount"], 0)
            self.assertGreater(quote["exchange_rate"], 0)
            self.assertIsNone(quote["error_message"])

    def test_payment_methods(self):
        """Test different payment methods."""
        # Only test debit_card as bank_account is not supported in test environment
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            payment_method="debit_card",
            **self.working_corridor,
        )

        self.assertTrue(quote["success"])
        self.assertGreater(quote["receive_amount"], 0)
        self.assertIsNone(quote["error_message"])

    def test_receiving_methods(self):
        """Test different receiving methods."""
        receiving_methods = ["cash", "card"]

        for method in receiving_methods:
            quote = self.provider.get_quote(
                send_amount=float(self.test_amount),
                receiving_method=method,
                **self.working_corridor,
            )

            self.assertTrue(quote["success"])
            self.assertGreater(quote["receive_amount"], 0)
            self.assertIsNone(quote["error_message"])

    def test_invalid_currency(self):
        """Test with invalid currency."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            send_currency="INVALID",
            receive_currency="TRY",
            send_country="ESP",
            receive_country="TUR",
        )

        self.assertFalse(quote["success"])
        self.assertIn("Unsupported currency", quote["error_message"])

    def test_invalid_country(self):
        """Test with invalid country."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            send_currency="EUR",
            receive_currency="TRY",
            send_country="INVALID",
            receive_country="TUR",
        )

        self.assertFalse(quote["success"])
        self.assertIn("Unsupported country", quote["error_message"])

    def test_invalid_payment_method(self):
        """Test with invalid payment method."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            payment_method="invalid_method",
            **self.working_corridor,
        )

        self.assertFalse(quote["success"])
        self.assertIn("Unsupported payment method", quote["error_message"])

    def test_invalid_receiving_method(self):
        """Test with invalid receiving method."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            receiving_method="invalid_method",
            **self.working_corridor,
        )

        self.assertFalse(quote["success"])
        self.assertIn("Unsupported receiving method", quote["error_message"])

    def test_unsupported_corridors(self):
        """Test corridors that are not supported by the API."""
        unsupported_corridors = [
            {
                "send_country": "ESP",
                "receive_country": "IDN",
                "send_currency": "EUR",
                "receive_currency": "IDR",
            },
            {
                "send_country": "ESP",
                "receive_country": "VNM",
                "send_currency": "EUR",
                "receive_currency": "VND",
            },
            {
                "send_country": "ESP",
                "receive_country": "PHL",
                "send_currency": "EUR",
                "receive_currency": "PHP",
            },
        ]

        for corridor in unsupported_corridors:
            quote = self.provider.get_quote(
                send_amount=float(self.test_amount), **corridor
            )

            self.assertFalse(quote["success"])
            self.assertIsNotNone(quote["error_message"])

    def test_exchange_rate_consistency(self):
        """Test that exchange rates are consistent for the same amount."""
        quote1 = self.provider.get_quote(
            send_amount=float(self.test_amount), **self.working_corridor
        )

        quote2 = self.provider.get_quote(
            send_amount=float(self.test_amount), **self.working_corridor
        )

        self.assertTrue(quote1["success"])
        self.assertTrue(quote2["success"])
        self.assertAlmostEqual(
            quote1["exchange_rate"], quote2["exchange_rate"], places=4
        )

    def test_amount_validation(self):
        """Test amount validation."""
        invalid_amounts = [
            Decimal("-100.00"),
            Decimal("0.00"),
            Decimal("1000000000.00"),  # Very large amount
        ]

        for amount in invalid_amounts:
            quote = self.provider.get_quote(
                send_amount=float(amount), **self.working_corridor
            )

            self.assertFalse(quote["success"])
            self.assertIsNotNone(quote["error_message"])

    def test_supported_methods(self):
        """Test getting supported methods and currencies."""
        currencies = self.provider.get_supported_currencies()
        countries = self.provider.get_supported_countries()
        payment_methods = self.provider.get_supported_payment_methods()
        receiving_methods = self.provider.get_supported_receiving_methods()

        self.assertIsInstance(currencies, list)
        self.assertIsInstance(countries, list)
        self.assertIsInstance(payment_methods, list)
        self.assertIsInstance(receiving_methods, list)

        self.assertGreater(len(currencies), 0)
        self.assertGreater(len(countries), 0)
        self.assertGreater(len(payment_methods), 0)
        self.assertGreater(len(receiving_methods), 0)

        # Test that working corridor currencies and countries are supported
        self.assertIn(self.working_corridor["send_currency"], currencies)
        self.assertIn(self.working_corridor["receive_currency"], currencies)
        self.assertIn(self.working_corridor["send_country"], countries)
        self.assertIn(self.working_corridor["receive_country"], countries)

    def test_raw_response(self):
        """Test including raw response in quote."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            include_raw=True,
            **self.working_corridor,
        )

        self.assertTrue(quote["success"])
        self.assertIsNotNone(quote["raw_response"])
        self.assertIsInstance(quote["raw_response"], dict)


def main():
    """Run the test suite."""
    try:
        unittest.main(verbosity=2)
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
