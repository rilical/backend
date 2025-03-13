"""
Utility functions for the quotes app, including data transformation and normalization.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def transform_quotes_response(raw_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the raw quotes response into a clean, consistent format for the frontend.
    
    This function handles:
    - Removing duplicates
    - Filtering out failed quotes
    - Normalizing data structure across providers
    - Standardizing terminology
    - Applying filters requested by the user
    
    Args:
        raw_response: The raw response from aggregating quotes from multiple providers
        
    Returns:
        A cleaned and normalized response ready for frontend consumption
    """
    try:
        # Initialize the transformed response
        transformed = {
            "success": raw_response.get("success", True),
            "elapsed_seconds": raw_response.get("elapsed_seconds", 0),
            "source_country": raw_response.get("source_country"),
            "dest_country": raw_response.get("dest_country"),
            "source_currency": raw_response.get("source_currency"),
            "dest_currency": raw_response.get("destination_currency", raw_response.get("dest_currency")),
            "amount": raw_response.get("amount"),
            "timestamp": raw_response.get("timestamp"),
            "quotes": [],
            "cache_hit": raw_response.get("cache_hit", False),
            "filters_applied": raw_response.get("filters_applied", {})
        }
        
        # Get quotes and filter duplicates
        if "quotes" in raw_response:
            quotes = raw_response["quotes"]
            unique_quotes = filter_duplicate_providers(quotes)
            successful_quotes = [q for q in unique_quotes if q.get("success", False) is True]
            
            # Normalize each quote
            normalized_quotes = [normalize_quote(quote) for quote in successful_quotes]
            
            # Apply filters based on filters_applied
            filters = raw_response.get("filters_applied", {})
            max_delivery_time = filters.get("max_delivery_time_minutes")
            max_fee = filters.get("max_fee")
            payment_method_filter = filters.get("payment_method")
            delivery_method_filter = filters.get("delivery_method")
            
            filtered_quotes = normalized_quotes
            
            # Apply delivery time filter if specified
            if max_delivery_time is not None:
                filtered_quotes = [
                    q for q in filtered_quotes 
                    if q.get("delivery_time_minutes") is None or 
                    q.get("delivery_time_minutes") <= max_delivery_time
                ]
            
            # Apply fee filter if specified
            if max_fee is not None:
                filtered_quotes = [
                    q for q in filtered_quotes 
                    if q.get("fee") is None or q.get("fee") <= max_fee
                ]
                
            # Apply payment method filter if specified
            if payment_method_filter:
                filtered_quotes = [
                    q for q in filtered_quotes 
                    if q.get("payment_method") and 
                    payment_method_filter.lower() in q.get("payment_method", "").lower()
                ]
                
            # Apply delivery method filter if specified
            if delivery_method_filter:
                filtered_quotes = [
                    q for q in filtered_quotes 
                    if q.get("delivery_method") and 
                    delivery_method_filter.lower() in q.get("delivery_method", "").lower()
                ]
            
            # Sort the quotes based on filter criteria
            transformed["quotes"] = sort_quotes(
                filtered_quotes, 
                raw_response.get("filters_applied", {}).get("sort_by", "best_rate")
            )
        
        return transformed
    
    except Exception as e:
        logger.error(f"Error transforming quotes response: {str(e)}")
        # Return a minimal valid response in case of error
        return {
            "success": False,
            "error": "Error processing quote data",
            "quotes": []
        }

