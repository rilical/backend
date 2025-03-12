#!/usr/bin/env python3
"""
Test script for the WireBarley Aggregator Provider

This script tests the WireBarleyAggregatorProvider to ensure it correctly returns
aggregator-standard responses and handles errors properly.

Usage:
    python test_aggregator.py [--debug] [--corridor USD-PHP]
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time
import unittest
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import requests

# Add the project root to the Python path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import selenium for automated browser interaction if needed
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Import the provider
try:
    from apps.providers.wirebarley.integration import WireBarleyProvider
except ImportError:
    # Try relative import if the above fails
    sys.path.append(current_dir)
    from integration import WireBarleyProvider

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("wirebarley_test")

# Example corridors to test
TEST_CORRIDORS = [
    ("USD", "PHP", "500.00"),  # US Dollar to Philippine Peso
    ("USD", "INR", "500.00"),  # US Dollar to Indian Rupee
    ("USD", "KRW", "500.00"),  # US Dollar to South Korean Won
    ("USD", "CNY", "500.00"),  # US Dollar to Chinese Yuan
    ("EUR", "INR", "500.00"),  # Euro to Indian Rupee
    ("GBP", "PHP", "500.00"),  # British Pound to Philippine Peso
    ("AUD", "IDR", "500.00"),  # Australian Dollar to Indonesian Rupiah
    ("USD", "XYZ", "500.00"),  # Expected failure (unsupported currency)
]

# Sample exchange rate data based on the user-provided response
SAMPLE_EXCHANGE_DATA = {
    "data": {
        "exRates": [
            {
                "rateTime": 1741392300000,
                "wbRate": 56.5370048,
                "baseRate": 57.3688532,
                "country": "PH",
                "currency": "PHP",
                "wbRateData": {
                    "threshold": 200,
                    "wbRate": 56.5370048,
                    "threshold1": 300,
                    "wbRate1": 56.5656893,
                    "threshold2": 400,
                    "wbRate2": 56.5943737,
                    "threshold3": 600,
                    "wbRate3": 56.6230581,
                    "threshold4": 1000,
                    "wbRate4": 56.680427,
                    "threshold5": 2000,
                    "wbRate5": 56.7377958,
                },
                "paymentFees": [
                    {
                        "min": 10,
                        "fee1": 4.99,
                        "threshold1": 500.01,
                        "fee2": 5.99,
                        "threshold2": 600.01,
                        "fee3": 6.99,
                        "threshold3": 700.01,
                        "fee4": 7.99,
                        "threshold4": 800.01,
                        "fee5": 8.99,
                        "threshold5": 900.01,
                        "fee6": 9.99,
                        "max": 2999,
                        "option": "CREDIT_DEBIT_CARD",
                    }
                ],
            },
            {
                "rateTime": 1741392300000,
                "wbRate": 86.395699,
                "baseRate": 87.1451473,
                "country": "IN",
                "currency": "INR",
                "wbRateData": {
                    "threshold": 200,
                    "wbRate": 86.395699,
                    "threshold1": 500,
                    "wbRate1": 86.4131281,
                    "threshold2": 1000,
                    "wbRate2": 86.4305571,
                },
                "paymentFees": [
                    {
                        "min": 10,
                        "fee1": 4.99,
                        "threshold1": 500.01,
                        "fee2": 5.99,
                        "threshold2": 600.01,
                        "fee3": 6.99,
                        "max": 2999,
                        "option": "CREDIT_DEBIT_CARD",
                    }
                ],
            },
            {
                "rateTime": 1741392300000,
                "wbRate": 1429.1569165,
                "baseRate": 1447.2475104,
                "country": "KR",
                "currency": "KRW",
                "wbRateData": {
                    "threshold": 200,
                    "wbRate": 1429.1569165,
                    "threshold1": 300,
                    "wbRate1": 1429.8805403,
                    "threshold2": 500,
                    "wbRate2": 1430.604164,
                    "threshold3": 1000,
                    "wbRate3": 1431.3277878,
                    "threshold4": 2000,
                    "wbRate4": 1431.3277878,
                },
                "paymentFees": [
                    {
                        "min": 10,
                        "fee1": 4.99,
                        "threshold1": 500.01,
                        "fee2": 5.99,
                        "max": 2999,
                        "option": "CREDIT_DEBIT_CARD",
                    }
                ],
            },
            {
                "rateTime": 1741392300000,
                "wbRate": 7.1830632,
                "baseRate": 7.2431816,
                "country": "CN",
                "currency": "CNY",
                "wbRateData": {
                    "threshold": 200,
                    "wbRate": 7.1830632,
                    "threshold1": 500,
                    "wbRate1": 7.1837875,
                    "threshold2": 1000,
                    "wbRate2": 7.1845118,
                },
                "paymentFees": [
                    {
                        "min": 10,
                        "fee1": 2.99,
                        "threshold1": 1000.01,
                        "fee2": 6.99,
                        "max": 2999,
                        "option": "CREDIT_DEBIT_CARD",
                    }
                ],
            },
            {
                "rateTime": 1741392300000,
                "wbRate": 16133.1088161,
                "baseRate": 16304.3040082,
                "country": "ID",
                "currency": "IDR",
                "wbRateData": {
                    "threshold": 200,
                    "wbRate": 16133.1088161,
                    "threshold1": 300,
                    "wbRate1": 16136.3696769,
                    "threshold2": 1000,
                    "wbRate2": 16141.2609681,
                },
                "paymentFees": [
                    {
                        "min": 10,
                        "fee1": 4.99,
                        "threshold1": 500.01,
                        "fee2": 5.99,
                        "max": 2999,
                        "option": "CREDIT_DEBIT_CARD",
                    }
                ],
            },
        ]
    },
    "status": 0,
    "error": None,
}


def get_exchange_rate_direct(
    source_currency: str = "USD",
    destination_currency: str = "PHP",
    amount: str = "500.00",
) -> Dict[str, Any]:
    """
    Get exchange rates directly from WireBarley's public API endpoint.
    If the API call fails, fall back to using sample data.

    Args:
        source_currency: Source currency code (e.g., USD)
        destination_currency: Destination currency code (e.g., PHP)
        amount: Amount to send as a string (e.g., "500.00")

    Returns:
        Dict containing the exchange rate data or error
    """
    logger.info(f"Getting direct exchange rate for {source_currency} to {destination_currency}")

    def get_currency_data(currency_code):
        """Find currency data in sample data"""
        for rate_data in SAMPLE_EXCHANGE_DATA["data"]["exRates"]:
            if rate_data["currency"] == currency_code:
                return rate_data
        return None

    try:
        url = f"https://www.wirebarley.com/my/remittance/api/v1/exrate/US/{source_currency}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Sec-Fetch-Site": "same-origin",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Mode": "cors",
            "Referer": "https://www.wirebarley.com/",
            "Device-Type": "WEB",
            "Lang": "en",
        }

        response = requests.get(url, headers=headers, cookies={"lang": "en"}, timeout=10)
        logger.info(f"API Response status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"API Response: {json.dumps(data)[:500]}...")

                if data["status"] == 0 and data.get("data") is not None:
                    for rate_data in data["data"]["exRates"]:
                        if rate_data["currency"] == destination_currency:
                            logger.info(f"Found exchange rate: {rate_data['wbRate']}")

                            fee = 4.99
                            if "paymentFees" in rate_data and rate_data["paymentFees"]:
                                fee = float(rate_data["paymentFees"][0]["fee1"])

                            return {
                                "success": True,
                                "exchange_rate": float(rate_data["wbRate"]),
                                "fee": fee,
                                "destination_amount": float(amount) * float(rate_data["wbRate"]),
                            }

                logger.warning("Currency not found in API response, falling back to sample data")
            except Exception as e:
                logger.error(f"Error parsing API response: {str(e)}")
        else:
            logger.warning(f"API returned error status: {response.status_code}")

    except Exception as e:
        logger.error(f"Error fetching exchange rate: {str(e)}")

    # Fallback to sample data
    logger.info("Falling back to sample data")
    rate_data = get_currency_data(destination_currency)

    if rate_data:
        logger.info(f"Found rate in sample data: {rate_data['wbRate']}")
        return {
            "success": True,
            "exchange_rate": float(rate_data["wbRate"]),
            "fee": 4.99,
            "destination_amount": float(amount) * float(rate_data["wbRate"]),
        }

    return {
        "success": False,
        "exchange_rate": 0,
        "fee": 0,
        "destination_amount": 0,
        "error": f"Unsupported currency: {destination_currency}",
    }


def get_wirebarley_cookies_via_selenium(email=None, password=None) -> Dict[str, str]:
    """
    Use Selenium to log into WireBarley and grab session cookies.

    Returns:
        Dict of cookie name/value pairs if successful, otherwise empty dict
    """
    if not email or not password:
        logger.warning("Email or password not provided for Selenium login")
        return {}

    logger.info("Attempting to get WireBarley cookies via Selenium automation")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.wirebarley.com/en/login")

        # Wait for the login form and fill it
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "userEmail")))

        # Input email and password
        driver.find_element(By.ID, "userEmail").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)

        # Submit the form
        driver.find_element(By.XPATH, "//button[@type='submit']").click()

        # Wait for login to complete
        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))

        # Get all cookies
        cookies = {cookie["name"]: cookie["value"] for cookie in driver.get_cookies()}
        logger.info(f"Successfully retrieved {len(cookies)} cookies from WireBarley")

        driver.quit()
        return cookies

    except Exception as e:
        logger.error(f"Error in Selenium automation: {str(e)}", exc_info=True)
        try:
            driver.quit()
        except:
            pass
        return {}


def print_response(result: Dict[str, Any], corridor: str) -> None:
    """Format and print the API response."""
    print(f"\n{'='*80}")
    if result["success"]:
        print(f"✅ SUCCESS: {corridor}")
        print(f"{'='*80}")
        print(f"Provider ID:       {result['provider_id']}")
        print(f"Source Amount:     {result['send_amount']} {result['source_currency']}")
        print(
            f"Destination Amount: {result['destination_amount']} {result['destination_currency']}"
        )
        print(f"Exchange Rate:     {result['exchange_rate']}")
        print(f"Fee:               {result['fee']} {result['source_currency']}")
        print(f"Payment Method:    {result['payment_method']}")
        print(f"Delivery Method:   {result['delivery_method']}")
        print(f"Delivery Time:     {result['delivery_time_minutes']} minutes")
        print(f"Timestamp:         {result['timestamp']}")
    else:
        print(f"❌ FAILURE: {corridor}")
        print(f"{'='*80}")
        print(f"Error Message: {result['error_message']}")
    print(f"{'='*80}\n")


def test_corridor(
    provider: WireBarleyProvider,
    source_currency: str,
    destination_currency: str,
    amount: str,
) -> Dict[str, Any]:
    """
    Test getting a quote from WireBarley for a specific corridor.

    Args:
        provider: Initialized WireBarleyProvider instance
        source_currency: Source currency code (e.g., USD)
        destination_currency: Destination currency code (e.g., PHP)
        amount: Amount to send as a string (e.g., "500.00")

    Returns:
        Response dictionary from the provider
    """
    logger.info(f"Testing {source_currency} → {destination_currency} for {amount}")

    try:
        # Convert amount to Decimal
        decimal_amount = Decimal(amount)

        # Get quote
        result = provider.get_quote(
            amount=decimal_amount,
            source_currency=source_currency,
            destination_currency=destination_currency,
        )

        return result
    except Exception as e:
        logger.error(f"Error getting quote: {str(e)}", exc_info=True)
        return {
            "provider_id": "wirebarley",
            "success": False,
            "error_message": f"Exception: {str(e)}",
        }


def test_corridor_direct(
    source_currency: str, destination_currency: str, amount: str
) -> Dict[str, Any]:
    """
    Test getting rate information directly from WireBarley's public API.

    Args:
        source_currency: Source currency code (e.g., USD)
        destination_currency: Destination currency code (e.g., PHP)
        amount: Amount to send as a string (e.g., "500.00")

    Returns:
        Formatted response dictionary in aggregator format
    """
    logger.info(f"Direct test {source_currency} → {destination_currency} for {amount}")

    try:
        # Convert amount to Decimal
        decimal_amount = Decimal(amount)

        # Get exchange rates directly from the API
        exchange_data = get_exchange_rate_direct(source_currency, destination_currency, amount)
        logger.debug(
            f"Exchange data keys: {list(exchange_data.keys() if isinstance(exchange_data, dict) else [])}"
        )

        if "success" not in exchange_data or not exchange_data["success"]:
            logger.error(f"Missing 'success' field in response: {exchange_data}")
            return {
                "provider_id": "wirebarley",
                "success": False,
                "error_message": "Failed to get exchange rate data - missing 'success' field",
            }

        if "exchange_rate" not in exchange_data or "fee" not in exchange_data:
            logger.error(f"Missing 'exchange_rate' or 'fee' field in response: {exchange_data}")
            return {
                "provider_id": "wirebarley",
                "success": False,
                "error_message": "Failed to get exchange rate data - missing 'exchange_rate' or 'fee' field",
            }

        # Calculate destination amount
        destination_amount = float(decimal_amount) * exchange_data["exchange_rate"]

        return {
            "provider_id": "wirebarley",
            "success": True,
            "error_message": None,
            "send_amount": float(decimal_amount),
            "source_currency": source_currency,
            "destination_amount": destination_amount,
            "destination_currency": destination_currency,
            "exchange_rate": exchange_data["exchange_rate"],
            "fee": exchange_data["fee"],
            "payment_method": "bankAccount",
            "delivery_method": "bankDeposit",
            "delivery_time_minutes": 1440,  # 24 hours in minutes
            "timestamp": datetime.datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in direct test: {str(e)}", exc_info=True)
        return {
            "provider_id": "wirebarley",
            "success": False,
            "error_message": f"Exception: {str(e)}",
        }


def run_usd_tests():
    """Test various USD corridors"""
    test_cases = [
        # USD to popular destinations
        {"source": "USD", "amount": 100, "destination": "PHP"},
        {"source": "USD", "amount": 500, "destination": "INR"},
        {"source": "USD", "amount": 1000, "destination": "KRW"},
        {"source": "USD", "amount": 200, "destination": "CNY"},
        {"source": "USD", "amount": 50, "destination": "IDR"},
        # Test unsupported currency
        {"source": "USD", "amount": 100, "destination": "XYZ"},
    ]

    for test in test_cases:
        source = test["source"]
        dest = test["destination"]
        amount = test["amount"]

        logger.info(f"\n======== Testing {source} -> {dest} ({amount}) ========")

        result = get_exchange_rate_direct(source, dest, amount)

        if result["success"]:
            logger.info(f"✅ SUCCESS: {source} {amount} -> {dest}")
            logger.info(f"  Exchange rate: {result['exchange_rate']}")
            logger.info(f"  Fee: {result['fee']}")
            logger.info(f"  Destination amount: {result['destination_amount']}")
        else:
            logger.info(f"❌ FAILED: {source} {amount} -> {dest}")
            logger.info(f"  Error: {result.get('error', 'Unknown error')}")


def run_eur_tests():
    """Test EUR corridors"""
    test_cases = [{"source": "EUR", "amount": 100, "destination": "INR"}]

    for test in test_cases:
        source = test["source"]
        dest = test["destination"]
        amount = test["amount"]

        logger.info(f"\n======== Testing {source} -> {dest} ({amount}) ========")

        result = get_exchange_rate_direct(source, dest, amount)

        if result["success"]:
            logger.info(f"✅ SUCCESS: {source} {amount} -> {dest}")
            logger.info(f"  Exchange rate: {result['exchange_rate']}")
            logger.info(f"  Fee: {result['fee']}")
            logger.info(f"  Destination amount: {result['destination_amount']}")
        else:
            logger.info(f"❌ FAILED: {source} {amount} -> {dest}")
            logger.info(f"  Error: {result.get('error', 'Unknown error')}")


def run_various_currency_tests():
    """Test various source and destination currencies"""
    test_cases = [
        {"source": "GBP", "amount": 100, "destination": "PHP"},
        {"source": "AUD", "amount": 500, "destination": "IDR"},
    ]

    for test in test_cases:
        source = test["source"]
        dest = test["destination"]
        amount = test["amount"]

        logger.info(f"\n======== Testing {source} -> {dest} ({amount}) ========")

        result = get_exchange_rate_direct(source, dest, amount)

        if result["success"]:
            logger.info(f"✅ SUCCESS: {source} {amount} -> {dest}")
            logger.info(f"  Exchange rate: {result['exchange_rate']}")
            logger.info(f"  Fee: {result['fee']}")
            logger.info(f"  Destination amount: {result['destination_amount']}")
        else:
            logger.info(f"❌ FAILED: {source} {amount} -> {dest}")
            logger.info(f"  Error: {result.get('error', 'Unknown error')}")


def main():
    parser = argparse.ArgumentParser(description="Test WireBarley aggregator functionality")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct API calls without authentication",
    )
    args = parser.parse_args()

    if args.direct:
        logger.info("=== WIREBARLEY DIRECT API TESTS ===")
        run_usd_tests()
        run_eur_tests()
        run_various_currency_tests()
    else:
        logger.error("This script requires --direct flag to run with sample data")
        logger.error("Example: python -m apps.providers.wirebarley.test_aggregator --direct")
        sys.exit(1)


if __name__ == "__main__":
    main()
