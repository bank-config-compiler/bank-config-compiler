from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bank_config_compiler.draft_generation import (
    DraftGenerationContext,
    DraftGenerationError,
    DraftProviderResult,
    ProviderCallMetadata,
    ProviderSubcallMetadata,
    generate_docir_draft,
    generate_schemair_draft,
    load_schemair_resume_evidence,
    publish_generated_draft,
)
from bank_config_compiler.workspace import ingest_raw_doc


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_resume_summary(
    workspace: Path,
    *,
    attempt_id: str,
    contract_version: str,
    extra: dict[str, object],
) -> None:
    root = workspace / "provider-attempts" / "schemair" / attempt_id
    root.mkdir(parents=True)
    filename = (
        "provider-call-result.json"
        if "call-result" in contract_version
        else "provider-failure-result.json"
    )
    summary = {
        "contractVersion": contract_version,
        "taskId": "phase0-test",
        "artifactKind": "schemair",
        "sourceHash": "sha256:" + "1" * 64,
        "provider": "openai-chat",
        "attemptId": attempt_id,
        "requestedModel": "qwen-test-snapshot",
        "endpointFingerprint": "sha256:" + "2" * 64,
        "promptContractVersion": "draft-prompt/v11",
        "schemairFieldBatchSize": 8,
        **extra,
    }
    (root / filename).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )


@pytest.mark.parametrize(
    ("attempt_id", "contract_version", "extra"),
    (
        (
            "schemair-007",
            "draft-provider-failure-result/v2",
            {
                "calls": [
                    {
                        "sequence": 1,
                        "segment": "../outside",
                        "responseComplete": True,
                        "finishReason": "stop",
                        "responseContentHash": "sha256:" + "3" * 64,
                        "segmentContractVersion": "schemair-field-semantics-segment/v1",
                        "usage": {
                            "promptTokens": 1,
                            "completionTokens": 1,
                            "totalTokens": 2,
                        },
                    }
                ]
            },
        ),
        (
            "schemair-v3",
            "draft-provider-call-result/v3",
            {
                "selectors": {
                    "schemaId": "b2eboc-b2e0061-schema",
                    "schemaVersion": "v1",
                },
                "calls": [],
                "segments": [
                    {
                        "segment": "../outside",
                        "source": "REUSED",
                        "originAttemptId": "schemair-007",
                        "originCallSequence": 1,
                        "originResponseContentHash": "sha256:" + "3" * 64,
                        "fingerprint": {},
                        "usage": {
                            "promptTokens": 1,
                            "completionTokens": 1,
                            "totalTokens": 2,
                        },
                    }
                ],
            },
        ),
        (
            "schemair-v3-self",
            "draft-provider-call-result/v3",
            {
                "selectors": {
                    "schemaId": "b2eboc-b2e0061-schema",
                    "schemaVersion": "v1",
                },
                "calls": [],
                "segments": [
                    {
                        "segment": "schemair-metadata",
                        "source": "REUSED",
                        "originAttemptId": "schemair-v3-self",
                        "originCallSequence": 1,
                        "originResponseContentHash": "sha256:" + "3" * 64,
                        "fingerprint": {},
                        "usage": {
                            "promptTokens": 1,
                            "completionTokens": 1,
                            "totalTokens": 2,
                        },
                    }
                ],
            },
        ),
    ),
)
def test_resume_loader_rejects_unsafe_segment_before_response_io(
    tmp_path: Path,
    attempt_id: str,
    contract_version: str,
    extra: dict[str, object],
) -> None:
    workspace = tmp_path / "workspace"
    _write_resume_summary(
        workspace,
        attempt_id=attempt_id,
        contract_version=contract_version,
        extra=extra,
    )

    with pytest.raises(DraftGenerationError, match="segment"):
        load_schemair_resume_evidence(workspace, attempt_id)


