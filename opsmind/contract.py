"""Strict, dependency-free validation of a provider's diagnosis output.

Any LLM response must satisfy this contract before OpsMind will use it. This is the
guardrail that keeps a probabilistic model from injecting unchecked actions into an
operations workflow. Validation is hand-rolled (no jsonschema dependency) so it runs
in any environment.
"""

from __future__ import annotations

from typing import Any

from .models import Diagnosis, Remediation, Severity

VALID_ACTIONS = {
    "rollback_deployment",
    "restart_pods",
    "scale_up",
    "scale_down",
    "cordon_node",
    "no_action",
}


class ContractError(ValueError):
    """Raised when a provider response violates the diagnosis contract."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ContractError(msg)


def parse_diagnosis(raw: dict[str, Any], source: str) -> Diagnosis:
    """Validate a raw provider dict and turn it into a typed Diagnosis.

    Rejects missing fields, wrong types, out-of-range confidence, and unknown
    remediation actions. Returning a Diagnosis means the response is safe to use.
    """
    _require(isinstance(raw, dict), "diagnosis must be an object")

    for key in ("summary", "probable_cause", "confidence"):
        _require(key in raw, f"missing required field: {key}")

    _require(isinstance(raw["summary"], str) and raw["summary"].strip(),
             "summary must be a non-empty string")
    _require(isinstance(raw["probable_cause"], str) and raw["probable_cause"].strip(),
             "probable_cause must be a non-empty string")

    conf = raw["confidence"]
    _require(isinstance(conf, (int, float)) and not isinstance(conf, bool),
             "confidence must be a number")
    conf = float(conf)
    _require(0.0 <= conf <= 1.0, "confidence must be between 0 and 1")

    signals = raw.get("contributing_signals", [])
    _require(isinstance(signals, list) and all(isinstance(s, str) for s in signals),
             "contributing_signals must be a list of strings")

    remediations_raw = raw.get("remediations", [])
    _require(isinstance(remediations_raw, list), "remediations must be a list")

    remediations: list[Remediation] = []
    for i, r in enumerate(remediations_raw):
        _require(isinstance(r, dict), f"remediation[{i}] must be an object")
        action = r.get("action")
        _require(action in VALID_ACTIONS,
                 f"remediation[{i}].action '{action}' is not an allowed action")
        _require(isinstance(r.get("target", ""), str),
                 f"remediation[{i}].target must be a string")
        risk_raw = str(r.get("risk", "warning"))
        try:
            risk = Severity(risk_raw)
        except ValueError as exc:
            raise ContractError(f"remediation[{i}].risk '{risk_raw}' is invalid") from exc
        remediations.append(
            Remediation(
                action=str(action),
                target=str(r.get("target", "")),
                rationale=str(r.get("rationale", "")),
                risk=risk,
                reversible=bool(r.get("reversible", True)),
            )
        )

    return Diagnosis(
        summary=raw["summary"].strip(),
        probable_cause=raw["probable_cause"].strip(),
        confidence=conf,
        contributing_signals=[s for s in signals],
        remediations=remediations,
        source=source,
    )
