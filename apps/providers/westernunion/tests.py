"""
Western Union Money Transfer API Tests

HOW TO RUN:
python3 -m unittest apps.providers.westernunion.tests
python3 -m unittest apps.providers.westernunion.tests.TestWesternUnionProviderRealAPI.test_discover_supported_methods
"""

import json
import logging
import random
import os
import time
import unittest
import traceback
from datetime import datetime
from decimal import Decimal

from apps.providers.westernunion.integration import WesternUnionProvider
from apps.providers.westernunion.exceptions import (
    WUError,
    WUAuthenticationError,
    WUValidationError,
    WUConnectionError
)

class TestWesternUnionProviderRealAPI(unittest.TestCase):
    """Real-API tests for Western Union Provider."""

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        
        cls.results_dir = "test_results_wu"
        cls.logs_dir = os.path.join(cls.results_dir, "logs")
        
        os.makedirs(cls.results_dir, exist_ok=True)
        os.makedirs(cls.logs_dir, exist_ok=True)
        
        root_log_file = os.path.join(cls.logs_dir, f"wu_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
        self.provider = WesternUnionProvider(timeout=30)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")

    def tearDown(self):
        test_log_file = os.path.join(self.logs_dir, f"{self._testMethodName}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.logger.info(f"=== Ending test: {self._testMethodName} ===")
        
        if hasattr(self, 'provider') and hasattr(self.provider, 'logger'):
            try:
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
        """Saves the JSON response to a timestamped file for reference."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/{prefix}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        self.logger.info(f"Saved response data to: {filename}")
        return filename

    def assertValidRateData(self, rate_data: dict):
        """Basic verification that required fields exist and are non-negative."""
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

    def test_discover_supported_methods(self):
        """Discover supported delivery methods and payment combinations."""
        test_method_log = os.path.join(self.logs_dir, f"test_discover_supported_methods_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_corridors = [
                ("US", "USD", "MX"),      # US to Mexico
                ("US", "USD", "PH"),      # US to Philippines 
                ("US", "USD", "IN"),      # US to India
                ("GB", "GBP", "IN"),      # UK to India
                ("CA", "CAD", "PH"),      # Canada to Philippines
                ("DE", "EUR", "TR"),      # Germany to Turkey
                ("AU", "AUD", "PH"),      # Australia to Philippines
                ("FR", "EUR", "MA"),      # France to Morocco
                ("IT", "EUR", "NG"),      # Italy to Nigeria
                ("ES", "EUR", "CO")       # Spain to Colombia
            ]
            
            test_logger.info(f"Testing {len(test_corridors)} corridors to discover supported delivery methods")
            
            all_results = {}
            
            for send_country, send_currency, receive_country in test_corridors:
                corridor_label = f"{send_country}({send_currency})->{receive_country}"
                test_logger.info(f"Testing corridor: {corridor_label}")
                
                try:
                    test_logger.info(f"Making initial catalog request for {corridor_label}")
                    
                    test_amount = Decimal("500.00")
                    
                    catalog_data = self.provider.get_catalog_data(
                        send_amount=test_amount,
                        send_currency=send_currency,
                        receive_country=receive_country,
                        send_country=send_country
                    )
                    
                    catalog_file = self.save_response_data(
                        catalog_data, 
                        f"CATALOG_{send_country}_{send_currency}_to_{receive_country}"
                    )
                    test_logger.info(f"Catalog response saved to {catalog_file}")
                    
                    service_groups = catalog_data.get("services_groups", [])
                    
                    if not service_groups:
                        test_logger.warning(f"No service groups found for {corridor_label}")
                        all_results[corridor_label] = {
                            "supported": False,
                            "reason": "No service groups found",
                            "options": []
                        }
                        continue
                    
                    test_logger.info(f"Found {len(service_groups)} service groups")
                    
                    delivery_methods = {}
                    for group in service_groups:
                        service_name = group.get("service_name", "Unknown")
                        service_code = group.get("service", "Unknown")
                        delivery_methods[service_code] = {
                            "name": service_name,
                            "payment_methods": []
                        }
                        
                        for pay_group in group.get("pay_groups", []):
                            pay_method = pay_group.get("fund_in", "Unknown")
                            pay_method_name = pay_group.get("fund_in_name", pay_method)
                            
                            if pay_method not in delivery_methods[service_code]["payment_methods"]:
                                delivery_methods[service_code]["payment_methods"].append({
                                    "code": pay_method,
                                    "name": pay_method_name
                                })
                    
                    test_logger.info(f"Available delivery methods for {corridor_label}:")
                    for code, details in delivery_methods.items():
                        payment_methods = [pm["name"] for pm in details["payment_methods"]]
                        test_logger.info(f"  - {details['name']} ({code}): {', '.join(payment_methods)}")
                    
                    test_amounts = [50, 200, 500, 1000]
                    corridor_results = {
                        "supported": True,
                        "delivery_methods": {},
                        "test_results": []
                    }
                    
                    for service_code, service_details in delivery_methods.items():
                        service_name = service_details["name"]
                        test_logger.info(f"Testing delivery method: {service_name} ({service_code})")
                        
                        corridor_results["delivery_methods"][service_code] = {
                            "name": service_name,
                            "payment_methods": {},
                            "successful_tests": 0,
                            "failed_tests": 0
                        }
                        
                        for payment_method in service_details["payment_methods"]:
                            pay_code = payment_method["code"]
                            pay_name = payment_method["name"]
                            test_logger.info(f"  Testing payment method: {pay_name} ({pay_code})")
                            
                            corridor_results["delivery_methods"][service_code]["payment_methods"][pay_code] = {
                                "name": pay_name,
                                "results": []
                            }
                            
                            for amount in test_amounts:
                                test_label = f"{corridor_label} {amount}{send_currency} via {service_name}/{pay_name}"
                                test_logger.info(f"    Testing amount: {amount} {send_currency}")
                                
                                try:
                                    catalog_specific = self.provider.get_catalog_data(
                                        send_amount=Decimal(str(amount)),
                                        send_currency=send_currency,
                                        receive_country=receive_country,
                                        send_country=send_country
                                    )
                                    
                                    result = None
                                    for group in catalog_specific.get("services_groups", []):
                                        if group.get("service") == service_code:
                                            for pay_group in group.get("pay_groups", []):
                                                if pay_group.get("fund_in") == pay_code:
                                                    fx_rate = float(pay_group.get("fx_rate", 0))
                                                    fee = float(pay_group.get("gross_fee", 0))
                                                    receive_amount = float(pay_group.get("receive_amount", 0))
                                                    
                                                    if fx_rate > 0 and receive_amount > 0:
                                                        result = {
                                                            "amount": amount,
                                                            "exchange_rate": fx_rate,
                                                            "fee": fee,
                                                            "receive_amount": receive_amount,
                                                            "delivery_days": group.get("speed_days", "Unknown"),
                                                            "success": True
                                                        }
                                                        test_logger.info(f"    SUCCESS: XR={fx_rate}, Fee={fee}, Receive={receive_amount}")
                                                        corridor_results["delivery_methods"][service_code]["successful_tests"] += 1
                                                    else:
                                                        result = {
                                                            "amount": amount,
                                                            "success": False,
                                                            "reason": "Invalid rate or receive amount"
                                                        }
                                                        test_logger.warning(f"    FAILED: Invalid rate or receive amount")
                                                        corridor_results["delivery_methods"][service_code]["failed_tests"] += 1
                                    
                                    if not result:
                                        result = {
                                            "amount": amount,
                                            "success": False,
                                            "reason": "Service/payment combination not found"
                                        }
                                        test_logger.warning(f"    FAILED: Service/payment combination not found")
                                        corridor_results["delivery_methods"][service_code]["failed_tests"] += 1
                                    
                                    corridor_results["delivery_methods"][service_code]["payment_methods"][pay_code]["results"].append(result)
                                    corridor_results["test_results"].append({
                                        "corridor": corridor_label,
                                        "amount": amount,
                                        "service_code": service_code,
                                        "service_name": service_name,
                                        "payment_code": pay_code,
                                        "payment_name": pay_name,
                                        "result": result
                                    })
                                    
                                except Exception as e:
                                    test_logger.error(f"    ERROR testing {test_label}: {str(e)}")
                                    test_logger.error(traceback.format_exc())
                                    
                                    corridor_results["delivery_methods"][service_code]["payment_methods"][pay_code]["results"].append({
                                        "amount": amount,
                                        "success": False,
                                        "error": str(e)
                                    })
                                    corridor_results["delivery_methods"][service_code]["failed_tests"] += 1
                                
                                time.sleep(random.uniform(1.0, 2.0))
                            
                            time.sleep(random.uniform(1.0, 1.5))
                    
                    all_results[corridor_label] = corridor_results
                    
                except Exception as e:
                    test_logger.error(f"Failed to test corridor {corridor_label}: {str(e)}")
                    test_logger.error(traceback.format_exc())
                    all_results[corridor_label] = {
                        "supported": False,
                        "error": str(e)
                    }
                
                time.sleep(random.uniform(3.0, 5.0))
            
            summary_file = self.save_response_data(all_results, "WU_DISCOVERY_SUMMARY")
            test_logger.info(f"Complete discovery results saved to {summary_file}")
            
            test_logger.info("\n=== DELIVERY METHOD DISCOVERY SUMMARY ===")
            supported_corridors = [corridor for corridor, results in all_results.items() 
                                if results.get("supported", False)]
            
            test_logger.info(f"Tested {len(test_corridors)} corridors, {len(supported_corridors)} supported")
            
            for corridor in supported_corridors:
                results = all_results[corridor]
                if "delivery_methods" not in results:
                    continue
                    
                total_successful = sum(
                    method.get("successful_tests", 0) 
                    for method in results["delivery_methods"].values()
                )
                total_failed = sum(
                    method.get("failed_tests", 0) 
                    for method in results["delivery_methods"].values()
                )
                
                test_logger.info(f"\n{corridor}:")
                test_logger.info(f"  Total tests: {total_successful + total_failed}")
                test_logger.info(f"  Successful: {total_successful}")
                test_logger.info(f"  Failed: {total_failed}")
                
                for service_code, service_data in results["delivery_methods"].items():
                    success_rate = 0
                    if service_data["successful_tests"] + service_data["failed_tests"] > 0:
                        success_rate = (service_data["successful_tests"] * 100) / (
                            service_data["successful_tests"] + service_data["failed_tests"]
                        )
                    
                    test_logger.info(f"  - {service_data['name']} ({service_code}): " +
                                   f"{service_data['successful_tests']} successes, " +
                                   f"{service_data['failed_tests']} failures " +
                                   f"({success_rate:.1f}% success rate)")
                    
                    for pay_code, pay_data in service_data["payment_methods"].items():
                        successful_results = [r for r in pay_data["results"] if r.get("success", False)]
                        if successful_results:
                            test_logger.info(f"    * {pay_data['name']} ({pay_code}): {len(successful_results)} successful tests")
                            
                            if successful_results:
                                best_result = max(successful_results, key=lambda x: x.get("exchange_rate", 0))
                                test_logger.info(f"      Best rate: {best_result.get('exchange_rate')} " +
                                               f"Fee: {best_result.get('fee')} " +
                                               f"Send: {best_result.get('amount')} " +
                                               f"Receive: {best_result.get('receive_amount')}")
            
            test_logger.info("\n=== SUPPORTED METHODS SUMMARY ===")
            corridor_methods = {}
            
            for corridor, results in all_results.items():
                if not results.get("supported", False) or "delivery_methods" not in results:
                    continue
                
                corridor_methods[corridor] = []
                
                for service_code, service_data in results["delivery_methods"].items():
                    if service_data["successful_tests"] > 0:
                        working_payment_methods = []
                        for pay_code, pay_data in service_data["payment_methods"].items():
                            if any(r.get("success", False) for r in pay_data["results"]):
                                working_payment_methods.append(pay_data["name"])
                        
                        corridor_methods[corridor].append({
                            "delivery_method": service_data["name"],
                            "payment_methods": working_payment_methods
                        })
            
            for corridor, methods in corridor_methods.items():
                test_logger.info(f"\n{corridor}:")
                for method in methods:
                    test_logger.info(f"  - {method['delivery_method']}: {', '.join(method['payment_methods'])}")
            
            test_logger.info("\n=== END SUMMARY ===")
            
        except Exception as e:
            test_logger.error(f"Discovery test failed: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_20_valid_combinations(self):
        """Test 20 different valid combinations of send countries, currencies, and receive countries."""
        test_method_log = os.path.join(self.logs_dir, f"test_20_valid_combinations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
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
        """Test 5 invalid input combinations that should fail gracefully."""
        test_method_log = os.path.join(self.logs_dir, f"test_5_invalid_inputs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            invalid_scenarios = [
                (-100, "USD", "MX", "US"),
                (5000, "???", "EG", "US"),
                (400, "USD", "XX", "US"),
                (400, "XYZ", "EG", "US"),
                (-50, "GBP", "ZZ", "GB"),
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
