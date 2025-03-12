#!/usr/bin/env python3
"""
Combined test script for XE Money Transfer API integration.
This script tests the XE Money Transfer API endpoints with live API calls.
"""

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime
from decimal import Decimal

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("xe_api_test")

# XE API endpoints
API_BASE_URL = "https://www.xe.com"
MIDMARKET_RATES_URL = "https://www.xe.com/api/protected/midmarket-converter/"
QUOTES_API_URL = "https://launchpad-api.xe.com/v2/quotes"
CONVERTER_URL = "https://www.xe.com/currencyconverter/convert/"
MONEY_TRANSFER_URL = "https://www.xe.com/xemoneytransfer/send/"


def test_midmarket_rates():
    """Test the midmarket rates endpoint"""
    logger.info("Testing midmarket rates endpoint...")

    try:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
                "Accept": "application/json",
            }
        )

        resp = session.get(MIDMARKET_RATES_URL, timeout=15)
        status_code = resp.status_code

        logger.info(f"Midmarket rates endpoint status: {status_code}")

        if status_code == 200:
            data = resp.json()
            logger.info(f"Response contains {len(data.get('rates', {}))} rates")
            logger.info(f"Example rates: {list(data.get('rates', {}).items())[:5]}")
        else:
            logger.error(f"Failed with status {status_code}: {resp.text[:200]}")

    except Exception as e:
        logger.error(f"Error testing midmarket rates: {str(e)}")


def get_currency_for_country(country_code):
    """Get the currency code for a country."""
    country_map = {
        "IN": "INR",  # India - Indian Rupee
        "PH": "PHP",  # Philippines - Philippine Peso
        "PK": "PKR",  # Pakistan - Pakistani Rupee
        "US": "USD",  # United States - US Dollar
        "GB": "GBP",  # United Kingdom - British Pound
        "CA": "CAD",  # Canada - Canadian Dollar
        "AU": "AUD",  # Australia - Australian Dollar
        "MX": "MXN",  # Mexico - Mexican Peso
        "FR": "EUR",  # France - Euro
        "DE": "EUR",  # Germany - Euro
    }
    return country_map.get(country_code, "USD")


def get_country_for_currency(currency_code):
    """Get a plausible source country for a currency."""
    currency_map = {
        "USD": "US",  # US Dollar - United States
        "GBP": "GB",  # British Pound - United Kingdom
        "EUR": "DE",  # Euro - Germany
        "CAD": "CA",  # Canadian Dollar - Canada
        "AUD": "AU",  # Australian Dollar - Australia
        "INR": "IN",  # Indian Rupee - India
        "PHP": "PH",  # Philippine Peso - Philippines
        "PKR": "PK",  # Pakistani Rupee - Pakistan
        "MXN": "MX",  # Mexican Peso - Mexico
    }
    return currency_map.get(currency_code, "US")


