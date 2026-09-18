"""Diagnosis providers. Default is the deterministic MockProvider; Bedrock is optional."""

from .base import DiagnosisProvider
from .mock import MockProvider

__all__ = ["DiagnosisProvider", "MockProvider", "get_provider"]


def get_provider(name: str = "mock"):
    """Factory. 'mock' works everywhere; 'bedrock' is imported lazily so boto3 is
    only required when it is actually selected."""
    name = (name or "mock").lower()
    if name == "mock":
        return MockProvider()
    if name == "bedrock":
        from .bedrock import BedrockProvider  # lazy import
        return BedrockProvider()
    raise ValueError(f"unknown provider: {name}")
