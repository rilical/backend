"""
Corridor Analyzer for RemitScout Aggregator.

This module provides utilities to analyze which corridors (country pairs) are supported
by which providers, helping to understand coverage and identify gaps.
"""

import logging
import sys
import json
import os
from typing import Dict, List, Set, Tuple
from tabulate import tabulate
from decimal import Decimal
import concurrent.futures

# Import the Aggregator
from apps.aggregator.aggregator import Aggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Common country corridors to test
TEST_CORRIDORS = [
    # Source country, destination country, source currency, destination currency
    ("US", "IN", "USD", "INR"),  # US to India
    ("US", "MX", "USD", "MXN"),  # US to Mexico
    ("US", "PH", "USD", "PHP"),  # US to Philippines
    ("GB", "IN", "GBP", "INR"),  # UK to India
    ("CA", "IN", "CAD", "INR"),  # Canada to India
    ("AU", "IN", "AUD", "INR"),  # Australia to India
    ("US", "CN", "USD", "CNY"),  # US to China
    ("GB", "PK", "GBP", "PKR"),  # UK to Pakistan
    ("SG", "IN", "SGD", "INR"),  # Singapore to India
    ("AE", "IN", "AED", "INR"),  # UAE to India
    ("DE", "TR", "EUR", "TRY"),  # Germany to Turkey
    ("AU", "PH", "AUD", "PHP"),  # Australia to Philippines
    ("CA", "MX", "CAD", "MXN"),  # Canada to Mexico
    ("SG", "MY", "SGD", "MYR"),  # Singapore to Malaysia
    ("DE", "PL", "EUR", "PLN"),  # Germany to Poland
]

def test_corridor(
    source_country: str, 
    dest_country: str, 
    source_currency: str, 
    dest_currency: str
) -> Dict:
    """
    Test a specific corridor with all providers to see which ones support it.
    
    Args:
        source_country: Source country code (ISO-2)
        dest_country: Destination country code (ISO-2)
        source_currency: Source currency code (ISO-3)
        dest_currency: Destination currency code (ISO-3)
        
    Returns:
        Dictionary with test results
    """
    logger.info(f"Testing corridor: {source_country}->{dest_country} ({source_currency}->{dest_currency})")
    
    # Call the aggregator with a standard amount
    result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=Decimal("1000.00"),
        sort_by="best_rate"
    )
    
    # Extract successful provider IDs
    successful_providers = [
        q.get("provider_id") for q in result.get("quotes", [])
        if q.get("success", False)
    ]
    
    # Extract failed provider IDs and error messages
    failed_providers = {}
    for provider in result.get("all_providers", []):
        if not provider.get("success", False):
            failed_providers[provider.get("provider_id", "Unknown")] = provider.get("error_message", "Unknown error")
    
    return {
        "corridor": f"{source_country}->{dest_country} ({source_currency}->{dest_currency})",
        "source_country": source_country,
        "dest_country": dest_country,
        "source_currency": source_currency,
        "dest_currency": dest_currency,
        "success": len(successful_providers) > 0,
        "successful_providers": successful_providers,
        "failed_providers": failed_providers,
        "total_providers": len(result.get("all_providers", [])),
        "success_count": len(successful_providers),
        "fail_count": len(failed_providers)
    }


