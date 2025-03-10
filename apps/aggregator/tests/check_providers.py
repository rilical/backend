#!/usr/bin/env python
"""
A simple script to verify that the Aggregator class can be imported
and to print its list of providers.
"""

import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Configure logging
logging.basicConfig(level=logging.INFO)

try:
    # Try to import the Aggregator
    from apps.aggregator.aggregator import Aggregator
    
    print("Successfully imported the Aggregator class!\n")
    
    # Print the providers
    print("Configured Providers:")
    for i, provider in enumerate(Aggregator.PROVIDERS, 1):
        provider_name = getattr(provider, "name", provider.__class__.__name__)
        print(f"{i}. {provider_name} ({provider.__class__.__name__})")
    
    print(f"\nTotal providers: {len(Aggregator.PROVIDERS)}")
    
except ImportError as e:
    print(f"Failed to import Aggregator: {e}")
except Exception as e:
    print(f"Unexpected error: {e}") 