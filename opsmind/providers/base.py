"""Provider interface. A provider turns Evidence into a RAW diagnosis dict.

The engine, not the provider, is responsible for validating that raw dict against the
contract. This keeps providers simple and keeps the safety check in one place.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import Evidence


class DiagnosisProvider(ABC):
    name: str = "base"

    @abstractmethod
    def diagnose(self, evidence: Evidence) -> dict[str, Any]:
        """Return a raw diagnosis dict (to be validated by the engine)."""
        raise NotImplementedError