def analyze_corridors(corridors=None, max_workers=5) -> List[Dict]:
    """
    Analyze a list of corridors to determine provider support.
    
    Args:
        corridors: List of corridors to test, each as (source_country, dest_country, source_currency, dest_currency)
        max_workers: Maximum number of concurrent tests
        
    Returns:
        List of test results
    """
    if corridors is None:
        corridors = TEST_CORRIDORS
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_corridor = {
            executor.submit(
                test_corridor, 
                source_country, 
                dest_country, 
                source_currency, 
                dest_currency
            ): (source_country, dest_country, source_currency, dest_currency) 
            for source_country, dest_country, source_currency, dest_currency in corridors
        }
        
        for future in concurrent.futures.as_completed(future_to_corridor):
            corridor = future_to_corridor[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(f"Completed corridor {corridor[0]}->{corridor[1]}: {result['success_count']}/{result['total_providers']} successful")
            except Exception as e:
                logger.error(f"Error testing corridor {corridor[0]}->{corridor[1]}: {str(e)}")
    
    return results


def generate_provider_matrix(results: List[Dict]) -> Dict:
    """
    Generate a matrix showing which providers support which corridors.
    
    Args:
        results: List of test results from analyze_corridors
        
    Returns:
        Dictionary with provider support matrix
    """
    providers = set()
    corridors = []
    
    # Collect all provider IDs and corridors
    for result in results:
        corridors.append(result["corridor"])
        providers.update(result["successful_providers"])
    
    # Sort providers and corridors
    providers = sorted(list(providers))
    
    # Create the matrix
    matrix = {provider: [] for provider in providers}
    for result in results:
        for provider in providers:
            if provider in result["successful_providers"]:
                matrix[provider].append("✓")
            else:
                matrix[provider].append("✗")
    
    return {
        "providers": providers,
        "corridors": corridors,
        "matrix": matrix
    }


def print_corridor_summary(results: List[Dict]) -> None:
    """
    Print a summary of corridor test results.
    
    Args:
        results: List of test results from analyze_corridors
    """
    # Sort results by success rate
    sorted_results = sorted(results, key=lambda x: x["success_count"], reverse=True)
    
    table_data = []
    for result in sorted_results:
        table_data.append([
            result["corridor"],
            f"{result['success_count']}/{result['total_providers']}",
            ", ".join(result["successful_providers"]),
            len(result["failed_providers"])
        ])
    
    headers = ["Corridor", "Success Rate", "Working Providers", "Failed Providers"]
    print("\nCorridor Support Summary:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def print_provider_summary(results: List[Dict]) -> None:
    """
    Print a summary of provider support across corridors.
    
    Args:
        results: List of test results from analyze_corridors
    """
    # Collect provider stats
    provider_stats = {}
    
    # Count successful corridors per provider
    for result in results:
        for provider in result["successful_providers"]:
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "successful_corridors": 0, 
                    "total_corridors": 0,
                    "corridors": []
                }
            provider_stats[provider]["successful_corridors"] += 1
            provider_stats[provider]["corridors"].append(result["corridor"])
        
        # Count total attempts per provider
        for provider in set(result["successful_providers"]).union(result["failed_providers"].keys()):
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "successful_corridors": 0, 
                    "total_corridors": 0,
                    "corridors": []
                }
            provider_stats[provider]["total_corridors"] += 1
    
    # Sort providers by success rate
    sorted_providers = sorted(
        provider_stats.items(), 
        key=lambda x: (x[1]["successful_corridors"], x[1]["successful_corridors"] / max(x[1]["total_corridors"], 1)), 
        reverse=True
    )
    
    table_data = []
    for provider, stats in sorted_providers:
        success_rate = f"{stats['successful_corridors']}/{stats['total_corridors']}"
        percentage = (stats['successful_corridors'] / max(stats['total_corridors'], 1)) * 100
        table_data.append([
            provider,
            success_rate,
            f"{percentage:.1f}%",
            ", ".join(stats["corridors"][:3]) + ("..." if len(stats["corridors"]) > 3 else "")
        ])
    
    headers = ["Provider", "Success Rate", "Percentage", "Example Corridors"]
    print("\nProvider Corridor Support:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def print_matrix(matrix: Dict) -> None:
    """
    Print the provider-corridor support matrix.
    
    Args:
        matrix: Matrix from generate_provider_matrix
    """
    headers = ["Provider"] + matrix["corridors"]
    table_data = []
    
    for provider in matrix["providers"]:
        row = [provider] + matrix["matrix"][provider]
        table_data.append(row)
    
    print("\nProvider-Corridor Support Matrix:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def save_results(results: List[Dict], filename: str) -> None:
    """
    Save analysis results to a JSON file.
    
    Args:
        results: List of test results from analyze_corridors
        filename: Path to the output file
    """
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {filename}")


def main() -> None:
    """Main function to run the corridor analysis."""
    logger.info("Starting corridor analysis...")
    
    # Analyze corridors
    results = analyze_corridors()
    
    # Print summaries
    print_corridor_summary(results)
    print_provider_summary(results)
    
    # Generate and print the matrix
    matrix = generate_provider_matrix(results)
    print_matrix(matrix)
    
    # Save results
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis")
    os.makedirs(output_dir, exist_ok=True)
    save_results(results, os.path.join(output_dir, "corridor_analysis.json"))
    
    logger.info("Corridor analysis complete!")


if __name__ == "__main__":
    main() 