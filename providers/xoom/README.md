# Xoom Integration

This module implements the integration with Xoom (a PayPal service) money transfer API. 
Xoom offers multiple payment and delivery methods for international money transfers.

## Overview

Xoom is a digital money transfer service owned by PayPal that allows users to send money, 
pay bills, and reload mobile phones for family and friends around the world. This integration
accesses Xoom's remittance API to fetch rates, fees, and delivery options.

## API Details

The integration interacts with Xoom's API to obtain exchange rates, fees, and payment/delivery options.

### Endpoints

- `/wapi/send-money-app/remittance-engine/remittance` - Main remittance pricing endpoint

### Authentication

The API requires authentication cookies and headers that are obtained through the web interface. 
Our implementation simulates a user session to obtain these tokens.

## Payment Methods

Xoom supports multiple payment methods, which vary by corridor:

- **PayPal USD (PYUSD)** - PayPal USD stablecoin
- **PayPal balance** - Standard PayPal balance
- **Bank Account (ACH)** - Direct bank transfer
- **Debit Card** - Payment via debit card
- **Credit Card** - Payment via credit card (usually has higher fees)

## Delivery Methods

Xoom offers several delivery options, which also vary by corridor:

- **Bank Deposit** - Direct deposit to recipient's bank account
- **Cash Pickup** - Available at partner locations (Walmart, OXXO, etc.)
- **Mobile Wallet** - Delivery to mobile wallets (e.g., Mercado Pago)
- **Debit Card Deposit** - Direct deposit to recipient's debit card

## Usage

To use the Xoom provider:

```python
from apps.providers.xoom.integration import XoomProvider

# Initialize the provider
xoom = XoomProvider(timeout=30)

# Get exchange rate for a specific corridor
result = xoom.get_exchange_rate(
    send_amount=Decimal("700.00"),
    send_currency="USD",
    receive_country="MX"
)

# Print the result
print(result)
```

## Error Handling

The integration handles various error scenarios:

- Connection errors
- Authentication failures
- Rate limiting
- Validation errors

All errors are mapped to specific exception classes derived from `XoomError`.

## Countries and Currencies

Xoom supports many countries and currencies. The integration automatically
fetches the list of supported countries and their respective currencies.

Popular corridors include:
- USA to Mexico
- USA to Philippines
- USA to India
- USA to Colombia
- USA to Guatemala

## Testing

See `tests.py` for comprehensive tests covering all major functionality. 