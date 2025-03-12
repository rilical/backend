"""
Tests for Xoom integration.

These tests verify the Xoom integration by mocking API responses
or making real API calls as appropriate.
"""

import json
import logging
import os
import random
import re
import time
import unittest
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
import requests
import responses
from bs4 import BeautifulSoup

from apps.providers.xoom.exceptions import (
    XoomAuthenticationError,
    XoomError,
    XoomValidationError,
)
from apps.providers.xoom.integration import XoomProvider

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("xoom_tests")
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


# Define paths for saving test results
def get_test_output_dir():
    """Get the directory for saving test outputs."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, "test_outputs")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def save_test_result(filename, data):
    """Save test result to a JSON file."""
    output_dir = get_test_output_dir()
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


class TestXoomProvider(unittest.TestCase):
    """Test the Xoom provider integration."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.provider = XoomProvider(timeout=5)

        # Create a directory for test outputs if it doesn't exist
        self.test_output_dir = get_test_output_dir()

    def tearDown(self):
        """Clean up after each test."""
        self.provider.session.close()

    @responses.activate
    def test_initialization(self):
        """Test provider initialization and session setup."""
        # Mock the home page response
        responses.add(
            responses.GET,
            "https://www.xoom.com/en-us/send-money",
            body="<html><head><meta name='csrf-token' content='test-token'></head><body></body></html>",
            status=200,
        )

        # Also mock the additional requests made during initialization
        responses.add(
            responses.GET,
            "https://www.xoom.com/segment/settings.json",
            json={"status": "ok"},
            status=200,
        )

        responses.add(
            responses.GET,
            "https://www.xoom.com/pa/gdpr",
            json={"status": "ok"},
            status=200,
        )

        provider = XoomProvider(timeout=5)

        # Verify the provider is initialized correctly
        self.assertEqual(provider.name, "Xoom")
        self.assertEqual(provider.base_url, "https://www.xoom.com")

        # Check that the session has the expected headers
        self.assertIn("User-Agent", provider.session.headers)

        # CSRF token should be extracted
        self.assertEqual(provider.session.headers.get("X-CSRF-Token"), "test-token")

    @responses.activate
    def test_fee_table_exchange_rate_success(self):
        """Test successful exchange rate retrieval via fee table API."""
        # Mock the homepage visit
        responses.add(
            responses.GET,
            "https://www.xoom.com/en-us/send-money",
            body="<html><head><meta name='csrf-token' content='test-token'></head><body></body></html>",
            status=200,
        )

        # Mock the fee table API response
        mock_fee_table_html = """
        <div>
            <data id="jsonData">
                {"data":{"receiveAmount":"10042.15","fxRate":"20.0843","rateBadge":null,"amountRounded":false,"showFtfFeeContent":false,"showFtfFxContent":false,"currencyDisclaimer":"In addition to the transaction fee, we also make money when we change your send currency into a different currency.","comparativeFxRate":null,"sendAmount":"500.00","remittanceResourceID":"test-id","showFtfBanner":false},"status":{"valid":true}}
            </data>
            <div id="js-fee-table-content">
                <div class="xvx-table-container" id="deposit">
                    <p class="xvx-table-container__heading xvx-font-copy xvx-text-center"> Fee for Bank Deposit</p>
                    <table class="xvx-table xvx-table--fee">
                        <tbody class="xvx-table--fee__body">
                            <tr class="xvx-table--fee__body-tr">
                                <td class="xvx-table--fee__body-td xvx-font-copy"> PayPal USD (PYUSD)</td>
                                <td class="xvx-table--fee__body-td xvx-font-copy fee-value"> 0.00</td>
                            </tr>
                            <tr class="xvx-table--fee__body-tr">
                                <td class="xvx-table--fee__body-td xvx-font-copy"> PayPal balance</td>
                                <td class="xvx-table--fee__body-td xvx-font-copy fee-value"> 0.00</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """

        responses.add(
            responses.GET,
            "https://www.xoom.com/calculate-fee-table",
            body=mock_fee_table_html,
            status=200,
        )

        # Make the API call
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("500.00"),
            send_currency="USD",
            receive_country="MX",
            receive_currency="MXN",
        )

        # Save the result to a JSON file
        filename = f"xoom_exchange_rate_MX_500USD_{time.strftime('%Y%m%d-%H%M%S')}.json"
        saved_path = save_test_result(filename, result)
        logger.info(f"Saved test result to {saved_path}")

        # Verify the result
        self.assertEqual(result["provider"], "Xoom")
        self.assertEqual(result["send_currency"], "USD")
        self.assertEqual(result["send_amount"], 500.0)
        self.assertEqual(result["receive_currency"], "MXN")
        self.assertEqual(result["receive_amount"], 10042.15)
        self.assertEqual(result["exchange_rate"], 20.0843)
        self.assertEqual(result["fee"], 0.0)
        self.assertEqual(result["delivery_method"], "bank deposit")
        self.assertIn("payment_method", result)

    @pytest.mark.integration
    def test_fee_table_api_live(self):
        """Integration test for fee table API with live calls."""
        # Define test corridors
        test_corridors = [
            {"code": "MX", "name": "Mexico", "currency": "MXN"},
            {"code": "PH", "name": "Philippines", "currency": "PHP"},
            {"code": "AR", "name": "Argentina", "currency": "ARS"},
        ]

        # Test amounts
        test_amounts = [Decimal("100.00"), Decimal("300.00")]

        # Results storage
        all_results = []
        success_count = 0
        total_tests = len(test_corridors) * len(test_amounts)

        # Timestamp for this test run
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        for country in test_corridors:
            for amount in test_amounts:
                country_code = country["code"]
                currency_code = country["currency"]

                logger.info(
                    f"Testing exchange rate for {amount} USD to {country['name']} ({currency_code})"
                )

                try:
                    # Get exchange rate
                    result = self.provider.get_exchange_rate(
                        send_amount=amount,
                        send_currency="USD",
                        receive_country=country_code,
                        receive_currency=currency_code,
                    )

                    # Save individual result to JSON
                    filename = f"xoom_rate_{country_code}_{amount}USD_{timestamp}.json"
                    saved_path = save_test_result(filename, result)
                    logger.info(f"Saved result to {saved_path}")

                    # Add to results
                    all_results.append(
                        {
                            "corridor": f"US-{country_code}",
                            "country_name": country["name"],
                            "send_amount": float(amount),
                            "result": result,
                        }
                    )

                    success_count += 1

                    # Log success with key details
                    logger.info(f"SUCCESS for {country_code}:")
                    logger.info(f"  Rate: {result['exchange_rate']}")
                    logger.info(f"  Fee: {result['fee']} {result['send_currency']}")
                    logger.info(
                        f"  Send: {result['send_amount']} {result['send_currency']}"
                    )
                    logger.info(
                        f"  Receive: {result['receive_amount']} {result['receive_currency']}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to get exchange rate for {country_code}: {str(e)}"
                    )
                    all_results.append(
                        {
                            "corridor": f"US-{country_code}",
                            "country_name": country["name"],
                            "send_amount": float(amount),
                            "error": str(e),
                        }
                    )

                # Pause between requests
                time.sleep(1)

        # Save complete results
        all_results_file = f"xoom_fee_table_tests_{timestamp}.json"
        all_results_path = save_test_result(all_results_file, all_results)
        logger.info(f"Saved all test results to {all_results_path}")

        # Verify at least some tests passed
        self.assertTrue(
            success_count > 0, f"All {total_tests} exchange rate tests failed"
        )
        logger.info(
            f"Successfully completed {success_count} out of {total_tests} tests"
        )

    @responses.activate
    def test_get_exchange_rate_fallback_to_fee_table(self):
        """Test that exchange rate retrieval falls back to fee table API when API call fails."""
        # Mock the primary API to fail
        responses.add(
            responses.POST,
            "https://www.xoom.com/wapi/send-money-app/remittance-engine/remittance",
            json={"error": "Authentication required"},
            status=401,
        )

        # Mock the fee table API to succeed
        mock_fee_table_html = """
        <div>
            <data id="jsonData">
                {"data":{"receiveAmount":"10042.15","fxRate":"20.0843","rateBadge":null,"amountRounded":false,"showFtfFeeContent":false,"showFtfFxContent":false,"currencyDisclaimer":"In addition to the transaction fee, we also make money when we change your send currency into a different currency.","comparativeFxRate":null,"sendAmount":"500.00","remittanceResourceID":"test-id","showFtfBanner":false},"status":{"valid":true}}
            </data>
            <div id="js-fee-table-content">
                <div class="xvx-table-container" id="deposit">
                    <p class="xvx-table-container__heading xvx-font-copy xvx-text-center"> Fee for Bank Deposit</p>
                    <table class="xvx-table xvx-table--fee">
                        <tbody class="xvx-table--fee__body">
                            <tr class="xvx-table--fee__body-tr">
                                <td class="xvx-table--fee__body-td xvx-font-copy"> PayPal USD (PYUSD)</td>
                                <td class="xvx-table--fee__body-td xvx-font-copy fee-value"> 0.00</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """

        responses.add(
            responses.GET,
            "https://www.xoom.com/calculate-fee-table",
            body=mock_fee_table_html,
            status=200,
        )

        # Make the API call which should fall back to fee table
        result = self.provider.get_exchange_rate(
            send_amount=Decimal("500.00"),
            send_currency="USD",
            receive_country="MX",
            receive_currency="MXN",
        )

        # Save the result
        filename = f"xoom_fallback_test_{time.strftime('%Y%m%d-%H%M%S')}.json"
        saved_path = save_test_result(filename, result)
        logger.info(f"Saved fallback test result to {saved_path}")

        # Verify the result contains expected data from fee table API
        self.assertEqual(result["provider"], "Xoom")
        self.assertEqual(result["exchange_rate"], 20.0843)
        self.assertEqual(result["receive_amount"], 10042.15)

    @responses.activate
    def test_get_supported_countries(self):
        """Test retrieval of supported countries."""
        # Mock the send money page response
        html_response = """
        <html>
            <script>
                window.__INITIAL_STATE__ = {
                    "data": {
                        "countries": [
                            {"code": "MX", "name": "Mexico", "currency": "MXN"},
                            {"code": "PH", "name": "Philippines", "currency": "PHP"}
                        ]
                    }
                };
            </script>
        </html>
        """

        responses.add(
            responses.GET,
            "https://www.xoom.com/en-us/send-money",
            body=html_response,
            status=200,
        )

        # Get countries
        countries = self.provider.get_supported_countries()

        # Save the countries to JSON
        filename = f"xoom_supported_countries_{time.strftime('%Y%m%d-%H%M%S')}.json"
        saved_path = save_test_result(filename, countries)
        logger.info(f"Saved supported countries to {saved_path}")

        # Verify countries were parsed correctly
        self.assertEqual(len(countries), 2)
        self.assertEqual(countries[0]["country_code"], "MX")
        self.assertEqual(countries[0]["country_name"], "Mexico")
        self.assertEqual(countries[0]["currency_code"], "MXN")

    @responses.activate
    def test_get_payment_methods(self):
        """Test retrieval of payment methods."""
        # Mock the API response
        mock_response = {
            "data": {
                "remittance": {
                    "quote": {
                        "pricing": [
                            {
                                "disbursementType": "DEPOSIT",
                                "paymentType": {"type": "PAYPAL_BALANCE"},
                                "feeAmount": {"rawValue": "0.0000"},
                                "content": [
                                    {
                                        "key": "feesFx.paymentType",
                                        "value": "PayPal balance",
                                    }
                                ],
                            },
                            {
                                "disbursementType": "DEPOSIT",
                                "paymentType": {"type": "DEBIT_CARD"},
                                "feeAmount": {"rawValue": "3.9900"},
                                "content": [
                                    {"key": "feesFx.paymentType", "value": "Debit Card"}
                                ],
                            },
                        ]
                    }
                }
            }
        }

        responses.add(
            responses.POST,
            "https://www.xoom.com/wapi/send-money-app/remittance-engine/remittance",
            json=mock_response,
            status=200,
        )

        # Get payment methods
        payment_methods = self.provider.get_payment_methods(target_country="MX")

        # Save to JSON
        filename = f"xoom_payment_methods_MX_{time.strftime('%Y%m%d-%H%M%S')}.json"
        saved_path = save_test_result(filename, payment_methods)
        logger.info(f"Saved payment methods to {saved_path}")

        # Verify payment methods were parsed correctly
        self.assertEqual(len(payment_methods), 2)
        self.assertEqual(payment_methods[0]["id"], "PAYPAL_BALANCE")
        self.assertEqual(payment_methods[0]["name"], "PayPal balance")
        self.assertEqual(payment_methods[0]["fee"], 0.0)

        self.assertEqual(payment_methods[1]["id"], "DEBIT_CARD")
        self.assertEqual(payment_methods[1]["name"], "Debit Card")
        self.assertEqual(payment_methods[1]["fee"], 3.99)


