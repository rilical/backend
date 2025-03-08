#!/usr/bin/env python3
"""
Test script for provider factory.
"""
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.providers.factory import ProviderFactory

def main():
    """Main entry point for testing provider factory."""
    print("Available providers:")
    available_providers = ProviderFactory.get_available_providers()
    for provider_name in sorted(available_providers.keys()):
        print(f"- {provider_name}")
    
    # Test creating a few providers
    test_providers = [
        "remitbee", 
        "orbitremit", 
        "placid", 
        "wirebarley"  # Added WireBarley to test
    ]
    
    for provider_name in test_providers:
        try:
            provider = ProviderFactory.get_provider(provider_name)
            print(f"\nCreated provider: {provider.name}")
            print(f"Base URL: {provider.base_url}")
        except Exception as e:
            print(f"Error creating provider {provider_name}: {e}")
    
    # Test with invalid provider
    try:
        provider = ProviderFactory.get_provider("nonexistent_provider")
        print(f"Created provider: {provider.name}")
    except ValueError as e:
        print(f"\nExpected error (should be caught): {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 