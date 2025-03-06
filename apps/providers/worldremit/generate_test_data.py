#!/usr/bin/env python3
"""
Generate simulated WorldRemit test data for testing purposes.
This script creates realistic test data for WorldRemit corridor calculations
when direct API access is not available or blocked by PerimeterX.
"""

import os
import json
import argparse
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
log_dir = "tests_results_worldremit/logs"
os.makedirs(log_dir, exist_ok=True)
output_dir = "tests_results_worldremit"
os.makedirs(output_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{log_dir}/generate_test_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Exchange rate data based on realistic values (as of early 2025)
EXCHANGE_RATES = {
    ("USD", "MXN"): 20.0199,
    ("USD", "PHP"): 56.6706,
    ("USD", "INR"): 83.2067,
    ("USD", "COP"): 3910.52,
    ("USD", "NGN"): 1507.86,
    ("USD", "GHS"): 15.4328,
    ("USD", "VND"): 24915.65,
    ("USD", "KES"): 128.75,
    ("USD", "USD"): 1.0,  # For dollarized countries like El Salvador and Ecuador
    ("GBP", "MXN"): 25.3241,
    ("GBP", "PHP"): 72.0327,
    ("GBP", "INR"): 105.5666,
    ("GBP", "NGN"): 1915.23,
    ("GBP", "VND"): 31632.42,
    ("GBP", "GHS"): 19.5873,
    ("GBP", "KES"): 163.42,
    ("EUR", "MXN"): 21.5467,
    ("EUR", "PHP"): 61.2378,
    ("EUR", "INR"): 89.7341,
    ("CAD", "PHP"): 41.2815,
    ("CAD", "INR"): 60.6308,
    ("AUD", "PHP"): 37.8945,
    ("AUD", "INR"): 55.6892,
    ("NZD", "PHP"): 34.5726,
    ("SGD", "PHP"): 42.6834,
}

# Fee structure based on send amount ranges
def calculate_fee(amount: float, currency: str) -> float:
    """Calculate the fee based on the send amount and currency."""
    if currency == "USD":
        if amount <= 100:
            return 0.99
        elif amount <= 300:
            return 1.49
        else:
            return 1.99
    elif currency == "GBP":
        if amount <= 50:
            return 0.79
        elif amount <= 150:
            return 0.99
        else:
            return 1.29
    elif currency == "EUR":
        if amount <= 100:
            return 0.89
        elif amount <= 250:
            return 1.39
        else:
            return 1.89
    else:
        # Default fee for other currencies
        return amount * 0.004  # 0.4% fee

# Test case definition
class TestCase:
    def __init__(self, send_country: str, send_currency: str, 
                 receive_country: str, receive_currency: str,
                 amount: float, method: str = "bank"):
        self.send_country = send_country
        self.send_currency = send_currency
        self.receive_country = receive_country
        self.receive_currency = receive_currency
        self.amount = amount
        self.method = method
        
    def __str__(self) -> str:
        return (f"{self.send_country}({self.send_currency}) → "
                f"{self.receive_country}({self.receive_currency}): "
                f"{self.amount} {self.send_currency} via {self.method}")

# Test corridors with representative combinations
TEST_CORRIDORS = [
    # US to various countries
    TestCase("US", "USD", "MX", "MXN", 100),
    TestCase("US", "USD", "MX", "MXN", 300),
    TestCase("US", "USD", "MX", "MXN", 500),
    TestCase("US", "USD", "PH", "PHP", 200),
    TestCase("US", "USD", "PH", "PHP", 500),
    TestCase("US", "USD", "IN", "INR", 250),
    TestCase("US", "USD", "IN", "INR", 500),
    # UK to various countries
    TestCase("GB", "GBP", "PH", "PHP", 50),
    TestCase("GB", "GBP", "PH", "PHP", 100),
    TestCase("GB", "GBP", "IN", "INR", 100),
    # Additional corridors (adding more to reach 20+)
    TestCase("US", "USD", "VN", "VND", 300),      # US to Vietnam
    TestCase("US", "USD", "GH", "GHS", 250),      # US to Ghana
    TestCase("GB", "GBP", "GH", "GHS", 150),      # UK to Ghana
    TestCase("GB", "GBP", "MX", "MXN", 200),      # UK to Mexico
    TestCase("GB", "GBP", "VN", "VND", 100),      # UK to Vietnam
    TestCase("CA", "CAD", "PH", "PHP", 300),      # Canada to Philippines
    TestCase("CA", "CAD", "IN", "INR", 200),      # Canada to India
    TestCase("AU", "AUD", "PH", "PHP", 250),      # Australia to Philippines
    TestCase("AU", "AUD", "IN", "INR", 300),      # Australia to India
    TestCase("NZ", "NZD", "PH", "PHP", 200),      # New Zealand to Philippines
    TestCase("SG", "SGD", "PH", "PHP", 150),      # Singapore to Philippines
    TestCase("US", "USD", "SV", "USD", 150),      # US to El Salvador (USD)
    TestCase("US", "USD", "EC", "USD", 200),      # US to Ecuador (USD)
    TestCase("US", "USD", "KE", "KES", 300),      # US to Kenya
    TestCase("GB", "GBP", "KE", "KES", 150),      # UK to Kenya
    # Failed corridors - would usually fail in real API
    TestCase("US", "USD", "CO", "COP", 300),
    TestCase("GB", "GBP", "NG", "NGN", 100),
    # Invalid currency in destination country - would usually fail
    TestCase("US", "USD", "DE", "USD", 200),
    TestCase("GB", "GBP", "FR", "GBP", 150),
]

def generate_transaction_id() -> str:
    """Generate a realistic transaction ID."""
    chars = "abcdef0123456789"
    return ''.join(random.choice(chars) for _ in range(32))

def calculate_exchange_result(test_case: TestCase) -> Dict[str, Any]:
    """Calculate exchange result for the given test case."""
    key = (test_case.send_currency, test_case.receive_currency)
    
    # Check if this is a corridor that should fail
    should_fail = False
    if test_case.receive_country in ["CO", "NG"]:
        should_fail = True  # Some corridors are typically problematic
    
    # Check for invalid currency for country
    if (test_case.receive_country == "DE" and test_case.receive_currency == "USD") or \
       (test_case.receive_country == "FR" and test_case.receive_currency == "GBP"):
        should_fail = True  # Invalid currency for country
    
    # Random failure for realism (10% chance)
    if random.random() < 0.1 and not should_fail:
        should_fail = True
    
    if should_fail or key not in EXCHANGE_RATES:
        return {
            "success": False,
            "error": {
                "message": "This corridor is currently unavailable.",
                "code": "CORRIDOR_UNAVAILABLE"
            }
        }
    
    # Calculate the exchange
    exchange_rate = EXCHANGE_RATES[key]
    fee = calculate_fee(test_case.amount, test_case.send_currency)
    
    # Add a small random variation to the exchange rate for realism
    variation = random.uniform(-0.0015, 0.0015)  # ±0.15%
    actual_rate = exchange_rate * (1 + variation)
    
    # Round to 4 decimal places
    actual_rate = round(actual_rate, 4)
    
    # Calculate receive amount
    receive_amount = round(test_case.amount * actual_rate, 2)
    
    # Generate the response
    response = {
        "success": True,
        "send": {
            "amount": test_case.amount,
            "currency": test_case.send_currency
        },
        "receive": {
            "amount": receive_amount,
            "currency": test_case.receive_currency
        },
        "exchangeRate": actual_rate,
        "fee": {
            "amount": fee,
            "currency": test_case.send_currency
        },
        "fullCalculation": {
            "id": generate_transaction_id(),
            "sendData": {
                "country": test_case.send_country,
                "currency": test_case.send_currency,
                "amount": test_case.amount
            },
            "receiveData": {
                "country": test_case.receive_country,
                "currency": test_case.receive_currency,
                "amount": receive_amount,
                "method": test_case.method
            },
            "fee": fee,
            "totalToPay": test_case.amount + fee,
            "appliedPromotions": [],
            "exchangeRate": actual_rate,
            "timestamp": int(time.time())
        },
        "timestamp": int(time.time()),
        "test_parameters": {
            "send_country": test_case.send_country,
            "send_currency": test_case.send_currency,
            "receive_country": test_case.receive_country,
            "receive_currency": test_case.receive_currency,
            "amount": test_case.amount,
            "method": test_case.method
        }
    }
    
    return response

def run_single_test(test_case: TestCase) -> Dict[str, Any]:
    """Run a single test and return the result."""
    logger.info(f"Generating test data for {test_case}")
    result = calculate_exchange_result(test_case)
    
    # Save the result to file
    filename = (f"{output_dir}/{test_case.send_currency}_"
               f"{test_case.receive_currency}_"
               f"{int(time.time())}.json")
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Test result saved to {filename}")
    return result

def run_test_suite() -> Dict[str, Any]:
    """Run the entire test suite and generate a summary."""
    logger.info("Starting test suite simulation")
    
    timestamp = int(time.time())
    date_str = datetime.utcfromtimestamp(timestamp).isoformat() + ".000Z"
    
    results = []
    passed = 0
    failed = 0
    
    for test_case in TEST_CORRIDORS:
        result = calculate_exchange_result(test_case)
        
        if result["success"]:
            passed += 1
        else:
            failed += 1
        
        results.append({
            "test_case": {
                "send_country": test_case.send_country,
                "send_currency": test_case.send_currency,
                "receive_country": test_case.receive_country,
                "receive_currency": test_case.receive_currency,
                "amount": test_case.amount,
                "method": test_case.method,
                "description": str(test_case)
            },
            "passed": result["success"],
            "calculation": result
        })
    
    # Create summary
    summary = {
        "timestamp": timestamp,
        "date": date_str,
        "total_tests": len(TEST_CORRIDORS),
        "passed": passed,
        "failed": failed,
        "tests": results
    }
    
    # Save the summary
    summary_filename = f"{output_dir}/test_suite_summary_{timestamp}.json"
    with open(summary_filename, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Test suite completed: {passed} passed, {failed} failed")
    logger.info(f"Summary saved to {summary_filename}")
    
    return summary

def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Generate simulated WorldRemit test data")
    parser.add_argument("--test-suite", action="store_true", help="Run the complete test suite")
    parser.add_argument("--send-country", help="Sending country code (e.g., US)")
    parser.add_argument("--send-currency", help="Sending currency code (e.g., USD)")
    parser.add_argument("--receive-country", help="Receiving country code (e.g., MX)")
    parser.add_argument("--receive-currency", help="Receiving currency code (e.g., MXN)")
    parser.add_argument("--amount", type=float, help="Amount to send")
    parser.add_argument("--method", default="bank", help="Payment method (bank, cash, mobile)")
    
    args = parser.parse_args()
    
    if args.test_suite:
        run_test_suite()
    elif all([args.send_country, args.send_currency, args.receive_country, args.receive_currency, args.amount]):
        test_case = TestCase(
            args.send_country,
            args.send_currency,
            args.receive_country,
            args.receive_currency,
            args.amount,
            args.method
        )
        run_single_test(test_case)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 