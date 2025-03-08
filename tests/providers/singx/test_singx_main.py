"""
Tests for the SingX remittance provider integration.

This module contains test cases for:
- Exchange rate retrieval
- Quote generation
- Fee calculation
- Error handling
- Various corridors and payment methods
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .integration import SingXProvider
from .exceptions import (
    SingXError,
    SingXAuthError,
    SingXAPIError,
    SingXValidationError,
    SingXCorridorError,
    SingXQuoteError,
    SingXRateError
)

# Test data
MOCK_EXCHANGE_RESPONSE = {
    "exchangeRate": "60.25",
    "singxFee": "5.00",
    "quote": "test-quote-id",
    "sendAmount": "1000.00",
    "receiveAmount": "60250.00",
    "totalPayable": "1005.00"
}

@pytest.fixture
def provider():
    """Create a SingX provider instance for testing."""
    return SingXProvider()

@pytest.fixture
def mock_response():
    """Create a mock response object."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = MOCK_EXCHANGE_RESPONSE
    return mock

def test_init(provider):
    """Test provider initialization."""
    assert provider.name == "singx"
    assert provider.base_url == "https://api.singx.co"
    assert provider.session is not None

def test_validate_country(provider):
    """Test country validation."""
    # Test valid country
    assert provider._validate_country("SG") == provider.COUNTRY_CODES["SG"]
    
    # Test invalid country
    with pytest.raises(SingXValidationError):
        provider._validate_country("XX")

@pytest.mark.asyncio
async def test_get_exchange_rate(provider, mock_response):
    """Test exchange rate retrieval."""
    with patch("requests.Session.post", return_value=mock_response):
        result = provider.get_exchange_rate(
            send_country="SG",
            send_currency="SGD",
            receive_country="IN",
            receive_currency="INR",
            amount=Decimal("1000.00")
        )
        
        assert result["success"] is True
        assert result["rate"] == "60.25"
        assert result["fee"] == "5.00"
        assert result["quote_id"] == "test-quote-id"

@pytest.mark.asyncio
async def test_get_quote_send_amount(provider, mock_response):
    """Test quote generation with send amount."""
    with patch("requests.Session.post", return_value=mock_response):
        result = provider.get_quote(
            send_amount=Decimal("1000.00"),
            send_currency="SGD",
            receive_currency="INR"
        )
        
        assert result["success"] is True
        assert result["send_amount"] == "1000.00"
        assert result["receive_amount"] == "60250.00"
        assert result["fee"] == "5.00"
        assert result["total_cost"] == "1005.00"

@pytest.mark.asyncio
async def test_get_quote_receive_amount(provider, mock_response):
    """Test quote generation with receive amount."""
    with patch("requests.Session.post", return_value=mock_response):
        result = provider.get_quote(
            receive_amount=Decimal("60250.00"),
            send_currency="SGD",
            receive_currency="INR"
        )
        
        assert result["success"] is True
        assert result["send_amount"] == "1000.00"
        assert result["receive_amount"] == "60250.00"
        assert result["fee"] == "5.00"

def test_get_quote_validation(provider):
    """Test quote validation."""
    with pytest.raises(SingXValidationError):
        provider.get_quote(
            send_amount=None,
            receive_amount=None,
            send_currency="SGD",
            receive_currency="INR"
        )

@pytest.mark.asyncio
async def test_get_fees(provider, mock_response):
    """Test fee calculation."""
    with patch("requests.Session.post", return_value=mock_response):
        result = provider.get_fees(
            send_amount=Decimal("1000.00"),
            send_currency="SGD",
            receive_currency="INR"
        )
        
        assert result["success"] is True
        assert result["transfer_fee"] == "5.00"
        assert result["total_fee"] == "5.00"
        assert result["fee_currency"] == "SGD"

def test_api_error_handling(provider):
    """Test API error handling."""
    mock_error_response = MagicMock()
    mock_error_response.status_code = 400
    mock_error_response.json.return_value = {
        "errors": ["Invalid request parameters"]
    }
    
    with patch("requests.Session.post", return_value=mock_error_response):
        with pytest.raises(SingXAPIError):
            provider._handle_response(mock_error_response)

def test_auth_error_handling(provider):
    """Test authentication error handling."""
    mock_auth_error = MagicMock()
    mock_auth_error.status_code = 401
    mock_auth_error.json.return_value = {
        "errors": ["Authentication failed"]
    }
    
    with patch("requests.Session.post", return_value=mock_auth_error):
        with pytest.raises(SingXAuthError):
            provider._handle_response(mock_auth_error)

@pytest.mark.parametrize("payment_method", [
    {"swift": True},
    {"cash_pickup": True},
    {"wallet": True},
    {"business": True}
])
def test_payment_methods(provider, mock_response, payment_method):
    """Test different payment methods."""
    with patch("requests.Session.post", return_value=mock_response):
        result = provider.get_quote(
            send_amount=Decimal("1000.00"),
            send_currency="SGD",
            receive_currency="INR",
            **payment_method
        )
        
        assert result["success"] is True
        assert result["send_amount"] == "1000.00"
        assert result["receive_amount"] == "60250.00"

@pytest.mark.parametrize("corridor", [
    ("SG", "IN", "SGD", "INR"),
    ("SG", "PH", "SGD", "PHP"),
    ("SG", "ID", "SGD", "IDR"),
    ("SG", "MY", "SGD", "MYR")
])
def test_supported_corridors(provider, mock_response, corridor):
    """Test supported corridors."""
    send_country, receive_country, send_currency, receive_currency = corridor
    
    with patch("requests.Session.post", return_value=mock_response):
        result = provider.get_exchange_rate(
            send_country=send_country,
            send_currency=send_currency,
            receive_country=receive_country,
            receive_currency=receive_currency
        )
        
        assert result["success"] is True
        assert result["source_country"] == send_country
        assert result["target_country"] == receive_country 