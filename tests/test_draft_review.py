from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from io import StringIO
from datetime import datetime, timezone
from pathlib import Path

import pytest

import bank_config_compiler.cli as draft_review_cli
import bank_config_compiler.draft_review as draft_review
from bank_config_compiler.artifact_validation import content_hash
from bank_config_compiler.draft_review import (
    DraftReviewError,
    approve_draft,
    validate_current_draft,
)
from bank_config_compiler.configuration_rules import load_rule_package
from bank_config_compiler.workspace import ingest_raw_doc


REPO_ROOT = Path(__file__).resolve().parents[1]


def _hash(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _workspace(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    raw = tmp_path / "source.md"
    raw.write_text("# Raw\n", encoding="utf-8", newline="")
    workspace = tmp_path / "workspace"
    ingest_raw_doc(
        raw,
        workspace,
        task_id="phase0-docir-review",
        interface_code="b2e0061",
    )
    draft = (
        REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md"
    ).read_bytes()
    (workspace / "docir-draft.md").write_bytes(draft)
    task = json.loads((workspace / "task.json").read_text(encoding="utf-8"))
    (workspace / "docir-generation-result.json").write_text(
        json.dumps(
            {
                "contractVersion": "draft-generation-result/v1",
                "taskId": task["taskId"],
                "interfaceCode": task["interfaceCode"],
                "artifactKind": "docir",
                "sourceHash": task["sourceHash"],
            }
        ),
        encoding="utf-8",
        newline="",
    )
    return workspace


def _bind_docir_approval(workspace: Path) -> None:
    task = json.loads((workspace / "task.json").read_text(encoding="utf-8"))
    final_hash = _hash((workspace / "docir-final.md").read_bytes())
    (workspace / "docir-approval-result.json").write_text(
        json.dumps(
            {
                "contractVersion": "draft-approval-result/v1",
                "taskId": task["taskId"],
                "interfaceCode": task["interfaceCode"],
                "artifactKind": "docir",
                "approvedDraftHash": final_hash,
                "reviewer": "fixture-reviewer",
                "reviewNote": "测试夹具中的 DocIR 已完成人工审核。",
                "reviewedAt": "2026-08-12T10:00:00+08:00",
                "finalArtifact": "docir-final.md",
                "finalHash": final_hash,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline="",
    )


def test_validate_current_docir_atomically_replaces_hash_bound_result_and_notes(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)

    result = validate_current_draft(workspace, "docir")

    draft_hash = _hash((workspace / "docir-draft.md").read_bytes())
    assert result["validatedArtifact"]["contentHash"] == draft_hash
    assert result["status"] == "passed"
    assert json.loads(
        (workspace / "docir-validation-result.json").read_text(encoding="utf-8")
    ) == result
    notes = (workspace / "docir-review-notes.md").read_text(encoding="utf-8")
    assert draft_hash in notes
    assert "DOCIR_REQUIRED_EVIDENCE_AMBIGUOUS" in notes


def test_validation_result_is_published_after_review_notes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    original_replace = draft_review.os.replace
    targets: list[str] = []

    def recording_replace(source: Path, target: Path) -> None:
        targets.append(Path(target).name)
        original_replace(source, target)

    monkeypatch.setattr(draft_review.os, "replace", recording_replace)

    validate_current_draft(workspace, "docir")

    assert targets[-2:] == [
        "docir-review-notes.md",
        "docir-validation-result.json",
    ]


def test_validation_aggregates_wire_and_locked_identity_issues(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    draft_path = workspace / "docir-draft.md"
    content = draft_path.read_text(encoding="utf-8")
    content = content.replace("| Interface Code | b2e0061 |", "| Interface Code | other |")
    content = content.replace("　`@version`", "`@version`")
    draft_path.write_text(content, encoding="utf-8", newline="")

    result = validate_current_draft(workspace, "docir")

    codes = {item["code"] for item in result["issues"]}
    assert "DOCIR_INTERFACE_CODE_MISMATCH" in codes
    assert "DOCIR_ITEM_INDENTATION" in codes
    assert result["summary"]["errorCount"] >= 2


def test_human_edit_invalidates_old_validation_until_revalidated(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    validate_current_draft(workspace, "docir")
    draft_path = workspace / "docir-draft.md"
    draft_path.write_bytes(draft_path.read_bytes() + b"\n")

    with pytest.raises(DraftReviewError, match="does not match current Draft"):
        approve_draft(
            workspace,
            "docir",
            reviewer="human-reviewer",
            review_note="逐项对照原始文档完成。",
            expected_content_hash=_hash(draft_path.read_bytes()),
        )


def test_approval_requires_zero_errors_and_exact_expected_hash(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    draft_path = workspace / "docir-draft.md"
    draft_path.write_text(
        draft_path.read_text(encoding="utf-8").replace("　`@version`", "`@version`"),
        encoding="utf-8",
        newline="",
    )
    validate_current_draft(workspace, "docir")

    with pytest.raises(DraftReviewError, match="zero ERROR"):
        approve_draft(
            workspace,
            "docir",
            reviewer="human-reviewer",
            review_note="仍需修正。",
            expected_content_hash=_hash(draft_path.read_bytes()),
        )

    workspace = _workspace(tmp_path / "second")
    validate_current_draft(workspace, "docir")
    with pytest.raises(DraftReviewError, match="expected content hash"):
        approve_draft(
            workspace,
            "docir",
            reviewer="human-reviewer",
            review_note="已完成。",
            expected_content_hash="sha256:" + "0" * 64,
        )


def test_docir_approval_publishes_byte_identical_final_and_hash_mapping(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    result = validate_current_draft(workspace, "docir")
    approved_hash = result["validatedArtifact"]["contentHash"]

    approval = approve_draft(
        workspace,
        "docir",
        reviewer="human-reviewer",
        review_note="逐项对照原始文档完成。",
        expected_content_hash=approved_hash,
        reviewed_at=datetime(2026, 8, 12, 10, 30, tzinfo=timezone.utc),
    )

    assert (workspace / "docir-final.md").read_bytes() == (
        workspace / "docir-draft.md"
    ).read_bytes()
    assert approval["approvedDraftHash"] == approved_hash
    assert approval["finalHash"] == approved_hash
    assert approval["reviewer"] == "human-reviewer"
    assert approval["reviewNote"] == "逐项对照原始文档完成。"
    assert json.loads(
        (workspace / "docir-approval-result.json").read_text(encoding="utf-8")
    ) == approval


def test_approval_result_is_published_after_final_and_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    result = validate_current_draft(workspace, "docir")
    original_replace = draft_review.os.replace
    targets: list[str] = []

    def recording_replace(source: Path, target: Path) -> None:
        targets.append(Path(target).name)
        original_replace(source, target)

    monkeypatch.setattr(draft_review.os, "replace", recording_replace)

    approve_draft(
        workspace,
        "docir",
        reviewer="human-reviewer",
        review_note="逐项对照原始文档完成。",
        expected_content_hash=result["validatedArtifact"]["contentHash"],
    )

    assert targets[-3:] == [
        "docir-final.md",
        "docir-validation-result.json",
        "docir-approval-result.json",
    ]


def test_approval_detects_concurrent_draft_change_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    result = validate_current_draft(workspace, "docir")
    original_read = draft_review._read_bytes
    reads = 0

    def changing_read(path: Path) -> bytes:
        nonlocal reads
        data = original_read(path)
        if path.name == "docir-draft.md":
            reads += 1
            if reads == 2:
                path.write_bytes(data + b"\n")
                return data + b"\n"
        return data

    monkeypatch.setattr(draft_review, "_read_bytes", changing_read)

    with pytest.raises(DraftReviewError, match="changed during approval"):
        approve_draft(
            workspace,
            "docir",
            reviewer="human-reviewer",
            review_note="逐项对照原始文档完成。",
            expected_content_hash=result["validatedArtifact"]["contentHash"],
        )
    assert not (workspace / "docir-final.md").exists()
    assert not (workspace / "docir-approval-result.json").exists()


def test_validate_and_noninteractive_approve_cli(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    validate = subprocess.run(
        [
            sys.executable,
            "-m",
            "bank_config_compiler",
            "validate-draft",
            "docir",
            "--workspace",
            str(workspace),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    content_hash = json.loads(
        (workspace / "docir-validation-result.json").read_text(encoding="utf-8")
    )["validatedArtifact"]["contentHash"]

    approve = subprocess.run(
        [
            sys.executable,
            "-m",
            "bank_config_compiler",
            "approve-draft",
            "docir",
            "--workspace",
            str(workspace),
            "--reviewer",
            "human-reviewer",
            "--review-note",
            "逐项对照原始文档完成。",
            "--expected-content-hash",
            content_hash,
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert approve.returncode == 0, approve.stderr
    assert (workspace / "docir-final.md").is_file()


def test_noninteractive_approval_rejects_missing_expected_hash(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    validate_current_draft(workspace, "docir")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bank_config_compiler",
            "approve-draft",
            "docir",
            "--workspace",
            str(workspace),
            "--reviewer",
            "human-reviewer",
            "--review-note",
            "逐项对照原始文档完成。",
        ],
        cwd=REPO_ROOT,
        input="",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 2
    assert "requires --expected-content-hash" in result.stderr
    assert not (workspace / "docir-final.md").exists()


def test_interactive_approval_displays_identity_summary_and_full_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = _workspace(tmp_path)

    class InteractiveInput(StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr(sys, "stdin", InteractiveInput())
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    exit_code = draft_review_cli.main(
        [
            "approve-draft",
            "docir",
            "--workspace",
            str(workspace),
            "--reviewer",
            "human-reviewer",
            "--review-note",
            "逐项对照原始文档完成。",
        ]
    )

    output = capsys.readouterr().out
    expected_hash = _hash((workspace / "docir-draft.md").read_bytes())
    assert exit_code == 0
    assert "taskId=phase0-docir-review" in output
    assert "interfaceCode=b2e0061" in output
    assert "Validation summary: ERROR=0, WARNING=1, INFO=0" in output
    assert f"Content hash: {expected_hash}" in output


def _write_json_review_case(
    workspace: Path,
    *,
    kind: str,
    draft_path: str,
    generation_path: str,
    artifact: dict,
    source_path: str,
    selectors: dict[str, str],
) -> None:
    candidate = json.loads(json.dumps(artifact))
    candidate["status"] = "DRAFT"
    candidate["review"] = {
        "status": "PENDING",
        "reviewer": None,
        "reviewedAt": None,
        "note": None,
    }
    target = workspace / draft_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8", newline="")
    task = json.loads((workspace / "task.json").read_text(encoding="utf-8"))
    source = workspace / source_path
    if kind == "schemair":
        _bind_docir_approval(workspace)
    if source.suffix == ".md":
        source_hash = _hash(source.read_bytes())
    else:
        source_hash = content_hash(json.loads(source.read_text(encoding="utf-8")))
    generation = workspace / generation_path
    generation.parent.mkdir(parents=True, exist_ok=True)
    generation.write_text(
        json.dumps(
            {
                "contractVersion": "draft-generation-result/v1",
                "taskId": task["taskId"],
                "interfaceCode": task["interfaceCode"],
                "artifactKind": kind,
                "sourceHash": source_hash,
                "selectors": selectors,
            }
        ),
        encoding="utf-8",
        newline="",
    )


def test_json_draft_approval_adds_only_lifecycle_metadata_and_final_validates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    chain = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    schema = json.loads((chain / "schemair-final.json").read_text(encoding="utf-8"))
    (workspace / "docir-final.md").write_bytes(
        (workspace / "docir-draft.md").read_bytes()
    )
    _write_json_review_case(
        workspace,
        kind="schemair",
        draft_path="schemair-draft.json",
        generation_path="schemair-generation-result.json",
        artifact=schema,
        source_path="docir-final.md",
        selectors={
            "schemaId": schema["schemaId"],
            "schemaVersion": schema["schemaVersion"],
        },
    )

    validation = validate_current_draft(workspace, "schemair")
    assert validation["summary"]["errorCount"] == 0

    class FixedDateTime:
        calls = 0

        @classmethod
        def now(cls):
            cls.calls += 1
            return datetime(2026, 8, 12, 10, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(draft_review, "datetime", FixedDateTime)
    approval = approve_draft(
        workspace,
        "schemair",
        reviewer="human-reviewer",
        review_note="逐项确认 SchemaIR。",
        expected_content_hash=validation["validatedArtifact"]["contentHash"],
    )

    final = json.loads((workspace / "schemair-final.json").read_text(encoding="utf-8"))
    draft = json.loads((workspace / "schemair-draft.json").read_text(encoding="utf-8"))
    assert final == {
        **draft,
        "status": "FINAL",
        "review": {
            "status": "APPROVED",
            "reviewer": "human-reviewer",
            "reviewedAt": approval["reviewedAt"],
            "note": "逐项确认 SchemaIR。",
        },
    }
    assert approval["approvedDraftHash"] != approval["finalHash"]
    assert approval["reviewedAt"] == final["review"]["reviewedAt"]
    assert FixedDateTime.calls == 1
    final_validation = json.loads(
        (workspace / "schemair-validation-result.json").read_text(encoding="utf-8")
    )
    assert final_validation["finalEligible"] is True


def test_schemair_validation_rejects_locked_identity_change(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    chain = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    schema = json.loads((chain / "schemair-final.json").read_text(encoding="utf-8"))
    (workspace / "docir-final.md").write_bytes(
        (workspace / "docir-draft.md").read_bytes()
    )
    _write_json_review_case(
        workspace,
        kind="schemair",
        draft_path="schemair-draft.json",
        generation_path="schemair-generation-result.json",
        artifact=schema,
        source_path="docir-final.md",
        selectors={
            "schemaId": schema["schemaId"],
            "schemaVersion": schema["schemaVersion"],
        },
    )
    draft_path = workspace / "schemair-draft.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft["schemaId"] = "human-edited-schema-id"
    draft["schemaVersion"] = "v2"
    draft_path.write_text(json.dumps(draft), encoding="utf-8", newline="")

    result = validate_current_draft(workspace, "schemair")

    lineage_issues = [
        item
        for item in result["issues"]
        if item["code"] == "DRAFT_GENERATION_LINEAGE_MISMATCH"
    ]
    assert result["summary"]["errorCount"] > 0
    assert lineage_issues
    assert "selectors" in lineage_issues[0]["message"]


def test_schemair_validation_rejects_changed_upstream_final_hash(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    chain = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    schema = json.loads((chain / "schemair-final.json").read_text(encoding="utf-8"))
    docir_final = workspace / "docir-final.md"
    docir_final.write_bytes((workspace / "docir-draft.md").read_bytes())
    _write_json_review_case(
        workspace,
        kind="schemair",
        draft_path="schemair-draft.json",
        generation_path="schemair-generation-result.json",
        artifact=schema,
        source_path="docir-final.md",
        selectors={
            "schemaId": schema["schemaId"],
            "schemaVersion": schema["schemaVersion"],
        },
    )
    docir_final.write_bytes(docir_final.read_bytes() + b"\n")

    result = validate_current_draft(workspace, "schemair")

    lineage_issues = [
        item
        for item in result["issues"]
        if item["code"] == "DRAFT_GENERATION_LINEAGE_MISMATCH"
    ]
    assert lineage_issues
    assert "sourceHash" in lineage_issues[0]["message"]


def test_schemair_validation_rejects_missing_docir_approval_evidence(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    chain = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    schema = json.loads((chain / "schemair-final.json").read_text(encoding="utf-8"))
    (workspace / "docir-final.md").write_bytes(
        (workspace / "docir-draft.md").read_bytes()
    )
    _write_json_review_case(
        workspace,
        kind="schemair",
        draft_path="schemair-draft.json",
        generation_path="schemair-generation-result.json",
        artifact=schema,
        source_path="docir-final.md",
        selectors={
            "schemaId": schema["schemaId"],
            "schemaVersion": schema["schemaVersion"],
        },
    )
    (workspace / "docir-approval-result.json").unlink()

    result = validate_current_draft(workspace, "schemair")

    assert any(
        item["code"] == "DOCIR_APPROVAL_EVIDENCE_INVALID"
        for item in result["issues"]
    )
    assert result["summary"]["errorCount"] > 0


def test_schemair_approval_rechecks_docir_approval_evidence(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    chain = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    schema = json.loads((chain / "schemair-final.json").read_text(encoding="utf-8"))
    (workspace / "docir-final.md").write_bytes(
        (workspace / "docir-draft.md").read_bytes()
    )
    _write_json_review_case(
        workspace,
        kind="schemair",
        draft_path="schemair-draft.json",
        generation_path="schemair-generation-result.json",
        artifact=schema,
        source_path="docir-final.md",
        selectors={
            "schemaId": schema["schemaId"],
            "schemaVersion": schema["schemaVersion"],
        },
    )
    validation = validate_current_draft(workspace, "schemair")
    approval_path = workspace / "docir-approval-result.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    approval["finalHash"] = "sha256:" + "a" * 64
    approval_path.write_text(json.dumps(approval), encoding="utf-8", newline="")

    with pytest.raises(DraftReviewError, match="Final Validator rejected approval"):
        approve_draft(
            workspace,
            "schemair",
            reviewer="human-reviewer",
            review_note="逐项确认 SchemaIR。",
            expected_content_hash=validation["validatedArtifact"]["contentHash"],
        )

    assert not (workspace / "schemair-final.json").exists()
    assert not (workspace / "schemair-approval-result.json").exists()


def test_schemair_approval_detects_concurrent_upstream_final_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    chain = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    schema = json.loads((chain / "schemair-final.json").read_text(encoding="utf-8"))
    docir_final = workspace / "docir-final.md"
    docir_final.write_bytes((workspace / "docir-draft.md").read_bytes())
    _write_json_review_case(
        workspace,
        kind="schemair",
        draft_path="schemair-draft.json",
        generation_path="schemair-generation-result.json",
        artifact=schema,
        source_path="docir-final.md",
        selectors={
            "schemaId": schema["schemaId"],
            "schemaVersion": schema["schemaVersion"],
        },
    )
    validation = validate_current_draft(workspace, "schemair")
    original_read = draft_review._read_bytes
    dependency_reads = 0

    def changing_dependency(path: Path) -> bytes:
        nonlocal dependency_reads
        data = original_read(path)
        if path.name == "docir-final.md":
            dependency_reads += 1
            if dependency_reads == 3:
                path.write_bytes(data + b"\n")
                return data + b"\n"
        return data

    monkeypatch.setattr(draft_review, "_read_bytes", changing_dependency)

    with pytest.raises(DraftReviewError, match="upstream Final changed"):
        approve_draft(
            workspace,
            "schemair",
            reviewer="human-reviewer",
            review_note="逐项确认 SchemaIR。",
            expected_content_hash=validation["validatedArtifact"]["contentHash"],
        )
    assert not (workspace / "schemair-final.json").exists()
    assert not (workspace / "schemair-approval-result.json").exists()


def test_standard_and_template_json_human_gates(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    chain = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    schema = json.loads((chain / "schemair-final.json").read_text(encoding="utf-8"))
    (workspace / "schemair-final.json").write_text(
        json.dumps(schema, ensure_ascii=False), encoding="utf-8", newline=""
    )
    standard = json.loads(
        (chain / "standards/assembly/v1/standard-final.json").read_text(encoding="utf-8")
    )
    _write_json_review_case(
        workspace,
        kind="standard",
        draft_path="standards/assembly/v1/standard-draft.json",
        generation_path="standards/assembly/v1/standard-generation-result.json",
        artifact=standard,
        source_path="schemair-final.json",
        selectors={
            "standardId": standard["standardId"],
            "direction": "ASSEMBLY",
            "standardVersion": "v1",
            "rulePackageVersion": "v1",
        },
    )
    standard_rules = load_rule_package(REPO_ROOT / "configuration-rules/v1")
    standard_draft_path = workspace / "standards/assembly/v1/standard-draft.json"
    standard_draft = json.loads(standard_draft_path.read_text(encoding="utf-8"))
    standard_draft.update(
        {
            "standardId": "human-edited-standard-id",
            "standardVersion": "v2",
            "direction": "PARSE",
        }
    )
    standard_draft_path.write_text(
        json.dumps(standard_draft), encoding="utf-8", newline=""
    )
    rejected_standard = validate_current_draft(
        workspace,
        "standard",
        direction="ASSEMBLY",
        standard_version="v1",
        rule_package=standard_rules,
    )
    rejected_standard_codes = {item["code"] for item in rejected_standard["issues"]}
    assert "LOCKED_DIRECTION_MISMATCH" in rejected_standard_codes
    assert "LOCKED_STANDARD_VERSION_MISMATCH" in rejected_standard_codes
    assert "DRAFT_GENERATION_LINEAGE_MISMATCH" in rejected_standard_codes
    standard_draft.update(
        {
            "standardId": standard["standardId"],
            "standardVersion": "v1",
            "direction": "ASSEMBLY",
        }
    )
    standard_draft_path.write_text(
        json.dumps(standard_draft), encoding="utf-8", newline=""
    )
    standard_validation = validate_current_draft(
        workspace,
        "standard",
        direction="ASSEMBLY",
        standard_version="v1",
        rule_package=standard_rules,
    )
    standard_approval = approve_draft(
        workspace,
        "standard",
        reviewer="human-reviewer",
        review_note="逐项确认 Standard。",
        expected_content_hash=standard_validation["validatedArtifact"]["contentHash"],
        direction="ASSEMBLY",
        standard_version="v1",
        rule_package=standard_rules,
    )
    assert standard_approval["finalHash"]

    template = json.loads(
        (chain / "templates/assembly/v1/template-final.json").read_text(encoding="utf-8")
    )
    template["standardRef"]["contentHash"] = standard_approval["finalHash"]
    _write_json_review_case(
        workspace,
        kind="template",
        draft_path="templates/assembly/b2e0061-assembly-common/v1/template-draft.json",
        generation_path="templates/assembly/b2e0061-assembly-common/v1/template-generation-result.json",
        artifact=template,
        source_path="standards/assembly/v1/standard-final.json",
        selectors={
            "direction": "ASSEMBLY",
            "standardVersion": "v1",
            "templateId": "b2e0061-assembly-common",
            "templateVersion": "v1",
            "rulePackageVersion": "v2",
        },
    )
    template_rules = load_rule_package(REPO_ROOT / "configuration-rules/v2")
    template_draft_path = (
        workspace
        / "templates/assembly/b2e0061-assembly-common/v1/template-draft.json"
    )
    template_draft = json.loads(template_draft_path.read_text(encoding="utf-8"))
    template_draft.update(
        {
            "templateId": "human-edited-template-id",
            "templateVersion": "v2",
            "direction": "PARSE",
        }
    )
    template_draft_path.write_text(
        json.dumps(template_draft), encoding="utf-8", newline=""
    )
    rejected_template = validate_current_draft(
        workspace,
        "template",
        direction="ASSEMBLY",
        standard_version="v1",
        template_id="b2e0061-assembly-common",
        template_version="v1",
        rule_package=template_rules,
    )
    rejected_template_codes = {item["code"] for item in rejected_template["issues"]}
    assert "LOCKED_DIRECTION_MISMATCH" in rejected_template_codes
    assert "LOCKED_TEMPLATE_ID_MISMATCH" in rejected_template_codes
    assert "LOCKED_TEMPLATE_VERSION_MISMATCH" in rejected_template_codes
    template_draft.update(
        {
            "templateId": "b2e0061-assembly-common",
            "templateVersion": "v1",
            "direction": "ASSEMBLY",
        }
    )
    template_draft_path.write_text(
        json.dumps(template_draft), encoding="utf-8", newline=""
    )
    template_validation = validate_current_draft(
        workspace,
        "template",
        direction="ASSEMBLY",
        standard_version="v1",
        template_id="b2e0061-assembly-common",
        template_version="v1",
        rule_package=template_rules,
    )
    template_approval = approve_draft(
        workspace,
        "template",
        reviewer="human-reviewer",
        review_note="逐项确认 Template。",
        expected_content_hash=template_validation["validatedArtifact"]["contentHash"],
        direction="ASSEMBLY",
        standard_version="v1",
        template_id="b2e0061-assembly-common",
        template_version="v1",
        rule_package=template_rules,
    )
    assert template_approval["finalHash"]
