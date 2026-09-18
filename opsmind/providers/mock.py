"""Deterministic, offline diagnosis provider.

This is not a toy: it encodes a small, transparent rule base that maps common
Kubernetes failure signatures to a probable cause and a safe proposed remediation.
It makes the whole system runnable and testable with zero external dependencies or
cost, and it is the reference behaviour the LLM provider is checked against.
"""

from __future__ import annotations

from typing import Any

from ..models import Evidence
from .base import DiagnosisProvider


class MockProvider(DiagnosisProvider):
    name = "mock"

    def diagnose(self, evidence: Evidence) -> dict[str, Any]:
        alert = evidence.alert
        breached = evidence.breached_metrics()
        breached_names = {m.name for m in breached}
        signals = [f"{m.name}={m.value}{m.unit} (>{m.threshold})" for m in breached]

        # Rule 1: a recent deploy plus an error-rate breach -> likely bad release.
        if evidence.recent_deploys and "error_rate" in breached_names:
            target = evidence.recent_deploys[0]
            return {
                "summary": f"Error rate rose on {alert.service} shortly after a deploy.",
                "probable_cause": f"A recent deployment ({target}) likely introduced a regression.",
                "confidence": 0.82,
                "contributing_signals": signals + [f"recent_deploy={target}"],
                "remediations": [
                    {
                        "action": "rollback_deployment",
                        "target": target,
                        "rationale": "Error rate breach correlates with the latest rollout.",
                        "risk": "warning",
                        "reversible": True,
                    }
                ],
            }

        # Rule 2: memory saturation -> restart / scale.
        if "memory_usage_pct" in breached_names:
            return {
                "summary": f"Memory saturation on {alert.service}.",
                "probable_cause": "Pods are near their memory limit, risking OOMKills.",
                "confidence": 0.6,
                "contributing_signals": signals,
                "remediations": [
                    {
                        "action": "restart_pods",
                        "target": f"deploy/{alert.service}",
                        "rationale": "Reclaim leaked memory while a fix is investigated.",
                        "risk": "warning",
                        "reversible": True,
                    },
                    {
                        "action": "scale_up",
                        "target": f"deploy/{alert.service}",
                        "rationale": "Spread load to reduce per-pod memory pressure.",
                        "risk": "info",
                        "reversible": True,
                    },
                ],
            }

        # Rule 3: latency breach without a deploy -> scale up.
        if "p99_latency_ms" in breached_names:
            return {
                "summary": f"Latency SLO at risk on {alert.service}.",
                "probable_cause": "Insufficient capacity for current load.",
                "confidence": 0.55,
                "contributing_signals": signals,
                "remediations": [
                    {
                        "action": "scale_up",
                        "target": f"deploy/{alert.service}",
                        "rationale": "Add replicas to bring P99 back under the SLO.",
                        "risk": "info",
                        "reversible": True,
                    }
                ],
            }

        # Fallback: not enough signal to act.
        return {
            "summary": f"Alert on {alert.service} with insufficient corroborating signal.",
            "probable_cause": "Evidence does not clearly indicate a single cause.",
            "confidence": 0.25,
            "contributing_signals": signals,
            "remediations": [
                {
                    "action": "no_action",
                    "target": alert.service,
                    "rationale": "Escalate to a human; automated action is not justified.",
                    "risk": "info",
                    "reversible": True,
                }
            ],
        }
