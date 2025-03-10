#!/usr/bin/env python
"""
Test script for the Aggregator concept with dummy providers.

This script simulates testing 10 corridors with dummy providers
that return predefined responses.
"""

import os
import sys
import logging
import time
import random
import concurrent.futures
from decimal import Decimal
from typing import Dict, Any, List, Optional
from tabulate import tabulate

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('aggregator_test')

# Define the corridors to test
CORRIDORS = [
    {
        "name": "USD to INR (US to India)",
        "source_country": "US",
        "dest_country": "IN",
        "source_currency": "USD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00")
    },
    {
        "name": "USD to PHP (US to Philippines)",
        "source_country": "US",
        "dest_country": "PH",
        "source_currency": "USD",
        "dest_currency": "PHP",
        "amount": Decimal("1000.00")
    },
    {
        "name": "GBP to INR (UK to India)",
        "source_country": "GB",
        "dest_country": "IN",
        "source_currency": "GBP",
        "dest_currency": "INR",
        "amount": Decimal("1000.00")
    },
    {
        "name": "EUR to NGN (Europe to Nigeria)",
        "source_country": "DE",
        "dest_country": "NG",
        "source_currency": "EUR",
        "dest_currency": "NGN",
        "amount": Decimal("1000.00")
    },
    {
        "name": "CAD to INR (Canada to India)",
        "source_country": "CA",
        "dest_country": "IN",
        "source_currency": "CAD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00")
    },
    {
        "name": "AUD to INR (Australia to India)",
        "source_country": "AU",
        "dest_country": "IN",
        "source_currency": "AUD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00")
    },
    {
        "name": "SGD to INR (Singapore to India)",
        "source_country": "SG",
        "dest_country": "IN",
        "source_currency": "SGD",
        "dest_currency": "INR",
        "amount": Decimal("1000.00")
    },
    {
        "name": "USD to MXN (US to Mexico)",
        "source_country": "US",
        "dest_country": "MX",
        "source_currency": "USD",
        "dest_currency": "MXN",
        "amount": Decimal("1000.00")
    },
    {
        "name": "GBP to EUR (UK to Europe)",
        "source_country": "GB",
        "dest_country": "DE",
        "source_currency": "GBP",
        "dest_currency": "EUR",
        "amount": Decimal("1000.00")
    },
    {
        "name": "AUD to PHP (Australia to Philippines)",
        "source_country": "AU",
        "dest_country": "PH",
        "source_currency": "AUD",
        "dest_currency": "PHP",
        "amount": Decimal("1000.00")
    }
]

# Define exchange rates for different currency pairs (simplified)
EXCHANGE_RATES = {
    "USD-INR": 83.5,
    "USD-PHP": 56.2,
    "GBP-INR": 106.8,
    "EUR-NGN": 1308.5,
    "CAD-INR": 61.7,
    "AUD-INR": 55.3,
    "SGD-INR": 62.2,
    "USD-MXN": 16.8,
    "GBP-EUR": 1.18,
    "AUD-PHP": 37.6
}

# Dummy provider classes
class DummyProvider1:
    name = "Provider1"
    
    def get_quote(self, amount, source_currency, dest_currency, source_country, dest_country, **kwargs):
        # Get the exchange rate for this currency pair
        key = f"{source_currency}-{dest_currency}"
        if key not in EXCHANGE_RATES:
            return {
                "success": False,
                "provider_id": self.name,
                "error_message": f"Unsupported corridor: {key}"
            }
        
        # 80% chance of success for realistic testing
        if random.random() < 0.8:
            # Add a small random variation to the rate (-5% to +5%)
            rate_variation = 1.0 + (random.random() * 0.1 - 0.05)
            rate = EXCHANGE_RATES[key] * rate_variation
            
            # Calculate fees (between 1% and 3% of the amount)
            fee_percentage = 0.01 + (random.random() * 0.02)
            fee = float(amount) * fee_percentage
            
            # Calculate delivery time (between 30 minutes and 48 hours)
            delivery_time = random.randint(30, 48 * 60)
            
            # Calculate destination amount
            destination_amount = float(amount) * rate
            
            return {
                "success": True,
                "provider_id": self.name,
                "exchange_rate": rate,
                "fee": fee,
                "send_amount": float(amount),
                "destination_amount": destination_amount,
                "delivery_time_minutes": delivery_time
            }
        else:
            return {
                "success": False,
                "provider_id": self.name,
                "error_message": "Service temporarily unavailable"
            }

