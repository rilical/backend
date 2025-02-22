"""
Serializers for provider rates API.
"""
from rest_framework import serializers
from .models import Provider, ExchangeRate

class ProviderSerializer(serializers.ModelSerializer):
    """Serializer for remittance providers."""
    
    class Meta:
        model = Provider
        fields = ['id', 'name', 'website', 'is_active']

class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializer for exchange rates with calculated fields."""
    
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    total_cost_usd = serializers.SerializerMethodField()
    recipient_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = ExchangeRate
        fields = [
            'provider_name',
            'send_amount',
            'send_currency',
            'receive_country',
            'exchange_rate',
            'transfer_fee',
            'total_cost_usd',
            'recipient_amount',
            'delivery_time',
            'timestamp'
        ]
    
    def get_total_cost_usd(self, obj):
        """Get total cost including fees."""
        return obj.total_cost_usd()
    
    def get_recipient_amount(self, obj):
        """Get amount recipient will receive."""
 