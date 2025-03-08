"""
Test suite to verify all providers return standardized response formats.

This test checks that provider responses conform to the expected format
with all required fields:
- provider_id
- success
- error_message
- send_amount
- source_currency
- destination_amount
- destination_currency
- exchange_rate
- fee
- payment_method
- delivery_method
- delivery_time_minutes
- timestamp
"""

import unittest
from decimal import Decimal
from datetime import datetime
import logging

# Import providers to test
from apps.providers.alansari.integration import AlAnsariProvider
from apps.providers.xoom.integration import XoomProvider
from apps.providers.orbitremit.integration import OrbitRemitProvider
from apps.providers.wise.integration import WiseProvider
from apps.providers.ria.integration import RIAProvider

# Disable logging during tests
logging.basicConfig(level=logging.ERROR)

class TestResponseStandardization(unittest.TestCase):
    """Test that providers conform to the expected response format."""
    
    def setUp(self):
        """Initialize provider instances."""
        self.alansari = AlAnsariProvider()
        self.xoom = XoomProvider()
        self.orbitremit = OrbitRemitProvider()
        self.wise = WiseProvider()
        self.ria = RIAProvider()
    
    def tearDown(self):
        """Clean up resources."""
        self.alansari.close()
        self.xoom.close()
        self.orbitremit.close()
        self.wise.close()
        self.ria.close()
    
    def test_standard_success_response_format(self):
        """Test that success responses have all required fields in the correct format."""
        # Create a mock successful response
        mock_success_response = {
            "success": True,
            "send_amount": 1000.0,
            "source_currency": "USD",
            "destination_amount": 55000.0,
            "destination_currency": "INR",
            "exchange_rate": 55.0,
            "fee": 5.0,
            "payment_method": "BANK_TRANSFER",
            "delivery_method": "BANK_DEPOSIT",
            "delivery_time_minutes": 1440,
            "timestamp": datetime.now().isoformat()
        }
        
        # Test each provider's standardize_response method
        providers = [
            (self.alansari, "alansari"),
            (self.xoom, "Xoom"),
            (self.orbitremit, "orbitremit"),
            (self.wise, "wise"),
            (self.ria, "ria")
        ]
        
        for provider, provider_id in providers:
            with self.subTest(provider=provider_id):
                standardized = provider.standardize_response(mock_success_response)
                
                # Check required fields
                self.assertTrue(isinstance(standardized, dict))
                self.assertEqual(standardized["provider_id"], provider_id)
                self.assertTrue(standardized["success"])
                self.assertIsNone(standardized["error_message"])
                self.assertEqual(standardized["send_amount"], 1000.0)
                self.assertEqual(standardized["source_currency"], "USD")
                self.assertEqual(standardized["destination_amount"], 55000.0)
                self.assertEqual(standardized["destination_currency"], "INR")
                self.assertEqual(standardized["exchange_rate"], 55.0)
                self.assertIsNotNone(standardized["fee"])
                self.assertIsNotNone(standardized["payment_method"])
                self.assertIsNotNone(standardized["delivery_method"])
                self.assertIsNotNone(standardized["delivery_time_minutes"])
                self.assertIsNotNone(standardized["timestamp"])
    
    def test_standard_error_response_format(self):
        """Test that error responses have all required fields."""
        # Create a mock error response
        mock_error_response = {
            "success": False,
            "error_message": "Test error message"
        }
        
        # Test each provider's standardize_response method
        providers = [
            (self.alansari, "alansari"),
            (self.xoom, "Xoom"),
            (self.orbitremit, "orbitremit"),
            (self.wise, "wise"),
            (self.ria, "ria")
        ]
        
        for provider, provider_id in providers:
            with self.subTest(provider=provider_id):
                standardized = provider.standardize_response(mock_error_response)
                
                # Check required fields for error response
                self.assertTrue(isinstance(standardized, dict))
                self.assertEqual(standardized["provider_id"], provider_id)
                self.assertFalse(standardized["success"])
                self.assertEqual(standardized["error_message"], "Test error message")
    
    def test_raw_response_inclusion(self):
        """Test that raw_response is included when provider_specific_data is True."""
        # Create a mock successful response with raw_response
        mock_response = {
            "success": True,
            "send_amount": 1000.0,
            "source_currency": "USD",
            "destination_amount": 55000.0,
            "destination_currency": "INR",
            "exchange_rate": 55.0,
            "raw_response": {"test": "data"}
        }
        
        # Test each provider's standardize_response method
        providers = [
            (self.alansari, "alansari"),
            (self.xoom, "Xoom"),
            (self.orbitremit, "orbitremit"),
            (self.wise, "wise"),
            (self.ria, "ria")
        ]
        
        for provider, provider_id in providers:
            with self.subTest(provider=provider_id):
                # Should not include raw_response when provider_specific_data is False (default)
                standardized = provider.standardize_response(mock_response)
                self.assertNotIn("raw_response", standardized)
                
                # Should include raw_response when provider_specific_data is True
                standardized = provider.standardize_response(mock_response, provider_specific_data=True)
                if "raw_response" in mock_response:
                    self.assertIn("raw_response", standardized)
                    self.assertEqual(standardized["raw_response"], {"test": "data"})


if __name__ == "__main__":
    unittest.main() 