"""
Utility functions for the aggregator module.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def validate_corridor(
    source_country: str, source_currency: str, dest_country: str, dest_currency: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate if a corridor (source country/currency to destination country/currency) is valid.

    Args:
        source_country: Two-letter ISO code for source country
        source_currency: Three-letter ISO code for source currency
        dest_country: Two-letter ISO code for destination country
        dest_currency: Three-letter ISO code for destination currency

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    # Basic validation of country codes (must be 2 letter ISO codes)
    if not (source_country and len(source_country) == 2):
        return False, f"Invalid source country code: {source_country}"

    if not (dest_country and len(dest_country) == 2):
        return False, f"Invalid destination country code: {dest_country}"

    # Basic validation of currency codes (must be 3 letter ISO codes)
    if not (source_currency and len(source_currency) == 3):
        return False, f"Invalid source currency code: {source_currency}"

    if not (dest_currency and len(dest_currency) == 3):
        return False, f"Invalid destination currency code: {dest_currency}"

    # All checks passed
    return True, None


def calculate_best_value_score(quote: Dict[str, Any], amount: Decimal) -> float:
    """
    Calculate a 'value score' for a quote, used for sorting by overall value.
    Higher scores are better.

    The formula balances exchange rate and fees, giving more weight to exchange rate
    for larger amounts.

    Args:
        quote: The quote dictionary
        amount: The send amount

    Returns:
        A value score (higher is better)
    """
    if not quote.get("success"):
        return float("-inf")

    exchange_rate = quote.get("exchange_rate", 0.0)
    fee = quote.get("fee", 0.0)

    # For amount=0, avoid division by zero
    if float(amount) == 0:
        return 0

    # Value formula: exchange_rate / (1 + fee_percentage)
    # This prioritizes exchange rate for larger amounts
    fee_percentage = fee / float(amount)
    return exchange_rate / (1 + fee_percentage)


def filter_by_preferences(
    quotes: List[Dict[str, Any]],
    max_fee: Optional[float] = None,
    max_delivery_time: Optional[int] = None,
    min_exchange_rate: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Filter quotes based on user preferences.

    Args:
        quotes: List of provider quotes
        max_fee: Maximum acceptable fee
        max_delivery_time: Maximum acceptable delivery time in minutes
        min_exchange_rate: Minimum acceptable exchange rate

    Returns:
        Filtered list of quotes
    """
    filtered_quotes = quotes.copy()

    # Only apply filters to successful quotes
    successful_quotes = [q for q in filtered_quotes if q.get("success")]
    failed_quotes = [q for q in filtered_quotes if not q.get("success")]

    if max_fee is not None:
        successful_quotes = [q for q in successful_quotes if q.get("fee", float("inf")) <= max_fee]

    if max_delivery_time is not None:
        successful_quotes = [
            q
            for q in successful_quotes
            if q.get("delivery_time_minutes", float("inf")) <= max_delivery_time
        ]

    if min_exchange_rate is not None:
        successful_quotes = [
            q for q in successful_quotes if q.get("exchange_rate", 0) >= min_exchange_rate
        ]

    return successful_quotes + failed_quotes
