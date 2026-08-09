from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from bank_config_compiler.workspace import (
    WorkspaceError,
    read_json_artifact,
    write_json_artifact,
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


def test_phase0a_profile_is_no_longer_a_cli_choice(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = run_cli("check", "--workspace", str(workspace), "--profile", "phase0a", cwd=Path.cwd())

    assert result.returncode == 2
    assert "invalid choice" in result.stderr


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


def test_read_json_artifact_rejects_duplicate_properties(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "schemair-draft.json").write_text('{"status":"DRAFT","status":"FINAL"}', encoding="utf-8")

    with pytest.raises(WorkspaceError, match="duplicate object property: status"):
        read_json_artifact(workspace, "schemair-draft.json")


@pytest.mark.parametrize("content", ["[]", "null", "true", "1"])
def test_read_json_artifact_rejects_non_object_root(tmp_path: Path, content: str) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "schemair-draft.json").write_text(content, encoding="utf-8")

    with pytest.raises(WorkspaceError, match="JSON root must be an object"):
        read_json_artifact(workspace, "schemair-draft.json")


def test_read_json_artifact_rejects_non_finite_number(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "schemair-draft.json").write_text('{"confidence":NaN}', encoding="utf-8")

    with pytest.raises(WorkspaceError, match="non-finite number"):
        read_json_artifact(workspace, "schemair-draft.json")


def test_nested_json_artifact_round_trip_is_utf8_without_bom(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    output = write_json_artifact(
        workspace,
        "standards/assembly/v1/standard-draft.json",
        {"displayName": "中文", "version": "v1"},
    )

    assert output.read_bytes().startswith(b"{")
    assert read_json_artifact(workspace, "standards/assembly/v1/standard-draft.json") == {
        "displayName": "中文",
        "version": "v1",
    }


def test_json_artifact_path_cannot_escape_workspace(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="stay within the workspace"):
        write_json_artifact(tmp_path, "../outside.json", {"value": 1})
