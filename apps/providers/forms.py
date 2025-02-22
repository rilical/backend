from django import forms
from decimal import Decimal

class SendMoneyForm(forms.Form):
    """
    Form to validate the inputs needed to send money, such as
    send_amount, send_currency, receive_country, etc.
    """

    # Basic numeric field for the amount
    send_amount = forms.DecimalField(
        min_value=Decimal('1.00'),
        max_value=Decimal('5000.00'),
        decimal_places=2,
        required=True,
        label="Amount to Send"
    )

    # Currency code field (ISO 4217)
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('GBP', 'British Pound'),
        ('EUR', 'Euro'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
        ('SGD', 'Singapore Dollar'),
        ('JPY', 'Japanese Yen'),
        ('INR', 'Indian Rupee'),
        ('EGP', 'Egyptian Pound'),
        ('MXN', 'Mexican Peso'),
        ('NZD', 'New Zealand Dollar'),
    ]

    send_currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        required=True,
        label="Currency Code"
    )

    # Country codes with common destinations
    COUNTRY_CHOICES = [
        ('US', 'United States'),
        ('GB', 'United Kingdom'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('IT', 'Italy'),
        ('EG', 'Egypt'),
        ('MX', 'Mexico'),
        ('IN', 'India'),
        ('PH', 'Philippines'),
        ('TR', 'Turkey'),
        ('NG', 'Nigeria'),
    ]

    receive_country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=True,
        label="Destination Country"
    )

    send_country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=True,
        label="Origin Country"
    )

    # Optional location fields
    sender_postal_code = forms.CharField(
        max_length=10,
        required=False,
        label="Sender Postal Code"
    )
    
    sender_city = forms.CharField(
        max_length=50,
        required=False,
        label="Sender City"
    )
    
    sender_state = forms.CharField(
        max_length=50,
        required=False,
        label="Sender State/Province"
    )

    def clean(self):
        """
        Custom validation to ensure sensible combinations of fields
        """
        cleaned_data = super().clean()
        send_country = cleaned_data.get('send_country')
        receive_country = cleaned_data.get('receive_country')

        if send_country and receive_country:
            if send_country == receive_country:
                raise forms.ValidationError(
                    "Send and receive countries must be different"
                )

        return cleaned_data 