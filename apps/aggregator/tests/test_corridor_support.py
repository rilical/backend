#!/usr/bin/env python3
"""
Test script to analyze corridor support across all providers.
This helps identify which providers work for which corridors.
"""

import os
import sys
import logging
import time
import json
from decimal import Decimal
from tabulate import tabulate
from typing import Dict, List, Any, Tuple
import concurrent.futures

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Import the aggregator
from apps.aggregator.aggregator import Aggregator

# Define test corridors
TEST_CORRIDORS = [
    # source_country, dest_country, source_currency, dest_currency, test_name
    ("US", "IN", "USD", "INR", "US to India"),
    ("US", "MX", "USD", "MXN", "US to Mexico"),
    ("US", "PH", "USD", "PHP", "US to Philippines"),
    ("GB", "IN", "GBP", "INR", "UK to India"),
    ("CA", "IN", "CAD", "INR", "Canada to India"),
    ("AU", "IN", "AUD", "INR", "Australia to India"),
    ("SG", "IN", "SGD", "INR", "Singapore to India"),
    ("AE", "IN", "AED", "INR", "UAE to India"),
    ("US", "NG", "USD", "NGN", "US to Nigeria"),
    ("ZA", "ZW", "ZAR", "USD", "South Africa to Zimbabwe"),
]


def test_corridor(corridor: Tuple[str, str, str, str, str]) -> Dict[str, Any]:
    """
    Test a specific corridor with all providers.
    
    Args:
        corridor: Tuple of (source_country, dest_country, source_currency, dest_currency, test_name)
        
    Returns:
        Dictionary with test results
    """
    source_country, dest_country, source_currency, dest_currency, test_name = corridor
    
    logger.info(f"Testing corridor: {test_name} ({source_country}->{dest_country}, {source_currency}->{dest_currency})")
    
    start_time = time.time()
    
    # Get all providers from the Aggregator
    all_providers = [p.__class__.__name__ for p in Aggregator.PROVIDERS]
    
    # Call the aggregator
    result = Aggregator.get_all_quotes(
        source_country=source_country,
        dest_country=dest_country,
        source_currency=source_currency,
        dest_currency=dest_currency,
        amount=Decimal("1000.00"),
        sort_by="best_rate"
    )
    
    elapsed_time = time.time() - start_time
    
    # Extract successful and failed providers
    success_count = 0
    successful_providers = []
    failed_providers = {}
    
    for provider_result in result.get("all_providers", []):
        provider_id = provider_result.get("provider_id", "Unknown")
        if provider_result.get("success", False):
            success_count += 1
            successful_providers.append(provider_id)
        else:
            failed_providers[provider_id] = provider_result.get("error_message", "Unknown error")
    
    # Prepare results
    test_results = {
        "test_name": test_name,
        "source_country": source_country,
        "dest_country": dest_country,
        "source_currency": source_currency,
        "dest_currency": dest_currency,
        "corridor": f"{source_country}->{dest_country} ({source_currency}->{dest_currency})",
        "elapsed_seconds": round(elapsed_time, 2),
        "total_providers": len(all_providers),
        "success_count": success_count,
        "success_rate": round((success_count / len(all_providers)) * 100, 2) if all_providers else 0,
        "successful_providers": successful_providers,
        "failed_providers": failed_providers,
        "all_provider_results": result.get("all_providers", [])
    }
    
    logger.info(f"Corridor {test_name} completed in {elapsed_time:.2f}s. Success rate: {test_results['success_rate']}% ({success_count}/{len(all_providers)})")
    return test_results


def analyze_all_corridors() -> List[Dict[str, Any]]:
    """
    Test all corridors and return the results.
    
    Returns:
        List of test results for each corridor
    """
    results = []
    
    for corridor in TEST_CORRIDORS:
        try:
            result = test_corridor(corridor)
            results.append(result)
        except Exception as e:
            logger.error(f"Error testing corridor {corridor[4]}: {str(e)}")
    
    return results


