from __future__ import annotations

import hashlib
import json
import logging
from copy import deepcopy
from pathlib import Path

import pytest

import bank_config_compiler.draft_generation as draft_generation
from bank_config_compiler.configuration_rules import load_rule_package
from bank_config_compiler.draft_generation import (
    DraftGenerationContext,
    DraftGenerationError,
    DraftGenerationRequest,
    DraftProviderResult,
    FixtureDraftProvider,
    ProviderCallMetadata,
    generate_docir_draft,
    generate_interface_standard_draft,
    generate_interface_template_draft,
    generate_schemair_draft,
    publish_generated_draft,
)
from bank_config_compiler.workspace import ingest_raw_doc


REPO_ROOT = Path(__file__).resolve().parents[1]


class StaticProvider:
    name = "static-test"

    def __init__(self, *, artifact_content: str, review_notes: str) -> None:
        self.artifact_content = artifact_content
        self.review_notes = review_notes
        self.requests: list[DraftGenerationRequest] = []

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        self.requests.append(request)
        return DraftProviderResult(
            response_text=json.dumps(
                {
                    "contractVersion": "draft-provider-response/v1",
                    "artifactKind": request.artifact_kind,
                    "artifactContent": self.artifact_content,
                    "reviewNotes": self.review_notes,
                },
                ensure_ascii=False,
            ),
            metadata=ProviderCallMetadata(provider_name=self.name),
        )


class RawProvider:
    name = "raw-test"

    def __init__(self, response: str) -> None:
        self.response = response

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        return DraftProviderResult(
            response_text=self.response,
            metadata=ProviderCallMetadata(provider_name=self.name),
        )


class FailingProvider:
    name = "failing-test"

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        raise RuntimeError("SECRET-BANK-PAYLOAD")


class DraftErrorProvider:
    name = "draft-error-test"

    def generate(
        self,
        request: DraftGenerationRequest,
        context: DraftGenerationContext,
    ) -> DraftProviderResult:
        raise DraftGenerationError("SECRET-BANK-PAYLOAD")


def load_json(relative_path: str) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def pending_draft(final_artifact: dict) -> dict:
    draft = deepcopy(final_artifact)
    draft["status"] = "DRAFT"
    draft["review"] = {
        "status": "PENDING",
        "reviewer": None,
        "reviewedAt": None,
        "note": None,
    }
    return draft


def schema_candidate(final_artifact: dict) -> dict:
    candidate = pending_draft(final_artifact)
    locale = deepcopy(candidate["envelope"]["fields"][3])
    locale.update(
        path="Root.bocb2e.@lang",
        fieldName="@lang",
        displayName="历史语言属性",
        description="历史报文示例中的语言属性。",
    )
    candidate["envelope"]["fields"].insert(4, locale)
    return candidate


def test_docir_generator_uses_provider_contract_and_binds_review_notes() -> None:
    raw_doc = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/raw-doc.md").read_text(encoding="utf-8")
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(encoding="utf-8")
    notes = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/review-notes.expected.md").read_text(
        encoding="utf-8"
    )
    provider = StaticProvider(artifact_content=docir, review_notes=notes)

    generated = generate_docir_draft(raw_doc=raw_doc, provider=provider, task_id="phase0-test")

    assert generated.request.artifact_kind == "docir"
    assert generated.artifact == docir
    assert generated.validation_result is not None
    assert generated.validation_result["status"] == "passed"
    assert generated.content_hash.startswith("sha256:")
    assert f"Artifact content hash: `{generated.content_hash}`" in generated.review_notes
    assert "## 显式 Review 证据" in generated.review_notes
    assert notes.strip() not in generated.review_notes
    assert provider.requests == [generated.request]


