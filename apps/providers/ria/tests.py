"""Tests for Ria Money Transfer provider."""
import json
import unittest
from decimal import Decimal
from datetime import datetime
import os
import logging
from unittest.mock import patch, MagicMock

from apps.providers.integrations.ria import (
    RiaProvider,
    RiaInitializationError,
    RiaCatalogError
)

class TestRiaProvider(unittest.TestCase):
    """
    Test cases for Ria provider implementation.
    We'll specifically test fetching the calculator data and exchange rates.
    """

    def setUp(self):
        """Set up test cases."""
        self.provider = RiaProvider()
        # Create a directory for test results if it doesn't exist
        self.results_dir = "test_results"
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

    def save_response_data(self, data, prefix):
        """Save response data to a file with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/{prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nSaved response data to: {filename}")

    @patch("apps.providers.integrations.ria.requests.Session.get")
    @patch("apps.providers.integrations.ria.requests.Session.options")
    @patch("apps.providers.integrations.ria.requests.Session.post")
    def test_get_catalog_data_us_to_mexico(self, mock_post, mock_options, mock_get):
        """Test sending USD from US to Mexico."""
        send_amount = 300
        send_currency = "USD"
        send_country = "US"
        receive_country = "MX"
        
        logging.info(f"Testing get_catalog_data for sending ${send_amount} from {send_country} to {receive_country}")
        
        # Mock responses
        mock_options.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(status_code=200)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "model": {
                    "transferDetails": {
                        "selections": {
                            "countryTo": "MX",
                            "currencyTo": "MXN",
                            "currencyFrom": "USD",
                            "amountFrom": 300
                        },
                        "calculations": {
                            "amountTo": 6167.34,
                            "amountFrom": 300,
                            "totalFeesAndTaxes": 1.99,
                            "totalAmount": 301.99,
                            "exchangeRate": 20.25,
                            "transferFee": 1.99,
                            "variableRates": [
                                {
                                    "value": "BankDeposit",
                                    "exchangeRate": 20.25,
                                    "payAgentName": "",
                                    "isBestRate": False
                                },
                                {
                                    "value": "MobilePayment",
                                    "exchangeRate": 20.31,
                                    "payAgentName": "",
                                    "isBestRate": False
                                },
                                {
                                    "value": "OfficePickup",
                                    "exchangeRate": 20.36,
                                    "payAgentName": "Nueva Wal-Mart de Mexico",
                                    "isBestRate": True
                                }
                            ]
                        }
                    }
                }
            }
        )
        
        try:
            catalog_data = self.provider.get_catalog_data(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(catalog_data, "Catalog data should not be None")
            self.assertIn("model", catalog_data, "Response should contain model")
            
            # Log service details
            calculations = catalog_data["model"]["transferDetails"]["calculations"]
            for rate_info in calculations.get("variableRates", []):
                logging.info(f"\nService Details:")
                logging.info(f"Service Type: {rate_info.get('value', 'Unknown')}")
                logging.info(f"Exchange Rate: {rate_info.get('exchangeRate', 'N/A')} MXN/USD")
                logging.info(f"Agent: {rate_info.get('payAgentName', 'N/A')}")
                logging.info(f"Is Best Rate: {rate_info.get('isBestRate', False)}")
            
            # Save response for analysis
            self.save_response_data(catalog_data, f"ria_us_to_mexico_{send_amount}usd")
                
        except Exception as e:
            logging.error(f"Error in test_get_catalog_data_us_to_mexico: {str(e)}")
            raise

    @patch("apps.providers.integrations.ria.requests.Session.get")
    @patch("apps.providers.integrations.ria.requests.Session.options")
    @patch("apps.providers.integrations.ria.requests.Session.post")
    def test_get_exchange_rate_us_to_mexico(self, mock_post, mock_options, mock_get):
        """Test getting exchange rate for USD from US to Mexico."""
        send_amount = 300
        send_currency = "USD"
        send_country = "US"
        receive_country = "MX"
        
        logging.info(f"Testing get_exchange_rate for sending ${send_amount} from {send_country} to {receive_country}")
        
        # Mock responses
        mock_options.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(status_code=200)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "model": {
                    "transferDetails": {
                        "selections": {
                            "countryTo": "MX",
                            "currencyTo": "MXN",
                            "currencyFrom": "USD",
                            "amountFrom": 300
                        },
                        "calculations": {
                            "amountTo": 6167.34,
                            "amountFrom": 300,
                            "totalFeesAndTaxes": 1.99,
                            "totalAmount": 301.99,
                            "exchangeRate": 20.25,
                            "transferFee": 1.99,
                            "variableRates": [
                                {
                                    "value": "BankDeposit",
                                    "exchangeRate": 20.25,
                                    "payAgentName": "",
                                    "isBestRate": False
                                },
                                {
                                    "value": "MobilePayment",
                                    "exchangeRate": 20.31,
                                    "payAgentName": "",
                                    "isBestRate": False
                                },
                                {
                                    "value": "OfficePickup",
                                    "exchangeRate": 20.36,
                                    "payAgentName": "Nueva Wal-Mart de Mexico",
                                    "isBestRate": True
                                }
                            ]
                        }
                    }
                }
            }
        )
        
        try:
            rate_data = self.provider.get_exchange_rate(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(rate_data, "Exchange rate data should not be None")
            
            # Log rate details
            logging.info(f"\nExchange Rate Details:")
            logging.info(f"Rate: {rate_data.get('exchange_rate', 'N/A')} MXN/USD")
            logging.info(f"Fee: {rate_data.get('transfer_fee', 'N/A')} USD")
            logging.info(f"Service: {rate_data.get('service_name', 'N/A')}")
            logging.info(f"Delivery Time: {rate_data.get('delivery_time', 'N/A')}")
            logging.info(f"Receive Amount: {rate_data.get('receive_amount', 'N/A')} MXN")
            
            # Calculate total cost in USD
            total_usd = float(send_amount) + float(rate_data.get('transfer_fee', 0))
            logging.info(f"Total Cost: ${total_usd:.2f} USD")
            
            # Calculate effective exchange rate (after fees)
            receive_amount = float(rate_data.get('receive_amount', 0))
            effective_rate = receive_amount / float(send_amount)
            logging.info(f"Effective Rate (after fees): {effective_rate:.4f} MXN/USD")
            
            # Verify numeric fields
            self.assertGreater(float(rate_data.get('exchange_rate', 0)), 0, "Exchange rate should be positive")
            self.assertGreaterEqual(float(rate_data.get('transfer_fee', 0)), 0, "Fee should be non-negative")
            self.assertGreater(receive_amount, 0, "Receive amount should be positive")
            
            # Verify we got the best rate
            self.assertEqual(rate_data.get('exchange_rate'), 20.36, "Should get the best rate (OfficePickup)")
            
        except Exception as e:
            logging.error(f"Error in test_get_exchange_rate_us_to_mexico: {str(e)}")
            raise

    @patch("apps.providers.integrations.ria.requests.Session.get")
    @patch("apps.providers.integrations.ria.requests.Session.options")
    @patch("apps.providers.integrations.ria.requests.Session.post")
    def test_get_exchange_rate_invalid_country(self, mock_post, mock_options, mock_get):
        """Test getting exchange rate with an invalid country code."""
        send_amount = 100
        send_currency = "USD"
        send_country = "US"
        receive_country = "XXX"  # Invalid country code
        
        logging.info(f"Testing get_exchange_rate with invalid country code {receive_country}")
        
        # Mock responses to simulate an error
        mock_options.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(status_code=200)
        mock_post.return_value = MagicMock(
            status_code=400,
            json=lambda: {
                "errorResponse": {
                    "errors": [
                        {
                            "code": "INVALID_COUNTRY",
                            "message": "Invalid receiving country code"
                        }
                    ]
                }
            },
            raise_for_status=lambda: exec('raise requests.exceptions.HTTPError("400 Client Error")')
        )
        
        try:
            rate_data = self.provider.get_exchange_rate(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            # Should return None for invalid country
            self.assertIsNone(rate_data, "Exchange rate data should be None for invalid country")
            
        except RiaCatalogError as e:
            # This is the expected behavior
            logging.info("Successfully caught RiaCatalogError for invalid country code")
            self.assertIn("Invalid receiving country code", str(e))
        except Exception as e:
            logging.error(f"Unexpected error in test_get_exchange_rate_invalid_country: {str(e)}")
            raise

    @patch("apps.providers.integrations.ria.requests.Session.get")
    @patch("apps.providers.integrations.ria.requests.Session.options")
    @patch("apps.providers.integrations.ria.requests.Session.post")
    def test_get_exchange_rate_multiple_methods(self, mock_post, mock_options, mock_get):
        """Test getting exchange rates with multiple delivery methods."""
        send_amount = 500
        send_currency = "USD"
        send_country = "US"
        receive_country = "MX"
        
        logging.info(f"Testing get_exchange_rate with multiple methods for sending ${send_amount} from {send_country} to {receive_country}")
        
        # Mock responses with multiple delivery methods
        mock_options.return_value = MagicMock(status_code=200)
        mock_get.return_value = MagicMock(status_code=200)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "model": {
                    "transferDetails": {
                        "selections": {
                            "countryTo": "MX",
                            "currencyTo": "MXN",
                            "currencyFrom": "USD",
                            "amountFrom": 500
                        },
                        "calculations": {
                            "amountTo": 10125.00,
                            "amountFrom": 500,
                            "totalFeesAndTaxes": 2.99,
                            "totalAmount": 502.99,
                            "exchangeRate": 20.25,
                            "transferFee": 2.99,
                            "variableRates": [
                                {
                                    "value": "BankDeposit",
                                    "exchangeRate": 20.25,
                                    "payAgentName": "Banco Azteca",
                                    "isBestRate": False
                                },
                                {
                                    "value": "MobilePayment",
                                    "exchangeRate": 20.31,
                                    "payAgentName": "BBVA Mexico",
                                    "isBestRate": False
                                },
                                {
                                    "value": "OfficePickup",
                                    "exchangeRate": 20.36,
                                    "payAgentName": "Nueva Wal-Mart de Mexico",
                                    "isBestRate": True
                                }
                            ]
                        },
                        "transferOptions": {
                            "deliveryMethods": [
                                {
                                    "value": "OfficePickup",
                                    "text": "Cash pickup"
                                },
                                {
                                    "value": "BankDeposit",
                                    "text": "Bank"
                                },
                                {
                                    "value": "MobilePayment",
                                    "text": "Mobile wallet"
                                }
                            ]
                        }
                    }
                }
            }
        )
        
        try:
            rate_data = self.provider.get_exchange_rate(
                send_amount=send_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                send_country=send_country
            )
            
            self.assertIsNotNone(rate_data, "Exchange rate data should not be None")
            
            # Save the full response data for analysis
            self.save_response_data(rate_data, f"ria_multiple_methods_{send_amount}usd")
            
            # Log rate details
            logging.info(f"\nBest Exchange Rate Details:")
            logging.info(f"Rate: {rate_data.get('exchange_rate', 'N/A')} MXN/USD")
            logging.info(f"Fee: {rate_data.get('transfer_fee', 'N/A')} USD")
            logging.info(f"Service: {rate_data.get('service_name', 'N/A')}")
            logging.info(f"Delivery Time: {rate_data.get('delivery_time', 'N/A')}")
            logging.info(f"Receive Amount: {rate_data.get('receive_amount', 'N/A')} MXN")
            
            # Calculate total cost in USD
            total_usd = float(send_amount) + float(rate_data.get('transfer_fee', 0))
            logging.info(f"Total Cost: ${total_usd:.2f} USD")
            
            # Calculate effective exchange rate (after fees)
            receive_amount = float(rate_data.get('receive_amount', 0))
            effective_rate = receive_amount / float(send_amount)
            logging.info(f"Effective Rate (after fees): {effective_rate:.4f} MXN/USD")
            
            # Verify numeric fields
            self.assertGreater(float(rate_data.get('exchange_rate', 0)), 0, "Exchange rate should be positive")
            self.assertGreaterEqual(float(rate_data.get('transfer_fee', 0)), 0, "Fee should be non-negative")
            self.assertGreater(receive_amount, 0, "Receive amount should be positive")
            
            # Verify we got the best rate
            self.assertEqual(rate_data.get('exchange_rate'), 20.36, "Should get the best rate (OfficePickup)")
            self.assertIn("Nueva Wal-Mart", rate_data.get('service_name', ""), "Should use the agent with best rate")
            
        except Exception as e:
            logging.error(f"Error in test_get_exchange_rate_multiple_methods: {str(e)}")
            raise

def test_ria():
    """Run Ria provider tests."""
    results = {
        'provider': 'Ria',
        'tests': [],
        'passed': 0,
        'failed': 0
    }

    suite = unittest.TestLoader().loadTestsFromTestCase(TestRiaProvider)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)

    # Get all test names from the test case class
    test_names = [name for name in dir(TestRiaProvider) if name.startswith('test_')]
    
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