def print_corridor_summary(results: List[Dict[str, Any]]) -> None:
    """
    Print a summary of corridor test results.
    
    Args:
        results: List of test results from test_corridor
    """
    # Sort results by success rate (descending)
    sorted_results = sorted(results, key=lambda x: x["success_rate"], reverse=True)
    
    headers = ["Corridor", "Success Rate", "Working Providers", "Failed Count"]
    table_data = []
    
    for result in sorted_results:
        table_data.append([
            result["test_name"],
            f"{result['success_count']}/{result['total_providers']} ({result['success_rate']}%)",
            ", ".join(result["successful_providers"]),
            len(result["failed_providers"])
        ])
    
    print("\n=== Corridor Support Summary ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def print_provider_summary(results: List[Dict[str, Any]]) -> None:
    """
    Print a summary of provider support across corridors.
    
    Args:
        results: List of test results from test_corridor
    """
    provider_stats = {}
    all_providers = set()
    
    # Collect all providers
    for result in results:
        all_providers.update(result["successful_providers"])
        all_providers.update(result["failed_providers"].keys())
    
    # Initialize stats for each provider
    for provider in all_providers:
        provider_stats[provider] = {
            "total_corridors": 0,
            "successful_corridors": 0,
            "corridors": []
        }
    
    # Collect statistics
    for result in results:
        for provider in all_providers:
            provider_stats[provider]["total_corridors"] += 1
            
            if provider in result["successful_providers"]:
                provider_stats[provider]["successful_corridors"] += 1
                provider_stats[provider]["corridors"].append(result["test_name"])
    
    # Sort providers by success rate
    sorted_providers = sorted(
        provider_stats.items(),
        key=lambda x: (x[1]["successful_corridors"], x[1]["successful_corridors"] / x[1]["total_corridors"]),
        reverse=True
    )
    
    headers = ["Provider", "Success Rate", "Percentage", "Example Corridors"]
    table_data = []
    
    for provider, stats in sorted_providers:
        success_rate = f"{stats['successful_corridors']}/{stats['total_corridors']}"
        percentage = (stats['successful_corridors'] / stats['total_corridors']) * 100
        examples = ", ".join(stats["corridors"][:3])
        if len(stats["corridors"]) > 3:
            examples += ", ..."
        
        table_data.append([
            provider,
            success_rate,
            f"{percentage:.1f}%",
            examples if stats["corridors"] else "None"
        ])
    
    print("\n=== Provider Support Summary ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def create_provider_matrix(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a matrix showing which providers support which corridors.
    
    Args:
        results: List of test results from test_corridor
        
    Returns:
        Dictionary with matrix data
    """
    all_providers = set()
    corridors = []
    
    # Collect all providers and corridors
    for result in results:
        all_providers.update(result["successful_providers"])
        all_providers.update(result["failed_providers"].keys())
        corridors.append(result["test_name"])
    
    # Sort providers and corridors
    sorted_providers = sorted(list(all_providers))
    
    # Create the matrix
    matrix = {provider: [] for provider in sorted_providers}
    
    # Fill the matrix
    for result in results:
        for provider in sorted_providers:
            if provider in result["successful_providers"]:
                matrix[provider].append("✓")
            else:
                matrix[provider].append("✗")
    
    return {
        "providers": sorted_providers,
        "corridors": corridors,
        "matrix": matrix
    }


def print_matrix(matrix: Dict[str, Any]) -> None:
    """
    Print the provider-corridor support matrix.
    
    Args:
        matrix: Matrix data from create_provider_matrix
    """
    headers = ["Provider"] + matrix["corridors"]
    table_data = []
    
    for provider in matrix["providers"]:
        row = [provider] + matrix["matrix"][provider]
        table_data.append(row)
    
    print("\n=== Provider-Corridor Support Matrix ===")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def save_results(results: List[Dict[str, Any]], filename: str) -> None:
    """
    Save test results to a JSON file.
    
    Args:
        results: List of test results from test_corridor
        filename: Path to save the results
    """
    # Remove large fields to reduce file size
    simplified_results = []
    
    for result in results:
        simplified = result.copy()
        simplified.pop("all_provider_results", None)
        simplified_results.append(simplified)
    
    with open(filename, 'w') as f:
        json.dump(simplified_results, f, indent=2, default=str)
    
    logger.info(f"Results saved to {filename}")


def main():
    """Main function."""
    print("RemitScout Aggregator - Corridor Support Analysis")
    print("===============================================")
    
    try:
        # Test all corridors
        results = analyze_all_corridors()
        
        # Print summaries
        print_corridor_summary(results)
        print_provider_summary(results)
        
        # Create and print the matrix
        matrix = create_provider_matrix(results)
        print_matrix(matrix)
        
        # Save results
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(output_dir, exist_ok=True)
        save_results(results, os.path.join(output_dir, "corridor_support.json"))
        
        print("\nAnalysis complete!")
        
    except Exception as e:
        logger.exception(f"Error during analysis: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 