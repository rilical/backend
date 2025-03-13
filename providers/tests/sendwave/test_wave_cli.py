#!/usr/bin/env python3
"""
CLI tool to test the Wave (Sendwave) provider integration.
"""

import argparse
import json
import logging
import sys
from decimal import Decimal

from providers.sendwave.exceptions import (
    SendwaveApiError,
    SendwaveConnectionError,
    SendwaveCorridorUnsupportedError,
    SendwaveError,
    SendwaveResponseError,
)
from providers.sendwave.integration import WaveProvider

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("wave_test")


def main():
    parser = argparse.ArgumentParser(description="Test Wave (Sendwave) Provider")
    parser.add_argument("--amount", type=float, default=500, help="Send amount")
    parser.add_argument("--currency", type=str, default="USD", help="Send currency code (e.g. USD)")
    parser.add_argument("--country", type=str, default="PH", help="Receive country code (e.g. PH)")
    parser.add_argument(
        "--segment", type=str, default="ph_gcash", help="Segment name e.g. ph_gcash"
    )
    parser.add_argument(
        "--sendCountryIso2",
        type=str,
        default="us",
        help="2-letter code where money is sent from (e.g. us)",
    )
    args = parser.parse_args()

    wave = WaveProvider()

    # Convert user input
    amount = Decimal(str(args.amount))
    scy = args.currency.upper()
    rcy = args.country.upper()

    logger.info(f"Testing Wave with {amount} {scy} to {rcy}, segment={args.segment}")

    try:
        # We can pass segment_name / send_country_iso2 in kwargs
        quote = wave.get_exchange_rate(
            send_amount=amount,
            send_currency=scy,
            receive_country=rcy,
            segment_name=args.segment,
            send_country_iso2=args.sendCountryIso2,
        )

        print("Result:")
        print(json.dumps(quote, indent=2))
        return 0
    except SendwaveCorridorUnsupportedError as e:
        logger.warning(f"Corridor not supported: {e}")
        print(f"Corridor not supported: {e}")
        return 1
    except SendwaveConnectionError as e:
        logger.error(f"Connection error: {e}")
        print(f"Connection error: {e}")
        return 1
    except SendwaveApiError as e:
        logger.error(f"API error: {e}")
        print(f"API error: {e}")
        return 1
    except SendwaveResponseError as e:
        logger.error(f"Response error: {e}")
        print(f"Response error: {e}")
        return 1
    except SendwaveError as e:
        logger.error(f"Sendwave error: {e}")
        print(f"Sendwave error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
