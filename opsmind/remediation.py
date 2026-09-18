"""Gated remediation execution.

Safety model:
- Dry-run is the default. Nothing touches a cluster unless allow_execute=True.
- Only allow-listed actions can run, and only if their risk is within max_risk.
- Every decision is recorded, so the incident report shows exactly what happened.

The actual kubectl calls are intentionally stubbed behind an executor function so the
logic is unit-testable offline and a real executor can be injected for a live cluster.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .models import Diagnosis, Remediation, Severity

_RISK_ORDER = {Severity.INFO: 0, Severity.WARNING: 1, Severity.CRITICAL: 2}

# Actions OpsMind is ever willing to run automatically (when execution is enabled).
AUTO_ALLOWED = {"restart_pods", "scale_up", "rollback_deployment", "no_action"}


@dataclass
class RemediationResult:
    action: str
    target: str
    executed: bool
    reason: str


def _default_executor(remediation: Remediation) -> None:
    """Placeholder for a real kubectl/API call. Replaced in a live deployment."""
    raise NotImplementedError("inject a real executor to run against a cluster")


def apply_remediations(
    diagnosis: Diagnosis,
    allow_execute: bool = False,
    max_risk: Severity = Severity.WARNING,
    executor: Callable[[Remediation], None] | None = None,
) -> list[RemediationResult]:
    """Decide (and optionally perform) remediations. Returns a per-action record."""
    executor = executor or _default_executor
    results: list[RemediationResult] = []

    for r in diagnosis.remediations:
        if r.action == "no_action":
            results.append(RemediationResult(r.action, r.target, False, "no action proposed"))
            continue
        if not allow_execute:
            results.append(RemediationResult(r.action, r.target, False, "dry-run (execution disabled)"))
            continue
        if r.action not in AUTO_ALLOWED:
            results.append(RemediationResult(r.action, r.target, False,
                                             f"action '{r.action}' not in auto allow-list"))
            continue
        if _RISK_ORDER[r.risk] > _RISK_ORDER[max_risk]:
            results.append(RemediationResult(r.action, r.target, False,
                                             f"risk {r.risk.value} exceeds max_risk {max_risk.value}"))
            continue
        executor(r)
        results.append(RemediationResult(r.action, r.target, True, "executed"))

    return results