def filter_duplicate_providers(quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out duplicate provider quotes, keeping the one with the best rate.
    
    Args:
        quotes: List of quote objects from various providers
        
    Returns:
        List of quotes with duplicates removed
    """
    unique_providers = {}
    
    for quote in quotes:
        provider_id = quote.get("provider_id", "").upper()
        
        # Skip if no provider_id
        if not provider_id:
            continue
            
        # Determine exchange rate from various possible field names
        exchange_rate = get_exchange_rate(quote)
        
        # If we already have this provider and the new quote has a better rate, replace it
        if provider_id in unique_providers:
            existing_rate = get_exchange_rate(unique_providers[provider_id])
            if exchange_rate and existing_rate and exchange_rate > existing_rate:
                unique_providers[provider_id] = quote
        else:
            unique_providers[provider_id] = quote
    
    return list(unique_providers.values())

def get_exchange_rate(quote: Dict[str, Any]) -> Optional[float]:
    """Extract exchange rate from a quote which might use different field names"""
    rate = quote.get("exchange_rate")
    if rate is None:
        rate = quote.get("rate")
    
    try:
        return float(rate) if rate is not None else None
    except (ValueError, TypeError):
        return None

def normalize_quote(quote: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single quote to a consistent format.
    
    Args:
        quote: The provider quote to normalize
        
    Returns:
        A normalized quote with consistent field names and types
    """
    # Get provider name, falling back to ID if name isn't available
    provider_name = quote.get("provider_name", quote.get("provider_id", "Unknown"))
    provider_id = quote.get("provider_id", "").upper()
    
    # Normalize amounts and currencies
    send_amount = normalize_numeric(quote.get("send_amount") or quote.get("source_amount"))
    send_currency = (quote.get("source_currency") or quote.get("send_currency") or "").upper()
    receive_amount = normalize_numeric(quote.get("destination_amount") or quote.get("receive_amount"))
    receive_currency = (quote.get("destination_currency") or quote.get("receive_currency") or "").upper()
    
    # Get exchange rate
    exchange_rate = get_exchange_rate(quote)
    fee = normalize_numeric(quote.get("fee", 0))
    
    # Normalize methods
    payment_method = standardize_method(quote.get("payment_method"))
    delivery_method = standardize_method(quote.get("delivery_method"))
    
    # Handle multiple delivery methods
    delivery_methods = quote.get("delivery_methods", [])
    if isinstance(delivery_methods, list) and delivery_methods:
        # Keep structured delivery methods if present
        standardized_delivery_methods = [
            {
                "method": standardize_method(dm.get("method")),
                "time_minutes": normalize_numeric(dm.get("time_minutes")),
                "fee": normalize_numeric(dm.get("fee"))
            }
            for dm in delivery_methods
        ]
    elif delivery_method:
        # Create a single delivery method entry if only one exists
        standardized_delivery_methods = [{
            "method": delivery_method,
            "time_minutes": normalize_numeric(quote.get("delivery_time_minutes")),
            "fee": fee
        }]
    else:
        standardized_delivery_methods = []
    
    # Create normalized quote
    normalized = {
        "provider_id": provider_id,
        "provider_name": provider_name,
        "send_amount": send_amount,
        "send_currency": send_currency,
        "receive_amount": receive_amount,
        "receive_currency": receive_currency,
        "exchange_rate": exchange_rate,
        "fee": fee,
        "payment_method": payment_method,
        "delivery_method": delivery_method,
        "delivery_time_minutes": normalize_numeric(quote.get("delivery_time_minutes")),
        "delivery_methods": standardized_delivery_methods,
        "timestamp": quote.get("timestamp")
    }
    
    return normalized

def normalize_numeric(value: Any) -> Optional[float]:
    """
    Normalize any value to a float or None.
    
    Args:
        value: The value to normalize
        
    Returns:
        A float value or None if conversion fails
    """
    if value is None:
        return None
        
    try:
        if isinstance(value, str):
            # Remove any commas that might be used in numeric format
            return float(value.replace(',', ''))
        return float(value)
    except (ValueError, TypeError):
        return None

def standardize_method(method_str: Optional[str]) -> Optional[str]:
    """
    Standardize method strings for consistent terminology.
    
    Args:
        method_str: The original method string
        
    Returns:
        A standardized method string
    """
    if not method_str:
        return None
        
    method_str = str(method_str).lower()
    
    # Mapping of various terms to standard ones
    payment_method_mapping = {
        "bank": "bank_transfer",
        "bank_account": "bank_transfer",
        "banktransfer": "bank_transfer",
        "bank transfer": "bank_transfer",
        "card": "card_payment",
        "credit": "credit_card",
        "credit_card": "credit_card",
        "credit card": "credit_card",
        "debit": "debit_card",
        "debit_card": "debit_card",
        "debit card": "debit_card",
        "wallet": "e_wallet",
        "e-wallet": "e_wallet",
        "ewallet": "e_wallet",
        "e_wallet": "e_wallet",
        "cash": "cash_payment",
    }
    
    delivery_method_mapping = {
        "bank": "bank_deposit",
        "bank_deposit": "bank_deposit",
        "bank deposit": "bank_deposit",
        "bankdeposit": "bank_deposit",
        "cash": "cash_pickup",
        "cashpickup": "cash_pickup",
        "cash_pickup": "cash_pickup",
        "cash pickup": "cash_pickup",
        "mobile": "mobile_wallet",
        "mobilewallet": "mobile_wallet",
        "mobile_wallet": "mobile_wallet",
        "mobile wallet": "mobile_wallet",
    }
    
    # Try both mappings to see if we can standardize
    for mapping in [payment_method_mapping, delivery_method_mapping]:
        if method_str in mapping:
            return mapping[method_str]
    
    # Return original if we can't standardize
    return method_str

def sort_quotes(quotes: List[Dict[str, Any]], sort_by: str = "best_rate") -> List[Dict[str, Any]]:
    """
    Sort quotes based on provided criteria.
    
    Args:
        quotes: List of normalized quotes
        sort_by: Criteria to sort by (best_rate, lowest_fee, fastest_time, best_value)
        
    Returns:
        Sorted list of quotes
    """
    if sort_by == "best_rate":
        return sorted(quotes, key=lambda q: float(q.get("exchange_rate") or 0), reverse=True)
    elif sort_by == "lowest_fee":
        return sorted(quotes, key=lambda q: float(q.get("fee") or 0))
    elif sort_by == "fastest_time":
        # Sort by delivery time, handling None values
        return sorted(quotes, 
                     key=lambda q: float(q.get("delivery_time_minutes") or float('inf')))
    elif sort_by == "best_value":
        # Best value considers both exchange rate and fees
        def value_score(quote):
            rate = float(quote.get("exchange_rate") or 0)
            fee = float(quote.get("fee") or 0)
            send_amount = float(quote.get("send_amount") or 1)
            # Penalize fee as a percentage of send amount
            fee_penalty = fee / send_amount if send_amount else 0
            return rate * (1 - fee_penalty)
        
        return sorted(quotes, key=value_score, reverse=True)
    
    # Default to sorting by best rate
    return sorted(quotes, key=lambda q: float(q.get("exchange_rate") or 0), reverse=True) 