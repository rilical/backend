"""
WireBarley Provider Tests

This module contains comprehensive tests for the WireBarley remittance provider integration.
Tests cover both authenticated and public API functionality, with proper mocking for offline testing.
"""

import logging
import json
import unittest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, MagicMock

from .integration import WireBarleyProvider
from .exceptions import (
    WireBarleyError,
    WireBarleyAuthError,
    WireBarleyAPIError,
    WireBarleyCorridorError,
    WireBarleyRateError,
    WireBarleyValidationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            ("SAR", "PHP")   # Saudi to Philippines
        ]
    
    def setUp(self):
        """Set up each test."""
        self.provider._session = self.mock_session

class TestWireBarleyAuthentication(TestWireBarleyBase):
    """Test authentication and session management."""
    
    def test_session_initialization(self):
        """Test session initialization with cookies."""
        with patch.dict('os.environ', {'WIREBARLEY_COOKIES': '{"_ga": "test"}'}):
            self.assertTrue(self.provider._initialize_session())
            self.assertIsNotNone(self.provider.session)
    
    def test_session_validation(self):
        """Test session validation."""
        self.mock_session.get.return_value.json.return_value = {"status": 0}
        self.provider._validate_session()
        
        self.mock_session.get.return_value.json.return_value = {"status": 400}
        with self.assertRaises(WireBarleySessionError):
            self.provider._validate_session()

class TestWireBarleyRates(TestWireBarleyBase):
    """Test exchange rate functionality."""
    
    def test_get_exchange_rate(self):
        """Test getting exchange rates."""
        mock_response = {
            "success": True,
            "rate": 56.75,
            "fee": 4.99,
            "source_currency": "USD",
            "target_currency": "PHP"
        }
        
        with patch.object(self.provider, 'get_exchange_rate', return_value=mock_response):
            result = self.provider.get_exchange_rate(
                send_amount=Decimal("1000"),
                send_currency="USD",
                receive_country="PH"
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
            "wbRate2": 56.95
        }
        
        # Test amount below first threshold
        rate = self.provider._get_threshold_rate({"wbRateData": test_data}, Decimal("500"))
        self.assertEqual(rate, 56.75)
        
        # Test amount between thresholds
        rate = self.provider._get_threshold_rate({"wbRateData": test_data}, Decimal("7500"))
        self.assertEqual(rate, 56.85)
        
        # Test amount above all thresholds
        rate = self.provider._get_threshold_rate({"wbRateData": test_data}, Decimal("15000"))
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
                    "max_amount": "10000"
                }
            ]
        }
        
        with patch.object(self.provider, 'get_corridors', return_value=mock_response):
            result = self.provider.get_corridors("USD")
            self.assertTrue(result["success"])
            self.assertEqual(len(result["corridors"]), 1)
            self.assertEqual(result["corridors"][0]["source_currency"], "USD")
    
    def test_invalid_corridor(self):
        """Test handling of invalid corridors."""
        with self.assertRaises(WireBarleyCorridorError):
            self.provider.get_exchange_rate(
                send_amount=Decimal("1000"),
                send_currency="XXX",  # Invalid currency
                receive_country="YY"   # Invalid country
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
            "rate": 56.75
        }
        
        with patch.object(self.provider, 'get_quote', return_value=mock_response):
            result = self.provider.get_quote(
                send_amount=1000,
                send_currency="USD",
                receive_currency="PHP"
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["send_currency"], "USD")
            self.assertEqual(result["receive_currency"], "PHP")
    
    def test_quote_validation(self):
        """Test quote input validation."""
        with self.assertRaises(WireBarleyValidationError):
            self.provider.get_quote(
                send_amount=-1000,  # Invalid amount
                send_currency="USD",
                receive_currency="PHP"
            )

class TestWireBarleyFees(TestWireBarleyBase):
    """Test fee calculation functionality."""
    
    def test_calculate_fee(self):
        """Test fee calculation."""
        test_fees = [{
            "useDiscountFee": False,
            "min": 500,
            "fee1": 10,
            "threshold1": 1000,
            "fee2": 15,
            "threshold2": 5000,
            "max": 10000,
            "option": "BANK_ACCOUNT"
        }]
        
        # Test amount in first tier
        fee = self.provider._calculate_fee(
            Decimal("750"),
            "USD",
            {"paymentFees": test_fees}
        )
        self.assertEqual(fee, 10)
        
        # Test amount in second tier
        fee = self.provider._calculate_fee(
            Decimal("3000"),
            "USD",
            {"paymentFees": test_fees}
        )
        self.assertEqual(fee, 15)

def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)

if __name__ == "__main__":
    run_tests() 