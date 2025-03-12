"""
KoronaPay Provider Tests

This module contains comprehensive tests for the KoronaPay remittance provider integration.
Tests cover API functionality with proper mocking for offline testing.
"""

import json
import logging
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from .exceptions import (
    KoronaPayAPIError,
    KoronaPayAuthError,
    KoronaPayCorridorError,
    KoronaPayError,
    KoronaPayPaymentMethodError,
    KoronaPayValidationError,
)
from .integration import KoronaPayProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestKoronaPayBase(unittest.TestCase):
    """Base test class with common utilities."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.provider = KoronaPayProvider()
        cls.mock_session = MagicMock()
        cls.test_pairs = [
            # Common European corridors
            ("EUR", "USD", "ESP", "TUR"),  # Spain to Turkey
            ("EUR", "IDR", "DEU", "IDN"),  # Germany to Indonesia
            ("EUR", "USD", "FRA", "PHL"),  # France to Philippines
            ("EUR", "THB", "ITA", "THA"),  # Italy to Thailand
            # Different source countries
            ("EUR", "USD", "GBR", "TUR"),  # UK to Turkey
            ("EUR", "IDR", "NLD", "IDN"),  # Netherlands to Indonesia
            ("EUR", "USD", "POL", "PHL"),  # Poland to Philippines
            # Different payment methods
            ("EUR", "TRY", "ESP", "TUR"),  # Spain to Turkey (TRY)
            ("EUR", "USD", "DEU", "IDN"),  # Germany to Indonesia (USD)
        ]

    def setUp(self):
        """Set up each test."""
        self.provider.session = self.mock_session


class TestKoronaPayTariffs(TestKoronaPayBase):
    """Test tariff functionality."""

    def test_get_tariffs_success(self):
        """Test successful tariff retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sendingAmount": 312300,
                "sendingCurrency": {"code": "EUR"},
                "receivingAmount": 318193,
                "receivingCurrency": {"code": "USD"},
                "exchangeRate": 1.0192,
                "sendingCommission": 95,
                "sendingTransferCommission": 95,
            }
        ]

        self.mock_session.get.return_value = mock_response

        result = self.provider.get_tariffs(
            sending_country="ESP",
            receiving_country="TUR",
            sending_currency="EUR",
            receiving_currency="USD",
            amount=Decimal("3123.00"),
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["sending_currency"], "EUR")
        self.assertEqual(result["receiving_currency"], "USD")
        self.assertEqual(float(result["exchange_rate"]), 1.0192)
        self.assertEqual(float(result["fee"]), 0.95)

    def test_get_tariffs_multiple_corridors(self):
        """Test tariff retrieval for multiple corridors."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sendingAmount": 100000,
                "sendingCurrency": {"code": "EUR"},
                "receivingAmount": 101920,
                "receivingCurrency": {"code": "USD"},
                "exchangeRate": 1.0192,
                "sendingCommission": 95,
                "sendingTransferCommission": 95,
            }
        ]

        self.mock_session.get.return_value = mock_response

        # Test different European source countries
        test_source_countries = ["DEU", "FRA", "ITA", "ESP", "GBR"]
        for source_country in test_source_countries:
            result = self.provider.get_tariffs(
                sending_country=source_country,
                receiving_country="IDN",
                sending_currency="EUR",
                receiving_currency="IDR",
                amount=Decimal("1000.00"),
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["sending_currency"], "EUR")

    def test_get_tariffs_invalid_currency(self):
        """Test tariff retrieval with invalid currency."""
        with self.assertRaises(KoronaPayValidationError):
            self.provider.get_tariffs(
                sending_country="ESP",
                receiving_country="TUR",
                sending_currency="XXX",  # Invalid currency
                receiving_currency="USD",
                amount=Decimal("1000.00"),
            )

    def test_get_tariffs_api_error(self):
        """Test handling of API errors."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad Request"}

        self.mock_session.get.return_value = mock_response

        with self.assertRaises(KoronaPayAPIError):
            self.provider.get_tariffs(
                sending_country="ESP",
                receiving_country="TUR",
                sending_currency="EUR",
                receiving_currency="USD",
                amount=Decimal("1000.00"),
            )


class TestKoronaPayQuotes(TestKoronaPayBase):
    """Test quote functionality."""

    def test_get_quote_send_amount(self):
        """Test getting quote with send amount."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sendingAmount": 100000,
                "receivingAmount": 101920,
                "exchangeRate": 1.0192,
                "sendingCommission": 95,
            }
        ]

        self.mock_session.get.return_value = mock_response

        result = self.provider.get_quote(
            send_amount=1000.00, send_currency="EUR", receive_currency="USD"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["send_currency"], "EUR")
        self.assertEqual(result["receive_currency"], "USD")
        self.assertGreater(result["rate"], 0)

    def test_get_quote_receive_amount(self):
        """Test getting quote with receive amount."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sendingAmount": 98115,
                "receivingAmount": 100000,
                "exchangeRate": 1.0192,
                "sendingCommission": 95,
            }
        ]

        self.mock_session.get.return_value = mock_response

        result = self.provider.get_quote(
            receive_amount=1000.00, send_currency="EUR", receive_currency="USD"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["send_currency"], "EUR")
        self.assertEqual(result["receive_currency"], "USD")
        self.assertGreater(result["rate"], 0)

    def test_get_quote_validation(self):
        """Test quote validation."""
        with self.assertRaises(KoronaPayValidationError):
            self.provider.get_quote(
                send_amount=None,
                receive_amount=None,
                send_currency="EUR",
                receive_currency="USD",
            )


class TestKoronaPayRates(TestKoronaPayBase):
    """Test exchange rate functionality."""

    def test_get_exchange_rate(self):
        """Test getting exchange rates."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sendingAmount": 100000,
                "receivingAmount": 101920,
                "exchangeRate": 1.0192,
                "sendingCommission": 95,
            }
        ]

        self.mock_session.get.return_value = mock_response

        result = self.provider.get_exchange_rate(
            send_currency="EUR", receive_currency="USD"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["source_currency"], "EUR")
        self.assertEqual(result["target_currency"], "USD")
        self.assertEqual(result["rate"], 1.0192)

    def test_get_exchange_rate_error(self):
        """Test exchange rate error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}

        self.mock_session.get.return_value = mock_response

        result = self.provider.get_exchange_rate(
            send_currency="EUR", receive_currency="USD"
        )

        self.assertFalse(result["success"])
        self.assertIn("error", result)


class TestKoronaPayValidation(TestKoronaPayBase):
    """Test input validation."""

    def test_validate_currency(self):
        """Test currency validation."""
        self.assertEqual(self.provider._validate_currency("EUR"), "978")
        self.assertEqual(self.provider._validate_currency("USD"), "840")
        self.assertEqual(self.provider._validate_currency("TRY"), "949")

        with self.assertRaises(KoronaPayValidationError):
            self.provider._validate_currency("XXX")

    def test_validate_country(self):
        """Test country validation."""
        self.assertEqual(self.provider._validate_country("ESP"), "ESP")
        self.assertEqual(self.provider._validate_country("TUR"), "TUR")

        with self.assertRaises(KoronaPayValidationError):
            self.provider._validate_country("XXX")

    def test_validate_payment_method(self):
        """Test payment method validation."""
        self.assertEqual(
            self.provider._validate_payment_method("debit_card"), "debitCard"
        )
        self.assertEqual(
            self.provider._validate_payment_method("bank_account"), "bankAccount"
        )

        with self.assertRaises(KoronaPayPaymentMethodError):
            self.provider._validate_payment_method("invalid_method")


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