def test_schemair_generator_validates_pending_draft_and_rejects_final_output() -> None:
    docir_final = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )
    schemair_final = load_json("samples/trusted-chain/b2eboc-b2e0061/schemair-final.json")
    provider = StaticProvider(
        artifact_content=json.dumps(schema_candidate(schemair_final), ensure_ascii=False),
        review_notes="# SchemaIR Review\n\nPending Human Review.\n",
    )

    generated = generate_schemair_draft(
        docir_final=docir_final,
        provider=provider,
        task_id="phase0-test",
        interface_code="b2e0061",
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
    )

    assert generated.validation_result is not None
    assert generated.validation_result["summary"]["errorCount"] == 0
    assert generated.validation_result["finalEligible"] is False

    assert generated.artifact["status"] == "DRAFT"
    assert generated.artifact["review"]["status"] == "PENDING"


def test_standard_and_template_generators_require_exact_final_dependencies() -> None:
    schemair_final = load_json("samples/trusted-chain/b2eboc-b2e0061/schemair-final.json")
    standard_final = load_json(
        "samples/trusted-chain/b2eboc-b2e0061/standards/assembly/v1/standard-final.json"
    )
    template_final = load_json(
        "samples/trusted-chain/b2eboc-b2e0061/templates/assembly/v1/template-final.json"
    )
    standard_rules = load_rule_package(REPO_ROOT / "configuration-rules/v1")
    template_rules = load_rule_package(REPO_ROOT / "configuration-rules/v2")

    standard = generate_interface_standard_draft(
        schemair_final=schemair_final,
        rule_package=standard_rules,
        direction="ASSEMBLY",
        standard_id="b2e0061-assembly-standard",
        standard_version="v1",
        provider=StaticProvider(
            artifact_content=json.dumps(pending_draft(standard_final), ensure_ascii=False),
            review_notes="# Standard Review\n",
        ),
        task_id="phase0-test",
    )
    assert standard.validation_result is not None
    assert standard.validation_result["summary"]["errorCount"] == 0
    assert standard.validation_result["finalEligible"] is False

    template = generate_interface_template_draft(
        standard_final=standard_final,
        rule_package=template_rules,
        direction="ASSEMBLY",
        standard_version="v1",
        template_id="b2e0061-assembly-common",
        template_version="v1",
        provider=StaticProvider(
            artifact_content=json.dumps(pending_draft(template_final), ensure_ascii=False),
            review_notes="# Template Review\n",
        ),
        task_id="phase0-test",
    )
    assert template.validation_result is not None
    assert template.validation_result["summary"]["errorCount"] == 0
    assert template.validation_result["finalEligible"] is False

    with pytest.raises(DraftGenerationError, match="reviewed Final SchemaIR"):
        generate_interface_standard_draft(
            schemair_final=pending_draft(schemair_final),
            rule_package=standard_rules,
            direction="ASSEMBLY",
            standard_id="b2e0061-assembly-standard",
            standard_version="v1",
            provider=StaticProvider(
                artifact_content=json.dumps(pending_draft(standard_final), ensure_ascii=False),
                review_notes="# Standard Review\n",
            ),
            task_id="phase0-test",
        )


@pytest.mark.parametrize(
    ("direction", "standard_version", "message"),
    [
        ("PARSE", "v1", "coverage"),
    ],
)
def test_standard_generator_rejects_provider_output_for_different_request_selector(
    direction: str,
    standard_version: str,
    message: str,
) -> None:
    schemair_final = load_json("samples/trusted-chain/b2eboc-b2e0061/schemair-final.json")
    standard_final = load_json(
        "samples/trusted-chain/b2eboc-b2e0061/standards/assembly/v1/standard-final.json"
    )

    with pytest.raises(DraftGenerationError, match=message):
        generate_interface_standard_draft(
            schemair_final=schemair_final,
            rule_package=load_rule_package(REPO_ROOT / "configuration-rules/v1"),
            direction=direction,
            standard_id="b2e0061-assembly-standard",
            standard_version=standard_version,
            provider=StaticProvider(
                artifact_content=json.dumps(pending_draft(standard_final), ensure_ascii=False),
                review_notes="# Standard Review\n",
            ),
            task_id="selector-mismatch",
        )


