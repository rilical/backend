"""
Wise Money Transfer API Tests

HOW TO RUN:
python3 -m unittest apps.providers.wise.tests
python3 -m unittest apps.providers.wise.tests.TestWiseProviderRealAPI.test_discover_supported_methods
"""

import json
import logging
import os
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

import requests
from requests.exceptions import RequestException, HTTPError

from apps.providers.wise.integration import WiseProvider
from apps.providers.wise.exceptions import (
    WiseError,
    WiseAuthenticationError,
    WiseConnectionError,
    WiseValidationError,
    WiseRateLimitError
)


# Sample response data for tests
SAMPLE_QUOTE_RESPONSE = {
    "targetAmount": 110.00,
    "sourceAmount": 88.45,
    "rate": 1.26355,
    "status": "PENDING",
    "sourceCurrency": "GBP",
    "targetCurrency": "USD",
    "createdTime": "2025-02-25T06:32:55Z",
    "paymentOptions": [
        {
            "formattedEstimatedDelivery": "in 11 hours",
            "estimatedDelivery": "2025-02-25T17:30:00Z",
            "sourceAmount": 88.45,
            "targetAmount": 110.00,
            "fee": {
                "transferwise": 1.39,
                "payIn": 0.0,
                "total": 1.39
            },
            "payIn": "BANK_TRANSFER",
            "payOut": "BANK_TRANSFER",
            "disabled": False
        },
        {
            "formattedEstimatedDelivery": "in 11 hours",
            "estimatedDelivery": "2025-02-25T17:30:00Z",
            "sourceAmount": 89.03,
            "targetAmount": 110.00,
            "fee": {
                "transferwise": 1.39,
                "payIn": 0.58,
                "total": 1.97
            },
            "payIn": "DEBIT",
            "payOut": "BANK_TRANSFER",
            "disabled": False
        }
    ]
}


