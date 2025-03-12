"""
Test suite for Intermex integration.
"""

import unittest
from datetime import datetime
from decimal import Decimal

from apps.providers.intermex import IntermexProvider
from apps.providers.intermex.exceptions import IntermexError


class TestIntermexIntegration(unittest.TestCase):
    """Test cases for Intermex integration."""

    def setUp(self):
        """Set up test environment."""
        self.provider = IntermexProvider()
        self.test_amount = Decimal("1000.00")
        self.working_corridor = {
            "send_country": "US",
            "receive_country": "MX",
            "send_currency": "USD",
            "receive_currency": "MXN",
        }

    def test_working_corridor(self):
        """Test the known working corridor (US to Mexico)."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount), **self.working_corridor
        )
        self.assertTrue(quote["success"])
        self.assertIsNotNone(quote["exchange_rate"])
        self.assertIsNotNone(quote["receive_amount"])
        self.assertGreater(float(quote["exchange_rate"]), 0)

    def test_different_amounts(self):
        """Test quotes with different amounts."""
        amounts = [100.00, 500.00, 1000.00]
        for amount in amounts:
            quote = self.provider.get_quote(send_amount=amount, **self.working_corridor)
            self.assertTrue(quote["success"])
            self.assertGreater(quote["exchange_rate"], 0)

    def test_payment_methods(self):
        """Test different payment methods."""
        methods = ["debitCard", "bankAccount"]
        for method in methods:
            quote = self.provider.get_quote(
                send_amount=float(self.test_amount),
                payment_method=method,
                **self.working_corridor,
            )
            self.assertTrue(quote["success"])

    def test_receiving_methods(self):
        """Test different receiving methods."""
        methods = ["bankDeposit", "cashPickup"]
        for method in methods:
            quote = self.provider.get_quote(
                send_amount=float(self.test_amount),
                delivery_method=method,
                **self.working_corridor,
            )
            self.assertTrue(quote["success"])

    def test_invalid_currency(self):
        """Test with invalid currency."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            send_currency="INVALID",
            **{k: v for k, v in self.working_corridor.items() if k != "send_currency"},
        )
        self.assertFalse(quote["success"])
        self.assertIsNotNone(quote["error_message"])

    def test_invalid_country(self):
        """Test with invalid country."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            send_country="INVALID",
            **{k: v for k, v in self.working_corridor.items() if k != "send_country"},
        )
        self.assertFalse(quote["success"])
        self.assertIsNotNone(quote["error_message"])

    def test_invalid_payment_method(self):
        """Test with invalid payment method."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            payment_method="invalid_method",
            **self.working_corridor,
        )
        self.assertFalse(quote["success"])
        self.assertIsNotNone(quote["error_message"])

    def test_invalid_receiving_method(self):
        """Test with invalid receiving method."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            delivery_method="invalid_method",
            **self.working_corridor,
        )
        self.assertFalse(quote["success"])
        self.assertIsNotNone(quote["error_message"])

    def test_amount_validation(self):
        """Test amount validation."""
        # Test zero amount
        quote = self.provider.get_quote(send_amount=0.0, **self.working_corridor)
        self.assertFalse(quote["success"])
        self.assertIsNotNone(quote["error_message"])

        # Test negative amount
        quote = self.provider.get_quote(send_amount=-100.0, **self.working_corridor)
        self.assertFalse(quote["success"])
        self.assertIsNotNone(quote["error_message"])

        # Test very large amount
        quote = self.provider.get_quote(send_amount=1000000.0, **self.working_corridor)
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
        self.assertTrue(quote1["success"] and quote2["success"])
        self.assertEqual(quote1["exchange_rate"], quote2["exchange_rate"])

    def test_raw_response(self):
        """Test including raw response in quote."""
        quote = self.provider.get_quote(
            send_amount=float(self.test_amount),
            **self.working_corridor,
            include_raw=True,
        )
        self.assertTrue(quote["success"])
        self.assertIsNotNone(quote["raw_response"])

    def test_supported_methods(self):
        """Test getting supported methods and currencies."""
        # Test getting supported countries
        countries = self.provider.get_supported_countries()
        self.assertIsInstance(countries, list)
        self.assertIn("US", countries)
        self.assertIn("MX", countries)

        # Test getting supported currencies
        currencies = self.provider.get_supported_currencies()
        self.assertIsInstance(currencies, list)
        self.assertIn("USD", currencies)
        self.assertIn("MXN", currencies)

    def test_unsupported_corridors(self):
        """Test corridors that are not supported by the API."""
        unsupported_corridors = [
            {
                "send_country": "GB",
                "receive_country": "IN",
                "send_currency": "GBP",
                "receive_currency": "INR",
            },
            {
                "send_country": "FR",
                "receive_country": "VN",
                "send_currency": "EUR",
                "receive_currency": "VND",
            },
            {
                "send_country": "DE",
                "receive_country": "PH",
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


if __name__ == "__main__":
    unittest.main()
