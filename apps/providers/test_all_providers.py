#!/usr/bin/env python3
"""
Test utility to compare quotes from all available remittance providers.
This script allows you to quickly get and compare exchange rates, fees, and delivery times
across multiple money transfer providers for a specific corridor.
"""

import argparse
import logging
import sys
import traceback
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple

# Use relative imports instead of absolute imports
from factory import ProviderFactory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("provider_test")

def test_provider(
    provider_name: str,
    send_amount: Decimal,
    send_currency: str,
    receive_country: str
) -> Dict[str, Any]:
    """
    Test a specific provider for a given corridor and amount.
    
    Args:
        provider_name: Name of the provider to test
        send_amount: Amount to send
        send_currency: Currency code of the sending amount (e.g., 'USD', 'GBP')
        receive_country: ISO country code of the receiving country (e.g., 'IN', 'MX')
        
    Returns:
        Dictionary with test results including exchange rate, fees, etc.
    """
    result = {
        'provider': provider_name,
        'send_amount': send_amount,
        'send_currency': send_currency,
        'receive_country': receive_country,
        'success': False,
        'error': None
    }
    
    try:
        # Get provider instance
        provider = ProviderFactory.get_provider(provider_name)
        logger.info(f"Testing {provider_name} for {send_currency} to {receive_country}")
        
        # Get exchange rate
        rate_info = provider.get_exchange_rate(
            send_amount=send_amount,
            send_currency=send_currency,
            receive_country=receive_country
        )
        
        # Check if the provider supports this corridor
        if not rate_info or rate_info.get('success') is False:
            error_msg = rate_info.get('error_message', 'Corridor not supported or invalid response')
            result['error'] = error_msg
            logger.warning(f"{provider_name}: {error_msg}")
            return result
        
        # Get detailed quote
        quote = provider.get_quote(
            send_amount=send_amount,
            send_currency=send_currency,
            receive_country=receive_country
        )
        
        if not quote or quote.get('success') is False:
            error_msg = quote.get('error_message', 'Failed to get quote')
            result['error'] = error_msg
            logger.warning(f"{provider_name}: {error_msg}")
            return result
        
        # Successfully got a quote
        result.update({
            'success': True,
            'exchange_rate': quote.get('exchange_rate'),
            'receive_amount': quote.get('receive_amount'),
            'receive_currency': quote.get('receive_currency'),
            'fee': quote.get('fee', Decimal('0')),
            'delivery_time': quote.get('delivery_time', 'N/A'),
            'raw_response': quote  # Include the full response for inspection
        })
        
        logger.info(f"{provider_name}: Got quote {send_amount} {send_currency} → "
                    f"{result['receive_amount']} {result['receive_currency']} "
                    f"(Rate: {result['exchange_rate']}, Fee: {result['fee']})")
                    
    except Exception as e:
        logger.error(f"Error testing {provider_name}: {str(e)}")
        logger.debug(traceback.format_exc())
        result['error'] = str(e)
        
    return result

def format_results_table(results: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Format the results into a readable table.
    
    Args:
        results: List of result dictionaries from test_provider
        
    Returns:
        Tuple of (successful_table, failed_table) as formatted strings
    """
    # Split into successful and failed results
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    # Format successful results
    successful_table = ""
    if successful:
        # Extract the data we want to display
        table_data = []
        headers = ["Provider", "Send", "Receive", "Rate", "Fee", "Delivery"]
        
        for r in successful:
            table_data.append([
                r['provider'],
                f"{r['send_amount']} {r['send_currency']}",
                f"{r['receive_amount']} {r['receive_currency']}",
                r['exchange_rate'],
                r['fee'],
                r['delivery_time']
            ])
        
        # Sort by best exchange rate (highest receive amount)
        table_data.sort(key=lambda x: float(x[2].split()[0]), reverse=True)
        
        # Format as a table using simple formatting
        successful_table = "SUCCESSFUL QUOTES:\n"
        
        # Calculate column widths
        col_widths = [max(len(str(row[i])) for row in table_data + [headers]) for i in range(len(headers))]
        
        # Format header
        successful_table += " | ".join(f"{h:{w}s}" for h, w in zip(headers, col_widths)) + "\n"
        successful_table += "-+-".join("-" * w for w in col_widths) + "\n"
        
        # Format rows
        for row in table_data:
            successful_table += " | ".join(f"{str(cell):{w}s}" for cell, w in zip(row, col_widths)) + "\n"
    
    # Format failed results
    failed_table = ""
    if failed:
        failed_table = "FAILED QUOTES:\n"
        for r in failed:
            failed_table += f"{r['provider']}: {r['send_amount']} {r['send_currency']} → {r['receive_country']}: {r['error']}\n"
    
    return successful_table, failed_table

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Test remittance providers for a specific corridor")
    parser.add_argument("--amount", type=float, required=True, help="Amount to send")
    parser.add_argument("--currency", type=str, required=True, help="Currency code to send (e.g., USD, GBP)")
    parser.add_argument("--country", type=str, required=True, help="ISO country code to receive (e.g., IN, MX)")
    parser.add_argument("--provider", type=str, help="Specific provider to test (tests all if not specified)")
    
    args = parser.parse_args()
    
    # Convert amount to Decimal for precision
    amount = Decimal(str(args.amount))
    currency = args.currency.upper()
    country = args.country.upper()
    
    # Get all available providers or just the requested one
    if args.provider:
        providers_to_test = [args.provider.lower()]
    else:
        providers_to_test = ProviderFactory.list_providers()
    
    logger.info(f"Testing {len(providers_to_test)} providers for {amount} {currency} to {country}")
    
    # Run tests for each provider
    results = []
    for provider_name in providers_to_test:
        try:
            result = test_provider(provider_name, amount, currency, country)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to test {provider_name}: {e}")
            results.append({
                'provider': provider_name,
                'send_amount': amount,
                'send_currency': currency,
                'receive_country': country,
                'success': False,
                'error': str(e)
            })
    
    # Display results
    successful_table, failed_table = format_results_table(results)
    
    print("\n" + "="*80 + "\n")
    if successful_table:
        print(successful_table)
    else:
        print("No successful quotes found.\n")
    
    if failed_table:
        print("\n" + failed_table)
    
    print("\n" + "="*80)
    
    # Return non-zero exit code if all providers failed
    if not any(r.get('success') for r in results):
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main()) 