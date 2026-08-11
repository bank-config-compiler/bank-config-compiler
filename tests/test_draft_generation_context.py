from __future__ import annotations

import json
from pathlib import Path

from bank_config_compiler.draft_generation import (
    DraftGenerationContext,
    DraftProviderResult,
    ProviderCallMetadata,
    generate_docir_draft,
    publish_generated_draft,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CapturingProvider:
    name = "capturing-test"

    def __init__(self, artifact_content: str) -> None:
        self.artifact_content = artifact_content
        self.contexts: list[DraftGenerationContext] = []

    def generate(self, request, context: DraftGenerationContext) -> DraftProviderResult:
        self.contexts.append(context)
        return DraftProviderResult(
            response_text=json.dumps(
                {
                    "contractVersion": "draft-provider-response/v1",
                    "artifactKind": request.artifact_kind,
                    "artifactContent": self.artifact_content,
                    "reviewNotes": "Review generated content.",
                }
            ),
            metadata=ProviderCallMetadata(
                provider_name=self.name,
                attempt_id="docir-001",
                requested_model="qwen-test-snapshot",
                response_model="qwen-test-snapshot",
                response_id="chatcmpl-test",
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                started_at="2026-08-10T10:00:00+08:00",
                completed_at="2026-08-10T10:00:05+08:00",
                endpoint_fingerprint="sha256:" + "1" * 64,
                prompt_contract_version="draft-prompt/v1",
            ),
        )


def test_docir_generator_passes_source_content_in_explicit_context() -> None:
    raw_doc = "# Raw bank document\n"
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )
    provider = CapturingProvider(docir)

    generated = generate_docir_draft(raw_doc=raw_doc, provider=provider, task_id="phase0-test")

    assert provider.contexts == [
        DraftGenerationContext(
            source_content=raw_doc,
            source_content_type="text/markdown",
        )
    ]
    assert generated.provider_metadata.provider_name == "capturing-test"


def test_publish_real_provider_draft_writes_non_sensitive_call_result(tmp_path: Path) -> None:
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )
    generated = generate_docir_draft(
        raw_doc="# Raw bank document\n",
        provider=CapturingProvider(docir),
        task_id="phase0-test",
    )

    outputs = publish_generated_draft(tmp_path, generated)

    assert outputs["provider_call_result"] == tmp_path / "docir-provider-call-result.json"
    call_result = json.loads(outputs["provider_call_result"].read_text(encoding="utf-8"))
    assert call_result == {
        "contractVersion": "draft-provider-call-result/v1",
        "taskId": "phase0-test",
        "artifactKind": "docir",
        "sourceHash": generated.request.source_hash,
        "selectors": {},
        "provider": "capturing-test",
        "attemptId": "docir-001",
        "requestedModel": "qwen-test-snapshot",
        "responseModel": "qwen-test-snapshot",
        "responseId": "chatcmpl-test",
        "promptContractVersion": "draft-prompt/v1",
        "endpointFingerprint": "sha256:" + "1" * 64,
        "startedAt": "2026-08-10T10:00:00+08:00",
        "completedAt": "2026-08-10T10:00:05+08:00",
        "usage": {
            "promptTokens": 10,
            "completionTokens": 20,
            "totalTokens": 30,
        },
        "artifactContentHash": generated.content_hash,
    }
    serialized = outputs["provider_call_result"].read_text(encoding="utf-8")
    assert "test-key" not in serialized
    assert "https://" not in serialized
