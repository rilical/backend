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
        
        # Set up logging
        root_log_file = os.path.join(cls.logs_dir, f"wise_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
        # Initialize provider with no API key (for quotes only)
        self.provider = WiseProvider(api_key=None)
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
        """Test getting real exchange rate data from Wise API.
        
        This test verifies that the WiseProvider can successfully retrieve
        exchange rate information from the real Wise API for a US to Mexico corridor.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_get_exchange_rate_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing real exchange rate lookup from Wise US to MX")
            
            rate_data = self.provider.get_exchange_rate(
                send_amount=Decimal("100"),
                send_currency="USD",
                receive_country="MX"
            )
            
            # Verify and log the result
            self.assertIsNotNone(rate_data, "Should return exchange rate data")
            saved_file = self.save_response_data(rate_data, "exchange_rate_usd_to_mx")
            
            test_logger.info(f"Exchange rate: {rate_data['exchange_rate']}")
            test_logger.info(f"Fee: {rate_data['transfer_fee']} {rate_data['send_currency']}")
            test_logger.info(f"Delivery: {rate_data['delivery_time']}")
            test_logger.info(f"Receive amount: {rate_data['receive_amount']} {rate_data['receive_currency']}")
            test_logger.info(f"Response data saved to: {saved_file}")
            
        except Exception as e:
            test_logger.error(f"Error in test: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def get_currency_for_country(self, country_code: str) -> str:
        """Helper to get currency code for a country."""
        country_to_currency = {
            "US": "USD",
            "GB": "GBP",
            "IN": "INR",
            "EG": "EGP",
            "MX": "MXN",
            "CA": "CAD",
            "AU": "AUD",
            "NZ": "NZD",
            "JP": "JPY",
            "CN": "CNY",
            "PH": "PHP",
            "SG": "SGD",
            "AE": "AED",
            "ZA": "ZAR",
            "BR": "BRL",
            "NG": "NGN",
            "KE": "KES",
            "DE": "EUR",
            "FR": "EUR",
            "IT": "EUR",
            "ES": "EUR"
        }
        return country_to_currency.get(country_code, "USD")

    def test_common_corridors(self):
        """Test exchange rates for common money transfer corridors.
        
        This test checks multiple common money transfer corridors to verify
        that the WiseProvider can handle a variety of source/destination combinations.
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
                {"send": "GBP", "from": "GB", "to": "IN", "amount": 300},
                {"send": "EUR", "from": "DE", "to": "TR", "amount": 400},
                {"send": "CAD", "from": "CA", "to": "IN", "amount": 500}
            ]
            
            test_logger.info(f"Testing {len(test_cases)} common corridors")
            
            for case in test_cases:
                corridor_label = f"{case['from']}({case['send']})->{case['to']}"
                test_logger.info(f"Testing corridor: {corridor_label} with amount {case['amount']}")
                
                try:
                    rate_data = self.provider.get_exchange_rate(
                        send_amount=Decimal(str(case['amount'])),
                        send_currency=case['send'],
                        receive_country=case['to'],
                        send_country=case['from']
                    )
                    
                    if rate_data:
                        saved_file = self.save_response_data(
                            rate_data, 
                            f"{case['from']}_{case['send']}_to_{case['to']}_{case['amount']}"
                        )
                        test_logger.info(f"Success! Rate: {rate_data['exchange_rate']}, Fee: {rate_data['transfer_fee']}")
                        test_logger.info(f"Recipient gets: {rate_data['receive_amount']} {rate_data['receive_currency']}")
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

    def test_quotes_target_amount(self):
        """Test quotes with target amount specified instead of source amount.
        
        This test verifies that the provider can handle quotes where the target amount
        (how much the recipient should receive) is specified instead of the source amount.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_quotes_target_amount_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing quotes with target amount specified")
            
            # Get a quote specifying the target amount (how much recipient should get)
            quote_data = self.provider.get_quote(
                source_currency="GBP",
                target_currency="USD",
                target_amount=110.00
            )
            
            self.assertIsNotNone(quote_data)
            self.assertEqual(quote_data["targetCurrency"], "USD")
            self.assertEqual(float(quote_data["targetAmount"]), 110.00)
            
            # Save the response
            saved_file = self.save_response_data(quote_data, "quote_target_amount_specified")
            test_logger.info(f"Quote data with target amount saved to: {saved_file}")
            
            # Log key information
            test_logger.info(f"Source amount: {quote_data.get('sourceAmount')} {quote_data.get('sourceCurrency')}")
            test_logger.info(f"Target amount: {quote_data.get('targetAmount')} {quote_data.get('targetCurrency')}")
            test_logger.info(f"Exchange rate: {quote_data.get('rate')}")
            
            # Verify payment options
            payment_options = quote_data.get("paymentOptions", [])
            test_logger.info(f"Found {len(payment_options)} payment options")
            
            for i, option in enumerate(payment_options, 1):
                test_logger.info(f"Option {i}: {option.get('payIn')} to {option.get('payOut')}")
                test_logger.info(f"  Fee: {option.get('fee', {}).get('total')} {quote_data.get('sourceCurrency')}")
                test_logger.info(f"  Delivery: {option.get('formattedEstimatedDelivery')}")
                
        except Exception as e:
            test_logger.error(f"Error in test: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_discover_supported_methods(self):
        """Discover supported payment and delivery methods for various corridors.
        
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
            test_corridors = [
                ("US", "MX"),      # US to Mexico
                ("US", "PH"),      # US to Philippines 
                ("US", "IN"),      # US to India
                ("GB", "IN"),      # UK to India
                ("CA", "PH"),      # Canada to Philippines
            ]
            
            all_results = {}
            
            test_logger.info(f"Discovering supported methods for {len(test_corridors)} corridors")
            
            for send_country, receive_country in test_corridors:
                corridor_label = f"{send_country}->{receive_country}"
                test_logger.info(f"Testing corridor: {corridor_label}")
                
                try:
                    # Get payment methods for this corridor
                    payment_methods = self.provider.get_payment_methods(send_country, receive_country)
                    
                    # Get delivery methods for this corridor
                    delivery_methods = self.provider.get_delivery_methods(send_country, receive_country)
                    
                    test_logger.info(f"Found {len(payment_methods)} payment methods and {len(delivery_methods)} delivery methods")
                    
                    test_logger.info(f"Payment methods: {', '.join(payment_methods)}")
                    test_logger.info(f"Delivery methods: {', '.join(delivery_methods)}")
                    
                    # Sample amount to test
                    amount = 100
                    send_currency = self.get_currency_for_country(send_country)
                    
                    # Get quote data
                    try:
                        quote_data = self.provider.get_quote(
                            source_currency=send_currency,
                            target_currency=self.get_currency_for_country(receive_country),
                            source_amount=float(amount)
                        )
                        
                        if quote_data:
                            # Save the raw quote data
                            quote_file = self.save_response_data(
                                quote_data, 
                                f"QUOTE_{send_country}_{send_currency}_to_{receive_country}_{amount}"
                            )
                            test_logger.info(f"Quote data saved to {quote_file}")
                            
                            # Get exchange rate information
                            rate_data = self.provider.get_exchange_rate(
                                send_amount=Decimal(str(amount)),
                                send_currency=send_currency,
                                receive_country=receive_country,
                                send_country=send_country
                            )
                            
                            if rate_data:
                                rate_file = self.save_response_data(
                                    rate_data,
                                    f"{send_country}_{send_currency}_to_{receive_country}_{amount}"
                                )
                                test_logger.info(f"Rate data saved to {rate_file}")
                        else:
                            test_logger.warning(f"No quote data for {corridor_label}")
                            
                    except Exception as e:
                        test_logger.error(f"Error getting quote for {corridor_label}: {str(e)}")
                    
                    # Store results for this corridor
                    all_results[corridor_label] = {
                        "supported": True,
                        "payment_methods": payment_methods,
                        "delivery_methods": delivery_methods
                    }
                    
                except Exception as e:
                    test_logger.error(f"Failed to test corridor {corridor_label}: {str(e)}")
                    test_logger.error(traceback.format_exc())
                    all_results[corridor_label] = {
                        "supported": False,
                        "error": str(e)
                    }
                
            # Save the combined results
            summary_file = self.save_response_data(all_results, "WISE_DISCOVERY_SUMMARY")
            test_logger.info(f"Complete discovery results saved to {summary_file}")
            
            # Log a summary
            test_logger.info("\n=== METHOD DISCOVERY SUMMARY ===")
            supported_corridors = [corridor for corridor, results in all_results.items() 
                                if results.get("supported", False)]
            
            test_logger.info(f"Tested {len(test_corridors)} corridors, {len(supported_corridors)} supported")
            
            for corridor in supported_corridors:
                results = all_results[corridor]
                
                test_logger.info(f"\n{corridor}:")
                test_logger.info(f"  Payment methods: {', '.join(results.get('payment_methods', []))}")
                test_logger.info(f"  Delivery methods: {', '.join(results.get('delivery_methods', []))}")
                
            test_logger.info("\n=== END SUMMARY ===")
            
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