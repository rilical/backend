"""
Factory for creating remittance provider instances.
"""
from typing import Dict, Type

from .alansari.integration import AlAnsariProvider
from .base.provider import RemittanceProvider
from .dahabshiil.integration import DahabshiilProvider
from .mukuru.integration import MukuruProvider
from .orbitremit.integration import OrbitRemitProvider
from .paysend.integration import PaysendProvider
from .placid.integration import PlacidProvider

# Import only the providers we have confirmed are implemented
from .remitbee.integration import RemitbeeProvider
from .remitguru.integration import RemitGuruProvider
from .rewire.integration import RewireProvider
from .sendwave.integration import WaveProvider as SendwaveProvider
from .wirebarley.integration import WireBarleyProvider
from .xe.integration import XEProvider


class ProviderFactory:
    """Factory for creating and managing remittance provider instances."""

    _providers: Dict[str, Type[RemittanceProvider]] = {
        # Include only the providers we've implemented and confirmed
        "REMITBEE": RemitbeeProvider,
        "REMITGURU": RemitGuruProvider,
        "XE": XEProvider,
        "SENDWAVE": SendwaveProvider,
        "REWIRE": RewireProvider,
        "MUKURU": MukuruProvider,
        "DAHABSHIIL": DahabshiilProvider,
        "ALANSARI": AlAnsariProvider,
        "PLACID": PlacidProvider,
        "ORBITREMIT": OrbitRemitProvider,
        "WIREBARLEY": WireBarleyProvider,
        "PAYSEND": PaysendProvider,
        # Add more providers as they are implemented and confirmed
    }

    @classmethod
    def get_provider(cls, provider_name: str, **kwargs) -> RemittanceProvider:
        """
        Get an instance of a remittance provider.

        Args:
            provider_name: Name of the provider to instantiate
            **kwargs: Additional arguments to pass to the provider constructor

        Returns:
            An instance of the requested provider

        Raises:
            ValueError: If the requested provider is not supported
        """
        # Convert provider name to uppercase to ensure case-insensitive lookup
        provider_name_upper = provider_name.upper()
        if provider_name_upper not in cls._providers:
            raise ValueError(f"Unsupported provider: {provider_name}")

        provider_class = cls._providers[provider_name_upper]
        return provider_class(**kwargs)

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[RemittanceProvider]) -> None:
        """
        Register a new provider class.

        Args:
            name: Name to register the provider under
            provider_class: The provider class to register
        """
        cls._providers[name] = provider_class

    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[RemittanceProvider]]:
        """
        Get a dictionary of all available providers.

        Returns:
            Dictionary mapping provider names to provider classes
        """
        return dict(cls._providers)

    @classmethod
    def list_providers(cls) -> list:
        """
        Get a list of all available provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
