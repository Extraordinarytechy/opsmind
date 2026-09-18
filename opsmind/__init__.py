"""OpsMind: an AI-assisted incident response and gated self-healing agent for Kubernetes.

The package is provider-agnostic: the diagnosis engine consumes structured incident
evidence and returns a validated, machine-checkable diagnosis. An LLM is only ever
given the pre-computed evidence, and its response must satisfy a strict contract
before it is used. Remediations are dry-run by default and never execute without an
explicit, scoped opt-in.
"""

__version__ = "0.1.0"
