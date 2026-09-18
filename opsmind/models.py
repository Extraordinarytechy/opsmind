"""Core data models for OpsMind.

These are deliberately plain dataclasses (no heavy dependencies) so the engine runs
anywhere, including offline CI. Everything the LLM sees is built from these typed
structures, never from raw free text.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """A single firing alert, typically from Prometheus Alertmanager."""

    name: str
    severity: Severity
    summary: str
    service: str
    labels: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Alert":
        return Alert(
            name=str(d["name"]),
            severity=Severity(str(d.get("severity", "warning"))),
            summary=str(d.get("summary", "")),
            service=str(d.get("service", "unknown")),
            labels={str(k): str(v) for k, v in d.get("labels", {}).items()},
        )


@dataclass
class MetricSample:
    """A named signal with a value and the threshold it is compared against."""

    name: str
    value: float
    threshold: float | None = None
    unit: str = ""

    @property
    def breached(self) -> bool:
        return self.threshold is not None and self.value > self.threshold


@dataclass
class Evidence:
    """Everything OpsMind gathers about an incident BEFORE any AI is involved.

    Grounding the LLM in this deterministic evidence (rather than letting it guess)
    is the core safety idea, carried over from DriftMind.
    """

    alert: Alert
    metrics: list[MetricSample] = field(default_factory=list)
    recent_deploys: list[str] = field(default_factory=list)
    log_excerpts: list[str] = field(default_factory=list)
    slo: dict[str, Any] = field(default_factory=dict)

    def breached_metrics(self) -> list[MetricSample]:
        return [m for m in self.metrics if m.breached]

    def to_prompt_payload(self) -> dict[str, Any]:
        """The exact, minimal structure handed to a provider. No free-form text."""
        return {
            "alert": {
                "name": self.alert.name,
                "severity": self.alert.severity.value,
                "summary": self.alert.summary,
                "service": self.alert.service,
                "labels": self.alert.labels,
            },
            "metrics": [
                {"name": m.name, "value": m.value, "threshold": m.threshold,
                 "unit": m.unit, "breached": m.breached}
                for m in self.metrics
            ],
            "recent_deploys": list(self.recent_deploys),
            "log_excerpts": list(self.log_excerpts),
            "slo": dict(self.slo),
        }


@dataclass
class Remediation:
    """A proposed action. Never executed automatically unless explicitly allowed."""

    action: str            # stable identifier, e.g. "rollback_deployment"
    target: str            # e.g. "deploy/payments" in namespace "apps"
    rationale: str
    risk: Severity = Severity.WARNING
    reversible: bool = True


@dataclass
class Diagnosis:
    """The validated result of a diagnosis pass."""

    summary: str
    probable_cause: str
    confidence: float          # 0..1
    contributing_signals: list[str] = field(default_factory=list)
    remediations: list[Remediation] = field(default_factory=list)
    source: str = "unknown"    # which provider produced it

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["remediations"] = [
            {**asdict(r), "risk": r.risk.value} for r in self.remediations
        ]
        return d
