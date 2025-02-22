"""MoneyGram-specific exceptions."""
from typing import Optional, Dict, Any
from . import ProviderError


class MGError(ProviderError):
    """Base class for MoneyGram errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, provider="MoneyGram", error_code=error_code, details=details)

        