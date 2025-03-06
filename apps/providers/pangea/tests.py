"""
Pangea Money Transfer API Tests

HOW TO RUN:
python -m unittest apps.providers.pangea.tests
python -m unittest apps.providers.pangea.tests.TestPangeaProviderRealAPI.test_discover_supported_methods
"""

import json
import logging
import os
import traceback
import unittest
from datetime import datetime
from decimal import Decimal

from apps.providers.pangea.integration import PangeaProvider
from apps.providers.pangea.exceptions import (
    PangeaError,
    PangeaConnectionError,
    PangeaValidationError,
    PangeaRateLimitError,
    PangeaAuthenticationError
)

class TestPangeaProviderRealAPI(unittest.TestCase):
    """Real-API tests for Pangea Money Transfer Provider.
    
    This class contains tests that make real API calls to the Pangea Money Transfer API.
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
        
        cls.results_dir = "test_results_pangea"
        cls.logs_dir = os.path.join(cls.results_dir, "logs")
        
        os.makedirs(cls.results_dir, exist_ok=True)
        os.makedirs(cls.logs_dir, exist_ok=True)
        
        root_log_file = os.path.join(cls.logs_dir, f"pangea_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
        self.provider = PangeaProvider()
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")

    def tearDown(self):
        """Clean up after each test method."""
        test_log_file = os.path.join(self.logs_dir, f"{self._testMethodName}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.logger.info(f"=== Ending test: {self._testMethodName} ===")
        
        if hasattr(self, 'provider') and hasattr(self.provider, '_session'):
            try:
                session_logs = []
                if hasattr(self.provider._session, 'history'):
                    for req in self.provider._session.history:
                        session_logs.append(f"Request: {req.method} {req.url}")
                        session_logs.append(f"Response: {req.status_code}")
                
                if session_logs:
                    with open(test_log_file, 'w') as f:
                        f.write("\n".join(session_logs))
                    self.logger.info(f"Exported session logs to {test_log_file}")
            except Exception as e:
                self.logger.warning(f"Could not export session logs: {str(e)}")

    def save_response_data(self, data, prefix, error_reason=None):
        """Save JSON response data to a timestamped file for later analysis.
        
        Args:
            data: The data to save
            prefix: Prefix for the filename
            error_reason: Optional error information to include
            
        Returns:
            str: The filename where the data was saved
        """
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

    def test_get_exchange_rate_real(self):
        """Test getting real exchange rate data from Pangea API.
        
        This test verifies that the PangeaProvider can successfully retrieve
        exchange rate information from the real Pangea API for a US to Mexico corridor.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_get_exchange_rate_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing real exchange rate lookup from Pangea US to MX")
            
            result = self.provider.get_exchange_rate(
                send_amount=Decimal("100.00"),
                send_currency="USD",
                receive_country="MX"
            )
            
            # Verify and log the result
            self.assertIsNotNone(result, "Should return exchange rate data")
            saved_file = self.save_response_data(result, "exchange_rate_usd_to_mx")
            
            test_logger.info(f"Exchange rate: {result['exchange_rate']} MXN/USD")
            test_logger.info(f"Fee: {result['transfer_fee']} {result['send_currency']}")
            test_logger.info(f"Delivery: {result['delivery_time']}")
            test_logger.info(f"Receive amount: {result['receive_amount']} {result['receive_currency']}")
            test_logger.info(f"Response data saved to: {saved_file}")
            
        except Exception as e:
            test_logger.error(f"Error in test: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_common_corridors(self):
        """Test exchange rates for common money transfer corridors.
        
        This test checks multiple common money transfer corridors to verify
        that the PangeaProvider can handle a variety of source/destination combinations.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_common_corridors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_cases = [
                {"send": "USD", "from": "US", "to": "MX", "amount": 100},
                {"send": "USD", "from": "US", "to": "PH", "amount": 200},
                {"send": "USD", "from": "US", "to": "IN", "amount": 150}
            ]
            
            test_logger.info(f"Testing {len(test_cases)} common corridors")
            
            for case in test_cases:
                corridor_label = f"{case['from']}({case['send']})->{case['to']}"
                test_logger.info(f"Testing corridor: {corridor_label} with amount {case['amount']}")
                
                try:
                    result = self.provider.get_exchange_rate(
                        send_amount=Decimal(str(case['amount'])),
                        send_currency=case['send'],
                        receive_country=case['to'],
                        send_country=case['from']
                    )
                    
                    if result:
                        saved_file = self.save_response_data(
                            result, 
                            f"{case['from']}_{case['send']}_to_{case['to']}_{case['amount']}"
                        )
                        test_logger.info(f"Success! Rate: {result['exchange_rate']}, Fee: {result['transfer_fee']}")
                        test_logger.info(f"Recipient gets: {result['receive_amount']} {result['receive_currency']}")
                        test_logger.info(f"Response data saved to: {saved_file}")
                    else:
                        test_logger.warning(f"No exchange rate data returned for {corridor_label}")
                        
                except Exception as e:
                    test_logger.error(f"Error testing corridor {corridor_label}: {str(e)}")
                    test_logger.error(traceback.format_exc())
            
        except Exception as e:
            test_logger.error(f"Error in test: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close() 
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_discover_supported_methods(self):
        """Discover supported payment methods for various currency corridors.
        
        This test attempts to discover all supported payment and delivery methods
        for various send/receive country corridors by making API calls and
        analyzing the responses.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_discover_supported_methods_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            # Define corridors to test
            corridors = [
                ("US", "USD", "MX", "MXN"),  # US to Mexico
                ("US", "USD", "CO", "COP"),  # US to Colombia
                ("US", "USD", "PH", "PHP"),  # US to Philippines
                ("CA", "CAD", "MX", "MXN")   # Canada to Mexico
            ]
            
            test_logger.info(f"Discovering supported payment methods for {len(corridors)} corridors")
            
            all_methods = {}
            
            for source_country, source_currency, target_country, target_currency in corridors:
                corridor_name = f"{source_country}_to_{target_country}"
                test_logger.info(f"Checking corridor: {corridor_name}")
                
                try:
                    # Get fees and exchange rate data
                    response = self.provider.get_fees_and_fx(
                        source_country=source_country,
                        target_country=target_country,
                        source_currency=source_currency,
                        target_currency=target_currency
                    )
                    
                    if not response:
                        test_logger.warning(f"No data available for {corridor_name}")
                        continue
                    
                    # Extract exchange rate options
                    exchange_rates = response.get("ExchangeRates", [])
                    
                    if not exchange_rates:
                        test_logger.warning(f"No exchange rate options for {corridor_name}")
                        continue
                    
                    test_logger.info(f"Found {len(exchange_rates)} exchange rate options for {corridor_name}")
                    
                    # Count unique payment methods
                    payment_methods = set()
                    for rate in exchange_rates:
                        payment_method = rate.get("TxMethod")
                        if payment_method:
                            payment_methods.add(payment_method)
                    
                    test_logger.info(f"Found {len(payment_methods)} unique payment methods: {', '.join(payment_methods)}")
                    
                    # Save the data
                    methods_data = {
                        "corridor": corridor_name,
                        "exchange_rates": exchange_rates,
                        "payment_methods": list(payment_methods)
                    }
                    
                    all_methods[corridor_name] = methods_data
                    
                    # Save to file
                    methods_file = self.save_response_data(methods_data, f"methods_{corridor_name}")
                    test_logger.info(f"Saved methods data to {methods_file}")
                    
                except Exception as e:
                    test_logger.error(f"Error discovering methods for {corridor_name}: {str(e)}")
                    test_logger.error(traceback.format_exc())
            
            # Save combined results
            summary_file = self.save_response_data(all_methods, "ALL_METHODS_SUMMARY")
            test_logger.info(f"Saved combined methods data to {summary_file}")
            
        except Exception as e:
            test_logger.error(f"Error in discovery test: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")


if __name__ == "__main__":
    unittest.main() 