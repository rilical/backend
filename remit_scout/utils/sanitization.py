"""
Utilities for input sanitization and validation.

This module provides functions for sanitizing and validating user input
to protect against common security vulnerabilities like injection attacks.
"""
import re
import html
import json
from typing import Any, Dict, List, Union, Optional

def sanitize_string(value: str) -> str:
    """
    Sanitize a string input to prevent XSS and other injection attacks.
    
    Args:
        value: The string to sanitize
        
    Returns:
        The sanitized string
    """
    if not isinstance(value, str):
        return str(value)
        
    # HTML escape the string to prevent XSS
    sanitized = html.escape(value)
    
    # Remove any script tags that might have been escaped
    sanitized = re.sub(r'&lt;script.*?&gt;.*?&lt;/script&gt;', '', sanitized, flags=re.DOTALL)
    
    return sanitized

def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.
    
    Args:
        data: The dictionary to sanitize
        
    Returns:
        A sanitized copy of the dictionary
    """
    if not isinstance(data, dict):
        return data
        
    result = {}
    for key, value in data.items():
        # Sanitize the key if it's a string
        safe_key = sanitize_string(key) if isinstance(key, str) else key
        
        # Recursively sanitize values
        if isinstance(value, dict):
            result[safe_key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[safe_key] = sanitize_list(value)
        elif isinstance(value, str):
            result[safe_key] = sanitize_string(value)
        else:
            result[safe_key] = value
            
    return result

def sanitize_list(data: List[Any]) -> List[Any]:
    """
    Recursively sanitize all string values in a list.
    
    Args:
        data: The list to sanitize
        
    Returns:
        A sanitized copy of the list
    """
    if not isinstance(data, list):
        return data
        
    result = []
    for item in data:
        if isinstance(item, dict):
            result.append(sanitize_dict(item))
        elif isinstance(item, list):
            result.append(sanitize_list(item))
        elif isinstance(item, str):
            result.append(sanitize_string(item))
        else:
            result.append(item)
            
    return result

def sanitize_json_string(json_str: str) -> str:
    """
    Sanitize a JSON string by parsing it and sanitizing all string values.
    
    Args:
        json_str: The JSON string to sanitize
        
    Returns:
        A sanitized JSON string
        
    Raises:
        ValueError: If the input is not valid JSON
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON input")
        
    if isinstance(data, dict):
        sanitized_data = sanitize_dict(data)
    elif isinstance(data, list):
        sanitized_data = sanitize_list(data)
    else:
        return json_str
        
    return json.dumps(sanitized_data)

def validate_country_code(country_code: str) -> bool:
    """
    Validate that a string is a valid ISO 3166-1 alpha-2 country code.
    
    Args:
        country_code: The country code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(country_code, str):
        return False
        
    # ISO 3166-1 alpha-2 country codes are 2 uppercase letters
    return bool(re.match(r'^[A-Z]{2}$', country_code))

def validate_currency_code(currency_code: str) -> bool:
    """
    Validate that a string is a valid ISO 4217 currency code.
    
    Args:
        currency_code: The currency code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(currency_code, str):
        return False
        
    # ISO 4217 currency codes are 3 uppercase letters
    return bool(re.match(r'^[A-Z]{3}$', currency_code))

def validate_amount(amount: Union[str, float, int]) -> bool:
    """
    Validate that a value is a valid positive amount.
    
    Args:
        amount: The amount to validate
        
    Returns:
        True if valid, False otherwise
    """
    if isinstance(amount, str):
        # If it's a string, try to convert to float
        try:
            amount = float(amount)
        except ValueError:
            return False
            
    # Check that it's a number and greater than zero
    return isinstance(amount, (int, float)) and amount > 0

def validate_quote_params(
    source_country: Optional[str] = None,
    dest_country: Optional[str] = None,
    source_currency: Optional[str] = None,
    dest_currency: Optional[str] = None,
    amount: Optional[Union[str, float, int]] = None
) -> Dict[str, str]:
    """
    Validate all parameters for a quote request.
    
    Args:
        source_country: The source country code
        dest_country: The destination country code
        source_currency: The source currency code
        dest_currency: The destination currency code
        amount: The amount to send
        
    Returns:
        A dictionary of validation errors, or an empty dict if all valid
    """
    errors = {}
    
    if source_country and not validate_country_code(source_country.upper()):
        errors['source_country'] = "Invalid source country code. Must be a valid ISO 3166-1 alpha-2 code."
        
    if dest_country and not validate_country_code(dest_country.upper()):
        errors['dest_country'] = "Invalid destination country code. Must be a valid ISO 3166-1 alpha-2 code."
        
    if source_currency and not validate_currency_code(source_currency.upper()):
        errors['source_currency'] = "Invalid source currency code. Must be a valid ISO 4217 code."
        
    if dest_currency and not validate_currency_code(dest_currency.upper()):
        errors['dest_currency'] = "Invalid destination currency code. Must be a valid ISO 4217 code."
        
    if amount is not None and not validate_amount(amount):
        errors['amount'] = "Invalid amount. Must be a positive number."
        
    return errors 