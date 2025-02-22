"""
Base class for remittance providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
from decimal import Decimal

class RemittanceProvider(ABC):
    """Abstract base class for remittance providers."""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
    
    @abstractmethod
    def get_exchange_rate(self, send_amount: Decimal, send_currency: str, 
                         receive_country: str) -> Optional[Dict]:
        """
        Get exchange rate and fees for a money transfer.
        
        Args:
            send_amount: Amount to send
            send_currency: Currency code to send (e.g. 'USD')
            receive_country: Destination country code (e.g. 'MX')
            
        Returns:
            Dictionary containing rate information or None if failed
        """
        pass