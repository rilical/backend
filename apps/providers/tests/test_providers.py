"""Tests for provider functionality."""
import json
from typing import Dict, List

from apps.providers.tests.providers.western_union_test import test_western_union
from apps.providers.tests.providers.money_gram_test import test_money_gram


def test_all() -> List[Dict]:
    """
    Run all provider tests and return results.
    
    Returns:
        List of test results (dict) for each provider
    """
    print("\nStarting provider tests...")
    results = []
    
    # Test Western Union provider
    print("\nRunning Western Union tests...")
    wu_results = test_western_union()
    results.append(wu_results)

    # Test Money Gram provider (Soon)
    # print("\n Running Moneygram tests...")
    # mg_results = test_money_gram
    # results.append(mg_results)

    
    
    # Add more provider tests here as they are implemented
    # results.append(test_moneygram())
    # results.append(test_ria())
    # etc.
    
    return results

def print_results(results: List[Dict]) -> None:
    """Print test results in a readable format."""
    print("\nProvider Test Results")
    print("=" * 50)
    
    total_passed = 0
    total_failed = 0
    
    for provider_result in results:
        provider_name = provider_result['provider']
        print(f"\n{provider_name}:")
        print("-" * 30)
        
        passed = provider_result['passed']
        failed = provider_result['failed']
        
        total_passed += passed
        total_failed += failed
        
        for test_outcome in provider_result['tests']:
            status_icon = "✅" if test_outcome['status'] == 'passed' else "❌"
            print(f"{status_icon} {test_outcome['name']}")
            if test_outcome['status'] == 'failed':
                print(f"   Error: {test_outcome.get('error', 'Unknown error')}")
    
    print("\nSummary:")
    print(f"Total Tests: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")

def main():
    """Run all provider tests and display results."""
    print("Starting test runner...")
    results = test_all()
    print_results(results)
    print("Test run complete.")

if __name__ == '__main__':
    main()
