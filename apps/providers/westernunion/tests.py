import json
import logging
import random
import os
import time
import unittest
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
        
        cls.results_dir = "test_results_wu"
        os.makedirs(cls.results_dir, exist_ok=True)

    def setUp(self):
        # Create a fresh provider before each test
        self.provider = WesternUnionProvider(timeout=30)
        self.logger = logging.getLogger(__name__)

    def save_response_data(self, data, prefix):
        """
        Saves the JSON response to a timestamped file for reference.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/{prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved response data to: {filename}")

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

        for (send_country, send_cur, recv_country, amt) in test_inputs:
            subtest_label = f"{send_country}->{recv_country} {amt}{send_cur}"
            with self.subTest(subtest_label):
                try:
                    rate_data = self.provider.get_exchange_rate(
                        Decimal(str(amt)),
                        send_cur,
                        recv_country,
                        send_country
                    )
                    if rate_data:
                        self.assertValidRateData(rate_data)
                        file_prefix = f"{send_country}_{send_cur}_to_{recv_country}_{amt}"
                        self.save_response_data(rate_data, file_prefix)
                        self.logger.info(f"Test PASSED: {subtest_label}")
                    else:
                        self.logger.warning(f"No result returned for {subtest_label}")
                except (WUError, WUAuthenticationError, WUValidationError, WUConnectionError) as e:
                    self.logger.error(f"Test FAILED: {subtest_label} => WU error: {e}")
                    self.fail(f"WUError on valid combo: {e}")
                except Exception as e:
                    self.logger.error(f"Test FAILED: {subtest_label} => Unexpected: {e}")
                    raise
                finally:
                    # Sleep ~2 seconds to help avoid rate-limiting
                    time.sleep(2)

    def test_5_invalid_inputs(self):
        """
        Test 5 clearly invalid inputs. 
        We expect either None or an exception to be raised.
        """
        invalid_scenarios = [
            (-100, "USD", "MX", "US"),   # Negative amount
            (5000, "???", "EG", "US"),   # Invalid currency
            (400, "USD", "XX", "US"),    # Unknown country
            (400, "XYZ", "EG", "US"),    # Another unknown currency
            (-50, "GBP", "ZZ", "GB"),    # Negative + unknown
        ]

        for (amt, curr, rcountry, scountry) in invalid_scenarios:
            subtest_label = f"Invalid {amt}{curr}, {scountry}->{rcountry}"
            with self.subTest(subtest_label):
                try:
                    result = self.provider.get_exchange_rate(
                        Decimal(str(amt)), curr, rcountry, scountry
                    )
                    # Expect None or an exception
                    self.assertIsNone(
                        result,
                        f"Expected None but got {result} for scenario: {subtest_label}"
                    )
                    self.logger.info(f"Test PASSED (returned None): {subtest_label}")
                except (WUError, WUAuthenticationError, WUValidationError, WUConnectionError) as e:
                    self.logger.info(f"Test PASSED (raised exception): {subtest_label} => {e}")
                except Exception as e:
                    self.logger.error(f"Test FAILED (unexpected): {subtest_label} => {e}")
                    raise
                finally:
                    time.sleep(random.randint(2, 12))

if __name__ == "__main__":
    unittest.main()
