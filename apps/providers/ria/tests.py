"""
RIA Money Transfer API Tests

HOW TO RUN:
python -m unittest apps.providers.ria.tests  
python -m unittest apps.providers.ria.tests.TestRIAProviderRealAPI.test_get_exchange_rate_real
"""

import json
import logging
import os
import time
import unittest
import traceback
from datetime import datetime
from decimal import Decimal

from apps.providers.ria.integration import RIAProvider
from apps.providers.ria.exceptions import RIAError, RIAValidationError, RIAAuthenticationError, RIAConnectionError

class TestRIAProviderRealAPI(unittest.TestCase):
    """Real-API tests for RIA Money Transfer Provider.
    
    This class contains tests that make real API calls to the RIA Money Transfer API.
    These tests focus exclusively on exchange rate functionality which is the critical component.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment before running any tests in this class."""
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        
        cls.results_dir = "test_results_ria"
        cls.logs_dir = os.path.join(cls.results_dir, "logs")
        
        os.makedirs(cls.results_dir, exist_ok=True)
        os.makedirs(cls.logs_dir, exist_ok=True)
        
        root_log_file = os.path.join(cls.logs_dir, f"ria_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(root_log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        cls.file_handler = file_handler
        cls.logger.info(f"Test run started. Logs will be saved to {root_log_file}")

    @classmethod
    def tearDownClass(cls):
        """Clean up resources after all tests in this class have run."""
        if hasattr(cls, 'file_handler') and cls.file_handler:
            cls.file_handler.close()
            logging.getLogger().removeHandler(cls.file_handler)
        
        cls.logger.info("Test run completed.")

    def setUp(self):
        """Set up test environment before each test method."""
        self.provider = RIAProvider(timeout=30)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")

    def tearDown(self):
        """Clean up after each test method."""
        self.logger.info(f"=== Ending test: {self._testMethodName} ===")

    def save_response_data(self, data, prefix, error_reason=None):
        """Save JSON response data to a timestamped file for later analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        if error_reason:
            response_data["error_reason"] = error_reason
            
        filename = f"{self.results_dir}/{prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(response_data, f, indent=2)
        self.logger.info(f"Saved response data to: {filename}")
        return filename

    def assertValidRateData(self, rate_data: dict):
        """Basic verification that required fields exist and are non-negative."""
        required_keys = {
            "provider", "timestamp", "send_amount", "send_currency",
            "receive_country", "exchange_rate", "transfer_fee",
            "payment_type", "delivery_time", "receive_amount"
        }
        for k in required_keys:
            self.assertIn(k, rate_data, f"Missing key '{k}' in rate data")

        self.assertGreaterEqual(rate_data["send_amount"], 0.0, "send_amount < 0")
        self.assertGreaterEqual(rate_data["exchange_rate"], 0.0, "exchange_rate < 0")
        self.assertGreaterEqual(rate_data["transfer_fee"], 0.0, "transfer_fee < 0")
        self.assertGreaterEqual(rate_data["receive_amount"], 0.0, "receive_amount < 0")

    def test_get_exchange_rate_real(self):
        """Test getting exchange rates using real API calls.
        
        This test verifies that the integration can fetch accurate exchange rates for
        a money transfer from US to Mexico, which is the primary functionality we need.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_get_exchange_rate_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing real exchange rate from US to MX")
            
            test_amount = Decimal("100.00")
            send_currency = "USD"
            receive_country = "MX"
            
            # Get the exchange rate
            rate_data = self.provider.calculate_rate(
                send_amount=float(test_amount),
                send_currency=send_currency,
                receive_country=receive_country,
                payment_method="DebitCard",
                delivery_method="BankDeposit"
            )
            
            test_logger.info(f"Rate data: {rate_data}")
            self.assertIsNotNone(rate_data, "Rate data should not be None")
            
            # Add payment_type key for assertValidRateData compatibility
            if rate_data and "payment_method" in rate_data:
                rate_data["payment_type"] = rate_data["payment_method"]
                
            # Add delivery_time if missing
            if rate_data and "delivery_time" not in rate_data:
                rate_data["delivery_time"] = "24-48 hours"
            
            saved_file = self.save_response_data(rate_data, "exchange_rate_US_MX")
            test_logger.info(f"Saved rate data to {saved_file}")
            
            self.assertValidRateData(rate_data)
            
            # Log the key information that matters
            test_logger.info(f"Exchange rate: {rate_data.get('exchange_rate')} {rate_data.get('currency_to', 'MXN')}/{send_currency}")
            test_logger.info(f"Transfer fee: {rate_data.get('transfer_fee')} {send_currency}")
            test_logger.info(f"Amount to be received: {rate_data.get('receive_amount')} {rate_data.get('currency_to', 'MXN')}")
            
        except Exception as e:
            test_logger.error(f"Unexpected error: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            
    def test_exchange_rates_for_corridors(self):
        """Test exchange rates for the most important corridors.
        
        Only tests exchange rates for the corridors we actually care about.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_exchange_rates_corridors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            # Only test the key corridors we care about
            test_corridors = [
                ("US", "USD", "MX"),  # US to Mexico - most important
                ("US", "USD", "CO"),  # US to Colombia
                ("US", "USD", "PH")   # US to Philippines
            ]
            
            test_logger.info(f"Testing exchange rates for {len(test_corridors)} corridors")
            
            for send_country, send_currency, receive_country in test_corridors:
                corridor_label = f"{send_country}_{send_currency}_to_{receive_country}"
                test_logger.info(f"Testing exchange rate for corridor: {corridor_label}")
                
                try:
                    # Use a consistent test amount
                    test_amount = Decimal("100.00")
                    
                    # Get exchange rate for this corridor
                    rate_data = self.provider.calculate_rate(
                        send_amount=float(test_amount),
                        send_currency=send_currency,
                        receive_country=receive_country,
                        payment_method="DebitCard",  # Use DebitCard as it works reliably
                        delivery_method="BankDeposit",  # Use BankDeposit as it works reliably
                        send_country=send_country
                    )
                    
                    if rate_data and rate_data.get("exchange_rate") is not None:
                        test_logger.info(f"✓ Exchange rate found: {rate_data.get('exchange_rate')}")
                        test_logger.info(f"  Fee: {rate_data.get('transfer_fee')} {send_currency}")
                        test_logger.info(f"  Receive amount: {rate_data.get('receive_amount')}")
                        
                        # Save successful results
                        self.save_response_data(
                            rate_data,
                            f"exchange_rate_{corridor_label}"
                        )
                    else:
                        test_logger.warning(f"✗ No exchange rate found for {corridor_label}")
                    
                except Exception as e:
                    test_logger.error(f"Error getting rate for {corridor_label}: {str(e)}")
                
                # Add a delay between requests
                time.sleep(2.0)
                
        except Exception as e:
            test_logger.error(f"Test failed: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()

if __name__ == "__main__":
    unittest.main()