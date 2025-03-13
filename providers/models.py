"""
Models for storing provider rates and information.
"""
from django.db import models
from django.utils import timezone


class Provider(models.Model):
    """Remittance service provider (e.g., Western Union, MoneyGram)."""

    name = models.CharField(max_length=100, unique=True)
    website = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class ExchangeRate(models.Model):
    """Exchange rate and fee information from a provider."""

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="rates")
    send_amount = models.DecimalField(max_digits=10, decimal_places=2)
    send_currency = models.CharField(max_length=3)  # ISO 4217 currency code
    receive_country = models.CharField(max_length=2)  # ISO 3166-1 alpha-2 country code
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4)
    transfer_fee = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=timezone.now)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.provider.name} - {self.send_currency} to {self.receive_country}"

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["send_currency", "receive_country", "timestamp"]),
            models.Index(fields=["provider", "timestamp"]),
        ]

    def total_cost_usd(self):
        """Calculate total cost in USD including fees."""
        return float(self.send_amount + self.transfer_fee)

    def recipient_amount(self):
        """Calculate how much the recipient will get."""
        return float(self.send_amount * self.exchange_rate)
