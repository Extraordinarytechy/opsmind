import unittest

from opsmind.contract import ContractError, parse_diagnosis


VALID = {
    "summary": "Error rate rose after a deploy.",
    "probable_cause": "Bad release.",
    "confidence": 0.8,
    "contributing_signals": ["error_rate=5%"],
    "remediations": [
        {"action": "rollback_deployment", "target": "deploy/payments",
         "rationale": "correlates with rollout", "risk": "warning", "reversible": True}
    ],
}


class TestContract(unittest.TestCase):
    def test_valid_passes(self):
        d = parse_diagnosis(VALID, source="mock")
        self.assertEqual(d.source, "mock")
        self.assertEqual(len(d.remediations), 1)
        self.assertEqual(d.remediations[0].action, "rollback_deployment")

    def test_missing_field_rejected(self):
        bad = dict(VALID)
        del bad["confidence"]
        with self.assertRaises(ContractError):
            parse_diagnosis(bad, source="mock")

    def test_out_of_range_confidence_rejected(self):
        bad = dict(VALID, confidence=1.7)
        with self.assertRaises(ContractError):
            parse_diagnosis(bad, source="mock")

    def test_unknown_action_rejected(self):
        bad = dict(VALID, remediations=[{"action": "delete_cluster", "target": "x"}])
        with self.assertRaises(ContractError):
            parse_diagnosis(bad, source="mock")

    def test_bool_confidence_rejected(self):
        bad = dict(VALID, confidence=True)
        with self.assertRaises(ContractError):
            parse_diagnosis(bad, source="mock")


if __name__ == "__main__":
    unittest.main()
