"""
RIA Money Transfer API Tests

HOW TO RUN:
python3 -m unittest apps.providers.ria.tests
python3 -m unittest apps.providers.ria.tests.TestRIAProviderRealAPI.test_discover_supported_methods
"""

import json
import logging
import random
import os
import time
import unittest
import traceback
from datetime import datetime
import requests
import pprint
import sys

from apps.providers.ria.integration import RIAProvider, RIAError

class TestRIAProviderRealAPI(unittest.TestCase):
    """Real-API tests for RIA Money Transfer Provider."""

    @classmethod
    def setUpClass(cls):
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
        if hasattr(cls, 'file_handler') and cls.file_handler:
            cls.file_handler.close()
            logging.getLogger().removeHandler(cls.file_handler)
        
        cls.logger.info("Test run completed.")

    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")
        try:
            self.provider = RIAProvider(timeout=30)
            self.logger.debug("Provider initialized successfully")
            
            self.assertIsNotNone(self.provider.bearer_token, "Should have bearer token after initialization")
            self.logger.debug("Current bearer token: %s...", self.provider.bearer_token[:40])
            
            self.calc_init = self.provider.initialize_calculator()
            self.valid_countries = self._get_valid_countries()
            self.logger.debug(f"Found {len(self.valid_countries)} valid country codes")
                
        except Exception as e:
            self.logger.error("Setup failed: %s", str(e), exc_info=True)
            raise

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

    def _get_valid_countries(self):
        """Extract valid country codes from calculator init data"""
        try:
            send_to_field = next(
                field for field in self.calc_init["formData"]["CalculatorForm"]["formFields"] 
                if field["id"] == "SendTo"
            )
            return {opt["value"]: opt["text"] for opt in send_to_field["options"]}
        except (KeyError, StopIteration):
            self.logger.error("Could not extract valid countries from calculator init data")
            return {}

    def _get_send_countries(self):
        """Extract send countries from calculator init data"""
        try:
            send_from_field = next(
                field for field in self.calc_init["formData"]["CalculatorForm"]["formFields"] 
                if field["id"] == "SendFrom"
            )
            return {opt["value"]: opt["text"] for opt in send_from_field["options"]}
        except (KeyError, StopIteration):
            self.logger.error("Could not extract send countries from calculator init data")
            return {"US": "United States"}  # Fallback to US

    def _get_payment_methods(self):
        """Extract available payment methods from calculator init data"""
        try:
            payment_field = next(
                field for field in self.calc_init["formData"]["CalculatorForm"]["formFields"] 
                if field["id"] == "PaymentMethod"
            )
            return [opt["value"] for opt in payment_field["options"]]
        except (KeyError, StopIteration):
            return ["BankAccount", "CreditCard", "DebitCard"]  # Fallback

    def save_response_data(self, data, prefix, error_reason=None):
        """Save JSON response for analysis"""
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

    def test_session_and_calculator_init(self):
        """Test the session token retrieval and calculator initialization flow"""
        test_method_log = os.path.join(self.logs_dir, f"test_session_and_calculator_init_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Starting session token and calculator initialization test")
            
            session_info = self.provider.get_session_info()
            test_logger.info("Session info retrieved successfully")
            self.assertIsNotNone(session_info)
            self.assertIsNotNone(self.provider.bearer_token, "Should have bearer token after session call")
            self.save_response_data(session_info, "session_info")
            
            self.assertIsNotNone(self.calc_init)
            self.assertGreater(len(self.valid_countries), 0, "Should have valid country codes")
            self.save_response_data(self.calc_init, "calculator_init")
            
            test_logger.info("Session token retrieval and calculator initialization successful")
            
            test_logger.info(f"Available receive countries: {', '.join(sorted(self.valid_countries.keys()))}")
            send_countries = self._get_send_countries()
            test_logger.info(f"Available send countries: {', '.join(sorted(send_countries.keys()))}")
            payment_methods = self._get_payment_methods()
            test_logger.info(f"Available payment methods: {', '.join(payment_methods)}")
            
        except Exception as e:
            test_logger.error("Session/calculator test failed: %s", str(e))
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_raw_response_structure(self):
        """Test and expose the actual response structure from a calculate call"""
        test_method_log = os.path.join(self.logs_dir, f"test_raw_response_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            send_country = "US"
            send_currency = "USD"
            receive_country = "MX"
            payment_method = "BankAccount"  
            delivery_method = "BankDeposit"
            
            test_logger.info(f"Testing raw response structure for {send_country}({send_currency})->{receive_country}")
            
            test_logger.info("Getting calculator initialization structure...")
            init_data = self.provider.initialize_calculator()
            
            if "formData" in init_data and "CalculatorForm" in init_data["formData"]:
                form_fields = init_data["formData"]["CalculatorForm"]["formFields"]
                test_logger.info(f"Form fields available: {[field['id'] for field in form_fields]}")
                
                try:
                    delivery_field = next(field for field in form_fields if field["id"] == "DeliveryMethod")
                    test_logger.info(f"Valid delivery methods: {[opt['value'] for opt in delivery_field['options']]}")
                except StopIteration:
                    test_logger.warning("No DeliveryMethod field found in form")
            
            test_logger.info(f"Making calculation with {payment_method}/{delivery_method}")
            result = self.provider.calculate_rate(
                send_amount=500,
                send_currency=send_currency,
                receive_country=receive_country,
                payment_method=payment_method,
                delivery_method=delivery_method,
                send_country=send_country
            )
            
            if result and "raw_response" in result:
                raw_file = self.save_response_data(
                    result["raw_response"], 
                    f"RAW_API_RESPONSE_{send_country}_{send_currency}_to_{receive_country}"
                )
                test_logger.info(f"Full API response structure saved to: {raw_file}")
                
                raw_response = result["raw_response"]
                if isinstance(raw_response, dict):
                    test_logger.info(f"Top-level keys: {', '.join(raw_response.keys())}")
                    
                    if "model" in raw_response:
                        model = raw_response["model"]
                        test_logger.info(f"Model keys: {', '.join(model.keys())}")
                        
                        if "transferDetails" in model:
                            transfer_details = model["transferDetails"]
                            test_logger.info(f"TransferDetails keys: {', '.join(transfer_details.keys())}")
                            
                            if "calculations" in transfer_details:
                                calcs = transfer_details["calculations"]
                                test_logger.info(f"TransferDetails.calculations keys: {', '.join(calcs.keys())}")
                                
                                check_fields = ["exchangeRate", "transferFee", "amountTo", "totalFeesAndTaxes"]
                                for field in check_fields:
                                    test_logger.info(f"TransferDetails.calculations.{field}: {calcs.get(field)}")
                        
                        if "transferDetails" in model and "transferOptions" in model["transferDetails"]:
                            options = model["transferDetails"]["transferOptions"]
                            test_logger.info(f"TransferOptions: {json.dumps(options, indent=2)}")
                    
                    if "calculations" in raw_response:
                        calc = raw_response["calculations"]
                        test_logger.info(f"Direct calculation keys: {', '.join(calc.keys())}")
                        
                        check_fields = ["exchangeRate", "transferFee", "amountTo", "totalFeesAndTaxes"]
                        for field in check_fields:
                            test_logger.info(f"calculations.{field}: {calc.get(field)}")
                    
                    if "statusMessage" in raw_response:
                        test_logger.info(f"Status message: {raw_response['statusMessage']}")
                        
                    if "errorResponse" in raw_response:
                        test_logger.info(f"Error response: {raw_response['errorResponse']}")
            else:
                test_logger.warning("No raw response available in calculation result")
        except Exception as e:
            test_logger.error(f"Failed to test raw response: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_token_refresh(self):
        """Test token refresh when expired"""
        test_method_log = os.path.join(self.logs_dir, f"test_token_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing token refresh when expired")
            
            old_token = self.provider.bearer_token
            test_logger.info(f"Original token: {old_token[:40]}...")
            self.provider.token_expiry = time.time() - 60
            test_logger.info("Forced token expiry by setting token_expiry to 60 seconds ago")
            
            test_logger.info("Making calculation call that should trigger token refresh")
            result = self.provider.calculate_rate(100, "USD", "MX")
            
            test_logger.info(f"New token: {self.provider.bearer_token[:40]}...")
            self.assertIsNotNone(result, "Should get result after token refresh")
            self.assertIsNotNone(self.provider.bearer_token, "Should have new bearer token")
            self.assertNotEqual(old_token, self.provider.bearer_token, "Should have different token after refresh")
            
            test_logger.info("Token refresh test passed")
        except Exception as e:
            test_logger.error("Token refresh test failed: %s", str(e))
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

    def test_discover_supported_methods(self):
        """Discover supported delivery and payment method combinations."""
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
                ("ES", "EUR", "CO"),      # Spain to Colombia
                ("GB", "GBP", "PH"),      # UK to Philippines
                ("IT", "EUR", "RO"),      # Italy to Romania
                ("US", "USD", "DO"),      # US to Dominican Republic
                ("CA", "CAD", "IN"),      # Canada to India
                ("DE", "EUR", "TR"),      # Germany to Turkey
                ("FR", "EUR", "MA")       # France to Morocco
            ]
            
            test_logger.info(f"Testing {len(test_corridors)} corridors with transferOptions discovery approach")
            
            all_results = {}
            
            for send_country, send_currency, receive_country in test_corridors:
                corridor_label = f"{send_country}({send_currency})->{receive_country}"
                test_logger.info(f"Testing corridor: {corridor_label}")
                
                try:
                    test_logger.info(f"Making initial discovery call for {corridor_label}")
                    initial_response = self.provider._do_calculate({
                        "selections": {
                            "countryTo": receive_country.upper(),
                            "amountFrom": 500.0,
                            "amountTo": None,
                            "currencyFrom": send_currency.upper(),
                            "currencyTo": None,
                            "paymentMethod": "DebitCard",
                            "deliveryMethod": "BankDeposit",
                            "shouldCalcAmountFrom": False,
                            "shouldCalcVariableRates": True,
                            "state": None,
                            "agentToId": None,
                            "stateTo": None,
                            "agentToLocationId": None,
                            "promoCode": None,
                            "promoId": 0,
                            "transferReason": None,
                            "countryFrom": send_country.upper()
                        }
                    })
                    
                    discovery_file = self.save_response_data(
                        initial_response, 
                        f"DISCOVERY_{send_country}_{send_currency}_to_{receive_country}"
                    )
                    test_logger.info(f"Discovery response saved to {discovery_file}")
                    
                    transfer_options_data = None
                    
                    if ("model" in initial_response and 
                        "transferDetails" in initial_response["model"] and 
                        "transferOptions" in initial_response["model"]["transferDetails"]):
                        transfer_options_data = initial_response["model"]["transferDetails"]["transferOptions"]
                        test_logger.info(f"Found transferOptions in model.transferDetails.transferOptions")
                    
                    elif "model" in initial_response and "transferOptions" in initial_response["model"]:
                        transfer_options_data = initial_response["model"]["transferOptions"]
                        test_logger.info(f"Found transferOptions in model.transferOptions")
                    elif "transferOptions" in initial_response:
                        transfer_options_data = initial_response["transferOptions"]
                        test_logger.info(f"Found transferOptions in top-level transferOptions")
                    
                    if not transfer_options_data:
                        test_logger.warning(f"No transferOptions found for {corridor_label}. Corridor may not be supported.")
                        all_results[corridor_label] = {
                            "supported": False,
                            "reason": "No transferOptions found",
                            "options": []
                        }
                        continue
                    
                    payment_methods = transfer_options_data.get("paymentMethods", [])
                    delivery_methods = transfer_options_data.get("deliveryMethods", [])
                    
                    test_logger.info(f"Found {len(payment_methods)} payment methods and {len(delivery_methods)} delivery methods")
                    
                    if not payment_methods or not delivery_methods:
                        test_logger.warning(f"Missing payment methods or delivery methods for {corridor_label}")
                        all_results[corridor_label] = {
                            "supported": False,
                            "reason": "Missing required method types",
                            "options": []
                        }
                        continue
                    
                    test_logger.info("Available payment methods:")
                    for pm in payment_methods:
                        test_logger.info(f"  - {pm.get('value')}: {pm.get('text')}")
                    
                    test_logger.info("Available delivery methods:")
                    for dm in delivery_methods:
                        test_logger.info(f"  - {dm.get('value')}: {dm.get('text')}")
                    
                    corridor_results = {
                        "supported": True,
                        "options": []
                    }
                    
                    for pm in payment_methods:
                        for dm in delivery_methods:
                            payment_method = pm.get("value")
                            delivery_method = dm.get("value")
                            option_label = f"{payment_method} + {delivery_method}"
                            
                            extra_fields = {}
                            
                            test_logger.info(f"Testing combination: {option_label}")
                            
                            try:
                                selections = {
                                    "countryTo": receive_country.upper(),
                                    "amountFrom": 500.0,
                                    "amountTo": None,
                                    "currencyFrom": send_currency.upper(),
                                    "currencyTo": None,
                                    "paymentMethod": payment_method,
                                    "deliveryMethod": delivery_method,
                                    "shouldCalcAmountFrom": False,
                                    "shouldCalcVariableRates": True,
                                    "state": None,
                                    "agentToId": None,
                                    "stateTo": None,
                                    "agentToLocationId": None,
                                    "promoCode": None,
                                    "promoId": 0,
                                    "transferReason": None,
                                    "countryFrom": send_country.upper()
                                }
                                
                                selections.update(extra_fields)
                                
                                option_response = self.provider._do_calculate({"selections": selections})
                                
                                if option_response:
                                    model_calcs = option_response.get("model", {}).get("transferDetails", {}).get("calculations", {})
                                    direct_calcs = option_response.get("calculations", {})
                                    
                                    calcs = model_calcs if model_calcs.get("exchangeRate") is not None else direct_calcs
                                    
                                    option_result = {
                                        "paymentMethod": payment_method,
                                        "deliveryMethod": delivery_method,
                                        "extraFields": extra_fields,
                                        "exchangeRate": calcs.get("exchangeRate"),
                                        "transferFee": calcs.get("transferFee"),
                                        "receiveAmount": calcs.get("amountTo"),
                                        "success": calcs.get("exchangeRate") is not None
                                    }
                                    
                                    if option_result["success"]:
                                        test_logger.info(f"Option SUCCESS: XR={option_result['exchangeRate']}, Fee={option_result['transferFee']}")
                                    else:
                                        test_logger.warning(f"Option returned NULL values despite 200 response")
                                    
                                    option_file = self.save_response_data(
                                        option_response,
                                        f"OPTION_{send_country}_{send_currency}_to_{receive_country}_{payment_method}_{delivery_method}"
                                    )
                                    test_logger.debug(f"Option response saved to {option_file}")
                                    
                                    corridor_results["options"].append(option_result)
                                else:
                                    test_logger.warning(f"Option failed with error response")
                                    corridor_results["options"].append({
                                        "paymentMethod": payment_method,
                                        "deliveryMethod": delivery_method,
                                        "extraFields": extra_fields,
                                        "success": False,
                                        "error": "API call failed"
                                    })
                            except Exception as e:
                                test_logger.error(f"Error testing option: {str(e)}")
                                test_logger.error(traceback.format_exc())
                                
                                corridor_results["options"].append({
                                    "paymentMethod": payment_method,
                                    "deliveryMethod": delivery_method,
                                    "extraFields": extra_fields,
                                    "success": False,
                                    "error": str(e)
                                })
                    
                    successful_options = [opt for opt in corridor_results["options"] if opt.get("success", False)]
                    corridor_results["supported"] = len(successful_options) > 0
                    test_logger.info(f"Corridor {corridor_label}: {len(successful_options)} of {len(corridor_results['options'])} options successful")
                    
                    all_results[corridor_label] = corridor_results
                    
                except Exception as e:
                    test_logger.error(f"Failed to test corridor {corridor_label}: {str(e)}")
                    test_logger.error(traceback.format_exc())
                    all_results[corridor_label] = {
                        "supported": False,
                        "error": str(e),
                        "options": []
                    }
                
                time.sleep(1)
            
            summary_file = self.save_response_data(all_results, "DISCOVERY_SUMMARY")
            test_logger.info(f"Complete discovery results saved to {summary_file}")
            
            test_logger.info("=== DISCOVERY SUMMARY ===")
            supported_corridors = [corridor for corridor, results in all_results.items() if results["supported"]]
            test_logger.info(f"Supported corridors: {len(supported_corridors)} of {len(test_corridors)}")
            
            for corridor in supported_corridors:
                working_options = [opt for opt in all_results[corridor]["options"] if opt.get("success", False)]
                test_logger.info(f"  - {corridor}: {len(working_options)} working options")
                for opt in working_options:
                    test_logger.info(f"    * {opt['paymentMethod']} + {opt['deliveryMethod']} → XR: {opt['exchangeRate']}, Fee: {opt['transferFee']}")
            
            test_logger.info("=== END SUMMARY ===")
            
        except Exception as e:
            test_logger.error(f"Discovery test failed: {str(e)}")
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")

if __name__ == "__main__":
    unittest.main()