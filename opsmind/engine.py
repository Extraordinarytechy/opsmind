"""The diagnosis engine ties evidence, a provider, and the contract together.

Flow: Evidence -> provider.diagnose() (raw dict) -> contract.parse_diagnosis()
(validated Diagnosis). The engine owns the validation so every provider, including an
LLM, is held to the same safety bar.
"""

from __future__ import annotations

from .contract import parse_diagnosis
from .models import Diagnosis, Evidence
from .providers.base import DiagnosisProvider


class DiagnosisEngine:
    def __init__(self, provider: DiagnosisProvider) -> None:
        self.provider = provider

    def diagnose(self, evidence: Evidence) -> Diagnosis:
        raw = self.provider.diagnose(evidence)
        # Validation raises ContractError on any violation; callers can catch it and
        # fall back to a safe no-action escalation.
        return parse_diagnosis(raw, source=self.provider.name)