def test_quotes_api(from_currency, to_country, amount):
    """
    Test the XE quotes API directly.

    Args:
        from_currency: Source currency code (e.g., 'USD', 'GBP')
        to_country: ISO country code of the receiving country (e.g., 'IN', 'PH')
        amount: Amount to send

    Returns:
        Dictionary with the API response or error details
    """
    # Get currency for the target country
    to_currency = get_currency_for_country(to_country)

    # Determine source country based on currency
    from_country = get_country_for_currency(from_currency)

    logger.info(
        f"Testing quotes API: {from_currency} ({from_country}) -> {to_currency} ({to_country}), amount={amount}"
    )

    # Build payload
    payload = {
        "sellCcy": from_currency,
        "buyCcy": to_currency,
        "userCountry": from_country,
        "amount": float(amount),
        "fixedCcy": from_currency,
        "countryTo": to_country,
    }

    # Add correlation ID and device ID for XE's API
    headers = {
        "X-Correlation-ID": f"XECOM-{uuid.uuid4()}",
        "deviceid": str(uuid.uuid4()),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://www.xe.com",
        "Referer": "https://www.xe.com/send-money/",
    }

    try:
        resp = requests.post(QUOTES_API_URL, json=payload, headers=headers, timeout=15)
        status_code = resp.status_code

        logger.info(f"Quotes API endpoint status: {status_code}")

        if status_code == 200:
            data = resp.json()

            # Save the full response to a file for inspection
            output_file = f"xe_quote_{from_currency}_{to_country}_{amount}.json"
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Full response saved to {output_file}")

            # Print key information
            if "quote" in data:
                quote = data["quote"]
                print("\nQuote Details:")
                print("=" * 60)
                print(f"Quote ID: {quote.get('quoteId')}")
                print(f"Status: {quote.get('quoteStatus')}")
                print(f"From: {from_currency} ({from_country})")
                print(f"To: {to_currency} ({to_country})")

                # Print individual quotes
                if "individualQuotes" in quote and len(quote["individualQuotes"]) > 0:
                    print("\nAvailable Options:")
                    print("-" * 60)

                    for i, q in enumerate(quote["individualQuotes"], 1):
                        provider = q.get("commissionProvider", "Unknown")
                        delivery = q.get("deliveryMethod", "Unknown")
                        settlement = q.get("settlementMethod", "Unknown")
                        sell_amount = q.get("sellAmount", "0")
                        buy_amount = q.get("buyAmount", "0")
                        rate = q.get("rate", 0)
                        fee = q.get("transferFee", "0")
                        payment_fee = q.get("paymentMethodFee", "0")
                        delivery_date = q.get("valueDate", "Unknown")

                        print(f"Option {i} - {provider} ({delivery}):")
                        print(f"  Send: {sell_amount} {from_currency}")
                        print(f"  Receive: {buy_amount} {to_currency}")
                        print(f"  Exchange Rate: {rate}")
                        print(f"  Transfer Fee: {fee} {from_currency}")
                        print(f"  Payment Method Fee: {payment_fee} {from_currency}")
                        print(f"  Estimated Delivery: {delivery_date}")
                        print(f"  Payment Method: {settlement}")
                        print()
            else:
                logger.warning("Response doesn't contain 'quote' field")
                print("\nAPI Response:")
                print("=" * 60)
                print(f"Response keys: {list(data.keys())}")
                print(json.dumps(data, indent=2)[:1000])

            return data
        else:
            error_msg = f"Failed with status {status_code}: {resp.text[:200]}"
            logger.error(error_msg)
            print(f"\nError: {error_msg}")
            return {"error": error_msg}

    except Exception as e:
        error_msg = f"Error testing quotes API: {str(e)}"
        logger.error(error_msg)
        print(f"\nError: {error_msg}")
        return {"error": error_msg}


def test_website_endpoints():
    """Test the XE website endpoints to check availability"""
    endpoints = [
        ("Currency Converter", f"{CONVERTER_URL}/?Amount=1000&From=USD&To=INR"),
        (
            "Money Transfer Page",
            f"{MONEY_TRANSFER_URL}/?Amount=1000&FromCurrency=USD&ToCurrency=INR",
        ),
    ]

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
        }
    )

    print("\nWebsite Endpoints Status:")
    print("=" * 60)

    for name, url in endpoints:
        try:
            resp = session.get(url, timeout=15)
            status = resp.status_code
            print(f"{name}: Status {status} {'(OK)' if status == 200 else '(Failed)'}")
            logger.info(f"{name} endpoint status: {status}")
        except Exception as e:
            print(f"{name}: Error - {str(e)}")
            logger.error(f"Error testing {name}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Test XE Money Transfer API")
    parser.add_argument(
        "--from",
        dest="from_currency",
        type=str,
        default="USD",
        help="Source currency (e.g., USD, GBP)",
    )
    parser.add_argument(
        "--to",
        dest="to_country",
        type=str,
        default="IN",
        help="Target country code (e.g., IN, PH)",
    )
    parser.add_argument("--amount", type=float, default=1000, help="Amount to send")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests including website endpoint tests",
    )

    args = parser.parse_args()

    print(
        f"XE Money Transfer API Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 80)

    # Always run midmarket rates test as it's the most basic
    print("\nTesting Midmarket Rates API:")
    print("-" * 60)
    test_midmarket_rates()

    # Always run quotes API test
    print("\nTesting Quotes API:")
    print("-" * 60)
    test_quotes_api(args.from_currency, args.to_country, args.amount)

    # Run website endpoints test if requested
    if args.all:
        test_website_endpoints()

    print("\nTests complete.")


if __name__ == "__main__":
    main()
