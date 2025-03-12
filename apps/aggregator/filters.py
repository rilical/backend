"""
Utility filters for the RemitScout Aggregator.

This module provides a collection of predefined filter functions for common filtering scenarios
when working with the RemitScout Aggregator. These functions can be passed to the `filter_fn`
parameter of the Aggregator.get_all_quotes method.
"""

from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Union


def create_min_exchange_rate_filter(
    min_rate: Union[float, Decimal]
) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that requires a minimum exchange rate."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False

        exchange_rate = quote.get("exchange_rate")
        if exchange_rate is None:
            return False

        return exchange_rate >= min_rate

    return filter_fn


def create_max_fee_filter(max_fee: Union[float, Decimal]) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that limits the maximum fee."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False

        fee = quote.get("fee")
        if fee is None:
            return False

        return fee <= max_fee

    return filter_fn


def create_max_delivery_time_filter(
    max_minutes: int,
) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that limits the maximum delivery time."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False

        delivery_time = quote.get("delivery_time_minutes")
        if delivery_time is None:
            return False

        return delivery_time <= max_minutes

    return filter_fn


def create_providers_include_filter(
    provider_ids: List[str],
) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that only includes specified providers."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        provider_id = quote.get("provider_id")
        if provider_id is None:
            return False

        return provider_id in provider_ids

    return filter_fn


def create_providers_exclude_filter(
    provider_ids: List[str],
) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that excludes specified providers."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        provider_id = quote.get("provider_id")
        if provider_id is None:
            return False

        return provider_id not in provider_ids

    return filter_fn


def create_payment_method_filter(
    payment_methods: List[str],
) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that only includes specified payment methods."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False

        payment_method = quote.get("payment_method")
        if payment_method is None:
            return False

        return payment_method in payment_methods

    return filter_fn


def create_delivery_method_filter(
    delivery_methods: List[str],
) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that only includes specified delivery methods."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False

        delivery_method = quote.get("delivery_method")
        if delivery_method is None:
            return False

        return delivery_method in delivery_methods

    return filter_fn


def create_min_destination_amount_filter(
    min_amount: Union[float, Decimal]
) -> Callable[[Dict[str, Any]], bool]:
    """Create a filter that requires a minimum destination amount."""

    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False

        dest_amount = quote.get("destination_amount")
        if dest_amount is None:
            return False

        return dest_amount >= min_amount

    return filter_fn


def combine_filters(*filters: Callable[[Dict[str, Any]], bool]) -> Callable[[Dict[str, Any]], bool]:
    """Combine multiple filters with AND logic."""

    def combined_filter(quote: Dict[str, Any]) -> bool:
        return all(f(quote) for f in filters)

    return combined_filter


def create_custom_filter(
    min_rate: Optional[float] = None,
    max_fee: Optional[float] = None,
    max_delivery_time: Optional[int] = None,
    include_providers: Optional[List[str]] = None,
    exclude_providers: Optional[List[str]] = None,
    payment_methods: Optional[List[str]] = None,
    delivery_methods: Optional[List[str]] = None,
    min_destination_amount: Optional[float] = None,
) -> Callable[[Dict[str, Any]], bool]:
    """Create a custom filter with multiple criteria."""
    filters = []

    if min_rate is not None:
        filters.append(create_min_exchange_rate_filter(min_rate))

    if max_fee is not None:
        filters.append(create_max_fee_filter(max_fee))

    if max_delivery_time is not None:
        filters.append(create_max_delivery_time_filter(max_delivery_time))

    if include_providers:
        filters.append(create_providers_include_filter(include_providers))

    if exclude_providers:
        filters.append(create_providers_exclude_filter(exclude_providers))

    if payment_methods:
        filters.append(create_payment_method_filter(payment_methods))

    if delivery_methods:
        filters.append(create_delivery_method_filter(delivery_methods))

    if min_destination_amount is not None:
        filters.append(create_min_destination_amount_filter(min_destination_amount))

    return combine_filters(*filters)
