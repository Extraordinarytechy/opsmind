import unittest

from opsmind.models import Diagnosis, Remediation, Severity
from opsmind.remediation import apply_remediations


def diag(*remediations) -> Diagnosis:
    return Diagnosis(summary="s", probable_cause="c", confidence=0.8,
                     remediations=list(remediations), source="mock")


class TestRemediationGating(unittest.TestCase):
    def test_dry_run_is_default(self):
        d = diag(Remediation("restart_pods", "deploy/x", "r", Severity.WARNING))
        results = apply_remediations(d)  # allow_execute defaults to False
        self.assertFalse(results[0].executed)
        self.assertIn("dry-run", results[0].reason)

    def test_execute_allowed_action(self):
        d = diag(Remediation("scale_up", "deploy/x", "r", Severity.INFO))
        ran = []
        results = apply_remediations(d, allow_execute=True, executor=lambda r: ran.append(r.action))
        self.assertTrue(results[0].executed)
        self.assertEqual(ran, ["scale_up"])

    def test_risk_cap_blocks_high_risk(self):
        d = diag(Remediation("rollback_deployment", "deploy/x", "r", Severity.CRITICAL))
        results = apply_remediations(d, allow_execute=True, max_risk=Severity.WARNING,
                                     executor=lambda r: None)
        self.assertFalse(results[0].executed)
        self.assertIn("exceeds max_risk", results[0].reason)

    def test_action_not_in_allowlist_blocked(self):
        d = diag(Remediation("cordon_node", "node/x", "r", Severity.INFO))
        results = apply_remediations(d, allow_execute=True, executor=lambda r: None)
        self.assertFalse(results[0].executed)
        self.assertIn("allow-list", results[0].reason)

    def test_no_action_is_noop(self):
        d = diag(Remediation("no_action", "svc", "escalate", Severity.INFO))
        results = apply_remediations(d, allow_execute=True, executor=lambda r: None)
        self.assertFalse(results[0].executed)


if __name__ == "__main__":
    unittest.main()
