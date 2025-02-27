"""
Intermex Money Transfer API Tests

HOW TO RUN:
python -m unittest apps.providers.intermex.tests  
python -m unittest apps.providers.intermex.tests.TestIntermexProviderRealAPI.test_get_exchange_rate_real
"""

import json
import logging
import os
import time
import unittest
import traceback
from datetime import datetime
from decimal import Decimal

from apps.providers.intermex.integration import IntermexProvider
from apps.providers.intermex.exceptions import (
    IntermexError, 
    IntermexValidationError, 
    IntermexAuthenticationError, 
    IntermexConnectionError,
    IntermexRateLimitError
)

class TestIntermexProviderRealAPI(unittest.TestCase):
    """Real-API tests for Intermex Money Transfer Provider."""

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        
        cls.results_dir = "test_results_intermex"
        cls.logs_dir = os.path.join(cls.results_dir, "logs")
        
        os.makedirs(cls.results_dir, exist_ok=True)
        os.makedirs(cls.logs_dir, exist_ok=True)
        
        root_log_file = os.path.join(cls.logs_dir, f"intermex_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(root_log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        cls.file_handler = file_handler
        cls.logger.info(f"Test run started. Logs will be saved to {root_log_file}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'file_handler') and cls.file_handler:
            cls.file_handler.close()
            logging.getLogger().removeHandler(cls.file_handler)
        
        cls.logger.info("Test run completed.")

    def setUp(self):
        self.provider = IntermexProvider(timeout=30)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")

    def tearDown(self):
        self.logger.info(f"=== Ending test: {self._testMethodName} ===")

    def save_response_data(self, data, prefix, error_reason=None):
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
        required_keys = {
            "provider", "timestamp", "send_amount", "send_currency",
            "receive_country", "exchange_rate", "transfer_fee",
            "payment_method", "delivery_method", "delivery_time", "receive_amount"
        }
        for k in required_keys:
            self.assertIn(k, rate_data, f"Missing key '{k}' in rate data")

        self.assertGreaterEqual(rate_data["send_amount"], 0.0, "send_amount < 0")
        self.assertGreaterEqual(rate_data["exchange_rate"], 0.0, "exchange_rate < 0")
        self.assertGreaterEqual(rate_data["transfer_fee"], 0.0, "transfer_fee < 0")
        self.assertGreaterEqual(rate_data["receive_amount"], 0.0, "receive_amount < 0")

    def test_get_exchange_rate_real(self):
        """Test getting exchange rates using real API calls."""
        test_method_log = os.path.join(self.logs_dir, f"test_get_exchange_rate_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing real exchange rate from USA to TUR")
            
            test_amount = Decimal("100.00")
            send_currency = "USD"
            receive_country = "TUR"
            receive_currency = "TRY"
            
            rate_data = self.provider.get_exchange_rate(
                send_amount=test_amount,
                send_currency=send_currency,
                receive_country=receive_country,
                receive_currency=receive_currency,
                payment_method="CreditCard",
                delivery_method="BankDeposit"
            )
            
            test_logger.info(f"Rate data: {rate_data}")
            self.assertIsNotNone(rate_data, "Rate data should not be None")
            
            saved_file = self.save_response_data(rate_data, "exchange_rate_USA_TUR")
            test_logger.info(f"Saved rate data to {saved_file}")
            
            self.assertValidRateData(rate_data)
            
            test_logger.info(f"Exchange rate: {rate_data.get('exchange_rate')} {receive_currency}/{send_currency}")
            test_logger.info(f"Transfer fee: {rate_data.get('transfer_fee')} {send_currency}")
            test_logger.info(f"Amount to be received: {rate_data.get('receive_amount')} {receive_currency}")
            
        except Exception as e:
            test_logger.error(f"Unexpected error: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            
    def test_exchange_rates_for_corridors(self):
        """Test exchange rates for the most important corridors."""
        test_method_log = os.path.join(self.logs_dir, f"test_exchange_rates_corridors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_corridors = [
                ("USA", "USD", "TUR", "TRY"),
                ("USA", "USD", "MX", "MXN"),
                ("USA", "USD", "CL", "COP"),
                ("USA", "USD", "GU", "GTQ"),
                ("USA", "USD", "SA", "USD"),
                ("USA", "USD", "HO", "HNL"),
                ("USA", "USD", "ESP", "EUR"),
                ("USA", "USD", "IT", "EUR"),
                ("USA", "USD", "EGY", "EGP"),
                ("USA", "USD", "NG", "NGN"),
                ("USA", "USD", "IND", "INR"),
                ("USA", "USD", "PH", "PHP"),
            ]
            
            test_logger.info(f"Testing exchange rates for {len(test_corridors)} corridors")
            
            success_count = 0
            failure_count = 0
            
            for send_country, send_currency, receive_country, receive_currency in test_corridors:
                corridor_label = f"{send_country}_{send_currency}_to_{receive_country}_{receive_currency}"
                test_logger.info(f"Testing exchange rate for corridor: {corridor_label}")
                
                try:
                    test_amount = Decimal("100.00")
                    
                    rate_data = self.provider.get_exchange_rate(
                        send_amount=test_amount,
                        send_currency=send_currency,
                        receive_country=receive_country,
                        receive_currency=receive_currency,
                        payment_method="CreditCard",
                        delivery_method="BankDeposit"
                    )
                    
                    if rate_data and rate_data.get("exchange_rate") is not None:
                        test_logger.info(f"✓ Exchange rate found: {rate_data.get('exchange_rate')}")
                        test_logger.info(f"  Fee: {rate_data.get('transfer_fee')} {send_currency}")
                        test_logger.info(f"  Receive amount: {rate_data.get('receive_amount')}")
                        
                        self.save_response_data(
                            rate_data,
                            f"exchange_rate_{corridor_label}"
                        )
                        success_count += 1
                    else:
                        test_logger.warning(f"✗ No exchange rate found for {corridor_label}")
                        failure_count += 1
                    
                except Exception as e:
                    test_logger.error(f"Error getting rate for {corridor_label}: {str(e)}")
                    failure_count += 1
                
                time.sleep(2.0)
            
            test_logger.info(f"Test summary: {success_count} successful corridors, {failure_count} failed corridors")
            if success_count > 0:
                self.assertTrue(True, f"Successfully tested {success_count} corridors")
            else:
                self.fail("No corridors were successfully tested")
                
        except Exception as e:
            test_logger.error(f"Test failed: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
    
    def test_comprehensive_destinations(self):
        """Test exchange rates for a comprehensive list of destinations."""
        test_method_log = os.path.join(self.logs_dir, f"test_comprehensive_destinations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            country_currency_map = {
                "MX": "MXN",
                "GU": "GTQ",
                "SA": "USD",
                "HO": "HNL",
                "CL": "COP",
                "EC": "USD",
                "PE": "PEN",
                "RP": "DOP",
                "BR": "BRL",
                "AR": "ARS",
                "BO": "BOB",
                "CR": "CRC",
                "CH": "CLP",
                "PA": "PAB",
                "NI": "NIO",
                "ESP": "EUR",
                "IT": "EUR",
                "FRA": "EUR",
                "DEU": "EUR",
                "GRC": "EUR",
                "PRT": "EUR",
                "BG": "BGN",
                "TUR": "TRY",
                "EGY": "EGP",
                "NG": "NGN",
                "GH": "GHS",
                "ET": "ETB",
                "KE": "KES",
                "SN": "XOF",
                "CM": "XAF",
                "IND": "INR",
                "PK": "PKR",
                "PH": "PHP",
                "VN": "VND",
                "TH": "THB",
            }
            
            test_countries = [
                "MX", "GU", "SA", "HO", "CL",
                "EC", "PE", "RP", "BR", "AR",
                "ESP", "IT", "DEU", "TUR",
                "EGY", "NG", "GH",
                "IND", "PH", "TH"
            ]
            
            test_logger.info(f"Testing exchange rates for {len(test_countries)} destinations")
            
            send_country = "USA"
            send_currency = "USD"
            test_amount = Decimal("100.00")
            
            success_count = 0
            failure_count = 0
            
            for receive_country in test_countries:
                receive_currency = country_currency_map.get(receive_country)
                if not receive_currency:
                    test_logger.warning(f"No currency mapping for {receive_country}, skipping")
                    continue
                    
                corridor_label = f"{send_country}_{send_currency}_to_{receive_country}_{receive_currency}"
                test_logger.info(f"Testing exchange rate for corridor: {corridor_label}")
                
                try:
                    rate_data = self.provider.get_exchange_rate(
                        send_amount=test_amount,
                        send_currency=send_currency,
                        receive_country=receive_country,
                        receive_currency=receive_currency,
                        payment_method="CreditCard",
                        delivery_method="BankDeposit"
                    )
                    
                    if rate_data and rate_data.get("exchange_rate") is not None:
                        test_logger.info(f"✓ Exchange rate found: {rate_data.get('exchange_rate')}")
                        test_logger.info(f"  Fee: {rate_data.get('transfer_fee')} {send_currency}")
                        test_logger.info(f"  Receive amount: {rate_data.get('receive_amount')}")
                        
                        self.save_response_data(
                            rate_data,
                            f"exchange_rate_{corridor_label}"
                        )
                        success_count += 1
                    else:
                        test_logger.warning(f"✗ No exchange rate found for {corridor_label}")
                        failure_count += 1
                    
                except Exception as e:
                    test_logger.error(f"Error getting rate for {corridor_label}: {str(e)}")
                    failure_count += 1
                
                time.sleep(2.0)
            
            test_logger.info(f"Test summary: {success_count} successful corridors, {failure_count} failed corridors")
            if success_count > 0:
                self.assertTrue(True, f"Successfully tested {success_count} corridors")
            else:
                self.fail("No corridors were successfully tested")
                
        except Exception as e:
            test_logger.error(f"Test failed: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            
    def test_payment_methods(self):
        """Test retrieving available payment methods for a specific corridor."""
        test_method_log = os.path.join(self.logs_dir, f"test_payment_methods_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing payment methods from USA to TUR")
            
            rate_data = self.provider.get_exchange_rate(
                send_amount=Decimal("100.00"),
                send_currency="USD",
                receive_country="TUR",
                receive_currency="TRY",
                payment_method="CreditCard",
                delivery_method="BankDeposit"
            )
            
            self.assertIsNotNone(rate_data, "Rate data should not be None")
            
            payment_methods = rate_data.get("available_payment_methods", [])
            
            test_logger.info(f"Payment methods: {payment_methods}")
            self.assertIsNotNone(payment_methods, "Payment methods should not be None")
            self.assertGreater(len(payment_methods), 0, "Should have at least one payment method")
            
            saved_file = self.save_response_data(payment_methods, "payment_methods_USA_TUR")
            test_logger.info(f"Saved payment methods to {saved_file}")
            
            for method in payment_methods:
                test_logger.info(f"Method: {method.get('name')} (ID: {method.get('id')}), Fee: {method.get('fee')}")
                
        except Exception as e:
            test_logger.error(f"Unexpected error: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()

if __name__ == "__main__":
    unittest.main() 