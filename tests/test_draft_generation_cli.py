from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

import bank_config_compiler.cli as cli
from bank_config_compiler.draft_generation import (
    DraftGenerationRequest,
    DraftProviderDiagnosticError,
    ProviderCallMetadata,
    ProviderFailureEvidence,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bank_config_compiler", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def workbook_snapshot(path: Path) -> dict:
    workbook = load_workbook(path, data_only=False, keep_links=False)
    result = {"sheetnames": workbook.sheetnames, "sheets": {}}
    for sheet in workbook.worksheets:
        cells = []
        for row in sheet.iter_rows():
            for cell in row:
                value = (
                    "<generated-at>"
                    if sheet.title == "Overview" and cell.coordinate == "B4"
                    else cell.value
                )
                cells.append(
                    (
                        cell.coordinate,
                        value,
                        cell.data_type,
                        cell.number_format,
                        cell.fill.fill_type,
                        cell.fill.fgColor.rgb,
                        cell.font.bold,
                        cell.font.color.type if cell.font.color else None,
                        cell.font.color.rgb
                        if cell.font.color and cell.font.color.type == "rgb"
                        else None,
                        cell.alignment.vertical,
                        cell.alignment.wrap_text,
                    )
                )
        validations = sorted(
            (str(item.sqref), item.type, item.formula1, item.allow_blank)
            for item in sheet.data_validations.dataValidation
        )
        widths = sorted(
            (name, dimension.width)
            for name, dimension in sheet.column_dimensions.items()
            if dimension.width is not None
        )
        result["sheets"][sheet.title] = {
            "dimensions": sheet.dimensions,
            "freeze": sheet.freeze_panes,
            "filter": sheet.auto_filter.ref,
            "gridlines": sheet.sheet_view.showGridLines,
            "widths": widths,
            "validations": validations,
            "cells": cells,
        }
    workbook.close()
    return result


def prepare_docir_case(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    raw_bytes = (REPO_ROOT / "samples/golden/b2eboc-b2e0061/raw-doc.md").read_bytes()
    (workspace / "raw-doc.md").write_bytes(raw_bytes)

    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    (fixture_root / "docir.md").write_bytes(
        (REPO_ROOT / "samples/golden/b2eboc-b2e0061/docir.expected.md").read_bytes()
    )
    (fixture_root / "notes.md").write_bytes(
        (REPO_ROOT / "samples/golden/b2eboc-b2e0061/review-notes.expected.md").read_bytes()
    )
    source_hash = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
    (fixture_root / "draft-stub-case.json").write_text(
        json.dumps(
            {
                "contractVersion": "draft-stub-case/v1",
                "caseId": "cli-docir-case",
                "responses": [
                    {
                        "request": {"artifactKind": "docir", "sourceHash": source_hash},
                        "artifactFile": "docir.md",
                        "reviewNotesFile": "notes.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
        newline="",
    )
    return workspace, fixture_root


def test_generate_draft_docir_cli_writes_fixed_outputs(tmp_path: Path) -> None:
    workspace, fixture_root = prepare_docir_case(tmp_path)

    result = run_cli(
        "generate-draft",
        "docir",
        "--workspace",
        str(workspace),
        "--provider",
        "fixture",
        "--fixture-root",
        str(fixture_root),
    )

    assert result.returncode == 0, result.stderr
    assert "saved docir Draft" in result.stdout
    assert (workspace / "docir-draft.md").is_file()
    assert (workspace / "docir-review-notes.md").is_file()


def test_generate_draft_cli_requires_explicit_fixture_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = run_cli(
        "generate-draft",
        "docir",
        "--workspace",
        str(workspace),
        "--provider",
        "fixture",
    )

    assert result.returncode == 2
    assert "--fixture-root" in result.stderr


def test_generate_draft_cli_openai_chat_requires_runtime_api_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("BANK_CONFIG_COMPILER_LLM_API_KEY", raising=False)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text("# Raw bank document\n", encoding="utf-8")

    result = run_cli(
        "generate-draft",
        "docir",
        "--workspace",
        str(workspace),
        "--provider",
        "openai-chat",
        "--chat-base-url",
        "https://example.invalid/v1",
        "--chat-model",
        "qwen-test-snapshot",
        "--attempt-id",
        "docir-001",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "BANK_CONFIG_COMPILER_LLM_API_KEY" in result.stderr
    assert not (workspace / "docir-draft.md").exists()


def test_main_loads_allowlisted_llm_configuration_from_cwd_dotenv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    for name in (
        "BANK_CONFIG_COMPILER_LLM_API_KEY",
        "BANK_CONFIG_COMPILER_LLM_BASE_URL",
        "BANK_CONFIG_COMPILER_LLM_MODEL",
        "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS",
        "UNRELATED_SETTING",
    ):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text(
        "BANK_CONFIG_COMPILER_LLM_API_KEY=dotenv-key\n"
        "BANK_CONFIG_COMPILER_LLM_BASE_URL=https://example.invalid/v1\n"
        "BANK_CONFIG_COMPILER_LLM_MODEL=qwen-test-snapshot\n"
        "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS=45.5\n"
        "UNRELATED_SETTING=must-not-be-loaded\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    def generate_draft(args) -> Path:
        assert cli._draft_provider(args) is provider
        return tmp_path / "docir-draft.md"

    provider = object()
    captured: dict[str, object] = {}

    def provider_factory(**kwargs: object) -> object:
        captured.update(kwargs)
        return provider

    monkeypatch.setattr(cli, "OpenAIChatDraftProvider", provider_factory)
    monkeypatch.setattr(cli, "_generate_draft", generate_draft)

    result = cli.main(
        [
            "generate-draft",
            "docir",
            "--workspace",
            str(tmp_path / "workspace"),
            "--provider",
            "openai-chat",
            "--attempt-id",
            "docir-001",
        ]
    )

    assert result == 0
    assert captured == {
        "api_key": "dotenv-key",
        "base_url": "https://example.invalid/v1",
        "model": "qwen-test-snapshot",
        "attempt_id": "docir-001",
        "timeout_seconds": 45.5,
    }
    assert "UNRELATED_SETTING" not in os.environ


def test_process_environment_and_cli_override_dotenv_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / ".env").write_text(
        "BANK_CONFIG_COMPILER_LLM_API_KEY=dotenv-key\n"
        "BANK_CONFIG_COMPILER_LLM_BASE_URL=https://dotenv.invalid/v1\n"
        "BANK_CONFIG_COMPILER_LLM_MODEL=dotenv-model\n"
        "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS=10\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BANK_CONFIG_COMPILER_LLM_API_KEY", "process-key")
    monkeypatch.setenv("BANK_CONFIG_COMPILER_LLM_MODEL", "process-model")
    runtime_environment = cli._load_runtime_environment()

    assert runtime_environment == {
        "BANK_CONFIG_COMPILER_LLM_API_KEY": "process-key",
        "BANK_CONFIG_COMPILER_LLM_BASE_URL": "https://dotenv.invalid/v1",
        "BANK_CONFIG_COMPILER_LLM_MODEL": "process-model",
        "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS": "10",
    }


def test_openai_chat_cli_configuration_is_forwarded_without_secret_defaults(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def provider_factory(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("BANK_CONFIG_COMPILER_LLM_API_KEY", "runtime-key")
    monkeypatch.setenv("BANK_CONFIG_COMPILER_LLM_BASE_URL", "https://env.invalid/v1")
    monkeypatch.setenv("BANK_CONFIG_COMPILER_LLM_MODEL", "env-model")
    monkeypatch.setenv("BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS", "10")
    monkeypatch.setattr(cli, "OpenAIChatDraftProvider", provider_factory)
    args = SimpleNamespace(
        provider="openai-chat",
        fixture_root=None,
        chat_base_url="https://example.invalid/v1",
        chat_model="qwen-test-snapshot",
        chat_timeout_seconds=45.5,
        attempt_id="docir-001",
    )

    cli._draft_provider(args)

    assert captured == {
        "api_key": "runtime-key",
        "base_url": "https://example.invalid/v1",
        "model": "qwen-test-snapshot",
        "attempt_id": "docir-001",
        "timeout_seconds": 45.5,
    }


def test_dotenv_example_lists_only_supported_llm_configuration() -> None:
    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    assert example == (
        "# Copy this file to .env and keep .env out of Git.\n"
        "BANK_CONFIG_COMPILER_LLM_API_KEY=\n"
        "BANK_CONFIG_COMPILER_LLM_BASE_URL=https://approved-provider.example/v1\n"
        "BANK_CONFIG_COMPILER_LLM_MODEL=approved-model-snapshot\n"
        "BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS=600\n"
    )


def test_generate_draft_cli_fails_closed_on_fixture_hash_mismatch(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text("different input", encoding="utf-8", newline="")

    result = run_cli(
        "generate-draft", "docir", "--workspace", str(workspace),
        "--provider", "fixture",
        "--fixture-root", str(REPO_ROOT / "samples/draft-generation/b2eboc-b2e0061"),
    )

    assert result.returncode == 2
    assert "no exact response" in result.stderr
    assert not (workspace / "docir-draft.md").exists()
    assert not (workspace / "docir-review-notes.md").exists()


def test_generate_docir_failure_publishes_partial_provider_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "phase0-docir-failure"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text(
        "# Raw bank document\n", encoding="utf-8", newline=""
    )

    class FailingProvider:
        name = "openai-chat"
        attempt_id = "docir-011"
        model = "qwen-test-snapshot"

        def generate(self, request, context):
            raise DraftProviderDiagnosticError(
                "chat stream failed: TimeoutError",
                evidence=ProviderFailureEvidence(
                    request=request,
                    metadata=ProviderCallMetadata(
                        provider_name=self.name,
                        attempt_id=self.attempt_id,
                        requested_model=self.model,
                        response_model=self.model,
                        response_id="chatcmpl-test",
                        started_at="2026-08-11T10:00:00+08:00",
                        completed_at="2026-08-11T10:01:00+08:00",
                        endpoint_fingerprint="sha256:" + "a" * 64,
                        prompt_contract_version="draft-prompt/v7",
                    ),
                    failure_stage="stream",
                    failure_detail="chat stream failed: TimeoutError",
                    error_type="TimeoutError",
                    response_complete=False,
                    response_text='{"contractVersion":"docir-extraction/v1"',
                    finish_reason=None,
                ),
            )

    monkeypatch.setattr(cli, "_draft_provider", lambda args: FailingProvider())
    args = SimpleNamespace(
        workspace=workspace,
        draft_kind="docir",
        provider="openai-chat",
        overwrite=False,
    )

    with pytest.raises(DraftProviderDiagnosticError) as caught:
        cli._generate_draft(args)

    summary_path = workspace / "docir-provider-failure-result.json"
    response_path = workspace / "docir-provider-failure-response.txt"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["contractVersion"] == "draft-provider-failure-result/v1"
    assert summary["artifactKind"] == "docir"
    assert summary["attemptId"] == "docir-011"
    assert summary["failureStage"] == "stream"
    assert summary["failureDetail"] == "chat stream failed: TimeoutError"
    assert summary["responseComplete"] is False
    assert summary["responseContentHash"].startswith("sha256:")
    assert summary["endpointFingerprint"] == "sha256:" + "a" * 64
    serialized_summary = summary_path.read_text(encoding="utf-8")
    assert "test-key" not in serialized_summary
    assert "https://" not in serialized_summary
    assert "Raw bank document" not in serialized_summary
    assert response_path.read_text(encoding="utf-8") == (
        '{"contractVersion":"docir-extraction/v1"'
    )
    assert not (workspace / "docir-draft.md").exists()
    assert not (workspace / "docir-review-notes.md").exists()
    assert not (workspace / "docir-provider-call-result.json").exists()
    assert set(caught.value.failure_evidence_paths) == {summary_path, response_path}
    assert summary["responseContentHash"] in cli._safe_error(caught.value)


def test_generate_docir_request_failure_does_not_create_empty_response_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "phase0-docir-request-failure"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text(
        "# Raw bank document\n", encoding="utf-8", newline=""
    )

    class FailingProvider:
        name = "openai-chat"
        attempt_id = "docir-011"
        model = "qwen-test-snapshot"

        def generate(self, request, context):
            raise DraftProviderDiagnosticError(
                "chat request failed: TimeoutError",
                evidence=ProviderFailureEvidence(
                    request=request,
                    metadata=ProviderCallMetadata(
                        provider_name=self.name,
                        attempt_id=self.attempt_id,
                        requested_model=self.model,
                        started_at="2026-08-11T10:00:00+08:00",
                        completed_at="2026-08-11T10:00:01+08:00",
                        endpoint_fingerprint="sha256:" + "a" * 64,
                        prompt_contract_version="draft-prompt/v7",
                    ),
                    failure_stage="request",
                    failure_detail="chat request failed: TimeoutError",
                    error_type="TimeoutError",
                    response_complete=False,
                    response_text=None,
                    finish_reason=None,
                ),
            )

    monkeypatch.setattr(cli, "_draft_provider", lambda args: FailingProvider())
    args = SimpleNamespace(
        workspace=workspace,
        draft_kind="docir",
        provider="openai-chat",
        overwrite=False,
    )

    with pytest.raises(DraftProviderDiagnosticError) as caught:
        cli._generate_draft(args)

    summary_path = workspace / "docir-provider-failure-result.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["failureStage"] == "request"
    assert summary["responseContentHash"] is None
    assert not (workspace / "docir-provider-failure-response.txt").exists()
    assert caught.value.failure_evidence_paths == (summary_path,)
    assert str(summary_path) in cli._safe_error(caught.value)


def test_overwriting_request_failure_removes_stale_response_evidence(tmp_path: Path) -> None:
    workspace = tmp_path / "phase0-docir-overwrite-failure"
    workspace.mkdir()

    def diagnostic(response_text: str | None) -> DraftProviderDiagnosticError:
        request = DraftGenerationRequest(
            task_id="phase0-docir-overwrite-failure",
            artifact_kind="docir",
            source_hash="sha256:" + "1" * 64,
        )
        return DraftProviderDiagnosticError(
            "provider failed",
            evidence=ProviderFailureEvidence(
                request=request,
                metadata=ProviderCallMetadata(
                    provider_name="openai-chat",
                    attempt_id="docir-011",
                    requested_model="qwen-test-snapshot",
                    started_at="2026-08-11T10:00:00+08:00",
                    completed_at="2026-08-11T10:00:01+08:00",
                    endpoint_fingerprint="sha256:" + "a" * 64,
                    prompt_contract_version="draft-prompt/v7",
                ),
                failure_stage="stream" if response_text is not None else "request",
                failure_detail="provider failed",
                error_type="TimeoutError",
                response_complete=False,
                response_text=response_text,
                finish_reason=None,
            ),
        )

    cli.publish_provider_failure(workspace, diagnostic("partial response"))
    response_path = workspace / "docir-provider-failure-response.txt"
    assert response_path.is_file()

    cli.publish_provider_failure(workspace, diagnostic(None), overwrite=True)

    summary = json.loads(
        (workspace / "docir-provider-failure-result.json").read_text(encoding="utf-8")
    )
    assert summary["failureStage"] == "request"
    assert summary["responseContentHash"] is None
    assert not response_path.exists()


def test_generate_draft_cli_never_promotes_docir_draft(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    fixture_root = REPO_ROOT / "samples/draft-generation/b2eboc-b2e0061"
    shutil.copyfile(
        REPO_ROOT / "samples/golden/b2eboc-b2e0061/raw-doc.md",
        workspace / "raw-doc.md",
    )

    docir = run_cli(
        "generate-draft", "docir", "--workspace", str(workspace),
        "--provider", "fixture", "--fixture-root", str(fixture_root),
    )
    assert docir.returncode == 0, docir.stderr
    assert (workspace / "docir-draft.md").is_file()
    assert not (workspace / "docir-final.md").exists()

    schemair = run_cli(
        "generate-draft", "schemair", "--workspace", str(workspace),
        "--provider", "fixture", "--fixture-root", str(fixture_root),
    )
    assert schemair.returncode == 2
    assert "docir-final.md is missing" in schemair.stderr
    assert not (workspace / "schemair-draft.json").exists()


def test_generate_draft_cli_completes_controlled_b2e0061_workflow(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    fixture_root = REPO_ROOT / "samples/draft-generation/b2eboc-b2e0061"
    raw_source = REPO_ROOT / "samples/golden/b2eboc-b2e0061/raw-doc.md"
    shutil.copyfile(raw_source, workspace / "raw-doc.md")

    docir = run_cli(
        "generate-draft", "docir", "--workspace", str(workspace),
        "--provider", "fixture", "--fixture-root", str(fixture_root),
    )
    assert docir.returncode == 0, docir.stderr

    # Human gate 只能通过显式装载已审核 fixture 表达；严禁把本次生成的 Draft 自动提升为 Final。
    shutil.copyfile(fixture_root / "docir-final.md", workspace / "docir-final.md")
    assert (workspace / "docir-final.md").read_bytes() == (
        fixture_root / "docir-final.md"
    ).read_bytes()
    schemair = run_cli(
        "generate-draft", "schemair", "--workspace", str(workspace),
        "--provider", "fixture", "--fixture-root", str(fixture_root),
    )
    assert schemair.returncode == 0, schemair.stderr

    trusted = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    for name in ("schemair-final.json", "schemair-validation-result.json"):
        shutil.copyfile(trusted / name, workspace / name)
    for direction, template_id in (
        ("assembly", "b2e0061-assembly-common"),
        ("parse", "b2e0061-parse-common"),
    ):
        standard = run_cli(
            "generate-draft", "standard", "--workspace", str(workspace),
            "--provider", "fixture", "--fixture-root", str(fixture_root),
            "--direction", direction, "--standard-version", "v1",
            "--rule-package", str(REPO_ROOT / "configuration-rules/v1"),
        )
        assert standard.returncode == 0, standard.stderr

        standard_dir = workspace / "standards" / direction / "v1"
        trusted_standard_dir = trusted / "standards" / direction / "v1"
        for name in ("standard-final.json", "standard-validation-result.json"):
            shutil.copyfile(trusted_standard_dir / name, standard_dir / name)
        template = run_cli(
            "generate-draft", "template", "--workspace", str(workspace),
            "--provider", "fixture", "--fixture-root", str(fixture_root),
            "--direction", direction, "--standard-version", "v1",
            "--template-id", template_id, "--template-version", "v1",
            "--rule-package", str(REPO_ROOT / "configuration-rules/v2"),
        )
        assert template.returncode == 0, template.stderr
        template_dir = workspace / "templates" / direction / template_id / "v1"
        assert (template_dir / "template-draft.json").is_file()

        trusted_template_dir = trusted / "templates" / direction / "v1"
        for name in ("template-final.json", "template-validation-result.json"):
            shutil.copyfile(trusted_template_dir / name, template_dir / name)

        phase0_args = [
            "--workspace", str(workspace),
            "--direction", direction,
            "--standard-version", "v1",
            "--template-id", template_id,
            "--template-version", "v1",
            "--standard-rule-package", str(REPO_ROOT / "configuration-rules/v1"),
            "--template-rule-package", str(REPO_ROOT / "configuration-rules/v2"),
        ]
        checked = run_cli("check", "--profile", "phase0", *phase0_args)
        assert checked.returncode == 0, checked.stderr

        workbook = run_cli(
            "generate-workbook",
            *phase0_args,
            "--standard-action",
            "CREATE",
        )
        assert workbook.returncode == 0, workbook.stderr
        actual_workbook = template_dir / "configuration-workbook.xlsx"
        expected_workbook = trusted_template_dir / "configuration-workbook.xlsx"
        assert workbook_snapshot(actual_workbook) == workbook_snapshot(expected_workbook)
