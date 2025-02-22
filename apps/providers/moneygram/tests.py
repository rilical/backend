"""Tests for MoneyGram provider using real API calls."""
import json
import unittest
from decimal import Decimal
from datetime import datetime
import os
import logging
import time

from apps.providers.integrations.money_gram import MoneyGramProvider
from apps.providers.exceptions.money_gram import MGError

class TestMoneyGramProvider(unittest.TestCase):
    """
    Test cases for the MoneyGramProvider that make *real* HTTP calls
    to the MoneyGram public endpoints (feeLookup, etc.).
    
    NOTE: 
      - MoneyGram may require captchas, device fingerprinting, or
        advanced cookies that can break these calls at any time.
      - If you see repeated 403/429/500 errors, it may be due to 
        MoneyGram blocking repeated automated requests.
      - Use these tests sparingly, or rely on mocks for your daily tests.
    """

    @classmethod
    def setUpClass(cls):
        """Set up logging and results directory."""
        logging.basicConfig(level=logging.INFO)
        cls.results_dir = "test_results_moneygram_real"
        os.makedirs(cls.results_dir, exist_ok=True)

    def setUp(self):
        """Set up a new MoneyGramProvider instance before each test."""
        self.provider = MoneyGramProvider(timeout=30)  # 30-second timeout
        self.logger = logging.getLogger(__name__)

    def save_response_data(self, data, prefix: str):
        """Save JSON data to a file with a timestamped name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/{prefix}_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"\n[RealTests] Saved response data to: {filename}")

    def test_get_catalog_data_us_to_philippines(self):
        """Test sending USD from USA to Philippines with real API calls."""
        send_amount = Decimal("1500")
        send_currency = "USD"
        send_country = "USA"
        receive_country = "PHL"
        
        self.logger.info(
            f"REAL TEST: get_catalog_data for ${send_amount} "
            f"from {send_country} to {receive_country}"
        )
        
        try:
            catalog_data = self.provider.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(catalog_data, "Catalog data should not be None")
            self.assertIn("paymentOptions", catalog_data, "Response should contain paymentOptions")
            
            # Log service details
            for payment_option in catalog_data['paymentOptions']:
                for receive_group in payment_option.get('receiveGroups', []):
                    for option in receive_group.get('receiveOptions', []):
                        self.logger.info(f"\nService Details:")
                        self.logger.info(f"Service Type: {option.get('description', 'Unknown')}")
                        self.logger.info(f"Exchange Rate: {option.get('exchangeRate', 'N/A')} PHP/USD")
                        self.logger.info(f"Fee: {option.get('sendFees', 'N/A')} USD")
                        self.logger.info(f"Send Amount: {option.get('sendAmount', 'N/A')} USD")
                        self.logger.info(f"Receive Amount: {option.get('receiveAmount', 'N/A')} PHP")
                        self.logger.info(f"Delivery Time: {option.get('estimatedDeliveryDate', 'N/A')}")
            
            self.save_response_data(catalog_data, f"us_to_philippines_{send_amount}usd_real")
                
        except MGError as e:
            self.logger.error(f"MG error: {e}")
            self.fail(f"Test failed due to MoneyGram error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def test_get_catalog_data_us_to_vietnam(self):
        """Test sending USD from USA to Vietnam with real API calls."""
        send_amount = Decimal("2000")
        send_currency = "USD" 
        send_country = "USA"
        receive_country = "VNM"
        
        self.logger.info(
            f"REAL TEST: get_catalog_data for ${send_amount} "
            f"from {send_country} to {receive_country}"
        )
        
        try:
            catalog_data = self.provider.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(catalog_data, "Catalog data should not be None")
            self.assertIn("paymentOptions", catalog_data, "Response should contain paymentOptions")
            
            # Log service details
            for payment_option in catalog_data['paymentOptions']:
                for receive_group in payment_option.get('receiveGroups', []):
                    for option in receive_group.get('receiveOptions', []):
                        self.logger.info(f"\nService Details:")
                        self.logger.info(f"Service Type: {option.get('description', 'Unknown')}")
                        self.logger.info(f"Exchange Rate: {option.get('exchangeRate', 'N/A')} VND/USD")
                        self.logger.info(f"Fee: {option.get('sendFees', 'N/A')} USD")
                        self.logger.info(f"Send Amount: {option.get('sendAmount', 'N/A')} USD")
                        self.logger.info(f"Receive Amount: {option.get('receiveAmount', 'N/A')} VND")
                        self.logger.info(f"Delivery Time: {option.get('estimatedDeliveryDate', 'N/A')}")
            
            self.save_response_data(catalog_data, f"us_to_vietnam_{send_amount}usd_real")
                
        except MGError as e:
            self.logger.error(f"MG error: {e}")
            self.fail(f"Test failed due to MoneyGram error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def test_get_catalog_data_us_to_colombia(self):
        """Test sending USD from USA to Colombia with real API calls."""
        send_amount = Decimal("800")
        send_currency = "USD"
        send_country = "USA" 
        receive_country = "COL"
        
        self.logger.info(
            f"REAL TEST: get_catalog_data for ${send_amount} "
            f"from {send_country} to {receive_country}"
        )
        
        try:
            catalog_data = self.provider.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(catalog_data, "Catalog data should not be None")
            self.assertIn("paymentOptions", catalog_data, "Response should contain paymentOptions")
            
            # Log service details
            for payment_option in catalog_data['paymentOptions']:
                for receive_group in payment_option.get('receiveGroups', []):
                    for option in receive_group.get('receiveOptions', []):
                        self.logger.info(f"\nService Details:")
                        self.logger.info(f"Service Type: {option.get('description', 'Unknown')}")
                        self.logger.info(f"Exchange Rate: {option.get('exchangeRate', 'N/A')} COP/USD")
                        self.logger.info(f"Fee: {option.get('sendFees', 'N/A')} USD")
                        self.logger.info(f"Send Amount: {option.get('sendAmount', 'N/A')} USD")
                        self.logger.info(f"Receive Amount: {option.get('receiveAmount', 'N/A')} COP")
                        self.logger.info(f"Delivery Time: {option.get('estimatedDeliveryDate', 'N/A')}")
            
            self.save_response_data(catalog_data, f"us_to_colombia_{send_amount}usd_real")
                
        except MGError as e:
            self.logger.error(f"MG error: {e}")
            self.fail(f"Test failed due to MoneyGram error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def test_get_catalog_data_us_to_nigeria(self):
        """Test sending USD from USA to Nigeria with real API calls."""
        send_amount = Decimal("1200")
        send_currency = "USD"
        send_country = "USA"
        receive_country = "NGA"
        
        self.logger.info(
            f"REAL TEST: get_catalog_data for ${send_amount} "
            f"from {send_country} to {receive_country}"
        )
        
        try:
            catalog_data = self.provider.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(catalog_data, "Catalog data should not be None")
            self.assertIn("paymentOptions", catalog_data, "Response should contain paymentOptions")
            
            # Log service details
            for payment_option in catalog_data['paymentOptions']:
                for receive_group in payment_option.get('receiveGroups', []):
                    for option in receive_group.get('receiveOptions', []):
                        self.logger.info(f"\nService Details:")
                        self.logger.info(f"Service Type: {option.get('description', 'Unknown')}")
                        self.logger.info(f"Exchange Rate: {option.get('exchangeRate', 'N/A')} NGN/USD")
                        self.logger.info(f"Fee: {option.get('sendFees', 'N/A')} USD")
                        self.logger.info(f"Send Amount: {option.get('sendAmount', 'N/A')} USD")
                        self.logger.info(f"Receive Amount: {option.get('receiveAmount', 'N/A')} NGN")
                        self.logger.info(f"Delivery Time: {option.get('estimatedDeliveryDate', 'N/A')}")
            
            self.save_response_data(catalog_data, f"us_to_nigeria_{send_amount}usd_real")
                
        except MGError as e:
            self.logger.error(f"MG error: {e}")
            self.fail(f"Test failed due to MoneyGram error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def test_get_catalog_data_us_to_dominican_republic(self):
        """Test sending USD from USA to Dominican Republic with real API calls."""
        send_amount = Decimal("2500")
        send_currency = "USD"
        send_country = "USA"
        receive_country = "DOM"
        
        self.logger.info(
            f"REAL TEST: get_catalog_data for ${send_amount} "
            f"from {send_country} to {receive_country}"
        )
        
        try:
            catalog_data = self.provider.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(catalog_data, "Catalog data should not be None")
            self.assertIn("paymentOptions", catalog_data, "Response should contain paymentOptions")
            
            # Log service details
            for payment_option in catalog_data['paymentOptions']:
                for receive_group in payment_option.get('receiveGroups', []):
                    for option in receive_group.get('receiveOptions', []):
                        self.logger.info(f"\nService Details:")
                        self.logger.info(f"Service Type: {option.get('description', 'Unknown')}")
                        self.logger.info(f"Exchange Rate: {option.get('exchangeRate', 'N/A')} DOP/USD")
                        self.logger.info(f"Fee: {option.get('sendFees', 'N/A')} USD")
                        self.logger.info(f"Send Amount: {option.get('sendAmount', 'N/A')} USD")
                        self.logger.info(f"Receive Amount: {option.get('receiveAmount', 'N/A')} DOP")
                        self.logger.info(f"Delivery Time: {option.get('estimatedDeliveryDate', 'N/A')}")
            
            self.save_response_data(catalog_data, f"us_to_dominican_republic_{send_amount}usd_real")
                
        except MGError as e:
            self.logger.error(f"MG error: {e}")
            self.fail(f"Test failed due to MoneyGram error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

def test_money_gram():
    """Run MoneyGram provider tests."""
    results = {
        'provider': 'MoneyGram',
        'tests': [],
        'passed': 0,
        'failed': 0
    }

    suite = unittest.TestLoader().loadTestsFromTestCase(TestMoneyGramProvider)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)

    # Get all test names from the test case class
    test_names = [name for name in dir(TestMoneyGramProvider) if name.startswith('test_')]
    
    # Track failures
    for failed_test in test_result.failures + test_result.errors:
        test_name = failed_test[0].id().split('.')[-1]
        results['tests'].append({
            'name': test_name,
            'status': 'failed',
            'error': str(failed_test[1])
        })
        results['failed'] += 1

    # Track passes
    passed_count = test_result.testsRun - len(test_result.failures) - len(test_result.errors)
    results['passed'] = passed_count

    # Add passed tests
    for test_name in test_names:
        if not any(t['name'] == test_name for t in results['tests']):
            results['tests'].append({
                'name': test_name,
                'status': 'passed'
            })

    return results

if __name__ == '__main__':
    unittest.main()
