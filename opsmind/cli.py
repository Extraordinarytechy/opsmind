"""OpsMind CLI: diagnose an incident from an alert+evidence JSON file.

Usage:
    python -m opsmind.cli examples/sample_alert.json
    python -m opsmind.cli examples/sample_alert.json --provider bedrock --execute

Dry-run by default. --execute only performs auto-allowed, in-risk actions and still
needs a real executor wired for a live cluster (none is used here).
"""

from __future__ import annotations

import argparse
import json
import sys

from .engine import DiagnosisEngine
from .models import Alert, Evidence, MetricSample
from .providers import get_provider
from .remediation import apply_remediations
from .report import render_incident_report


def _load_evidence(path: str) -> Evidence:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    alert = Alert.from_dict(d["alert"])
    metrics = [
        MetricSample(
            name=m["name"], value=float(m["value"]),
            threshold=(None if m.get("threshold") is None else float(m["threshold"])),
            unit=m.get("unit", ""),
        )
        for m in d.get("metrics", [])
    ]
    return Evidence(
        alert=alert,
        metrics=metrics,
        recent_deploys=d.get("recent_deploys", []),
        log_excerpts=d.get("log_excerpts", []),
        slo=d.get("slo", {}),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opsmind")
    parser.add_argument("evidence", help="path to an alert+evidence JSON file")
    parser.add_argument("--provider", default="mock", help="mock (default) or bedrock")
    parser.add_argument("--execute", action="store_true",
                        help="perform auto-allowed remediations (default: dry-run)")
    args = parser.parse_args(argv)

    evidence = _load_evidence(args.evidence)
    engine = DiagnosisEngine(get_provider(args.provider))
    diagnosis = engine.diagnose(evidence)
    results = apply_remediations(diagnosis, allow_execute=args.execute,
                                 executor=lambda r: None)
    executed = [r.action for r in results if r.executed]
    print(render_incident_report(evidence, diagnosis, executed=executed, simulated=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
