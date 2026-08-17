from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from bank_config_compiler.draft_generation import (
    DraftGenerationContext,
    DraftGenerationError,
    DraftGenerationRequest,
    DraftProviderResult,
    ProviderCallMetadata,
    generate_docir_draft,
    generate_schemair_draft,
    publish_generated_draft,
)
from bank_config_compiler.workspace import ingest_raw_doc


REPO_ROOT = Path(__file__).resolve().parents[1]


class AuditableProvider:
    name = "openai-chat"

    def __init__(self, artifact_content: str) -> None:
        self.artifact_content = artifact_content

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        return DraftProviderResult(
            response_text=json.dumps(
                {
                    "contractVersion": "draft-provider-response/v1",
                    "artifactKind": request.artifact_kind,
                    "artifactContent": self.artifact_content,
                    "reviewNotes": "# Review\n\nPending.\n",
                },
                ensure_ascii=False,
            ),
            metadata=ProviderCallMetadata(
                provider_name=self.name,
                attempt_id="docir-020",
                requested_model="approved-model",
                started_at="2026-08-12T10:00:00+08:00",
                completed_at="2026-08-12T10:01:00+08:00",
                endpoint_fingerprint="sha256:" + "1" * 64,
                prompt_contract_version="draft-prompt/v12",
            ),
        )


class StaticProvider:
    name = "static-test"

    def __init__(self, artifact_content: str) -> None:
        self.artifact_content = artifact_content

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        return DraftProviderResult(
            response_text=json.dumps(
                {
                    "contractVersion": "draft-provider-response/v1",
                    "artifactKind": request.artifact_kind,
                    "artifactContent": self.artifact_content,
                    "reviewNotes": "# Review\n\nPending.\n",
                },
                ensure_ascii=False,
            ),
            metadata=ProviderCallMetadata(provider_name=self.name),
        )


def schema_candidate(final_artifact: dict) -> dict:
    field_names = (
        "fieldName",
        "displayName",
        "format",
        "length",
        "description",
        "conditionText",
        "sourceText",
        "evidence",
        "confidence",
        "uncertain",
        "uncertainReason",
        "reviewNote",
    )

    def semantic_field(field: dict) -> dict:
        result = {name: deepcopy(field[name]) for name in field_names}
        if field["dataType"] == "object":
            result["required"] = field["required"]
        return result

    def semantic_message(message: dict) -> dict:
        return {
            "functionType": message["functionType"],
            "xmlEncoding": message["xmlEncoding"],
            "xmlEncodingEvidence": deepcopy(message["xmlEncodingEvidence"]),
            "description": message["description"],
            "fields": [semantic_field(field) for field in message["fields"]],
            "conditionalConstraints": [
                {key: deepcopy(value) for key, value in condition.items() if key != "review"}
                for condition in message["conditionalConstraints"]
            ],
        }

    return {
        "envelope": {
            "description": final_artifact["envelope"]["description"],
            "fields": [
                semantic_field(field) for field in final_artifact["envelope"]["fields"]
            ],
        },
        "messages": [semantic_message(message) for message in final_artifact["messages"]],
    }


def test_ingest_creates_task_manifest_bound_to_raw_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# 银行接口\n", encoding="utf-8", newline="")
    workspace = tmp_path / "workspace"

    ingest_raw_doc(
        source,
        workspace,
        task_id="phase0-docir-020",
        interface_code="b2e0061",
    )

    manifest = json.loads((workspace / "task.json").read_text(encoding="utf-8"))
    assert manifest == {
        "contractVersion": "phase0-task/v1",
        "taskId": "phase0-docir-020",
        "interfaceCode": "b2e0061",
        "messageFormat": "XML",
        "sourceDocument": "raw-doc.md",
        "sourceHash": "sha256:" + hashlib.sha256("# 银行接口\n".encode()).hexdigest(),
    }


def test_publish_writes_generation_lineage_and_never_reuses_attempt(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Raw\n", encoding="utf-8", newline="")
    workspace = tmp_path / "workspace"
    ingest_raw_doc(source, workspace, task_id="phase0-docir-020", interface_code="b2e0061")
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )
    generated = generate_docir_draft(
        raw_doc="# Raw\n",
        provider=AuditableProvider(docir),
        task_id="phase0-docir-020",
    )

    outputs = publish_generated_draft(workspace, generated)

    generation = json.loads(outputs["generation_result"].read_text(encoding="utf-8"))
    assert generation["contractVersion"] == "draft-generation-result/v1"
    assert generation["taskId"] == "phase0-docir-020"
    assert generation["interfaceCode"] == "b2e0061"
    assert generation["attemptId"] == "docir-020"
    assert generation["candidateHash"].startswith("sha256:")
    assert generation["initialDraftHash"] == generated.content_hash
    assert generation["initialValidation"]["state"] == "reviewable"
    attempt = workspace / "provider-attempts" / "docir" / "docir-020"
    assert (attempt / "provider-call-result.json").is_file()
    assert (attempt / "provider-response.json").is_file()
    assert (attempt / "generated-draft.md").read_text(encoding="utf-8") == docir

    with pytest.raises(DraftGenerationError, match="attempt ID.*already exists"):
        publish_generated_draft(workspace, generated, overwrite=True)


def test_schemair_generation_keeps_materializable_validator_errors() -> None:
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )
    final = json.loads(
        (REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061/schemair-final.json").read_text(
            encoding="utf-8"
        )
    )
    invalid = schema_candidate(final)
    locale = deepcopy(invalid["envelope"]["fields"][3])
    locale.update(
        fieldName="@lang",
        displayName="历史语言属性",
        confidence=2,
    )
    invalid["envelope"]["fields"].insert(4, locale)

    generated = generate_schemair_draft(
        docir_final=docir,
        provider=StaticProvider(json.dumps(invalid, ensure_ascii=False)),
        task_id="invalid-schemair",
        interface_code="b2e0061",
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
    )

    assert generated.validation_result is not None
    assert generated.validation_result["summary"]["errorCount"] > 0
    assert generated.publication_state == "invalid"
