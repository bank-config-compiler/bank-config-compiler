from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


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


def test_generate_draft_cli_runs_six_controlled_b2e0061_calls(tmp_path: Path) -> None:
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

    # 仅在临时测试 workspace 模拟已完成 Human gate 的输入；生产命令不会自动执行此提升。
    shutil.copyfile(workspace / "docir-draft.md", workspace / "docir-final.md")
    schemair = run_cli(
        "generate-draft", "schemair", "--workspace", str(workspace),
        "--provider", "fixture", "--fixture-root", str(fixture_root),
    )
    assert schemair.returncode == 0, schemair.stderr

    trusted = REPO_ROOT / "samples/trusted-chain/b2eboc-b2e0061"
    shutil.copyfile(trusted / "schemair-final.json", workspace / "schemair-final.json")
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
        shutil.copyfile(
            trusted / "standards" / direction / "v1" / "standard-final.json",
            standard_dir / "standard-final.json",
        )
        template = run_cli(
            "generate-draft", "template", "--workspace", str(workspace),
            "--provider", "fixture", "--fixture-root", str(fixture_root),
            "--direction", direction, "--standard-version", "v1",
            "--template-id", template_id, "--template-version", "v1",
            "--rule-package", str(REPO_ROOT / "configuration-rules/v2"),
        )
        assert template.returncode == 0, template.stderr
        assert (workspace / "templates" / direction / template_id / "v1" / "template-draft.json").is_file()
