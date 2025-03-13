#!/usr/bin/env python3
"""
Intermex Provider Test Script

This script tests the Intermex integration by making live API calls.
"""

import logging
import sys
from decimal import Decimal
from typing import Any, Dict

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("intermex-test")


def get_headers() -> Dict[str, str]:
    """Get required headers for API requests."""
    return {
        "Pragma": "no-cache",
        "Accept": "application/json, text/plain, */*",
        "Sec-Fetch-Site": "cross-site",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Sec-Fetch-Mode": "cors",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.intermexonline.com",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
        "Referer": "https://www.intermexonline.com/",
        "Sec-Fetch-Dest": "empty",
        "PartnerId": "1",
        "ChannelId": "1",
        "Priority": "u=3, i",
        "Ocp-Apim-Subscription-Key": "2162a586e2164623a1cd9b6b2d300b4c",
        "LanguageId": "1",
    }


def test_get_delivery_and_payments() -> Dict[str, Any]:
    """Test the delivery and payments endpoint."""
    url = "https://api.imxi.com/pricing/api/deliveryandpayments"

    params = {
        "DestCountryAbbr": "MX",
        "DestCurrency": "MXN",
        "OriCountryAbbr": "USA",
        "OriCurrency": "USD",
        "OriStateAbbr": "PA",
    }

    try:
        response = requests.get(url, headers=get_headers(), params=params)
        response.raise_for_status()

        data = response.json()
        logger.info("Delivery and Payments Response:")
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {data}")

        return {"success": True, "data": data}

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get delivery and payments: {e}")
        return {"success": False, "error": str(e)}


def test_get_fees_rates(amount: Decimal = Decimal("1.00")) -> Dict[str, Any]:
    """Test the fees and rates endpoint."""
    url = "https://api.imxi.com/pricing/api/v2/feesrates"

    params = {
        "DestCountryAbbr": "MX",
        "DestCurrency": "MXN",
        "OriCountryAbbr": "USA",
        "OriStateAbbr": "PA",
        "StyleId": "3",
        "TranTypeId": "1",
        "DeliveryType": "W",
        "OriCurrency": "USD",
        "ChannelId": "1",
        "OriAmount": str(amount),
        "DestAmount": "0",
        "SenderPaymentMethodId": "3",
    }

    try:
        response = requests.get(url, headers=get_headers(), params=params)
        response.raise_for_status()

        data = response.json()
        logger.info("\nFees and Rates Response:")
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {data}")

        return {"success": True, "data": data}

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get fees and rates: {e}")
        return {"success": False, "error": str(e)}


def test_different_amounts():
    """Test getting quotes for different amounts."""
    amounts = [1.00, 100.00, 500.00, 1000.00]

    for amount in amounts:
        logger.info(f"\nTesting amount: ${amount}")
        result = test_get_fees_rates(Decimal(str(amount)))

        if result["success"]:
            data = result["data"]
            logger.info(f"Exchange Rate: {data.get('rate', 'N/A')}")
            logger.info(f"Fee Amount: ${data.get('feeAmount', 'N/A')}")
            logger.info(f"Total Cost: ${data.get('totalAmount', 'N/A')}")
            logger.info(f"Send Amount: ${data.get('origAmount', 'N/A')}")
            logger.info(f"Receive Amount: {data.get('destAmount', 'N/A')} MXN")

            # Log available payment methods
            payment_methods = data.get("paymentMethods", [])
            if payment_methods:
                logger.info("\nAvailable Payment Methods:")
                for method in payment_methods:
                    logger.info(f"- {method['senderPaymentMethodName']}: ${method['feeAmount']}")
        else:
            logger.error(f"Failed to get quote for amount {amount}: {result['error']}")


def main():
    """Run all tests."""
    logger.info("=== Testing Intermex Integration ===")

    # Test delivery and payment methods
    logger.info("\nTesting delivery and payment methods...")
    delivery_result = test_get_delivery_and_payments()

    if not delivery_result["success"]:
        logger.error("Failed to get delivery and payment methods")
        return

    # Test different amounts
    logger.info("\nTesting different amounts...")
    test_different_amounts()


if __name__ == "__main__":
    main()