def test_standard_generator_uses_locked_identity_instead_of_model_identity() -> None:
    schemair_final = load_json("samples/trusted-chain/b2eboc-b2e0061/schemair-final.json")
    standard_final = load_json(
        "samples/trusted-chain/b2eboc-b2e0061/standards/assembly/v1/standard-final.json"
    )
    candidate = pending_draft(standard_final)
    candidate.update(standardId="model-id", standardVersion="v9")

    generated = generate_interface_standard_draft(
        schemair_final=schemair_final,
        rule_package=load_rule_package(REPO_ROOT / "configuration-rules/v1"),
        direction="ASSEMBLY",
        standard_id="b2e0061-assembly-standard",
        standard_version="v2",
        provider=StaticProvider(
            artifact_content=json.dumps(candidate, ensure_ascii=False),
            review_notes="# Standard Review\n",
        ),
        task_id="locked-identity",
    )

    assert generated.artifact["standardId"] == "b2e0061-assembly-standard"
    assert generated.artifact["standardVersion"] == "v2"


def test_template_generator_uses_locked_identity_instead_of_model_identity() -> None:
    standard_final = load_json(
        "samples/trusted-chain/b2eboc-b2e0061/standards/assembly/v1/standard-final.json"
    )
    template_final = load_json(
        "samples/trusted-chain/b2eboc-b2e0061/templates/assembly/v1/template-final.json"
    )

    candidate = pending_draft(template_final)
    candidate.update(templateId="model-id", templateVersion="v9")
    generated = generate_interface_template_draft(
        standard_final=standard_final,
        rule_package=load_rule_package(REPO_ROOT / "configuration-rules/v2"),
        direction="ASSEMBLY",
        standard_version="v1",
        template_id="b2e0061-assembly-common",
        template_version="v2",
        provider=StaticProvider(
            artifact_content=json.dumps(candidate, ensure_ascii=False),
            review_notes="# Template Review\n",
        ),
        task_id="locked-identity",
    )
    assert generated.artifact["templateId"] == "b2e0061-assembly-common"
    assert generated.artifact["templateVersion"] == "v2"


