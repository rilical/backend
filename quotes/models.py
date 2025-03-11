from django.db import models
from django.utils import timezone


class Provider(models.Model):
    """
    Model representing a remittance provider service.
    """
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    website = models.URLField(blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
    api_base_url = models.URLField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FeeQuote(models.Model):
    """
    Model storing fee quotes from various providers for specific corridors.
    """
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='quotes')
    source_country = models.CharField(max_length=3)  # ISO 3166-1 alpha-3 country code
    destination_country = models.CharField(max_length=3)  # ISO 3166-1 alpha-3 country code
    source_currency = models.CharField(max_length=3)  # ISO 4217 currency code
    destination_currency = models.CharField(max_length=3)  # ISO 4217 currency code
    payment_method = models.CharField(max_length=50)  # e.g., "DEBIT_CARD", "BANK_TRANSFER"
    delivery_method = models.CharField(max_length=50)  # e.g., "PICKUP", "BANK_DEPOSIT"
    send_amount = models.DecimalField(max_digits=10, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6)
    delivery_time_minutes = models.IntegerField()
    destination_amount = models.DecimalField(max_digits=14, decimal_places=2)
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [
            [
                'provider', 'source_country', 'destination_country', 
                'source_currency', 'destination_currency', 'payment_method', 
                'delivery_method', 'send_amount'
            ]
        ]
        indexes = [
            models.Index(fields=['provider', 'source_country', 'destination_country']),
            models.Index(fields=['source_country', 'destination_country']),
            models.Index(fields=['provider', 'payment_method', 'delivery_method']),
            models.Index(fields=['last_updated']),
        ]
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.provider.name}: {self.source_country} → {self.destination_country} ({self.send_amount} {self.source_currency})"


class QuoteQueryLog(models.Model):
    """
    Log of user quote queries for analytics and caching optimization.
    """
    source_country = models.CharField(max_length=3)
    destination_country = models.CharField(max_length=3)
    source_currency = models.CharField(max_length=3)
    destination_currency = models.CharField(max_length=3)
    send_amount = models.DecimalField(max_digits=10, decimal_places=2)
    user_ip = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['source_country', 'destination_country']),
            models.Index(fields=['timestamp']),
        ] 