def prepare_workspace(tmp_path: Path, *, task_id: str = "phase0-test") -> Path:
    source = tmp_path / f"{task_id}.md"
    source.write_text("# Raw bank document\n", encoding="utf-8", newline="")
    workspace = tmp_path / "workspace"
    ingest_raw_doc(source, workspace, task_id=task_id, interface_code="b2e0061")
    return workspace


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

    workspace = prepare_workspace(tmp_path)
    publish_generated_draft(workspace, generated)

    call_result_path = (
        workspace / "provider-attempts" / "docir" / "docir-001" / "provider-call-result.json"
    )
    call_result = json.loads(call_result_path.read_text(encoding="utf-8"))
    assert call_result == {
        "contractVersion": "draft-provider-call-result/v2",
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
        "docirFieldBatchSize": None,
        "schemairFieldBatchSize": None,
        "usage": {
            "promptTokens": 10,
            "completionTokens": 20,
            "totalTokens": 30,
        },
        "calls": [
            {
                "sequence": 1,
                "segment": "complete-artifact",
                "outcome": "succeeded",
                "requestedModel": "qwen-test-snapshot",
                "responseModel": "qwen-test-snapshot",
                "responseId": "chatcmpl-test",
                "promptContractVersion": "draft-prompt/v1",
                "segmentContractVersion": None,
                "startedAt": "2026-08-10T10:00:00+08:00",
                "completedAt": "2026-08-10T10:00:05+08:00",
                "finishReason": "stop",
                "responseComplete": True,
                "responseContentHash": None,
                "usage": {
                    "promptTokens": 10,
                    "completionTokens": 20,
                    "totalTokens": 30,
                },
            }
        ],
        "artifactContentHash": generated.content_hash,
    }
    serialized = call_result_path.read_text(encoding="utf-8")
    assert "test-key" not in serialized
    assert "https://" not in serialized


def test_publish_segmented_docir_records_ordered_subcalls(tmp_path: Path) -> None:
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )

    class SegmentedProvider(CapturingProvider):
        def generate(self, request, context: DraftGenerationContext) -> DraftProviderResult:
            result = super().generate(request, context)
            calls = tuple(
                ProviderSubcallMetadata(
                    segment=segment,
                    outcome="succeeded",
                    response_complete=True,
                    response_content_hash="sha256:" + digit * 64,
                    requested_model="qwen-test-snapshot",
                    response_model="qwen-test-snapshot",
                    response_id=f"chatcmpl-{sequence}",
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30,
                    started_at=f"2026-08-11T10:00:0{sequence}+08:00",
                    completed_at=f"2026-08-11T10:00:0{sequence + 1}+08:00",
                    finish_reason="stop",
                    prompt_contract_version="draft-prompt/v9",
                    segment_contract_version=contract,
                )
                for sequence, (segment, contract, digit) in enumerate(
                    (
                        (
                            "interface-envelope",
                            "docir-interface-envelope-segment/v2",
                            "1",
                        ),
                        (
                            "messages-outline",
                            "docir-messages-outline-segment/v1",
                            "2",
                        ),
                    ),
                    start=1,
                )
            )
            return DraftProviderResult(
                response_text=result.response_text,
                metadata=ProviderCallMetadata(
                    provider_name=self.name,
                    attempt_id="docir-012",
                    requested_model="qwen-test-snapshot",
                    response_model="qwen-test-snapshot",
                    prompt_tokens=20,
                    completion_tokens=40,
                    total_tokens=60,
                    started_at=calls[0].started_at,
                    completed_at=calls[-1].completed_at,
                    endpoint_fingerprint="sha256:" + "3" * 64,
                    prompt_contract_version="draft-prompt/v9",
                    calls=calls,
                    docir_field_batch_size=16,
                ),
            )

    generated = generate_docir_draft(
        raw_doc="# Raw bank document\n",
        provider=SegmentedProvider(docir),
        task_id="phase0-test",
    )

    workspace = prepare_workspace(tmp_path)
    publish_generated_draft(workspace, generated)
    call_result = json.loads(
        (
            workspace
            / "provider-attempts"
            / "docir"
            / "docir-012"
            / "provider-call-result.json"
        ).read_text(encoding="utf-8")
    )

    assert call_result["contractVersion"] == "draft-provider-call-result/v2"
    assert call_result["docirFieldBatchSize"] == 16
    assert [call["sequence"] for call in call_result["calls"]] == [1, 2]
    assert [call["segment"] for call in call_result["calls"]] == [
        "interface-envelope",
        "messages-outline",
    ]


