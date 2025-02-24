"""
RIA Money Transfer API Tests

HOW TO RUN THESE TESTS PROPERLY:
---------------------------------
To run all tests:
    python3 -m unittest apps.providers.ria.tests

To run the most reliable test that discovers supported delivery methods:
    python3 -m unittest apps.providers.ria.tests.TestRIAProviderRealAPI.test_discover_supported_methods

To run a specific test:
    python3 -m unittest apps.providers.ria.tests.TestRIAProviderRealAPI.<test_method_name>

NOTE: Using 'python3 -m unittest apps/providers/ria/tests.py' will NOT work correctly.
      Always use dot notation (apps.providers.ria.tests) not file paths with slashes.
"""

import json
import logging
import random
import os
import time
import unittest
from datetime import datetime
import requests
import pprint
import sys
import traceback

from apps.providers.ria.integration import RIAProvider, RIAError

class TestRIAProviderRealAPI(unittest.TestCase):
    """
    Real-API tests for RIA Money Transfer Provider.
    Tests the session-based token retrieval and calculator flow.
    """

    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        cls.results_dir = "test_results_ria"
        cls.logs_dir = os.path.join(cls.results_dir, "logs")
        
        # Create both directories
        os.makedirs(cls.results_dir, exist_ok=True)
        os.makedirs(cls.logs_dir, exist_ok=True)
        
        # Set up a root file handler to capture all logs
        root_log_file = os.path.join(cls.logs_dir, f"ria_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"=== Starting test: {self._testMethodName} ===")
        self.logger.info("Initializing RIAProvider (will get token from /Authorization/session)")
        try:
            self.provider = RIAProvider(timeout=30)
            self.logger.debug("Provider initialized successfully")
            
            # Verify we got a bearer token
            self.assertIsNotNone(self.provider.bearer_token, "Should have bearer token after initialization")
            self.logger.debug("Current bearer token: %s...", self.provider.bearer_token[:40])
            
            # Get calculator init data to validate country codes
            self.calc_init = self.provider.initialize_calculator()
            self.valid_countries = self._get_valid_countries()
            self.logger.debug(f"Found {len(self.valid_countries)} valid country codes")
            
        except Exception as e:
            self.logger.error("Setup failed: %s", str(e), exc_info=True)
            raise

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
        
        # Create a file handler specific to this test
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Starting session token and calculator initialization test")
            
            # Test session info and token retrieval
            session_info = self.provider.get_session_info()
            test_logger.info("Session info retrieved successfully")
            self.assertIsNotNone(session_info)
            self.assertIsNotNone(self.provider.bearer_token, "Should have bearer token after session call")
            self.save_response_data(session_info, "session_info")
            
            # Test calculator init and validate country list
            test_logger.info("Initializing calculator")
            self.assertIsNotNone(self.calc_init)
            self.assertGreater(len(self.valid_countries), 0, "Should have valid country codes")
            self.save_response_data(self.calc_init, "calculator_init")
            
            test_logger.info("Session token retrieval and calculator initialization successful")
            
            # Log all available countries
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

    # NOTE: This test method is kept for reference but may not work reliably.
    # Use test_discover_supported_methods instead for better results.
    def test_available_delivery_methods(self):
        """Discover available delivery methods for each corridor"""
        test_method_log = os.path.join(self.logs_dir, f"test_available_delivery_methods_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Create a file handler specific to this test
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            # Test key corridors that had issues
            test_corridors = [
                ("US", "USD", "MX"),  # US to Mexico
                ("US", "USD", "PH"),  # US to Philippines 
                ("US", "USD", "IN"),  # US to India
                ("ES", "EUR", "CO"),  # Spain to Colombia
                ("GB", "GBP", "PH"),  # UK to Philippines
                ("IT", "EUR", "RO"),  # Italy to Romania
                ("US", "USD", "DO"),  # US to Dominican Republic
            ]
            
            test_logger.info(f"Testing {len(test_corridors)} corridors for delivery methods")
            
            for send_country, send_currency, receive_country in test_corridors:
                test_label = f"{send_country}({send_currency})->{receive_country}"
                test_logger.info(f"Testing delivery methods for corridor: {test_label}")
                
                try:
                    # First, try a direct calculation to inspect response structure
                    test_logger.info(f"Making initial calculation for {test_label}")
                    result = self.provider.calculate_rate(
                        send_amount=500,
                        send_currency=send_currency,
                        receive_country=receive_country,
                        payment_method="DebitCard",  # Most common
                        delivery_method="BankDeposit",  # Most common
                        send_country=send_country
                    )
                    
                    # Log the response to understand the response structure
                    if result:
                        test_logger.info(f"Initial calculation for {test_label} successful")
                        if "raw_response" in result:
                            # Save the full raw response to examine its structure
                            raw_response = result["raw_response"] 
                            raw_file = self.save_response_data(
                                raw_response,
                                f"RAW_{send_country}_{send_currency}_to_{receive_country}"
                            )
                            test_logger.info(f"Raw response saved to {raw_file}")
                            
                            # Check which field contains calculations
                            if "model" in raw_response and "transferDetails" in raw_response["model"] and "calculations" in raw_response["model"]["transferDetails"]:
                                model_calcs = raw_response["model"]["transferDetails"]["calculations"]
                                test_logger.debug(f"Found calculations in model.transferDetails.calculations: {list(model_calcs.keys())}")
                                test_logger.debug(f"Exchange rate: {model_calcs.get('exchangeRate')}")
                                test_logger.debug(f"Transfer fee: {model_calcs.get('transferFee')}")
                            
                            if "calculations" in raw_response:
                                direct_calcs = raw_response["calculations"]
                                test_logger.debug(f"Found calculations in top-level: {list(direct_calcs.keys())}")
                                test_logger.debug(f"Exchange rate: {direct_calcs.get('exchangeRate')}")
                                
                            # Check for delivery methods info in the response
                            if "transferOptions" in raw_response.get("model", {}).get("transferDetails", {}):
                                options = raw_response["model"]["transferDetails"]["transferOptions"]
                                test_logger.info(f"Found transfer options: {options}")
                    else:
                        test_logger.warning(f"Initial calculation for {test_label} returned no results")
                    
                    # Now try all delivery methods
                    test_logger.info(f"Retrieving all available delivery methods for {test_label}")
                    delivery_methods = self.provider.get_available_delivery_methods(
                        receive_country=receive_country,
                        send_country=send_country
                    )
                    
                    # Save the complete delivery methods data
                    methods_file = self.save_response_data(
                        delivery_methods,
                        f"METHODS_{send_country}_{send_currency}_to_{receive_country}"
                    )
                    test_logger.info(f"Delivery methods saved to {methods_file}")
                    
                    # Log summary of available methods
                    supported_methods = [method for method, data in delivery_methods.items() 
                                        if data["supported"]]
                    
                    test_logger.info(f"Corridor {test_label} supports {len(supported_methods)} delivery methods: {', '.join(supported_methods)}")
                    
                    # For each supported method, log details
                    for method, data in delivery_methods.items():
                        if data["supported"]:
                            payment_methods = data["working_payment_methods"]
                            test_logger.info(f"  - {method}: Works with {', '.join(payment_methods)}")
                            
                            # Try a calculation with known working method
                            if payment_methods:
                                try:
                                    test_logger.info(f"Testing calculation for {test_label} with {method} and {payment_methods[0]}")
                                    result = self.provider.calculate_rate(
                                        send_amount=500,  # Increased amount
                                        send_currency=send_currency,
                                        receive_country=receive_country,
                                        payment_method=payment_methods[0],
                                        delivery_method=method,
                                        send_country=send_country
                                    )
                                    
                                    # Save the result regardless of nulls
                                    calc_file = self.save_response_data(
                                        result,
                                        f"CALC_{send_country}_{send_currency}_to_{receive_country}_{method}"
                                    )
                                    test_logger.info(f"Calculation result saved to {calc_file}")
                                    
                                    # Check for nulls and analyze the response
                                    if result:
                                        has_nulls = any(
                                            result[field] is None for field in 
                                            ["exchange_rate", "transfer_fee", "receive_amount"]
                                        )
                                        
                                        if has_nulls and "raw_response" in result:
                                            raw = result["raw_response"]
                                            test_logger.warning(f"Null values in response for {method}! Checking raw structure...")
                                            
                                            # Check both possible locations for calculations
                                            model_calcs = raw.get("model", {}).get("transferDetails", {}).get("calculations", {})
                                            direct_calcs = raw.get("calculations", {})
                                            
                                            test_logger.warning(f"model.transferDetails.calculations: {model_calcs if model_calcs else 'None'}")
                                            test_logger.warning(f"top-level calculations: {direct_calcs if direct_calcs else 'None'}")
                                            
                                            # Check status message
                                            if "statusMessage" in raw:
                                                test_logger.warning(f"Status message: {raw['statusMessage']}")
                                            
                                            # Check for error response
                                            if "errorResponse" in raw:
                                                test_logger.warning(f"Error response: {raw['errorResponse']}")
                                except Exception as e:
                                    test_logger.error(f"Error testing calculation for {method}: {str(e)}")
                                    test_logger.error(traceback.format_exc())
                    
                except Exception as e:
                    test_logger.error(f"Failed to test methods for {test_label}: {str(e)}")
                    test_logger.error(traceback.format_exc())
                finally:
                    test_logger.info(f"Completed testing corridor {test_label}")
                    time.sleep(1)  # Brief pause between corridors
                
            test_logger.info("Delivery methods discovery test completed")
            
        except Exception as e:
            test_logger.error("Test failed: %s", str(e))
            test_logger.error(traceback.format_exc())
            raise
        finally:
            test_logger.removeHandler(file_handler)
            file_handler.close()
            test_logger.info(f"Test logs saved to: {test_method_log}")
            
    def test_raw_response_structure(self):
        """Test and expose the actual response structure from a calculate call"""
        test_method_log = os.path.join(self.logs_dir, f"test_raw_response_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Create a file handler specific to this test
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            # Use a corridor that we know works
            send_country = "US"
            send_currency = "USD"
            receive_country = "MX"
            payment_method = "BankAccount"  
            delivery_method = "BankDeposit"
            
            test_logger.info(f"Testing raw response structure for {send_country}({send_currency})->{receive_country}")
            
            # First, check the options structure
            test_logger.info("Getting calculator initialization structure...")
            init_data = self.provider.initialize_calculator()
            
            # Analyze the form fields to understand valid options
            if "formData" in init_data and "CalculatorForm" in init_data["formData"]:
                form_fields = init_data["formData"]["CalculatorForm"]["formFields"]
                test_logger.info(f"Form fields available: {[field['id'] for field in form_fields]}")
                
                # Log valid delivery methods from form
                try:
                    delivery_field = next(field for field in form_fields if field["id"] == "DeliveryMethod")
                    test_logger.info(f"Valid delivery methods: {[opt['value'] for opt in delivery_field['options']]}")
                except StopIteration:
                    test_logger.warning("No DeliveryMethod field found in form")
            
            # Make a calculation call
            test_logger.info(f"Making calculation with {payment_method}/{delivery_method}")
            result = self.provider.calculate_rate(
                send_amount=500,
                send_currency=send_currency,
                receive_country=receive_country,
                payment_method=payment_method,
                delivery_method=delivery_method,
                send_country=send_country
            )
            
            # Output the full raw response structure
            if result and "raw_response" in result:
                # Save the raw API response
                raw_file = self.save_response_data(
                    result["raw_response"], 
                    f"RAW_API_RESPONSE_{send_country}_{send_currency}_to_{receive_country}"
                )
                test_logger.info(f"Full API response structure saved to: {raw_file}")
                
                # Log the top-level keys
                raw_response = result["raw_response"]
                if isinstance(raw_response, dict):
                    test_logger.info(f"Top-level keys: {', '.join(raw_response.keys())}")
                    
                    # Check model structure (which appears to contain most data)
                    if "model" in raw_response:
                        model = raw_response["model"]
                        test_logger.info(f"Model keys: {', '.join(model.keys())}")
                        
                        # Check for transferDetails which contains most important data
                        if "transferDetails" in model:
                            transfer_details = model["transferDetails"]
                            test_logger.info(f"TransferDetails keys: {', '.join(transfer_details.keys())}")
                            
                            # Check calculations in transferDetails
                            if "calculations" in transfer_details:
                                calcs = transfer_details["calculations"]
                                test_logger.info(f"TransferDetails.calculations keys: {', '.join(calcs.keys())}")
                                
                                # Important fields to check
                                check_fields = ["exchangeRate", "transferFee", "amountTo", "totalFeesAndTaxes"]
                                for field in check_fields:
                                    test_logger.info(f"TransferDetails.calculations.{field}: {calcs.get(field)}")
                        
                        # Check for transferOptions
                        if "transferDetails" in model and "transferOptions" in model["transferDetails"]:
                            options = model["transferDetails"]["transferOptions"]
                            test_logger.info(f"TransferOptions: {json.dumps(options, indent=2)}")
                    
                    # Check direct calculations object (mostly obsolete but kept for compatibility)
                    if "calculations" in raw_response:
                        calc = raw_response["calculations"]
                        test_logger.info(f"Direct calculation keys: {', '.join(calc.keys())}")
                        
                        # Important fields to check
                        check_fields = ["exchangeRate", "transferFee", "amountTo", "totalFeesAndTaxes"]
                        for field in check_fields:
                            test_logger.info(f"calculations.{field}: {calc.get(field)}")
                    
                    # Check status message 
                    if "statusMessage" in raw_response:
                        test_logger.info(f"Status message: {raw_response['statusMessage']}")
                        
                    # Check error response
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
        
        # Create a file handler specific to this test
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            test_logger.info("Testing token refresh when expired")
            
            # Force token expiry
            old_token = self.provider.bearer_token
            test_logger.info(f"Original token: {old_token[:40]}...")
            self.provider.token_expiry = time.time() - 60
            test_logger.info("Forced token expiry by setting token_expiry to 60 seconds ago")
            
            # Make a call that should trigger refresh
            test_logger.info("Making calculation call that should trigger token refresh")
            result = self.provider.calculate_rate(100, "USD", "MX")
            
            # Verify we got a new token
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
        """
        Discover actually supported delivery and payment method combinations
        by parsing transferOptions from the initial response.
        
        This is the RECOMMENDED test method for detecting available methods,
        as it uses the proper API response structure to check what's supported.
        """
        test_method_log = os.path.join(self.logs_dir, f"test_discover_supported_methods_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Create a file handler specific to this test
        file_handler = logging.FileHandler(test_method_log)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        test_logger = logging.getLogger(f"{__name__}.{self._testMethodName}")
        test_logger.addHandler(file_handler)
        test_logger.setLevel(logging.DEBUG)
        
        try:
            # Test key corridors 
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
                
                # Step 1: Make initial calculation with default parameters
                try:
                    test_logger.info(f"Making initial discovery call for {corridor_label}")
                    initial_response = self.provider._do_calculate({
                        "selections": {
                            "countryTo": receive_country.upper(),
                            "amountFrom": 500.0,  # Higher amount to increase success chance
                            "amountTo": None,
                            "currencyFrom": send_currency.upper(),
                            "currencyTo": None,
                            "paymentMethod": "DebitCard",  # Default payment method
                            "deliveryMethod": "BankDeposit", # Default delivery method
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
                    
                    # Save the raw discovery response
                    discovery_file = self.save_response_data(
                        initial_response, 
                        f"DISCOVERY_{send_country}_{send_currency}_to_{receive_country}"
                    )
                    test_logger.info(f"Discovery response saved to {discovery_file}")
                    
                    # Step 2: Check for transferOptions in the response
                    transfer_options_data = None
                    
                    # Check in model.transferDetails.transferOptions (correct location based on response)
                    if ("model" in initial_response and 
                        "transferDetails" in initial_response["model"] and 
                        "transferOptions" in initial_response["model"]["transferDetails"]):
                        transfer_options_data = initial_response["model"]["transferDetails"]["transferOptions"]
                        test_logger.info(f"Found transferOptions in model.transferDetails.transferOptions")
                    
                    # Alternative locations to check
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
                    
                    # Extract payment methods and delivery methods from transferOptions
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
                    
                    # Log the available methods
                    test_logger.info("Available payment methods:")
                    for pm in payment_methods:
                        test_logger.info(f"  - {pm.get('value')}: {pm.get('text')}")
                    
                    test_logger.info("Available delivery methods:")
                    for dm in delivery_methods:
                        test_logger.info(f"  - {dm.get('value')}: {dm.get('text')}")
                    
                    # Step 3: Test each combination of payment method and delivery method
                    corridor_results = {
                        "supported": True,
                        "options": []
                    }
                    
                    for pm in payment_methods:
                        for dm in delivery_methods:
                            payment_method = pm.get("value")
                            delivery_method = dm.get("value")
                            option_label = f"{payment_method} + {delivery_method}"
                            
                            # We don't have extra fields like agentToId in this approach,
                            # but we could add them if needed
                            extra_fields = {}
                            
                            test_logger.info(f"Testing combination: {option_label}")
                            
                            # Step 4: Try calculation with this specific combination
                            try:
                                # Create selections with the payment and delivery methods
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
                                
                                # Update with any extra fields
                                selections.update(extra_fields)
                                
                                option_response = self.provider._do_calculate({"selections": selections})
                                
                                if option_response:
                                    # Check for calculations in both possible locations
                                    model_calcs = option_response.get("model", {}).get("transferDetails", {}).get("calculations", {})
                                    direct_calcs = option_response.get("calculations", {})
                                    
                                    # Use whichever has exchange rate
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
                                    
                                    # Log success/failure and relevant details
                                    if option_result["success"]:
                                        test_logger.info(f"Option SUCCESS: XR={option_result['exchangeRate']}, Fee={option_result['transferFee']}")
                                    else:
                                        test_logger.warning(f"Option returned NULL values despite 200 response")
                                    
                                    # Save the detailed response
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
                    
                    # Determine if any options actually worked
                    successful_options = [opt for opt in corridor_results["options"] if opt.get("success", False)]
                    corridor_results["supported"] = len(successful_options) > 0
                    test_logger.info(f"Corridor {corridor_label}: {len(successful_options)} of {len(corridor_results['options'])} options successful")
                    
                    # Save the corridor results
                    all_results[corridor_label] = corridor_results
                    
                except Exception as e:
                    test_logger.error(f"Failed to test corridor {corridor_label}: {str(e)}")
                    test_logger.error(traceback.format_exc())
                    all_results[corridor_label] = {
                        "supported": False,
                        "error": str(e),
                        "options": []
                    }
                
                # Brief pause between corridors
                time.sleep(1)
            
            # Step 5: Save the complete results and summarize findings
            summary_file = self.save_response_data(all_results, "DISCOVERY_SUMMARY")
            test_logger.info(f"Complete discovery results saved to {summary_file}")
            
            # Print a summary of supported corridors and methods
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