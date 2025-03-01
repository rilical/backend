"""
Factory for creating remittance provider instances.
"""
from typing import Dict, Type

from .base.provider import RemittanceProvider
from .moneygram.integration import MoneyGramProvider
from .westernunion.integration import WesternUnionProvider
from .ria.integration import RiaProvider
from .worldremit.integration import WorldRemitProvider
from .remitly.integration import RemitlyProvider

class ProviderFactory:
    """Factory for creating and managing remittance provider instances."""

    _providers: Dict[str, Type[RemittanceProvider]] = {
        'western_union': WesternUnionProvider,
        'moneygram': MoneyGramProvider,
        'ria': RiaProvider,
        'worldremit': WorldRemitProvider,
        'remitly': RemitlyProvider,
        # Add more providers here as they are implemented
        # 'moneygram': MoneyGramProvider,
        # 'ria': RiaProvider,
        # etc.
    }

    @classmethod
    def get_provider(cls, provider_name: str, **kwargs) -> RemittanceProvider:
        """
        Get an instance of a remittance provider.

        Args:
            provider_name: Name of the provider (e.g., 'western_union')
            **kwargs: Additional arguments to pass to the provider constructor

        Returns:
            An instance of the requested provider

        Raises:
            ValueError: If the provider is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unsupported provider: {provider_name}")

        return provider_class(**kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """Get a list of supported provider names."""
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[RemittanceProvider]) -> None:
        """
        Register a new provider class.

        Args:
            name: Name for the provider
            provider_class: The provider class to register
        """
        cls._providers[name.lower()] = provider_class