# Integration tests that make real API calls
@pytest.mark.integration
class TestXoomIntegration:
    """Integration tests for Xoom provider making real API calls."""

    def setup_method(self):
        """Set up the provider for each test."""
        self.provider = XoomProvider(timeout=30)
        self.test_output_dir = get_test_output_dir()

    def teardown_method(self):
        """Clean up after each test."""
        self.provider.session.close()

    def test_get_exchange_rates_multiple_corridors(self):
        """Test getting exchange rates for multiple corridors using the fee table API."""
        # Define test corridors
        test_corridors = [
            {"source": "USD", "destination": "MX", "currency": "MXN", "name": "Mexico"},
            {
                "source": "USD",
                "destination": "PH",
                "currency": "PHP",
                "name": "Philippines",
            },
            {"source": "USD", "destination": "IN", "currency": "INR", "name": "India"},
            {
                "source": "USD",
                "destination": "CO",
                "currency": "COP",
                "name": "Colombia",
            },
            {"source": "USD", "destination": "BR", "currency": "BRL", "name": "Brazil"},
        ]

        # Test amounts
        test_amounts = [Decimal("100.00"), Decimal("300.00"), Decimal("500.00")]

        # Timestamp for this test run
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Store results
        all_results = []
        success_count = 0
        total_tests = len(test_corridors) * len(test_amounts)

        logger.info("=== RUNNING EXCHANGE RATE TESTS WITH FEE TABLE API ===")

        for corridor in test_corridors:
            for amount in test_amounts:
                logger.info(
                    f"Testing {amount} {corridor['source']} to {corridor['destination']} ({corridor['currency']})"
                )

                try:
                    # Get exchange rate
                    result = self.provider.get_exchange_rate(
                        send_amount=amount,
                        send_currency=corridor["source"],
                        receive_country=corridor["destination"],
                        receive_currency=corridor["currency"],
                    )

                    # Log success details
                    logger.info(
                        f"SUCCESS: Exchange rate {result['exchange_rate']}, Fee: {result['fee']}"
                    )

                    # Save individual result to JSON
                    file_prefix = (
                        f"{corridor['source']}_{corridor['destination']}_{amount}"
                    )
                    filename = f"xoom_exchange_rate_{file_prefix}_{timestamp}.json"
                    saved_path = save_test_result(filename, result)
                    logger.info(f"Saved result to {saved_path}")

                    # Add to results collection
                    all_results.append(
                        {
                            "corridor": f"{corridor['source']}-{corridor['destination']}",
                            "country_name": corridor["name"],
                            "send_amount": float(amount),
                            "result": result,
                        }
                    )

                    success_count += 1

                except Exception as e:
                    logger.error(f"Error testing {corridor['destination']}: {str(e)}")
                    all_results.append(
                        {
                            "corridor": f"{corridor['source']}-{corridor['destination']}",
                            "country_name": corridor["name"],
                            "send_amount": float(amount),
                            "error": str(e),
                        }
                    )

                # Pause between requests to avoid rate limiting
                time.sleep(1.5)

        # Save complete results
        all_results_file = f"xoom_integration_tests_{timestamp}.json"
        all_results_path = save_test_result(all_results_file, all_results)
        logger.info(f"Saved all integration test results to {all_results_path}")

        # Print summary
        logger.info(f"=== SUMMARY: {success_count}/{total_tests} tests successful ===")

        # Assert at least some tests were successful
        assert success_count > 0, "All exchange rate tests failed"

    def test_get_supported_countries_live(self):
        """Test getting supported countries from the live API."""
        countries = self.provider.get_supported_countries()

        # Save to JSON
        filename = (
            f"xoom_supported_countries_live_{time.strftime('%Y%m%d-%H%M%S')}.json"
        )
        saved_path = save_test_result(filename, countries)
        logger.info(f"Saved live supported countries to {saved_path}")

        # There should be a decent number of countries
        assert len(countries) > 5

        # Key countries should be in the list
        country_codes = [c["country_code"] for c in countries]
        assert "MX" in country_codes  # Mexico
        assert "PH" in country_codes  # Philippines
