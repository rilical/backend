"""
Remittance providers package.

This package contains implementations for various remittance providers
that can be used to get exchange rates and fees.
"""

from .factory import ProviderFactory

# Expose helpful functions
def get_provider_by_name(provider_name, **kwargs):
    """
    Get a provider instance by name.
    
    Args:
        provider_name: Name of the provider
        **kwargs: Additional arguments to pass to the provider
        
    Returns:
        An instance of the requested provider
    """
    return ProviderFactory.get_provider(provider_name, **kwargs)

def list_providers():
    """
    Get a list of all registered provider names.
    
    Returns:
        List of provider names
    """
    return ProviderFactory.list_providers()
