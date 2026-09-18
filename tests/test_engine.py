import unittest

from opsmind.engine import DiagnosisEngine
from opsmind.models import Alert, Evidence, MetricSample, Severity
from opsmind.providers import MockProvider


def make_evidence(**kw) -> Evidence:
    alert = Alert(name=kw.get("alert", "HighErrorRate"),
                  severity=Severity.CRITICAL,
                  summary="test",
                  service=kw.get("service", "payments"))
    return Evidence(
        alert=alert,
        metrics=kw.get("metrics", []),
        recent_deploys=kw.get("recent_deploys", []),
        slo=kw.get("slo", {}),
    )


class TestEngineRules(unittest.TestCase):
    def setUp(self):
        self.engine = DiagnosisEngine(MockProvider())

    def test_deploy_plus_error_rate_suggests_rollback(self):
        ev = make_evidence(
            metrics=[MetricSample("error_rate", 5.0, 1.0, "%")],
            recent_deploys=["deploy/payments@v2.1.0"],
        )
        d = self.engine.diagnose(ev)
        self.assertEqual(d.remediations[0].action, "rollback_deployment")
        self.assertGreater(d.confidence, 0.7)

    def test_memory_saturation_suggests_restart(self):
        ev = make_evidence(metrics=[MetricSample("memory_usage_pct", 96.0, 90.0, "%")])
        d = self.engine.diagnose(ev)
        actions = {r.action for r in d.remediations}
        self.assertIn("restart_pods", actions)

    def test_latency_breach_suggests_scale_up(self):
        ev = make_evidence(metrics=[MetricSample("p99_latency_ms", 900.0, 500.0, "ms")])
        d = self.engine.diagnose(ev)
        self.assertEqual(d.remediations[0].action, "scale_up")

    def test_weak_signal_falls_back_to_no_action(self):
        ev = make_evidence(metrics=[MetricSample("cpu_pct", 20.0, 90.0, "%")])
        d = self.engine.diagnose(ev)
        self.assertEqual(d.remediations[0].action, "no_action")
        self.assertLess(d.confidence, 0.5)


if __name__ == "__main__":
    unittest.main()
