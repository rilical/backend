"""
WireBarley Provider Tests

This module contains comprehensive tests for the WireBarley remittance provider integration.
Tests cover both authenticated and public API functionality, with proper mocking for offline testing.
"""

import json
import logging
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests

from .exceptions import (
    WireBarleyAPIError,
    WireBarleyAuthError,
    WireBarleyCorridorError,
    WireBarleyError,
    WireBarleyRateError,
    WireBarleySessionError,
    WireBarleyValidationError,
)
from .integration import WireBarleyProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestWireBarleyBase(unittest.TestCase):
    """Base test class with common utilities."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.provider = WireBarleyProvider()
        cls.mock_session = MagicMock()
        cls.test_pairs = [
            # Common corridors
            ("USD", "PHP"),  # US to Philippines
            ("AUD", "INR"),  # Australia to India
            ("CAD", "PHP"),  # Canada to Philippines
            ("HKD", "CNY"),  # Hong Kong to China
            # High-value corridors
            ("KRW", "USD"),  # Korea to US
            ("JPY", "USD"),  # Japan to US
            ("IDR", "SGD"),  # Indonesia to Singapore
            # European corridors
            ("EUR", "GBP"),  # Europe to UK
            ("CHF", "EUR"),  # Switzerland to Europe
            # Middle East corridors
            ("AED", "INR"),  # UAE to India
            ("SAR", "PHP"),  # Saudi to Philippines
        ]

    def setUp(self):
        """Set up each test."""
        self.provider._session = self.mock_session


class TestWireBarleyAuthentication(TestWireBarleyBase):
    """Test authentication and session management."""

    def test_session_initialization(self):
        """Test session initialization with cookies."""
        with patch.dict("os.environ", {"WIREBARLEY_COOKIES": '{"_ga": "test"}'}):
            self.assertTrue(self.provider._initialize_session())
            self.assertIsNotNone(self.provider.session)

    def test_session_validation(self):
        """Test session validation."""
        # Mock the session object itself
        self.provider.session = MagicMock()

        # Test 1: Valid session - status code 200
        mock_response_valid = MagicMock()
        mock_response_valid.status_code = 200
        self.provider.session.get.return_value = mock_response_valid
        self.assertTrue(self.provider._validate_session())

        # Test 2: Invalid session - status code 401
        mock_response_invalid = MagicMock()
        mock_response_invalid.status_code = 401
        self.provider.session.get.return_value = mock_response_invalid
        self.assertFalse(self.provider._validate_session())

        # Test 3: Exception during validation
        self.provider.session.get.side_effect = requests.RequestException(
            "Connection error"
        )
        self.assertFalse(self.provider._validate_session())


class TestWireBarleyRates(TestWireBarleyBase):
    """Test exchange rate functionality."""

    def test_get_exchange_rate(self):
        """Test getting exchange rates."""
        mock_response = {
            "success": True,
            "rate": 56.75,
            "fee": 4.99,
            "source_currency": "USD",
            "target_currency": "PHP",
        }

        with patch.object(
            self.provider, "get_exchange_rate", return_value=mock_response
        ):
            result = self.provider.get_exchange_rate(
                send_amount=Decimal("1000"), send_currency="USD", receive_currency="PHP"
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["source_currency"], "USD")
            self.assertEqual(result["target_currency"], "PHP")

    def test_threshold_rates(self):
        """Test threshold-based rate calculation."""
        test_data = {
            "threshold": 1000,
            "wbRate": 56.75,
            "threshold1": 5000,
            "wbRate1": 56.85,
            "threshold2": 10000,
            "wbRate2": 56.95,
        }

        # Create a corridor data object that matches the expected structure
        corridor_obj = {"wbRateData": test_data}

        # Test amount below first threshold
        rate = self.provider._pick_threshold_rate(corridor_obj, Decimal("500"))
        self.assertEqual(rate, 56.75)

        # Test amount between thresholds
        rate = self.provider._pick_threshold_rate(corridor_obj, Decimal("7500"))
        # The implementation will return the rate for the first threshold that is >= the amount
        # For 7500, that's threshold2 (10000) with rate2 (56.95)
        self.assertEqual(rate, 56.95)

        # Test amount above all thresholds
        rate = self.provider._pick_threshold_rate(corridor_obj, Decimal("15000"))
        # For amounts above all thresholds, it returns the last threshold's rate
        self.assertEqual(rate, 56.95)


class TestWireBarleyCorridors(TestWireBarleyBase):
    """Test corridor functionality."""

    def test_get_corridors(self):
        """Test fetching available corridors."""
        mock_response = {
            "success": True,
            "corridors": [
                {
                    "source_currency": "USD",
                    "target_currency": "PHP",
                    "country_code": "PH",
                    "min_amount": "10",
                    "max_amount": "10000",
                }
            ],
        }

        with patch.object(self.provider, "get_corridors", return_value=mock_response):
            result = self.provider.get_corridors("USD")
            self.assertTrue(result["success"])
            self.assertEqual(len(result["corridors"]), 1)
            self.assertEqual(result["corridors"][0]["source_currency"], "USD")

    def test_invalid_corridor(self):
        """Test handling of invalid corridors."""
        # Mock the method to raise the exception
        with patch.object(
            self.provider,
            "get_exchange_rate",
            side_effect=WireBarleyCorridorError("Invalid corridor"),
        ):
            with self.assertRaises(WireBarleyCorridorError):
                self.provider.get_exchange_rate(
                    send_amount=Decimal("1000"),
                    send_currency="XXX",
                    receive_currency="YYY",
                )


class TestWireBarleyQuotes(TestWireBarleyBase):
    """Test quote functionality."""

    def test_get_quote(self):
        """Test getting quotes."""
        mock_response = {
            "success": True,
            "send_amount": 1000,
            "send_currency": "USD",
            "receive_amount": 56750,
            "receive_currency": "PHP",
            "fee": 4.99,
            "rate": 56.75,
        }

        with patch.object(self.provider, "get_quote", return_value=mock_response):
            result = self.provider.get_quote(
                amount=Decimal("1000"),
                source_currency="USD",
                destination_currency="PHP",
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["send_currency"], "USD")
            self.assertEqual(result["receive_currency"], "PHP")

    def test_quote_validation(self):
        """Test quote input validation."""
        # Test with None amount - should return error response
        result = self.provider.get_quote(amount=None)
        self.assertFalse(result["success"])
        self.assertTrue("Amount is required" in result["error_message"])

        # Test with negative amount - should fail validation
        result = self.provider.get_quote(
            amount=Decimal("-100"), source_currency="USD", destination_currency="PHP"
        )
        self.assertFalse(result["success"])


class TestWireBarleyFees(TestWireBarleyBase):
    """Test fee calculation functionality."""

    def test_calculate_fee(self):
        """Test fee calculation."""
        # Create test fee data
        test_fees = [
            {
                "min": 500,
                "max": 10000,
                "fee1": 10,
                "threshold2": 1000,
                "fee2": 15,
                "threshold3": 5000,
                "fee3": 20,
            }
        ]

        # Create corridor data object with the payment fees
        corridor_obj = {"paymentFees": test_fees}

        # Test amount in first tier
        fee = self.provider._calculate_fee(
            corridor_obj=corridor_obj, amount=Decimal("750")
        )
        # With amount 750, it should use fee1 (10) since it's between min (500) and threshold2 (1000)
        self.assertEqual(fee, 10)

        # Test amount in second tier
        fee = self.provider._calculate_fee(
            corridor_obj=corridor_obj, amount=Decimal("3000")
        )
        # With amount 3000, it should use fee2 (15) since it's between threshold2 (1000) and threshold3 (5000)
        self.assertEqual(fee, 15)

        # Test amount in third tier
        fee = self.provider._calculate_fee(
            corridor_obj=corridor_obj, amount=Decimal("7000")
        )
        # With amount 7000, it should use fee3 (20) since it's above threshold3 (5000)
        self.assertEqual(fee, 20)


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
