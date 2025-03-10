"""
RemitScout Aggregator Module

This module provides a parallel execution aggregator that fetches quotes from multiple
remittance providers simultaneously and returns consolidated results.
"""

from apps.aggregator.aggregator import Aggregator

__all__ = ["Aggregator"]
