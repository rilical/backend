"""
Production-ready module for RemitScout API.

This module used to provide development-only patches but is now production-ready
with no mocks or patches.
"""

def patch_aggregator():
    """
    Production implementation - does nothing.
    All providers now implement the required methods directly.
    """
    print("Running in production mode - no patches applied.")

# No patching in production
patch_aggregator() 