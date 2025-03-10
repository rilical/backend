"""
Utility filters for the RemitScout Aggregator.

This module provides a collection of predefined filter functions for common filtering scenarios
when working with the RemitScout Aggregator. These functions can be passed to the `filter_fn`
parameter of the Aggregator.get_all_quotes method.
"""

from typing import Dict, Any, Callable, List, Optional, Union
from decimal import Decimal


def create_min_exchange_rate_filter(min_rate: Union[float, Decimal]) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that requires a minimum exchange rate.
    
    Args:
        min_rate: The minimum acceptable exchange rate
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
        
        exchange_rate = quote.get("exchange_rate")
        if exchange_rate is None:
            return False
            
        return float(exchange_rate) >= float(min_rate)
        
    return filter_fn


def create_max_fee_filter(max_fee: Union[float, Decimal]) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that limits the maximum fee.
    
    Args:
        max_fee: The maximum acceptable fee
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
            
        fee = quote.get("fee")
        if fee is None:
            return False
            
        return float(fee) <= float(max_fee)
        
    return filter_fn


def create_max_delivery_time_filter(max_minutes: int) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that limits the maximum delivery time.
    
    Args:
        max_minutes: The maximum acceptable delivery time in minutes
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
            
        delivery_time = quote.get("delivery_time_minutes")
        if delivery_time is None:
            return False
            
        return int(delivery_time) <= max_minutes
        
    return filter_fn


def create_providers_include_filter(provider_ids: List[str]) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that only includes specific providers.
    
    Args:
        provider_ids: List of provider IDs to include
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
            
        provider_id = quote.get("provider_id")
        if provider_id is None:
            return False
            
        return provider_id in provider_ids
        
    return filter_fn


def create_providers_exclude_filter(provider_ids: List[str]) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that excludes specific providers.
    
    Args:
        provider_ids: List of provider IDs to exclude
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
            
        provider_id = quote.get("provider_id")
        if provider_id is None:
            return False
            
        return provider_id not in provider_ids
        
    return filter_fn


def create_payment_method_filter(payment_methods: List[str]) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that requires specific payment methods.
    
    Args:
        payment_methods: List of acceptable payment methods
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
            
        payment_method = quote.get("payment_method")
        if payment_method is None:
            return False
            
        return payment_method.lower() in [m.lower() for m in payment_methods]
        
    return filter_fn


def create_delivery_method_filter(delivery_methods: List[str]) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that requires specific delivery methods.
    
    Args:
        delivery_methods: List of acceptable delivery methods
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
            
        delivery_method = quote.get("delivery_method")
        if delivery_method is None:
            return False
            
        return delivery_method.lower() in [m.lower() for m in delivery_methods]
        
    return filter_fn


def create_min_destination_amount_filter(min_amount: Union[float, Decimal]) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a filter that requires a minimum destination amount.
    
    Args:
        min_amount: The minimum acceptable destination amount
        
    Returns:
        A filter function that can be passed to Aggregator.get_all_quotes
    """
    def filter_fn(quote: Dict[str, Any]) -> bool:
        if not quote.get("success", False):
            return False
            
        destination_amount = quote.get("destination_amount")
        if destination_amount is None:
            return False
            
        return float(destination_amount) >= float(min_amount)
        
    return filter_fn


def combine_filters(*filters: Callable[[Dict[str, Any]], bool]) -> Callable[[Dict[str, Any]], bool]:
    """
    Combine multiple filters with AND logic.
    
    Args:
        *filters: Filter functions to combine
        
    Returns:
        A combined filter function that requires all filters to pass
    """
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
    min_destination_amount: Optional[float] = None
) -> Callable[[Dict[str, Any]], bool]:
    """
    Create a custom filter combining multiple criteria.
    
    Args:
        min_rate: Minimum acceptable exchange rate
        max_fee: Maximum acceptable fee
        max_delivery_time: Maximum acceptable delivery time in minutes
        include_providers: List of providers to include (only these will be included)
        exclude_providers: List of providers to exclude
        payment_methods: List of acceptable payment methods
        delivery_methods: List of acceptable delivery methods
        min_destination_amount: Minimum acceptable destination amount
        
    Returns:
        A combined filter function with all the specified criteria
    """
    filters = []
    
    if min_rate is not None:
        filters.append(create_min_exchange_rate_filter(min_rate))
        
    if max_fee is not None:
        filters.append(create_max_fee_filter(max_fee))
        
    if max_delivery_time is not None:
        filters.append(create_max_delivery_time_filter(max_delivery_time))
        
    if include_providers is not None:
        filters.append(create_providers_include_filter(include_providers))
        
    if exclude_providers is not None:
        filters.append(create_providers_exclude_filter(exclude_providers))
        
    if payment_methods is not None:
        filters.append(create_payment_method_filter(payment_methods))
        
    if delivery_methods is not None:
        filters.append(create_delivery_method_filter(delivery_methods))
        
    if min_destination_amount is not None:
        filters.append(create_min_destination_amount_filter(min_destination_amount))
        
    return combine_filters(*filters) if filters else (lambda x: True) 