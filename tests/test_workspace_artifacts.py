from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from bank_config_compiler.workspace import (
    WorkspaceError,
    read_json_artifact,
    write_text_artifact,
)


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bank_config_compiler", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_check_raw_profile_passes_with_raw_doc(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text("raw doc", encoding="utf-8")

    result = run_cli("check", "--workspace", str(workspace), "--profile", "raw", cwd=Path.cwd())

    assert result.returncode == 0, result.stderr
    assert "workspace check passed" in result.stdout


def test_check_raw_profile_reports_missing_raw_doc(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = run_cli("check", "--workspace", str(workspace), "--profile", "raw", cwd=Path.cwd())

    assert result.returncode == 2
    assert "raw-doc.md" in result.stderr
    assert "missing" in result.stderr


def test_check_phase0a_profile_reports_missing_artifact(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text("raw doc", encoding="utf-8")

    result = run_cli("check", "--workspace", str(workspace), "--profile", "phase0a", cwd=Path.cwd())

    assert result.returncode == 2
    assert "docir-draft.md" in result.stderr
    assert "missing" in result.stderr


def test_check_phase0a_profile_rejects_invalid_json(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for artifact in ("raw-doc.md", "docir-draft.md", "docir-final.md"):
        (workspace / artifact).write_text("text", encoding="utf-8")
    (workspace / "schemair-draft.json").write_text("{not-json", encoding="utf-8")
    (workspace / "schemair-validation-result.json").write_text("{}", encoding="utf-8")
    (workspace / "schemair-final.json").write_text("{}", encoding="utf-8")

    result = run_cli("check", "--workspace", str(workspace), "--profile", "phase0a", cwd=Path.cwd())

    assert result.returncode == 2
    assert "schemair-draft.json" in result.stderr
    assert "valid JSON" in result.stderr


def test_check_rejects_utf8_bom_artifact(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_bytes(b"\xef\xbb\xbfraw doc")

    result = run_cli("check", "--workspace", str(workspace), "--profile", "raw", cwd=Path.cwd())

    assert result.returncode == 2
    assert "raw-doc.md" in result.stderr
    assert "UTF-8 without BOM" in result.stderr


def test_write_text_artifact_rejects_unknown_artifact(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="unknown artifact"):
        write_text_artifact(tmp_path, "unknown.md", "content")


def test_read_json_artifact_rejects_invalid_json(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "schemair-draft.json").write_text("{bad", encoding="utf-8")

    with pytest.raises(WorkspaceError, match="valid JSON"):
        read_json_artifact(workspace, "schemair-draft.json")
