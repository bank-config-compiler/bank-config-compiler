from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bank_config_compiler", *args],
        cwd=REPO_ROOT,
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
