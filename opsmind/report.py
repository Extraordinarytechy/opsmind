"""Render a human-readable incident report from a Diagnosis.

The report is what gets committed/attached after an incident, and it is deliberately
explicit about what was automated versus what needs a human.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import Diagnosis, Evidence


def render_incident_report(evidence: Evidence, diagnosis: Diagnosis,
                           executed: list[str] | None = None,
                           simulated: bool = True) -> str:
    executed = executed or []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    a = evidence.alert

    lines: list[str] = []
    lines.append(f"# Incident Report: {a.name}")
    if simulated:
        lines.append("")
        lines.append("> NOTE: generated from a simulated (lab) incident, not production traffic.")
    lines.append("")
    lines.append(f"- Time: {ts}")
    lines.append(f"- Service: {a.service}")
    lines.append(f"- Severity: {a.severity.value}")
    lines.append(f"- Diagnosis source: {diagnosis.source}")
    lines.append(f"- Confidence: {diagnosis.confidence:.2f}")
    lines.append("")
    lines.append("## Summary")
    lines.append(diagnosis.summary)
    lines.append("")
    lines.append("## Probable cause")
    lines.append(diagnosis.probable_cause)
    lines.append("")
    lines.append("## Evidence")
    for m in evidence.metrics:
        flag = " (breached)" if m.breached else ""
        thr = "" if m.threshold is None else f" / threshold {m.threshold}{m.unit}"
        lines.append(f"- {m.name}: {m.value}{m.unit}{thr}{flag}")
    if evidence.recent_deploys:
        lines.append(f"- recent deploys: {', '.join(evidence.recent_deploys)}")
    lines.append("")
    lines.append("## Proposed remediations")
    if not diagnosis.remediations:
        lines.append("- none")
    for r in diagnosis.remediations:
        state = "EXECUTED" if r.action in executed else "PROPOSED (dry-run)"
        lines.append(f"- [{state}] {r.action} -> {r.target} "
                     f"(risk: {r.risk.value}, reversible: {r.reversible})")
        if r.rationale:
            lines.append(f"    rationale: {r.rationale}")
    lines.append("")
    return "\n".join(lines)