def test_publish_segmented_schemair_records_batch_size_and_ordered_subcalls(
    tmp_path: Path,
) -> None:
    docir = (REPO_ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md").read_text(
        encoding="utf-8"
    )
    candidate_text = (
        REPO_ROOT / "samples/draft-generation/b2eboc-b2e0061/artifacts/schemair-draft.json"
    ).read_text(encoding="utf-8")
    responses = tuple(f'{{"segment":{sequence}}}' for sequence in range(1, 10))
    calls = tuple(
        ProviderSubcallMetadata(
            segment=segment,
            outcome="succeeded",
            response_complete=True,
            response_content_hash=(
                "sha256:" + hashlib.sha256(response.encode("utf-8")).hexdigest()
            ),
            requested_model="qwen-test-snapshot",
            response_model="qwen-test-snapshot",
            response_id=f"chatcmpl-{sequence}",
            started_at=f"2026-08-20T10:00:{sequence:02d}+08:00",
            completed_at=f"2026-08-20T10:00:{sequence + 1:02d}+08:00",
            finish_reason="stop",
            prompt_contract_version="draft-prompt/v11",
            segment_contract_version=(
                "schemair-metadata-segment/v1"
                if sequence == 1
                else "schemair-field-semantics-segment/v1"
            ),
        )
        for sequence, (segment, response) in enumerate(
            zip(
                (
                    "schemair-metadata",
                    "schemair-envelope-fields-001",
                    "schemair-envelope-fields-002",
                    "schemair-assembly-fields-001",
                    "schemair-assembly-fields-002",
                    "schemair-assembly-fields-003",
                    "schemair-assembly-fields-004",
                    "schemair-parse-fields-001",
                    "schemair-parse-fields-002",
                ),
                responses,
                strict=True,
            ),
            start=1,
        )
    )

    class SegmentedSchemaIRProvider:
        name = "openai-chat"

        def generate(self, request, context: DraftGenerationContext) -> DraftProviderResult:
            return DraftProviderResult(
                response_text=json.dumps(
                    {
                        "contractVersion": "draft-provider-response/v1",
                        "artifactKind": "schemair",
                        "artifactContent": candidate_text,
                        "reviewNotes": "Pending review.",
                    }
                ),
                metadata=ProviderCallMetadata(
                    provider_name=self.name,
                    attempt_id="schemair-004",
                    requested_model="qwen-test-snapshot",
                    response_model="qwen-test-snapshot",
                    started_at=calls[0].started_at,
                    completed_at=calls[-1].completed_at,
                    endpoint_fingerprint="sha256:" + "4" * 64,
                    prompt_contract_version="draft-prompt/v11",
                    calls=calls,
                    schemair_field_batch_size=8,
                ),
                candidate_content=candidate_text,
                subcall_response_texts=responses,
            )

    generated = generate_schemair_draft(
        docir_final=docir,
        provider=SegmentedSchemaIRProvider(),
        task_id="phase0-test",
        interface_code="b2e0061",
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
    )
    workspace = prepare_workspace(tmp_path)
    publish_generated_draft(workspace, generated)
    call_result = json.loads(
        (
            workspace
            / "provider-attempts/schemair/schemair-004/provider-call-result.json"
        ).read_text(encoding="utf-8")
    )

    assert call_result["docirFieldBatchSize"] is None
    assert call_result["schemairFieldBatchSize"] == 8
    assert len(call_result["calls"]) == 9
    assert call_result["calls"][-1]["segment"] == "schemair-parse-fields-002"
