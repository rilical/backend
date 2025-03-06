#!/usr/bin/env python
"""
Dahabshiil Provider Test Script

This script tests the Dahabshiil integration by fetching quotes for various corridors.
"""

import logging
import sys
from decimal import Decimal

from apps.providers.dahabshiil.integration import DahabshiilProvider
from apps.providers.dahabshiil.exceptions import DahabshiilApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("dahabshiil-test")

def test_quotes():
    """Test getting quotes for various corridors."""
    with DahabshiilProvider() as provider:
        # Test US to KE corridor
        amount = Decimal("100.00")
        quote = provider.get_quote(
            amount=amount,
            source_currency="USD",
            dest_currency="KES",
            source_country="US",
            dest_country="KE"
        )

        # Log the results
        if quote["success"]:
            logger.info(f"Quote successful: Rate={quote['exchange_rate']}, "
                       f"Fee={quote['fee']}, "
                       f"Send={quote['send_amount']}, "
                       f"Receive={quote['receive_amount']}")
        else:
            logger.info(f"Quote failed: {quote['error_message']}")

if __name__ == "__main__":
    logger.info("=== Testing Dahabshiil Integration ===")
    test_quotes() 