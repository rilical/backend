"""
Live testing script for SingX integration.

This script performs live API calls to validate the SingX integration.
It tests various corridors and payment methods with small amounts.

Usage:
    python test_live.py
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any, Dict

from apps.providers.singx.exceptions import SingXError
from apps.providers.singx.integration import SingXProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Test corridors with specific rates and fees
TEST_CORRIDORS = [
    {
        "name": "Singapore to India (SGD to INR)",
        "send_country": "SG",
        "receive_country": "IN",
        "send_currency": "SGD",
        "receive_currency": "INR",
        "amount": Decimal("100.00"),
        "expected_rate": Decimal("64.8864"),
        "expected_fee": Decimal("6.16"),
    },
    {
        "name": "Singapore to Philippines",
        "send_country": "SG",
        "receive_country": "PH",
        "send_currency": "SGD",
        "receive_currency": "PHP",
        "amount": Decimal("150.00"),
    },
    {
        "name": "Singapore to Indonesia",
        "send_country": "SG",
        "receive_country": "ID",
        "send_currency": "SGD",
        "receive_currency": "IDR",
        "amount": Decimal("200.00"),
    },
    {
        "name": "Singapore to Malaysia",
        "send_country": "SG",
        "receive_country": "MY",
        "send_currency": "SGD",
        "receive_currency": "MYR",
        "amount": Decimal("250.00"),
    },
]

# Test payment methods
PAYMENT_METHODS = [
    {"name": "Bank Transfer", "params": {}},
    {"name": "SWIFT", "params": {"swift": True}},
    {"name": "Cash Pickup", "params": {"cash_pickup": True}},
    {"name": "Wallet", "params": {"wallet": True}},
]


def validate_rate(actual: Decimal, expected: Decimal, tolerance: Decimal = Decimal("0.01")) -> bool:
    """
    Validate if the actual rate is within tolerance of expected rate.

    Args:
        actual: Actual rate from API
        expected: Expected rate
        tolerance: Acceptable difference percentage (default 1%)

    Returns:
        bool: True if within tolerance, False otherwise
    """
    if not expected:
        return True

    difference = abs(actual - expected) / expected * 100
    return difference <= tolerance


async def test_exchange_rates() -> None:
    """Test exchange rate retrieval for all corridors."""
    logger.info("Testing exchange rates...")
    provider = SingXProvider()

    for corridor in TEST_CORRIDORS:
        try:
            result = provider.get_exchange_rate(
                send_country=corridor["send_country"],
                send_currency=corridor["send_currency"],
                receive_country=corridor["receive_country"],
                receive_currency=corridor["receive_currency"],
                amount=corridor["amount"],
            )

            if result["success"]:
                actual_rate = Decimal(str(result["rate"]))
                expected_rate = corridor.get("expected_rate")

                rate_info = (
                    f"{corridor['name']}: Rate {actual_rate}, "
                    f"Fee {result['fee']} {corridor['send_currency']}"
                )

                if expected_rate:
                    if validate_rate(actual_rate, expected_rate):
                        logger.info(f"{rate_info} ✓ (matches expected rate {expected_rate})")
                    else:
                        logger.warning(
                            f"{rate_info} ⚠ (differs from expected rate {expected_rate}, "
                            f"difference: {abs(actual_rate - expected_rate):,.4f})"
                        )
                else:
                    logger.info(rate_info)
            else:
                logger.error(f"{corridor['name']}: Failed - {result.get('error')}")

        except Exception as e:
            logger.error(f"{corridor['name']}: Error - {str(e)}")


async def test_quotes() -> None:
    """Test quote generation for all corridors and payment methods."""
    logger.info("Testing quotes...")
    provider = SingXProvider()

    for corridor in TEST_CORRIDORS:
        for payment_method in PAYMENT_METHODS:
            try:
                result = provider.get_quote(
                    send_amount=corridor["amount"],
                    send_currency=corridor["send_currency"],
                    receive_currency=corridor["receive_currency"],
                    send_country=corridor["send_country"],
                    receive_country=corridor["receive_country"],
                    **payment_method["params"],
                )

                if result["success"]:
                    actual_fee = Decimal(str(result["fee"]))
                    expected_fee = corridor.get("expected_fee")

                    quote_info = (
                        f"{corridor['name']} ({payment_method['name']}): "
                        f"Send {result['send_amount']} {corridor['send_currency']}, "
                        f"Receive {result['receive_amount']} {corridor['receive_currency']}, "
                        f"Fee {actual_fee} {corridor['send_currency']}"
                    )

                    if expected_fee:
                        if actual_fee == expected_fee:
                            logger.info(f"{quote_info} ✓ (matches expected fee)")
                        else:
                            logger.warning(
                                f"{quote_info} ⚠ (differs from expected fee {expected_fee}, "
                                f"difference: {abs(actual_fee - expected_fee):,.2f})"
                            )
                    else:
                        logger.info(quote_info)
                else:
                    logger.error(
                        f"{corridor['name']} ({payment_method['name']}): "
                        f"Failed - {result.get('error')}"
                    )

            except Exception as e:
                logger.error(f"{corridor['name']} ({payment_method['name']}): " f"Error - {str(e)}")


async def test_fees() -> None:
    """Test fee calculation for all corridors."""
    logger.info("Testing fees...")
    provider = SingXProvider()

    for corridor in TEST_CORRIDORS:
        try:
            result = provider.get_fees(
                send_amount=corridor["amount"],
                send_currency=corridor["send_currency"],
                receive_currency=corridor["receive_currency"],
                send_country=corridor["send_country"],
            )

            if result["success"]:
                actual_fee = Decimal(str(result["transfer_fee"]))
                expected_fee = corridor.get("expected_fee")

                fee_info = (
                    f"{corridor['name']}: "
                    f"Transfer Fee {actual_fee} {result['fee_currency']}, "
                    f"Total Fee {result['total_fee']} {result['fee_currency']}"
                )

                if expected_fee:
                    if actual_fee == expected_fee:
                        logger.info(f"{fee_info} ✓ (matches expected fee)")
                    else:
                        logger.warning(
                            f"{fee_info} ⚠ (differs from expected fee {expected_fee}, "
                            f"difference: {abs(actual_fee - expected_fee):,.2f})"
                        )
                else:
                    logger.info(fee_info)
            else:
                logger.error(f"{corridor['name']}: Failed - {result.get('error')}")

        except Exception as e:
            logger.error(f"{corridor['name']}: Error - {str(e)}")


async def main():
    """Main test function."""
    logger.info("Starting SingX integration live tests...")
    logger.info("Testing with specific SGD to INR rate (64.8864) and fee (6.16 SGD)")

    try:
        # Run tests
        await test_exchange_rates()
        logger.info("-" * 80)

        await test_quotes()
        logger.info("-" * 80)

        await test_fees()
        logger.info("-" * 80)

        logger.info("Live tests completed.")

    except Exception as e:
        logger.error(f"Test suite error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