class DummyProvider2:
    name = "Provider2"
    
    def get_quote(self, amount, source_currency, dest_currency, source_country, dest_country, **kwargs):
        # This provider supports fewer corridors (70% of them)
        key = f"{source_currency}-{dest_currency}"
        if key not in EXCHANGE_RATES or random.random() > 0.7:
            return {
                "success": False,
                "provider_id": self.name,
                "error_message": f"Unsupported corridor: {key}"
            }
        
        # 90% chance of success when the corridor is supported
        if random.random() < 0.9:
            # This provider has less competitive rates (-2% to +2%)
            rate_variation = 1.0 + (random.random() * 0.04 - 0.02)
            rate = EXCHANGE_RATES[key] * rate_variation
            
            # Lower fees (between 0.5% and 2% of the amount)
            fee_percentage = 0.005 + (random.random() * 0.015)
            fee = float(amount) * fee_percentage
            
            # Slower delivery time (between 2 hours and 72 hours)
            delivery_time = random.randint(120, 72 * 60)
            
            # Calculate destination amount
            destination_amount = float(amount) * rate
            
            return {
                "success": True,
                "provider_id": self.name,
                "exchange_rate": rate,
                "fee": fee,
                "send_amount": float(amount),
                "destination_amount": destination_amount,
                "delivery_time_minutes": delivery_time
            }
        else:
            return {
                "success": False,
                "provider_id": self.name,
                "error_message": "Unable to process request"
            }

class DummyProvider3:
    name = "Provider3"
    
    def get_quote(self, amount, source_currency, dest_currency, source_country, dest_country, **kwargs):
        # This provider specializes in a few corridors (30% of them with better rates)
        key = f"{source_currency}-{dest_currency}"
        specialized_corridors = ["USD-INR", "USD-PHP", "GBP-INR"]
        
        if key not in EXCHANGE_RATES:
            return {
                "success": False,
                "provider_id": self.name,
                "error_message": f"Unsupported corridor: {key}"
            }
        
        if key in specialized_corridors:
            # Better rates for specialized corridors (+1% to +5%)
            rate_variation = 1.01 + (random.random() * 0.04)
            # Lower fees for specialized corridors (0.3% to 1%)
            fee_percentage = 0.003 + (random.random() * 0.007)
            # Faster delivery for specialized corridors (15 min to 6 hours)
            delivery_time = random.randint(15, 6 * 60)
            success_chance = 0.95
        else:
            # Competitive but not specialized
            rate_variation = 1.0 + (random.random() * 0.04 - 0.02)
            fee_percentage = 0.008 + (random.random() * 0.012)
            delivery_time = random.randint(60, 24 * 60)
            success_chance = 0.8
        
        if random.random() < success_chance:
            rate = EXCHANGE_RATES[key] * rate_variation
            fee = float(amount) * fee_percentage
            destination_amount = float(amount) * rate
            
            return {
                "success": True,
                "provider_id": self.name,
                "exchange_rate": rate,
                "fee": fee,
                "send_amount": float(amount),
                "destination_amount": destination_amount,
                "delivery_time_minutes": delivery_time
            }
        else:
            return {
                "success": False,
                "provider_id": self.name,
                "error_message": "Temporary system maintenance"
            }

