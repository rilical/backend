"""
Wise Money Transfer API Tests

HOW TO RUN:
python -m unittest apps.providers.wise.tests
python -m unittest apps.providers.wise.tests.TestWiseProviderRealAPI.test_discover_supported_methods
"""

import json
import logging
import os
import traceback
import unittest
from datetime import datetime
from decimal import Decimal

from apps.providers.wise.integration import WiseProvider
from apps.providers.wise.exceptions import (
    WiseError,
    WiseAuthenticationError,
    WiseConnectionError,
    WiseValidationError,
    WiseRateLimitError
)


class TestWiseProviderRealAPI(unittest.TestCase):
    """Real-API tests for Wise Money Transfer Provider.
    
    This class contains tests that make real API calls to the Wise Money Transfer API.
    These tests verify the functionality of the integration with actual API responses.
    
    Note: Running these tests will make real API calls and may consume API quota or incur costs.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment before running any tests in this class.
        
        Creates necessary directories for test outputs and configures logging.
        """
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        
        # Create results directory if it doesn't exist
        cls.results_dir = "test_results_wise"
        cls.logs_dir = os.path.join(cls.results_dir, "logs")
        
        os.makedirs(cls.results_dir, exist_ok=True)
        os.makedirs(cls.logs_dir, exist_ok=True)
        
        # Set up logging to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(cls.logs_dir, f"wise_tests_{timestamp}.log")
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add the file handler to the logger
        cls.logger.addHandler(file_handler)
        cls.logger.info("Test run started. Logs will be saved to %s", log_file)
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a test-specific logger
        self.test_name = self._testMethodName
        self.test_logger = logging.getLogger(f"{__name__}.{self.test_name}")
        
        # Set up logging to file for this test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.logs_dir, f"{self.test_name}_{timestamp}.log")
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add the file handler to the logger
        self.test_logger.addHandler(file_handler)
        
        # Initialize the provider
        self.api_key = os.environ.get("WISE_API_KEY")
        self.provider = WiseProvider(api_key=self.api_key)
        
        # For unauthenticated tests, override the _create_quote method
        if not self.api_key:
            self.provider._create_quote = self.provider._create_unauthenticated_quote
        
        self.logger.info(f"=== Starting test: {self.test_name} ===")
    
    def tearDown(self):
        """Clean up after each test."""
        # Close the provider
        if hasattr(self, 'provider'):
            self.provider.close()
        
        # Close the test logger
        for handler in self.test_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.test_logger.info(f"Test logs saved to: {handler.baseFilename}")
                handler.close()
                self.test_logger.removeHandler(handler)
        
        self.logger.info(f"=== Ending test: {self.test_name} ===")
    
    def test_get_exchange_rate_real(self):
        """Test getting real exchange rate data from Wise API."""
        self.test_logger.info("Testing real exchange rate lookup from Wise US to MX")
        
        try:
            # Get exchange rate for USD to MXN
            rate_data = self.provider.get_exchange_rate(
                send_amount=Decimal("100.00"),
                send_currency="USD",
                receive_currency="MXN"
            )
            
            # Verify the response
            self.assertTrue(rate_data["success"])
            self.assertEqual(rate_data["source_currency"], "USD")
            self.assertEqual(rate_data["destination_currency"], "MXN")
            self.assertGreater(rate_data["exchange_rate"], 0)
            self.assertGreater(rate_data["destination_amount"], 0)
            
            # Log the results
            self.test_logger.info(f"Exchange rate: {rate_data['exchange_rate']}")
            self.test_logger.info(f"Fee: {rate_data['fee']}")
            self.test_logger.info(f"Destination amount: {rate_data['destination_amount']}")
            
        except Exception as e:
            self.test_logger.error(f"Error in test: {str(e)}")
            self.test_logger.error(traceback.format_exc())
            raise
    
    def test_common_corridors(self):
        """Test exchange rates for common currency corridors."""
        self.test_logger.info("Testing 5 common corridors")
        
        # Define test corridors
        corridors = [
            {"send_country": "US", "send_currency": "USD", "receive_country": "MX", "receive_currency": "MXN", "amount": "100"},
            {"send_country": "US", "send_currency": "USD", "receive_country": "PH", "receive_currency": "PHP", "amount": "200"},
            {"send_country": "GB", "send_currency": "GBP", "receive_country": "IN", "receive_currency": "INR", "amount": "300"},
            {"send_country": "DE", "send_currency": "EUR", "receive_country": "TR", "receive_currency": "TRY", "amount": "400"},
            {"send_country": "CA", "send_currency": "CAD", "receive_country": "IN", "receive_currency": "INR", "amount": "500"}
        ]
        
        results = []
        
        for corridor in corridors:
            send_country = corridor["send_country"]
            send_currency = corridor["send_currency"]
            receive_country = corridor["receive_country"]
            receive_currency = corridor["receive_currency"]
            amount = Decimal(corridor["amount"])
            
            self.test_logger.info(f"Testing corridor: {send_country}({send_currency})->{receive_country} with amount {amount}")
            
            try:
                # Get exchange rate
                rate_data = self.provider.get_exchange_rate(
                    send_amount=amount,
                    send_currency=send_currency,
                    receive_currency=receive_currency
                )
                
                # Add to results
                results.append({
                    "corridor": f"{send_country}({send_currency})->{receive_country}({receive_currency})",
                    "amount": str(amount),
                    "success": rate_data["success"],
                    "exchange_rate": rate_data.get("exchange_rate"),
                    "fee": rate_data.get("fee"),
                    "destination_amount": rate_data.get("destination_amount"),
                    "error": rate_data.get("error_message")
                })
                
                # Log the results
                if rate_data["success"]:
                    self.test_logger.info(f"Exchange rate: {rate_data['exchange_rate']}")
                    self.test_logger.info(f"Fee: {rate_data['fee']}")
                    self.test_logger.info(f"Destination amount: {rate_data['destination_amount']}")
                else:
                    self.test_logger.warning(f"Failed to get rate: {rate_data.get('error_message')}")
                
            except Exception as e:
                self.test_logger.error(f"Error testing corridor {send_country}({send_currency})->{receive_country}: {str(e)}")
                self.test_logger.error(traceback.format_exc())
                results.append({
                    "corridor": f"{send_country}({send_currency})->{receive_country}({receive_currency})",
                    "amount": str(amount),
                    "success": False,
                    "error": str(e)
                })
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.results_dir, f"WISE_CORRIDORS_{timestamp}.json")
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.test_logger.info(f"Results saved to: {results_file}")
    
    def test_quotes_target_amount(self):
        """Test quotes with target amount specified instead of source amount."""
        self.test_logger.info("Testing quotes with target amount specified")
        
        try:
            # Create a quote with target amount
            quote_data = self.provider._create_unauthenticated_quote(
                source_currency="EUR",
                target_currency="USD",
                target_amount=100.0
            )
            
            # Verify the response
            self.assertIn("paymentOptions", quote_data)
            self.assertEqual(quote_data["targetCurrency"], "USD")
            self.assertEqual(quote_data["sourceCurrency"], "EUR")
            
            # The sourceAmount might not be present in all responses
            # so we'll check for the rate instead
            self.assertIsNotNone(quote_data.get("rate"))
            
            # Log the results
            self.test_logger.info(f"Source amount: {quote_data.get('sourceAmount', 'Not provided')}")
            self.test_logger.info(f"Target amount: 100.0")
            self.test_logger.info(f"Exchange rate: {quote_data.get('rate')}")
            
        except Exception as e:
            self.test_logger.error(f"Error in test: {str(e)}")
            self.test_logger.error(traceback.format_exc())
            raise
    
    def test_discover_supported_methods(self):
        """Discover supported payment and delivery methods for various corridors."""
        self.test_logger.info("Discovering supported methods for 5 corridors")
        
        # Define test corridors
        corridors = [
            {"send_country": "US", "receive_country": "MX"},
            {"send_country": "US", "receive_country": "PH"},
            {"send_country": "US", "receive_country": "IN"},
            {"send_country": "GB", "receive_country": "IN"},
            {"send_country": "CA", "receive_country": "PH"}
        ]
        
        results = []
        supported_count = 0
        
        for corridor in corridors:
            send_country = corridor["send_country"]
            receive_country = corridor["receive_country"]
            
            self.test_logger.info(f"Testing corridor: {send_country}->{receive_country}")
            
            try:
                # Get payment methods
                payment_methods = self.get_payment_methods(send_country, receive_country)
                
                # Get delivery methods
                delivery_methods = self.get_delivery_methods(send_country, receive_country)
                
                # Add to results
                results.append({
                    "corridor": f"{send_country}->{receive_country}",
                    "supported": True,
                    "payment_methods": payment_methods,
                    "delivery_methods": delivery_methods
                })
                
                supported_count += 1
                
                # Log the results
                self.test_logger.info(f"Payment methods: {payment_methods}")
                self.test_logger.info(f"Delivery methods: {delivery_methods}")
                
            except Exception as e:
                self.test_logger.error(f"Failed to test corridor {send_country}->{receive_country}: {str(e)}")
                self.test_logger.error(traceback.format_exc())
                results.append({
                    "corridor": f"{send_country}->{receive_country}",
                    "supported": False,
                    "error": str(e)
                })
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.results_dir, f"WISE_DISCOVERY_SUMMARY_{timestamp}.json")
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Saved response data to: {results_file}")
        self.test_logger.info(f"Complete discovery results saved to {results_file}")
        
        # Print summary
        self.test_logger.info("\n=== METHOD DISCOVERY SUMMARY ===")
        self.test_logger.info(f"Tested {len(corridors)} corridors, {supported_count} supported")
        self.test_logger.info("\n=== END SUMMARY ===")
    
    def get_payment_methods(self, source_country: str, target_country: str) -> list:
        """Get available payment methods for a specific corridor."""
        # This would typically call the Wise API to get available payment methods
        # For now, return a static list based on common options
        common_methods = ["BANK_TRANSFER", "CARD"]
        
        # Add country-specific methods
        if source_country == "GB":
            common_methods.append("PISP")  # Open Banking available in UK
        
        return common_methods
    
    def get_delivery_methods(self, source_country: str, target_country: str) -> list:
        """Get available delivery methods for a specific corridor."""
        # This would typically call the Wise API to get available delivery methods
        # For now, return a static list based on common options
        methods = ["BANK_TRANSFER"]
        
        # Add cash pickup for countries where it's commonly available
        if target_country in ["MX", "PH", "IN"]:
            methods.append("CASH_PICKUP")
            
        # Add SWIFT for international transfers to certain countries
        if target_country not in ["US", "GB", "EU"]:
            methods.append("SWIFT")
            
        return methods


if __name__ == "__main__":
    unittest.main() 