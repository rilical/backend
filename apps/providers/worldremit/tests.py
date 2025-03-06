#!/usr/bin/env python3
"""
WorldRemit API integration tests.

This module provides functionality for testing WorldRemit exchange rate calculations.
It supports both direct API calls and using ScrapeOps to bypass PerimeterX protection.

IMPORTANT NOTES:
---------------
1. Direct API calls to WorldRemit are likely to be blocked by PerimeterX with 403 errors
2. If you encounter consistent 403 errors, you have two options:
   a. Use ScrapeOps with a valid API key (set SCRAPEOPS_API_KEY env variable)
   b. Use the test data generator for simulating responses
      
   To use the test data generator:
   ```
   python3 apps/providers/worldremit/generate_test_data.py --test-suite
   # or for individual tests
   python3 apps/providers/worldremit/generate_test_data.py --send-country US --send-currency USD --receive-country MX --receive-currency MXN --amount 500
   ```
   
   This will generate realistic test data in the tests_results_worldremit directory.
"""

import json
import logging
import requests
import uuid
import sys
import time
import os
import argparse
import random
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional, Any, Union, List
from urllib.parse import urlencode

# Create result directories if they don't exist
RESULTS_DIR = "tests_results_worldremit"
LOGS_DIR = os.path.join(RESULTS_DIR, "logs")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Set up logging
log_filename = os.path.join(LOGS_DIR, f"worldremit_test_{int(time.time())}.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("worldremit_test")

# User agent rotation to help bypass protection
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

def make_calculation_request(
    send_country: str,
    send_currency: str,
    receive_country: str,
    receive_currency: str,
    amount: Union[float, Decimal],
    payout_method: Optional[str] = None,
    use_scrapeops: bool = False,
    scrapeops_api_key: Optional[str] = None,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Make a calculation request to the WorldRemit GraphQL API.
    
    Args:
        send_country: The sending country code (e.g., "US")
        send_currency: The sending currency code (e.g., "USD")
        receive_country: The receiving country code (e.g., "MX")
        receive_currency: The receiving currency code (e.g., "MXN")
        amount: The amount to send
        payout_method: Optional payout method code
        use_scrapeops: Whether to use ScrapeOps to bypass PerimeterX protection
        scrapeops_api_key: ScrapeOps API key (required if use_scrapeops is True)
        max_retries: Maximum number of retry attempts for direct API calls
        
    Returns:
        Dict containing the calculation results or error
    """
    # Construct GraphQL query for calculation
    query = """mutation createCalculation(
      $amount: BigDecimal!
        $type: CalculationType!
        $sendCountryCode: CountryCode!
        $sendCurrencyCode: CurrencyCode!
        $receiveCountryCode: CountryCode!
        $receiveCurrencyCode: CurrencyCode!
        $payOutMethodCode: String
        $correspondentId: String
      ) {
        createCalculation(
          calculationInput: {
            amount: $amount
            send: { country: $sendCountryCode, currency: $sendCurrencyCode }
            type: $type
            receive: {
              country: $receiveCountryCode
              currency: $receiveCurrencyCode
            }
            payOutMethodCode: $payOutMethodCode
            correspondentId: $correspondentId
          }
        ) {
          calculation {
            id
            isFree
            informativeSummary {
              fee {
                value {
                  amount
                  currency
                }
                type
              }
              appliedPromotions
              totalToPay {
                amount
              }
            }
            send {
              currency
              amount
            }
            receive {
              amount
              currency
            }
            exchangeRate {
              value
              crossedOutValue
            }
          }
          errors {
            __typename
            ... on GenericCalculationError {
              message
              genericType: type
            }
            ... on ValidationCalculationError {
              message
              type
              code
              description
            }
          }
        }
      }"""
      
    # Construct variables for the GraphQL query
    variables = {
        "amount": amount,
        "type": "SEND",
        "sendCountryCode": send_country,
        "sendCurrencyCode": send_currency,
        "receiveCountryCode": receive_country,
        "receiveCurrencyCode": receive_currency,
        "correspondentId": None
    }
    
    # Add payout method if specified
    if payout_method:
        variables["payOutMethodCode"] = payout_method
    
    # Construct the full GraphQL payload
    payload = {
        "operationName": "createCalculation",
        "variables": variables,
        "query": query
    }
    
    # Define API endpoint - moved here so it's available for both methods
    url = "https://api.worldremit.com/graphql"
    
    # Initial headers for both methods
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.worldremit.com",
        "x-wr-platform": "Web",
        "x-wr-requestid": str(uuid.uuid4()),
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": f"https://www.worldremit.com/en/send-money/{send_country.lower()}/{receive_country.lower()}?lc={send_country.lower()}"
    }
    
    # Make the request (with or without ScrapeOps)
    if use_scrapeops and scrapeops_api_key:
        return make_scrapeops_request(url, payload, headers, scrapeops_api_key)
    else:
        return try_direct_api_request(send_country, receive_country, payload, max_retries)

def try_direct_api_request(
    send_country: str, 
    receive_country: str, 
    payload: Dict, 
    max_retries: int
) -> Dict[str, Any]:
    """Attempt direct API request with multiple retry strategies."""
    
    # API endpoint
    url = "https://api.worldremit.com/graphql"
    
    # Try different strategies
    for attempt in range(max_retries):
        try:
            # Create headers with variations for each attempt
            user_agent = random.choice(USER_AGENTS)
            
            # Create headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://www.worldremit.com",
                "x-wr-platform": "Web",
                "x-wr-requestid": str(uuid.uuid4()),
                "User-Agent": user_agent,
                "Referer": f"https://www.worldremit.com/en/send-money/{send_country.lower()}/{receive_country.lower()}?lc={send_country.lower()}"
            }
            
            # Add random headers to appear more like a browser
            if attempt > 0:
                headers["Sec-Ch-Ua"] = '"Not.A/Brand";v="99", "Google Chrome";v="123", "Chromium";v="123"'
                headers["Sec-Ch-Ua-Mobile"] = "?0"
                headers["Sec-Ch-Ua-Platform"] = '"macOS"'
                headers["Sec-Fetch-Dest"] = "empty"
                headers["Sec-Fetch-Mode"] = "cors"
                headers["Sec-Fetch-Site"] = "same-site"
                headers["Accept-Language"] = "en-US,en;q=0.9"
                
            # Log request details
            logger.debug(f"Attempt {attempt+1}/{max_retries} making GraphQL request to {url}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Payload: {json.dumps(payload)}")
            
            # Add a small random delay to mimic human behavior
            delay = random.uniform(0.5, 2.0)
            time.sleep(delay)
            
            # Make the request with timeout
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Successful response: {json.dumps(result)}")
                return result
            elif response.status_code == 403:
                logger.warning(f"Blocked by PerimeterX (403 status). Attempt {attempt+1}/{max_retries}")
                # If this is not the last attempt, try again with a longer delay
                if attempt < max_retries - 1:
                    longer_delay = random.uniform(2.0, 5.0)
                    logger.info(f"Waiting {longer_delay:.2f} seconds before retry...")
                    time.sleep(longer_delay)
            else:
                logger.error(f"Failed request: {response.status_code}")
                logger.error(f"Response text: {response.text}")
                
                # If we have a non-403 error, it might be a real API error rather than blocking
                return {"error": f"Request failed with status {response.status_code}", "response": response.text}
                
        except Exception as e:
            logger.error(f"Exception during request: {str(e)}")
            
            # Only retry on connection-related errors
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.info(f"Retrying after connection error...")
                    time.sleep(1)
            else:
                return {"error": str(e)}
    
    # If we've exhausted retries
    logger.error("Exhausted all retry attempts, could not access WorldRemit API")
    return {
        "error": "Could not access WorldRemit API after multiple attempts", 
        "details": "Request was likely blocked by PerimeterX protection"
    }

def make_scrapeops_request(url: str, payload: Dict, headers: Dict, api_key: str) -> Dict[str, Any]:
    """
    Make a request through ScrapeOps to bypass PerimeterX protection.
    
    Args:
        url: The API endpoint URL
        payload: The GraphQL payload
        headers: Request headers
        api_key: ScrapeOps API key
        
    Returns:
        Dict containing the response or error
    """
    logger.info("Making request through ScrapeOps to bypass PerimeterX")
    
    # Convert the payload to a string (ScrapeOps requires this)
    json_str = json.dumps(payload)
    
    # Create a simplified version with no extra whitespace for ScrapeOps
    simplified_json = json.dumps(payload, separators=(',', ':'))
    logger.debug(f"Simplified payload: {simplified_json}")
    
    # Convert headers to string
    headers_str = json.dumps(headers)
    
    # ScrapeOps API endpoint
    scrapeops_url = "https://proxy.scrapeops.io/v1/"
    
    # Parameters for ScrapeOps
    params = {
        'api_key': api_key,  # Use the actual API key passed as parameter
        'url': url,
        'bypass': 'perimeterx',
        'render_js': os.environ.get('SCRAPEOPS_RENDER_JS', 'true'),
        'residential': os.environ.get('SCRAPEOPS_USE_RESIDENTIAL', 'true'),
        'method': 'POST',
        'post_content_type': 'application/json',
        'custom_headers': headers_str,
        'post_data': simplified_json
    }
    
    # Log the ScrapeOps parameters (excluding API key for security)
    safe_params = {k: v for k, v in params.items() if k != 'api_key'}
    logger.debug(f"ScrapeOps parameters: {json.dumps(safe_params)}")
    logger.debug(f"Using ScrapeOps API key: {api_key[:4]}...{api_key[-4:]}")
    
    try:
        response = requests.get(scrapeops_url, params=params)
        logger.info(f"ScrapeOps response status: {response.status_code}")
        
        if response.status_code == 200:
            # Parse and return the result
            result = response.json()
            
            # NEW: Add detailed logging of the ScrapeOps response
            logger.debug(f"ScrapeOps raw response content (first 1000 chars): {response.text[:1000]}")
            logger.debug(f"ScrapeOps response content type: {response.headers.get('content-type')}")
            logger.debug(f"ScrapeOps response length: {len(response.text)} characters")
            
            # Log the parsed JSON result
            try:
                logger.debug(f"ScrapeOps parsed JSON: {json.dumps(result, indent=2)}")
            except Exception as e:
                logger.debug(f"Failed to dump JSON result: {e}")
                
            return result
        else:
            logger.error(f"ScrapeOps request failed: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return {"error": f"ScrapeOps request failed with status {response.status_code}", "response": response.text}
    except Exception as e:
        logger.error(f"Exception during ScrapeOps request: {str(e)}")
        return {"error": str(e)}

def extract_calculation_data(response_data: Dict) -> Dict:
    """
    Extract the relevant calculation data from the API response.
    
    Args:
        response_data: The API response data
        
    Returns:
        Dict containing the extracted calculation data or error
    """
    if "error" in response_data:
        return response_data
    
    try:
        # Extract calculation from the response
        calculation = response_data.get("data", {}).get("createCalculation", {}).get("calculation")
        errors = response_data.get("data", {}).get("createCalculation", {}).get("errors", [])
        
        if not calculation and errors:
            # Handle GraphQL errors
            error_messages = [f"{error.get('message', 'Unknown error')}" for error in errors]
            return {"error": "GraphQL error", "details": error_messages}
        
        if not calculation:
            return {"error": "No calculation data found in the response"}
        
        # Extract data from the calculation
        send_amount = calculation.get("send", {}).get("amount")
        send_currency = calculation.get("send", {}).get("currency")
        receive_amount = calculation.get("receive", {}).get("amount")
        receive_currency = calculation.get("receive", {}).get("currency")
        exchange_rate = calculation.get("exchangeRate", {}).get("value")
        fee_amount = calculation.get("informativeSummary", {}).get("fee", {}).get("value", {}).get("amount")
        fee_currency = calculation.get("informativeSummary", {}).get("fee", {}).get("value", {}).get("currency")
        
        # Construct the result
        result = {
            "send": {
                "amount": send_amount,
                "currency": send_currency
            },
            "receive": {
                "amount": receive_amount,
                "currency": receive_currency
            },
            "exchangeRate": exchange_rate,
            "fee": {
                "amount": fee_amount,
                "currency": fee_currency
            },
            "fullCalculation": calculation
        }
        
        return result
    except Exception as e:
        logger.error(f"Error extracting calculation data: {str(e)}")
        return {"error": f"Failed to extract calculation data: {str(e)}"}

def run_test_suite():
    """Run a comprehensive test suite for WorldRemit corridors."""
    timestamp = int(time.time())
    logger.info("\n======================================================================")
    logger.info("WORLDREMIT COMPREHENSIVE TEST SUITE")
    logger.info("======================================================================\n")
    
    # Define test corridors (send_country/currency -> receive_country/currency)
    test_cases = [
        # US to Mexico with different amounts
        {"send_country": "US", "send_currency": "USD", "receive_country": "MX", "receive_currency": "MXN", "amount": 100, "description": "US/USD → MX/MXN (100 USD)"},
        {"send_country": "US", "send_currency": "USD", "receive_country": "MX", "receive_currency": "MXN", "amount": 500, "description": "US/USD → MX/MXN (500 USD)"},
        {"send_country": "US", "send_currency": "USD", "receive_country": "MX", "receive_currency": "MXN", "amount": 1000, "description": "US/USD → MX/MXN (1000 USD)"},
        
        # US to Philippines
        {"send_country": "US", "send_currency": "USD", "receive_country": "PH", "receive_currency": "PHP", "amount": 200, "description": "US/USD → PH/PHP (200 USD)"},
        {"send_country": "US", "send_currency": "USD", "receive_country": "PH", "receive_currency": "PHP", "amount": 500, "description": "US/USD → PH/PHP (500 USD)"},
        
        # Other corridors from US
        {"send_country": "US", "send_currency": "USD", "receive_country": "IN", "receive_currency": "INR", "amount": 500, "description": "US/USD → IN/INR (500 USD)"},
        {"send_country": "US", "send_currency": "USD", "receive_country": "CO", "receive_currency": "COP", "amount": 500, "description": "US/USD → CO/COP (500 USD)"},
        {"send_country": "US", "send_currency": "USD", "receive_country": "VN", "receive_currency": "VND", "amount": 500, "description": "US/USD → VN/VND (500 USD)"},
        
        # UK corridors
        {"send_country": "GB", "send_currency": "GBP", "receive_country": "PH", "receive_currency": "PHP", "amount": 100, "description": "GB/GBP → PH/PHP (100 GBP)"},
        {"send_country": "GB", "send_currency": "GBP", "receive_country": "IN", "receive_currency": "INR", "amount": 100, "description": "GB/GBP → IN/INR (100 GBP)"},
        {"send_country": "GB", "send_currency": "GBP", "receive_country": "NG", "receive_currency": "NGN", "amount": 100, "description": "GB/GBP → NG/NGN (100 GBP)"},
        
        # EU corridors
        {"send_country": "DE", "send_currency": "EUR", "receive_country": "IN", "receive_currency": "INR", "amount": 100, "description": "DE/EUR → IN/INR (100 EUR)"},
        {"send_country": "FR", "send_currency": "EUR", "receive_country": "MA", "receive_currency": "MAD", "amount": 100, "description": "FR/EUR → MA/MAD (100 EUR)"},
    ]
    
    # Get ScrapeOps API key from environment or command line
    scrapeops_api_key = os.environ.get("SCRAPEOPS_API_KEY", "")
    use_scrapeops = bool(scrapeops_api_key) and os.environ.get("USE_SCRAPEOPS", "").lower() in ["true", "1", "yes"]
    
    # Results storage
    results = {
        "timestamp": timestamp,
        "date": datetime.now().isoformat(),
        "total_tests": len(test_cases),
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Run each test case
    for i, test in enumerate(test_cases, 1):
        logger.info(f"Test {i}/{len(test_cases)}: {test['description']}")
        
        # Wait between tests to avoid rate limiting
        if i > 1:
            wait_time = random.uniform(3, 7)  # Random wait between 3-7 seconds
            logger.info(f"Waiting {wait_time:.2f} seconds before next test...")
            time.sleep(wait_time)
        
        # Run the test
        response_data = make_calculation_request(
            send_country=test["send_country"],
            send_currency=test["send_currency"],
            receive_country=test["receive_country"],
            receive_currency=test["receive_currency"],
            amount=test["amount"],
            use_scrapeops=use_scrapeops,
            scrapeops_api_key=scrapeops_api_key,
            max_retries=5  # More retries for test suite
        )
        
        # Extract calculation data
        calculation = extract_calculation_data(response_data)
        
        # Check if test passed
        passed = "error" not in calculation
        
        # Store test result
        test_result = {
            "test_case": test,
            "passed": passed,
            "calculation": calculation
        }
        
        results["tests"].append(test_result)
        
        if passed:
            results["passed"] += 1
            logger.info(f"✅ Passed: {test['description']}")
            
            # Save individual test result
            save_path = f"tests_results_worldremit/{test['send_country']}_{test['send_currency']}_{test['receive_country']}_{test['receive_currency']}_{test['amount']}_{timestamp}.json"
            with open(save_path, "w") as f:
                json.dump(test_result, f, indent=2)
        else:
            results["failed"] += 1
            logger.error(f"❌ Failed: {test['description']}")
    
    # Log test suite summary
    logger.info("\n======================================================================")
    logger.info(f"TEST SUITE SUMMARY: {results['passed']}/{results['total_tests']} tests passed")
    logger.info("======================================================================")
    
    for i, test in enumerate(test_cases, 1):
        test_result = results["tests"][i-1]
        status = "✅ Passed" if test_result["passed"] else "❌ Failed"
        logger.info(f"{status} - Test {i}: {test['description']}")
    
    # Save test suite summary
    summary_path = f"tests_results_worldremit/test_suite_summary_{timestamp}.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nSummary saved to {summary_path}")
    
    return results

def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description='Test WorldRemit calculation')
    
    # Add command-line arguments
    parser.add_argument('--send-country', type=str, help='Sending country code (e.g., US)')
    parser.add_argument('--send-currency', type=str, help='Sending currency code (e.g., USD)')
    parser.add_argument('--receive-country', type=str, help='Receiving country code (e.g., MX)')
    parser.add_argument('--receive-currency', type=str, help='Receiving currency code (e.g., MXN)')
    parser.add_argument('--amount', type=float, default=500.0, help='Amount to send')
    parser.add_argument('--method', type=str, help='Payment method code (optional)')
    parser.add_argument('--scrapeops', action='store_true', help='Use ScrapeOps to bypass PerimeterX protection')
    parser.add_argument('--test-suite', action='store_true', help='Run comprehensive test suite')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries for direct API calls')
    parser.add_argument('--use-test-data', action='store_true', help='Use generated test data instead of live API calls')
    
    args = parser.parse_args()
    
    # Check if running test suite
    if args.test_suite:
        run_test_suite()
        return
    
    # Check required arguments for single test
    if not all([args.send_country, args.send_currency, args.receive_country, args.receive_currency]):
        parser.error('--receive-country and --receive-currency are required when not using --test-suite')
        return
    
    # Log test information
    logger.info("\n======================================================================")
    logger.info("WORLDREMIT CALCULATION TEST")
    logger.info("======================================================================")
    logger.info(f"Send country: {args.send_country}")
    logger.info(f"Send currency: {args.send_currency}")
    logger.info(f"Receive country: {args.receive_country}")
    logger.info(f"Receive currency: {args.receive_currency}")
    logger.info(f"Amount: {args.amount} {args.send_currency}")
    logger.info(f"Payment method: {args.method if args.method else 'Not specified'}")
    logger.info(f"Max retries: {args.max_retries}")
    logger.info(f"Using test data: {args.use_test_data}")
    logger.info("======================================================================\n")
    
    # Get ScrapeOps API key from environment
    scrapeops_api_key = os.environ.get("SCRAPEOPS_API_KEY", "")
    use_scrapeops = args.scrapeops and scrapeops_api_key
    
    if args.scrapeops and not scrapeops_api_key:
        logger.warning("ScrapeOps API key not found in environment. Set SCRAPEOPS_API_KEY environment variable.")
    
    if args.use_test_data:
        # Use the test data generator instead of making API calls
        logger.info("Using test data generator instead of live API calls")
        result = use_test_data_generator(
            send_country=args.send_country,
            send_currency=args.send_currency,
            receive_country=args.receive_country,
            receive_currency=args.receive_currency,
            amount=args.amount,
            method=args.method
        )
        calculation = result
    else:
        # Calculate exchange rate using live API
        logger.info(f"Calculating exchange from {args.send_currency} to {args.receive_currency}...")
        
        response_data = make_calculation_request(
            send_country=args.send_country,
            send_currency=args.send_currency,
            receive_country=args.receive_country,
            receive_currency=args.receive_currency,
            amount=args.amount,
            payout_method=args.method,
            use_scrapeops=use_scrapeops,
            scrapeops_api_key=scrapeops_api_key,
            max_retries=args.max_retries
        )
        
        # Extract calculation data
        calculation = extract_calculation_data(response_data)
    
    # Check if calculation was successful
    if "error" in calculation:
        logger.error(f"\n❌ Calculation failed!\n")
        logger.error(f"Error: {calculation['error']}")
        if 'details' in calculation:
            logger.error(f"Details: {calculation['details']}")
        
        # If API call failed and we're not already using test data, suggest using it
        if not args.use_test_data:
            logger.warning("\nConsider using --use-test-data flag to use the test data generator instead.")
        
        sys.exit(1)
    
    # Log calculation results
    logger.info("\n======================================================================")
    logger.info("CALCULATION RESULTS")
    logger.info("======================================================================")
    logger.info(f"Send: {calculation['send']['amount']} {calculation['send']['currency']}")
    logger.info(f"Receive: {calculation['receive']['amount']} {calculation['receive']['currency']}")
    logger.info(f"Exchange rate: {calculation['exchangeRate']} {calculation['receive']['currency']}/{calculation['send']['currency']}")
    logger.info(f"Fee: {calculation['fee']['amount']} {calculation['fee']['currency']}")
    logger.info("======================================================================\n")
    
    # Save results to JSON file
    timestamp = int(time.time())
    filename = f"tests_results_worldremit/{args.send_currency}_{args.receive_currency}_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(calculation, f, indent=2)
    
    logger.info(f"Results saved to {filename}")
    logger.info("✅ Test completed successfully!\n")

def use_test_data_generator(
    send_country: str,
    send_currency: str,
    receive_country: str,
    receive_currency: str,
    amount: Union[float, Decimal],
    method: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate test data instead of calling the live API.
    This is useful when the API is blocking requests.
    
    Args:
        send_country: The sending country code (e.g., "US")
        send_currency: The sending currency code (e.g., "USD")
        receive_country: The receiving country code (e.g., "MX")
        receive_currency: The receiving currency code (e.g., "MXN")
        amount: The amount to send
        method: Optional payout method code
        
    Returns:
        Dict containing the simulated calculation results
    """
    logger.info(f"Generating test data for {send_currency} to {receive_currency} exchange...")
    
    try:
        # Try to import the generate_test_data module
        import importlib.util
        import sys
        
        spec = importlib.util.spec_from_file_location(
            "generate_test_data", 
            os.path.join(os.path.dirname(__file__), "generate_test_data.py")
        )
        if not spec or not spec.loader:
            raise ImportError("Could not load generate_test_data.py")
            
        generator = importlib.util.module_from_spec(spec)
        sys.modules["generate_test_data"] = generator
        spec.loader.exec_module(generator)
        
        # Create a test case
        method = method or "bank"
        test_case = generator.TestCase(
            send_country=send_country,
            send_currency=send_currency,
            receive_country=receive_country,
            receive_currency=receive_currency,
            amount=float(amount),
            method=method
        )
        
        # Generate the exchange result
        result = generator.calculate_exchange_result(test_case)
        
        # Check if the result is successful
        if not result.get("success", False):
            return {
                "error": "This corridor is currently unavailable in the test data generator",
                "details": result.get("error", {}).get("message", "Unknown error")
            }
        
        # Convert to the format expected by extract_calculation_data
        return {
            "send": result["send"],
            "receive": result["receive"],
            "exchangeRate": result["exchangeRate"],
            "fee": result["fee"],
            "fullCalculation": result["fullCalculation"]
        }
        
    except Exception as e:
        logger.error(f"Error generating test data: {str(e)}")
        return {"error": f"Failed to generate test data: {str(e)}"}

if __name__ == "__main__":
    main() 