def test_fixture_provider_requires_exact_request_fingerprint(tmp_path: Path) -> None:
    artifact = tmp_path / "docir.md"
    notes = tmp_path / "notes.md"
    artifact.write_text("# Interface\n", encoding="utf-8", newline="")
    notes.write_text("# Review\n", encoding="utf-8", newline="")
    request = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="docir",
        source_hash="sha256:" + "1" * 64,
    )
    (tmp_path / "draft-stub-case.json").write_text(
        json.dumps(
            {
                "contractVersion": "draft-stub-case/v1",
                "caseId": "exact-case",
                "responses": [
                    {
                        "request": request.case_fingerprint(),
                        "artifactFile": "docir.md",
                        "reviewNotesFile": "notes.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    provider = FixtureDraftProvider(tmp_path)
    context = DraftGenerationContext(
        source_content="# Raw bank document\n",
        source_content_type="text/markdown",
    )

    response = provider.generate(request, context)
    assert json.loads(response.response_text)["artifactContent"] == "# Interface\n"

    mismatch = DraftGenerationRequest(
        task_id="phase0-test",
        artifact_kind="docir",
        source_hash="sha256:" + "2" * 64,
    )
    with pytest.raises(DraftGenerationError, match="no exact response"):
        provider.generate(mismatch, context)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (
            '{"contractVersion":"draft-provider-response/v1","artifactKind":"docir",'
            '"artifactContent":"# Interface","reviewNotes":"review","extra":true}',
            "unknown properties",
        ),
        (
            '{"contractVersion":"draft-provider-response/v1","artifactKind":"docir",'
            '"artifactKind":"docir","artifactContent":"# Interface","reviewNotes":"review"}',
            "duplicate object property",
        ),
    ],
)
def test_provider_response_is_strict(response: str, message: str) -> None:
    with pytest.raises(DraftGenerationError, match=message):
        generate_docir_draft(
            raw_doc="raw",
            provider=RawProvider(response),
            task_id="strict-response",
        )


def test_provider_exception_does_not_log_or_return_sensitive_payload(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING), pytest.raises(DraftGenerationError) as caught:
        generate_docir_draft(
            raw_doc="raw",
            provider=FailingProvider(),
            task_id="safe-error",
        )

    assert "SECRET-BANK-PAYLOAD" not in str(caught.value)
    assert "SECRET-BANK-PAYLOAD" not in caplog.text
    assert "RuntimeError" in str(caught.value)


def test_provider_draft_error_does_not_log_or_return_sensitive_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING), pytest.raises(DraftGenerationError) as caught:
        generate_docir_draft(
            raw_doc="raw",
            provider=DraftErrorProvider(),
            task_id="safe-draft-error",
        )

    assert "SECRET-BANK-PAYLOAD" not in str(caught.value)
    assert "SECRET-BANK-PAYLOAD" not in caplog.text
    assert "DraftGenerationError" in str(caught.value)


def test_docir_generator_rejects_provider_content_with_bom() -> None:
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )

    with pytest.raises(DraftGenerationError, match="BOM"):
        generate_docir_draft(
            raw_doc="raw",
            provider=StaticProvider(
                artifact_content="\ufeff" + docir,
                review_notes="# DocIR Review\n",
            ),
            task_id="bom-content",
        )


def test_fixture_provider_rejects_path_escape(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("review", encoding="utf-8", newline="")
    (tmp_path / "draft-stub-case.json").write_text(
        json.dumps(
            {
                "contractVersion": "draft-stub-case/v1",
                "caseId": "path-escape",
                "responses": [
                    {
                        "request": {
                            "artifactKind": "docir",
                            "sourceHash": "sha256:" + "1" * 64,
                        },
                        "artifactFile": "../outside.md",
                        "reviewNotesFile": "notes.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(DraftGenerationError, match="stay within the fixture root"):
        FixtureDraftProvider(tmp_path)


def test_reviewed_final_docir_matches_the_approved_candidate() -> None:
    fixture_root = REPO_ROOT / "samples/draft-generation/b2eboc-b2e0061"
    approved_hash = "sha256:c45a6bbbf8cda12e0632d9b3b89f13e63645bf9ae1ea4ff9608b633be3573aa6"
    draft_bytes = (fixture_root / "artifacts/docir-draft.md").read_bytes()
    final_bytes = (fixture_root / "docir-final.md").read_bytes()

    assert final_bytes == draft_bytes
    assert f"sha256:{hashlib.sha256(final_bytes).hexdigest()}" == approved_hash

    review = (fixture_root / "docir-final-review.md").read_text(encoding="utf-8")
    assert "Status: `APPROVED`" in review
    assert "Reviewer：`deng`" in review
    assert approved_hash in review

    manifest = json.loads((fixture_root / "draft-stub-case.json").read_text(encoding="utf-8"))
    schemair_requests = [
        entry["request"]
        for entry in manifest["responses"]
        if entry["request"]["artifactKind"] == "schemair"
    ]
    assert schemair_requests == [
            {
                "artifactKind": "schemair",
                "sourceHash": approved_hash,
                "schemaId": "b2eboc-b2e0061-schema",
                "schemaVersion": "v1",
            }
    ]


def test_controlled_b2e0061_fixture_generates_all_six_drafts() -> None:
    fixture_root = REPO_ROOT / "samples/draft-generation/b2eboc-b2e0061"
    provider = FixtureDraftProvider(fixture_root)
    raw_bytes = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/raw-doc.md").read_bytes()
    docir_bytes = (fixture_root / "artifacts/docir-draft.md").read_bytes()
    golden_docir_bytes = (
        REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md"
    ).read_bytes()
    assert b"\r\n" in raw_bytes
    assert docir_bytes == golden_docir_bytes
    raw_doc = raw_bytes.decode("utf-8")
    docir_candidate = docir_bytes.decode("utf-8")
    schemair_final = load_json("samples/trusted-chain/b2eboc-b2e0061/schemair-final.json")
    standard_rules = load_rule_package(REPO_ROOT / "configuration-rules/v1")
    template_rules = load_rule_package(REPO_ROOT / "configuration-rules/v2")

    docir = generate_docir_draft(raw_doc=raw_doc, provider=provider, task_id="fixture-test")
    schemair = generate_schemair_draft(
        docir_final=docir_candidate,
        provider=provider,
        task_id="fixture-test",
        interface_code="b2e0061",
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
    )
    assert docir.content_hash == "sha256:c45a6bbbf8cda12e0632d9b3b89f13e63645bf9ae1ea4ff9608b633be3573aa6"
    assert schemair.validation_result["summary"]["errorCount"] >= 0

    expected = {
        "assembly": (
            "b2e0061-assembly-common",
            "sha256:34691505230a063e7b0c92798f6bd81b7fc41c5a988b0476195fcc23ec778af4",
            "sha256:356b83c1aff90d83d82fa3bbc14f7fe8277c34605a3d5edb4cb99abd71c49957",
        ),
        "parse": (
            "b2e0061-parse-common",
            "sha256:28dfde20c7190d5eccc93558d0726e7675656c4e6029b77f3018e76807fcacb2",
            "sha256:33cd4f7ae02701d6ab19cf46628398354590dba3d612f91e43b06f78d1356621",
        ),
    }
    for direction, (template_id, standard_hash, template_hash) in expected.items():
        standard = generate_interface_standard_draft(
            schemair_final=schemair_final,
            rule_package=standard_rules,
            direction=direction.upper(),
            standard_id=f"b2e0061-{direction}-standard",
            standard_version="v1",
            provider=provider,
            task_id="fixture-test",
        )
        standard_final = load_json(
            f"samples/trusted-chain/b2eboc-b2e0061/standards/{direction}/v1/standard-final.json"
        )
        template = generate_interface_template_draft(
            standard_final=standard_final,
            rule_package=template_rules,
            direction=direction.upper(),
            standard_version="v1",
            template_id=template_id,
            template_version="v1",
            provider=provider,
            task_id="fixture-test",
        )
        assert standard.content_hash == standard_hash
        assert template.content_hash == template_hash


def test_publish_generated_draft_is_fail_closed_and_refuses_overwrite(tmp_path: Path) -> None:
    raw_doc = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/raw-doc.md").read_text(encoding="utf-8")
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(encoding="utf-8")
    generated = generate_docir_draft(
        raw_doc=raw_doc,
        provider=StaticProvider(artifact_content=docir, review_notes="# Review\n"),
        task_id="phase0-test",
    )
    source = tmp_path / "source.md"
    source.write_text(raw_doc, encoding="utf-8", newline="")
    workspace = tmp_path / "workspace"
    ingest_raw_doc(source, workspace, task_id="phase0-test", interface_code="b2e0061")

    outputs = publish_generated_draft(workspace, generated, overwrite=False)

    assert outputs["artifact"] == workspace / "docir-draft.md"
    assert outputs["review_notes"] == workspace / "docir-review-notes.md"
    assert outputs["artifact"].read_text(encoding="utf-8") == docir
    with pytest.raises(DraftGenerationError, match="already exists"):
        publish_generated_draft(workspace, generated, overwrite=False)


def test_publish_generated_draft_cleans_temporary_files_after_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docir = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_text(
        encoding="utf-8"
    )
    generated = generate_docir_draft(
        raw_doc="raw",
        provider=StaticProvider(artifact_content=docir, review_notes="# Review\n"),
        task_id="partial-publish",
    )
    source = tmp_path / "source.md"
    source.write_text("raw", encoding="utf-8", newline="")
    workspace = tmp_path / "workspace"
    ingest_raw_doc(source, workspace, task_id="partial-publish", interface_code="b2e0061")
    real_replace = draft_generation.os.replace
    replace_count = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("simulated replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(draft_generation.os, "replace", fail_second_replace)

    with pytest.raises(DraftGenerationError, match="failed to publish Draft outputs"):
        publish_generated_draft(workspace, generated)

    assert (workspace / "docir-draft.md").is_file()
    assert not (workspace / "docir-review-notes.md").exists()
    assert list(workspace.rglob("*.tmp")) == []
