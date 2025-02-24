import json
import logging
import random
import os
import time
import unittest
import traceback
from datetime import datetime
from decimal import Decimal

# Import real WU provider & exceptions
from apps.providers.westernunion.integration import WesternUnionProvider
from apps.providers.westernunion.exceptions import (
    WUError,
    WUAuthenticationError,
    WUValidationError,
    WUConnectionError
)

class TestWesternUnionProviderRealAPI(unittest.TestCase):
    """
    Real-API tests for Western Union Provider.
    Includes short sleeps to reduce blocking, and logs success/failure in detail.
    """

    @classmethod
    def setUpClass(cls):
        # Configure logging at INFO to see more logs
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        
        # Set up results and logs directories
        cls.results_dir = "test_results_wu"
        cls.logs_dir = os.path.join(cls.results_dir, "logs")
        
        # Create both directories
        os.makedirs(cls.results_dir, exist_ok=True)
        os.makedirs(cls.logs_dir, exist_ok=True)
        
        # Set up a root file handler to capture all logs
        root_log_file = os.path.join(cls.logs_dir, f"wu_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(root_log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        cls.file_handler = file_handler
        cls.logger.info(f"Test run started. Logs will be saved to {root_log_file}")

    @classmethod
    def tearDownClass(cls):
        # Close the file handler
        if hasattr(cls, 'file_handler') and cls.file_handler:
            cls.file_handler.close()
            logging.getLogger().removeHandler(cls.file_handler)
        
        cls.logger.info("Test run completed.")

    def setUp(self):
        # Create a fresh provider before each test
        self.provider = WesternUnionProvider(timeout=30)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")

    def tearDown(self):
        # Create a specific log file for this test
        test_log_file = os.path.join(self.logs_dir, f"{self._testMethodName}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.logger.info(f"=== Ending test: {self._testMethodName} ===")
        
        # Try to export logs from the provider's session
        if hasattr(self, 'provider') and hasattr(self.provider, 'logger'):
            try:
                # Export HTTP request/response logs if available
                session_logs = []
                if hasattr(self.provider, '_session') and hasattr(self.provider._session, 'history'):
                    for req in self.provider._session.history:
                        session_logs.append(f"Request: {req.method} {req.url}")
                        session_logs.append(f"Response: {req.status_code}")
                
                if session_logs:
                    with open(test_log_file, 'w') as f:
                        f.write("\n".join(session_logs))
                    self.logger.info(f"Exported session logs to {test_log_file}")
            except Exception as e:
                self.logger.warning(f"Could not export session logs: {str(e)}")

    def save_response_data(self, data, prefix):
        """
        Saves the JSON response to a timestamped file for reference.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/{prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved response data to: {filename}")
        return filename

    def assertValidRateData(self, rate_data: dict):
        """
        Basic verification that required fields exist and are non-negative.
        """
        required_keys = {
            "provider", "timestamp", "send_amount", "send_currency",
            "receive_country", "exchange_rate", "transfer_fee",
            "service_name", "delivery_time", "receive_amount"
        }
        for k in required_keys:
            self.assertIn(k, rate_data, f"Missing key '{k}' in rate data")

        self.assertGreaterEqual(rate_data["send_amount"], 0.0, "send_amount < 0")
        self.assertGreaterEqual(rate_data["exchange_rate"], 0.0, "exchange_rate < 0")
        self.assertGreaterEqual(rate_data["transfer_fee"], 0.0, "transfer_fee < 0")
        self.assertGreaterEqual(rate_data["receive_amount"], 0.0, "receive_amount < 0")

    def test_20_valid_combinations(self):
        """
        Test 20 different valid combos. Each sub-test does a real call,
        logs success or error, and then sleeps ~2 seconds to reduce rate-limit risk.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_20_valid_combinations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Create a file handler specific to this test
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_inputs = [
                ("US", "USD", "MX", 100),
                ("US", "USD", "EG", 500),
                ("GB", "GBP", "IN", 1000),
                ("GB", "GBP", "EG", 4999),
                ("CA", "CAD", "US", 120),
                ("AU", "AUD", "GB", 200),
                ("DE", "EUR", "TR", 300),
                ("DE", "EUR", "MX", 700),
                ("FR", "EUR", "NG", 2500),
                ("IT", "EUR", "US", 1000),
                ("SG", "SGD", "PH", 700),
                ("JP", "JPY", "US", 400),
                ("IN", "INR", "GB", 3000),
                ("US", "USD", "EG", 250),
                ("GB", "GBP", "IN", 400),
                ("US", "USD", "MX", 4500),
                ("CA", "CAD", "EG", 999),
                ("FR", "EUR", "IN", 2300),
                ("AU", "AUD", "US", 4950),
                ("NZ", "NZD", "PH", 1000),
            ]

            test_logger.info(f"Testing {len(test_inputs)} valid combinations")

            for (send_country, send_cur, recv_country, amt) in test_inputs:
                subtest_label = f"{send_country}->{recv_country} {amt}{send_cur}"
                test_logger.info(f"Testing combination: {subtest_label}")
                
                with self.subTest(subtest_label):
                    try:
                        test_logger.info(f"Making exchange rate request for {subtest_label}")
                        rate_data = self.provider.get_exchange_rate(
                            Decimal(str(amt)),
                            send_cur,
                            recv_country,
                            send_country
                        )
                        if rate_data:
                            self.assertValidRateData(rate_data)
                            file_prefix = f"{send_country}_{send_cur}_to_{recv_country}_{amt}"
                            saved_file = self.save_response_data(rate_data, file_prefix)
                            test_logger.info(f"Test PASSED: {subtest_label} - Rate data saved to {saved_file}")
                            
                            # Log key rate information
                            test_logger.info(f"Exchange rate: {rate_data.get('exchange_rate')}")
                            test_logger.info(f"Transfer fee: {rate_data.get('transfer_fee')}")
                            test_logger.info(f"Receive amount: {rate_data.get('receive_amount')}")
                            test_logger.info(f"Service name: {rate_data.get('service_name')}")
                            test_logger.info(f"Delivery time: {rate_data.get('delivery_time')}")
                        else:
                            test_logger.warning(f"No result returned for {subtest_label}")
                    except (WUError, WUAuthenticationError, WUValidationError, WUConnectionError) as e:
                        test_logger.error(f"Test FAILED: {subtest_label} => WU error: {e}")
                        self.fail(f"WUError on valid combo: {e}")
                    except Exception as e:
                        test_logger.error(f"Test FAILED: {subtest_label} => Unexpected: {e}")
                        test_logger.error(traceback.format_exc())
                        raise
                    finally:
                        # Sleep ~2 seconds to help avoid rate-limiting
                        test_logger.debug(f"Sleeping 2 seconds after {subtest_label}")
                        time.sleep(2)
            
            test_logger.info("Valid combinations test completed")
            
        except Exception as e:
            test_logger.error(f"Test failed: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_5_invalid_inputs(self):
        """
        Test 5 clearly invalid inputs. 
        We expect either None or an exception to be raised.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_5_invalid_inputs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Create a file handler specific to this test
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            invalid_scenarios = [
                (-100, "USD", "MX", "US"),   # Negative amount
                (5000, "???", "EG", "US"),   # Invalid currency
                (400, "USD", "XX", "US"),    # Unknown country
                (400, "XYZ", "EG", "US"),    # Another unknown currency
                (-50, "GBP", "ZZ", "GB"),    # Negative + unknown
            ]

            test_logger.info(f"Testing {len(invalid_scenarios)} invalid scenarios")

            for (amt, curr, rcountry, scountry) in invalid_scenarios:
                subtest_label = f"Invalid {amt}{curr}, {scountry}->{rcountry}"
                test_logger.info(f"Testing scenario: {subtest_label}")
                
                with self.subTest(subtest_label):
                    try:
                        test_logger.info(f"Making exchange rate request with invalid parameters: {subtest_label}")
                        result = self.provider.get_exchange_rate(
                            Decimal(str(amt)), curr, rcountry, scountry
                        )
                        # Expect None or an exception
                        self.assertIsNone(
                            result,
                            f"Expected None but got {result} for scenario: {subtest_label}"
                        )
                        test_logger.info(f"Test PASSED (returned None): {subtest_label}")
                    except (WUError, WUAuthenticationError, WUValidationError, WUConnectionError) as e:
                        test_logger.info(f"Test PASSED (raised expected exception): {subtest_label} => {e}")
                    except Exception as e:
                        test_logger.error(f"Test FAILED (unexpected error): {subtest_label} => {e}")
                        test_logger.error(traceback.format_exc())
                        raise
                    finally:
                        sleep_time = random.randint(2, 5)
                        test_logger.debug(f"Sleeping {sleep_time} seconds after {subtest_label}")
                        time.sleep(sleep_time)
            
            test_logger.info("Invalid inputs test completed")
            
        except Exception as e:
            test_logger.error(f"Test failed: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

if __name__ == "__main__":
    unittest.main()
