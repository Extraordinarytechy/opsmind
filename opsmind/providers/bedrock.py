"""Optional Amazon Bedrock provider.

Only imported when explicitly selected (see providers.get_provider), so boto3 is not a
hard dependency and the rest of OpsMind runs offline. The LLM is given ONLY the
structured evidence and is instructed to return JSON matching the diagnosis contract;
the engine still validates that JSON before it is trusted.
"""

from __future__ import annotations

import json
import os
from typing import Any

from ..models import Evidence
from .base import DiagnosisProvider

_SYSTEM_INSTRUCTIONS = (
    "You are an SRE assistant. You are given structured incident evidence as JSON. "
    "Return ONLY a JSON object with keys: summary (string), probable_cause (string), "
    "confidence (number 0..1), contributing_signals (array of strings), and "
    "remediations (array of objects with action, target, rationale, risk, reversible). "
    "The action MUST be one of: rollback_deployment, restart_pods, scale_up, "
    "scale_down, cordon_node, no_action. Base every statement only on the provided "
    "evidence. Do not invent metrics or events. If evidence is weak, propose no_action."
)


class BedrockProvider(DiagnosisProvider):
    name = "bedrock"

    def __init__(self, model_id: str | None = None, region: str | None = None) -> None:
        import boto3  # lazy: only needed if this provider is used

        self.model_id = model_id or os.getenv(
            "OPSMIND_BEDROCK_MODEL", "anthropic.claude-3-5-sonnet-20240620-v1:0"
        )
        self.client = boto3.client(
            "bedrock-runtime", region_name=region or os.getenv("AWS_REGION", "us-east-1")
        )

    def diagnose(self, evidence: Evidence) -> dict[str, Any]:
        payload = evidence.to_prompt_payload()
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "system": _SYSTEM_INSTRUCTIONS,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text",
                         "text": "Incident evidence:\n" + json.dumps(payload, indent=2)}
                    ],
                }
            ],
        }
        resp = self.client.invoke_model(
            modelId=self.model_id, body=json.dumps(body)
        )
        data = json.loads(resp["body"].read())
        text = data["content"][0]["text"]
        # The model must return JSON; extract the object defensively.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Bedrock response did not contain a JSON object")
        return json.loads(text[start : end + 1])