class SimulatedAggregator:
    """
    An aggregator that simulates quotes from multiple providers.
    """
    
    PROVIDERS = [
        DummyProvider1(),
        DummyProvider2(),
        DummyProvider3()
    ]
    
    @classmethod
    def get_all_quotes(
        cls,
        source_country: str,
        dest_country: str,
        source_currency: str,
        dest_currency: str,
        amount: Decimal,
        sort_by: str = "best_rate",
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Get quotes from all providers for a specific corridor.
        """
        logger.info(f"Testing corridor: {source_country}->{dest_country}, {source_currency}->{dest_currency}")
        
        start_time = time.time()
        
        # We'll store final results in a list
        results = []
        
        # Function to call a provider and handle exceptions
        def call_provider(provider):
            try:
                resp = provider.get_quote(
                    amount=amount,
                    source_currency=source_currency,
                    dest_currency=dest_currency,
                    source_country=source_country,
                    dest_country=dest_country,
                )
                return resp
            except Exception as exc:
                logger.exception(f"Provider {provider.name} threw exception: {exc}")
                return {
                    "provider_id": provider.name,
                    "success": False,
                    "error_message": str(exc)
                }
        
        # Launch provider calls in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_provider = {executor.submit(call_provider, p): p for p in cls.PROVIDERS}
            
            for future in concurrent.futures.as_completed(future_to_provider):
                result = future.result()
                results.append(result)
        
        # Sort results based on sort_by parameter
        if sort_by == "best_rate":
            # Put success quotes with highest exchange_rate first, then fails at the end
            success_quotes = [q for q in results if q.get("success")]
            fail_quotes = [q for q in results if not q.get("success")]
            success_quotes.sort(key=lambda x: x.get("exchange_rate", 0.0), reverse=True)
            results = success_quotes + fail_quotes
            
        elif sort_by == "fastest_time":
            # Put success quotes with smallest delivery_time_minutes first
            success_quotes = [q for q in results if q.get("success")]
            fail_quotes = [q for q in results if not q.get("success")]
            success_quotes.sort(key=lambda x: x.get("delivery_time_minutes", float("inf")))
            results = success_quotes + fail_quotes
            
        elif sort_by == "lowest_fee":
            # Put success quotes with lowest fee first
            success_quotes = [q for q in results if q.get("success")]
            fail_quotes = [q for q in results if not q.get("success")]
            success_quotes.sort(key=lambda x: x.get("fee", float("inf")))
            results = success_quotes + fail_quotes
        
        # Aggregator is successful if at least one provider succeeded
        aggregator_success = any(r.get("success") for r in results)
        
        # Build final response
        aggregator_response = {
            "success": aggregator_success,
            "source_country": source_country,
            "dest_country": dest_country,
            "source_currency": source_currency,
            "dest_currency": dest_currency,
            "send_amount": float(amount),
            "results": results,
            "timestamp": time.time()
        }
        
        end_time = time.time()
        logger.info(f"Aggregator finished in {end_time - start_time:.2f}s; success={aggregator_success}")
        return aggregator_response

def print_corridor_summary(corridor: Dict[str, Any], result: Dict[str, Any]) -> None:
    """
    Print a summary of results for a corridor.
    """
    print("\n" + "=" * 80)
    print(f"CORRIDOR: {corridor['name']}")
    print(f"Send: {corridor['amount']} {corridor['source_currency']} from {corridor['source_country']} "
          f"to {corridor['dest_country']} in {corridor['dest_currency']}")
    
    success_count = sum(1 for quote in result["results"] if quote.get("success"))
    fail_count = len(result["results"]) - success_count
    
    print(f"Overall Success: {result['success']}")
    print(f"Providers: {len(result['results'])} total, {success_count} successful, {fail_count} failed")
    
    if success_count > 0:
        # Prepare data for tabulation
        table_data = []
        for quote in result["results"]:
            if quote.get("success"):
                table_data.append([
                    quote.get("provider_id", "Unknown"),
                    f"{quote.get('exchange_rate', 0):.4f}",
                    f"{quote.get('fee', 0):.2f} {corridor['source_currency']}",
                    f"{quote.get('destination_amount', 0):.2f} {corridor['dest_currency']}",
                    f"{quote.get('delivery_time_minutes', 'N/A')} min"
                ])
        
        # Print table with results
        headers = ["Provider", "Rate", "Fee", "Recipient Gets", "Delivery Time"]
        print("\nSuccessful Quotes:")
        print(tabulate(table_data, headers=headers, tablefmt="pipe"))
    
    # Print failed providers
    failed_providers = [quote.get("provider_id", "Unknown") for quote in result["results"] 
                     if not quote.get("success")]
    if failed_providers:
        print("\nFailed Providers:", ", ".join(failed_providers))
    
    print("=" * 80)

def main():
    """Run the simulated aggregator for all corridors."""
    print("\nSIMULATED AGGREGATOR TESTS")
    print("==========================\n")
    print(f"Testing {len(CORRIDORS)} corridors with 3 simulated providers")
    
    all_results = []
    
    for corridor in CORRIDORS:
        result = SimulatedAggregator.get_all_quotes(
            source_country=corridor["source_country"],
            dest_country=corridor["dest_country"],
            source_currency=corridor["source_currency"],
            dest_currency=corridor["dest_currency"],
            amount=corridor["amount"],
            sort_by="best_rate"
        )
        
        print_corridor_summary(corridor, result)
        
        # Store the results
        all_results.append({
            "corridor": corridor,
            "result": result
        })
    
    # Print a final summary
    print("\nTEST SUMMARY")
    print("===========")
    
    table_data = []
    for i, test in enumerate(all_results, 1):
        corridor = test["corridor"]
        result = test["result"]
        success_count = sum(1 for quote in result["results"] if quote.get("success"))
        
        table_data.append([
            i,
            corridor["name"],
            f"{success_count}/{len(result['results'])}",
            "Y" if result["success"] else "N"
        ])
    
    headers = ["#", "Corridor", "Success Ratio", "Overall"]
    print(tabulate(table_data, headers=headers, tablefmt="pipe"))

if __name__ == "__main__":
    main() 