class TestWiseProviderMock(unittest.TestCase):
    """Test the Wise Provider with mock API responses."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.provider = WiseProvider(api_key=None)  # No API key needed for quotes
    
    @patch('requests.Session.post')
    def test_get_quote_success(self, mock_post):
        """Test successful quote retrieval."""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_QUOTE_RESPONSE
        mock_post.return_value = mock_response
        
        # Call the method
        result = self.provider.get_quote(
            source_currency="GBP",
            target_currency="USD",
            source_amount=88.45
        )
        
        # Verify result
        self.assertEqual(result["rate"], 1.26355)
        self.assertEqual(result["sourceCurrency"], "GBP")
        self.assertEqual(result["targetCurrency"], "USD")
        
        # Verify the API was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["sourceCurrency"], "GBP")
        self.assertEqual(kwargs["json"]["targetCurrency"], "USD")
        self.assertEqual(kwargs["json"]["sourceAmount"], 88.45)
        
    @patch('requests.Session.post')
    def test_get_quote_missing_amount(self, mock_post):
        """Test error when no amount is provided."""
        with self.assertRaises(WiseValidationError):
            self.provider.get_quote(
                source_currency="GBP",
                target_currency="USD"
            )
        
        # Verify API was not called
        mock_post.assert_not_called()
        
    @patch('requests.Session.post')
    def test_get_quote_http_error(self, mock_post):
        """Test handling of HTTP errors."""
        # Create mock error response
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.text = json.dumps({"error": "Invalid parameters"})
        
        # Create mock exception
        mock_error = HTTPError("Bad Request")
        mock_error.response = error_response
        
        # Configure mock to raise exception
        mock_post.side_effect = mock_error
        
        with self.assertRaises(WiseValidationError):
            self.provider.get_quote(
                source_currency="GBP",
                target_currency="USD",
                source_amount=88.45
            )
            
    @patch('requests.Session.post')
    def test_get_quote_auth_error(self, mock_post):
        """Test handling of authentication errors."""
        # Create mock error response
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.text = json.dumps({"error": "Unauthorized"})
        
        # Create mock exception
        mock_error = HTTPError("Unauthorized")
        mock_error.response = error_response
        
        # Configure mock to raise exception
        mock_post.side_effect = mock_error
        
        with self.assertRaises(WiseAuthenticationError):
            self.provider.get_quote(
                source_currency="GBP",
                target_currency="USD",
                source_amount=88.45
            )
            
    @patch('requests.Session.post')
    def test_get_quote_connection_error(self, mock_post):
        """Test handling of connection errors."""
        mock_post.side_effect = RequestException("Connection failed")
        
        with self.assertRaises(WiseConnectionError):
            self.provider.get_quote(
                source_currency="GBP",
                target_currency="USD",
                source_amount=88.45
            )
    
    @patch('requests.Session.post')
    def test_get_quote_rate_limit_error(self, mock_post):
        """Test handling of rate limit errors."""
        # Create mock error response
        error_response = MagicMock()
        error_response.status_code = 429
        error_response.text = json.dumps({"error": "Too Many Requests"})
        error_response.headers = {"Retry-After": "30"}
        
        # Create mock exception
        mock_error = HTTPError("Too Many Requests")
        mock_error.response = error_response
        
        # Configure mock to raise exception
        mock_post.side_effect = mock_error
        
        with self.assertRaises(WiseRateLimitError) as context:
            self.provider.get_quote(
                source_currency="GBP",
                target_currency="USD",
                source_amount=88.45
            )
            
        # Verify the error details include retry information
        self.assertIn("retry_after", context.exception.details)
        self.assertEqual(context.exception.details["retry_after"], "30")
            
    @patch('apps.providers.wise.integration.WiseProvider.get_quote')
    def test_get_exchange_rate_success(self, mock_get_quote):
        """Test getting exchange rate information successfully."""
        mock_get_quote.return_value = SAMPLE_QUOTE_RESPONSE
        
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("88.45"),
            send_currency="GBP",
            receive_country="US",
            receive_currency="USD"
        )
        
        # Verify correct parameters were passed
        mock_get_quote.assert_called_with(
            source_currency="GBP",
            target_currency="USD",
            source_amount=88.45
        )
        
        # Verify response formatting
        self.assertEqual(result['provider'], "Wise")
        self.assertEqual(result['send_amount'], 88.45)
        self.assertEqual(result['send_currency'], "GBP")
        self.assertEqual(result['receive_country'], "US")
        self.assertEqual(result['receive_currency'], "USD")
        self.assertEqual(result['exchange_rate'], 1.26355)
        self.assertEqual(result['transfer_fee'], 1.39)
        self.assertEqual(result['service_name'], "BANK_TRANSFER to BANK_TRANSFER")
        self.assertEqual(result['receive_amount'], 110.00)
        
    @patch('apps.providers.wise.integration.WiseProvider.get_quote')
    def test_country_currency_mapping(self, mock_get_quote):
        """Test country code to currency code mapping."""
        mock_get_quote.return_value = SAMPLE_QUOTE_RESPONSE
        
        # Test without explicitly providing receive_currency
        self.provider.get_exchange_rate(
            send_amount=Decimal("100"),
            send_currency="USD",
            receive_country="MX"
        )
        
        # Verify correct currency was derived from country code
        mock_get_quote.assert_called_with(
            source_currency="USD",
            target_currency="MXN",
            source_amount=100.0
        )

    @patch('apps.providers.wise.integration.WiseProvider.get_quote')
    def test_find_best_payment_option(self, mock_get_quote):
        """Test finding the best payment option from quote data."""
        mock_get_quote.return_value = SAMPLE_QUOTE_RESPONSE
        
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("88.45"),
            send_currency="GBP",
            receive_country="US",
            receive_currency="USD"
        )
        
        # The best option should be the one with lowest fee
        self.assertEqual(result['transfer_fee'], 1.39)
        self.assertEqual(result['service_name'], "BANK_TRANSFER to BANK_TRANSFER")


class TestWiseProviderRealAPI(unittest.TestCase):
    """Test the Wise Provider with real API calls."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create results directory if it doesn't exist
        self.results_dir = "test_results_wise"
        self.logs_dir = os.path.join(self.results_dir, "logs")
        
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Create a file handler for this test run
        log_filename = os.path.join(self.logs_dir, f"wise_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)
        
        # Also log to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Test run started. Logs will be saved to {log_filename}")
        
        # Initialize provider with no API key (for quotes only)
        self.provider = WiseProvider(api_key=None)
        
    def save_response_data(self, data, prefix):
        """Saves the JSON response to a timestamped file for reference."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/{prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved response data to: {filename}")
        return filename

    def test_get_exchange_rate_real(self):
        """Test getting real exchange rate data from Wise API."""
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")
        try:
            self.logger.info("Testing real exchange rate lookup")
            
            rate_data = self.provider.get_exchange_rate(
                send_amount=Decimal("100"),
                send_currency="USD",
                receive_country="MX"
            )
            
            if rate_data:
                self.assertIsNotNone(rate_data, "Should return rate data")
                saved_file = self.save_response_data(rate_data, "exchange_rate_usd_to_mx")
                
                self.logger.info(f"Exchange rate: {rate_data['exchange_rate']}")
                self.logger.info(f"Fee: {rate_data['transfer_fee']} {rate_data['send_currency']}")
                self.logger.info(f"Delivery: {rate_data['delivery_time']}")
                self.logger.info(f"Receive amount: {rate_data['receive_amount']} {rate_data['receive_currency']}")
                self.logger.info(f"Data saved to: {saved_file}")
            else:
                self.logger.warning("No rate data returned")
            
        except Exception as e:
            self.logger.error(f"Error in test: {e}", exc_info=True)
            self.fail(f"Exception during test: {e}")

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
        """Test common money transfer corridors."""
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")
        
        test_cases = [
            {"send": "USD", "from": "US", "to": "MX", "amount": 100},
            {"send": "USD", "from": "US", "to": "PH", "amount": 200},
            {"send": "GBP", "from": "GB", "to": "IN", "amount": 300},
            {"send": "EUR", "from": "DE", "to": "TR", "amount": 400},
            {"send": "CAD", "from": "CA", "to": "IN", "amount": 500}
        ]
        
        for case in test_cases:
            case_id = f"{case['send']}_to_{case['to']}_{case['amount']}"
            self.logger.info(f"Testing corridor: {case['from']} → {case['to']} ({case['amount']} {case['send']})")
            
            try:
                rate_data = self.provider.get_exchange_rate(
                    send_amount=Decimal(str(case['amount'])),
                    send_currency=case['send'],
                    receive_country=case['to'],
                    send_country=case['from']
                )
                
                if rate_data:
                    saved_file = self.save_response_data(rate_data, case_id)
                    self.logger.info(f"Success! Rate: {rate_data['exchange_rate']}, Fee: {rate_data['transfer_fee']}")
                    self.logger.info(f"Recipient gets: {rate_data['receive_amount']} {rate_data['receive_currency']}")
                    self.logger.info(f"Delivery time: {rate_data['delivery_time']}")
                    self.logger.info(f"Data saved to: {saved_file}")
                else:
                    self.logger.warning(f"No rate data for {case_id}")
                
            except Exception as e:
                self.logger.error(f"Error testing {case_id}: {e}")
        
        self.logger.info(f"=== Completed test: {self._testMethodName} ===")

    def test_quotes_target_amount(self):
        """Test quotes with target amount specified instead of source amount."""
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")
        
        try:
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
            self.logger.info(f"Quote data with target amount saved to: {saved_file}")
            
            # Log key information
            self.logger.info(f"Source amount: {quote_data.get('sourceAmount')} {quote_data.get('sourceCurrency')}")
            self.logger.info(f"Target amount: {quote_data.get('targetAmount')} {quote_data.get('targetCurrency')}")
            self.logger.info(f"Exchange rate: {quote_data.get('rate')}")
            
            # Verify payment options
            payment_options = quote_data.get("paymentOptions", [])
            self.logger.info(f"Found {len(payment_options)} payment options")
            
            for i, option in enumerate(payment_options, 1):
                self.logger.info(f"Option {i}: {option.get('payIn')} to {option.get('payOut')}")
                self.logger.info(f"  Fee: {option.get('fee', {}).get('total')} {quote_data.get('sourceCurrency')}")
                self.logger.info(f"  Delivery: {option.get('formattedEstimatedDelivery')}")
                
        except Exception as e:
            self.logger.error(f"Error in test: {e}", exc_info=True)
            self.fail(f"Exception during test: {e}")
            
        self.logger.info(f"=== Completed test: {self._testMethodName} ===")

    def test_discover_supported_methods(self):
        """Test discovering supported payment and delivery methods."""
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")
        
        test_corridors = [
            ("US", "MX"),      # US to Mexico
            ("US", "PH"),      # US to Philippines 
            ("US", "IN"),      # US to India
            ("GB", "IN"),      # UK to India
            ("CA", "PH"),      # Canada to Philippines
        ]
        
        all_results = {}
        
        for send_country, receive_country in test_corridors:
            corridor_label = f"{send_country}->{receive_country}"
            self.logger.info(f"Testing corridor: {corridor_label}")
            
            try:
                # Get payment methods for this corridor
                payment_methods = self.provider.get_payment_methods(send_country, receive_country)
                
                # Get delivery methods for this corridor
                delivery_methods = self.provider.get_delivery_methods(send_country, receive_country)
                
                self.logger.info(f"Found {len(payment_methods)} payment methods and {len(delivery_methods)} delivery methods")
                
                self.logger.info(f"Payment methods: {', '.join(payment_methods)}")
                self.logger.info(f"Delivery methods: {', '.join(delivery_methods)}")
                
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
                        self.logger.info(f"Quote data saved to {quote_file}")
                        
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
                            self.logger.info(f"Rate data saved to {rate_file}")
                    else:
                        self.logger.warning(f"No quote data for {corridor_label}")
                        
                except Exception as e:
                    self.logger.error(f"Error getting quote for {corridor_label}: {str(e)}")
                
                # Store results for this corridor
                all_results[corridor_label] = {
                    "supported": True,
                    "payment_methods": payment_methods,
                    "delivery_methods": delivery_methods
                }
                
            except Exception as e:
                self.logger.error(f"Failed to test corridor {corridor_label}: {str(e)}")
                all_results[corridor_label] = {
                    "supported": False,
                    "error": str(e)
                }
            
        # Save the combined results
        summary_file = self.save_response_data(all_results, "WISE_DISCOVERY_SUMMARY")
        self.logger.info(f"Complete discovery results saved to {summary_file}")
        
        # Log a summary
        self.logger.info("\n=== METHOD DISCOVERY SUMMARY ===")
        supported_corridors = [corridor for corridor, results in all_results.items() 
                            if results.get("supported", False)]
        
        self.logger.info(f"Tested {len(test_corridors)} corridors, {len(supported_corridors)} supported")
        
        for corridor in supported_corridors:
            results = all_results[corridor]
            
            self.logger.info(f"\n{corridor}:")
            self.logger.info(f"  Payment methods: {', '.join(results.get('payment_methods', []))}")
            self.logger.info(f"  Delivery methods: {', '.join(results.get('delivery_methods', []))}")
            
        self.logger.info("\n=== END SUMMARY ===")
        self.logger.info(f"=== Completed test: {self._testMethodName} ===")


if __name__ == "__main__":
    unittest.main() 