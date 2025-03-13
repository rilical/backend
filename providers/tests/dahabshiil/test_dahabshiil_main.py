#!/usr/bin/env python
"""
Dahabshiil Provider Test Script

This script tests the Dahabshiil integration by fetching quotes for various corridors.
"""

import json
import logging
import sys
import unittest
from decimal import Decimal

from providers.dahabshiil.integration import DahabshiilProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("test-dahabshiil-live")


class TestDahabshiilLive(unittest.TestCase):
    """Live tests calling the real Dahabshiil API."""

    def setUp(self):
        """Instantiate the Dahabshiil provider once per test."""
        self.provider = DahabshiilProvider()

    def test_quote_usd_to_kes(self):
        """Example: Send 100 USD from US to KES (Kenya)."""
        quote = self.provider.get_quote(
            amount=Decimal("100.00"),
            source_currency="USD",
            dest_currency="KES",
            source_country="US",
            dest_country="KE",
            include_raw=True,
        )
        logger.info("USD->KES Quote:\n%s", json.dumps(quote, indent=2))
        self.assertIn("success", quote)

        # Check if we received a 403 error (expected in test environments without API access)
        if not quote["success"] and "403" in quote.get("error_message", ""):
            self.skipTest(
                "Skipping test because of 403 Forbidden response - API access is restricted"
            )

        if quote["success"]:
            self.assertGreater(quote["exchange_rate"], 0.0, "Exchange rate should be > 0")
            self.assertGreater(quote["destination_amount"], 0.0, "Destination amount should be > 0")
        else:
            self.fail(f"Quote failed: {quote.get('error_message')}")

    def test_unsupported_corridor(self):
        """Test an obviously unsupported corridor, expecting an error."""
        quote = self.provider.get_quote(
            amount=Decimal("100.00"),
            source_currency="XYZ",  # likely invalid
            dest_currency="QQQ",  # likely invalid
            source_country="XX",
            dest_country="YY",
        )
        logger.info("Unsupported corridor:\n%s", json.dumps(quote, indent=2))
        self.assertFalse(quote["success"], "Unsupported corridor should fail.")
        self.assertIsNotNone(quote["error_message"], "Expect an error message.")

    def test_get_exchange_rate(self):
        """Test getting the exchange rate directly with get_exchange_rate."""
        exchange_rate = self.provider.get_exchange_rate(
            source_currency="USD",
            target_currency="KES",
            source_country="US",
            target_country="KE",
        )
        logger.info("USD->KES Exchange Rate:\n%s", json.dumps(exchange_rate, indent=2))

        # Check if we received a 403 error (expected in test environments without API access)
        if not exchange_rate["success"] and "403" in exchange_rate.get("error_message", ""):
            self.skipTest(
                "Skipping test because of 403 Forbidden response - API access is restricted"
            )

        if exchange_rate["success"]:
            self.assertIsNotNone(exchange_rate.get("rate"), "Rate should not be None")
            self.assertGreater(exchange_rate.get("rate", 0), 0, "Rate should be > 0")
        else:
            self.fail(f"Exchange rate failed: {exchange_rate.get('error_message')}")


if __name__ == "__main__":
    unittest.main()
