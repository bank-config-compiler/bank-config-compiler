from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bank_config_compiler", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def ingest_args(input_file: Path, workspace: Path) -> tuple[str, ...]:
    return (
        "ingest",
        "--input",
        str(input_file),
        "--workspace",
        str(workspace),
        "--task-id",
        "phase0-ingest-test",
        "--interface-code",
        "b2e0061",
    )


def test_ingest_writes_markdown_raw_doc(tmp_path: Path) -> None:
    input_file = tmp_path / "input.md"
    input_file.write_text("# Bank Doc\n\nField A", encoding="utf-8")
    workspace = tmp_path / "workspace"

    result = run_cli(*ingest_args(input_file, workspace), cwd=Path.cwd())

    assert result.returncode == 0, result.stderr
    assert (workspace / "raw-doc.md").read_text(encoding="utf-8") == "# Bank Doc\n\nField A"
    assert (workspace / "task.json").is_file()


def test_ingest_writes_text_raw_doc(tmp_path: Path) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("plain bank doc", encoding="utf-8")
    workspace = tmp_path / "workspace"

    result = run_cli(*ingest_args(input_file, workspace), cwd=Path.cwd())

    assert result.returncode == 0, result.stderr
    assert (workspace / "raw-doc.md").read_text(encoding="utf-8") == "plain bank doc"


def test_ingest_rejects_unsupported_extension(tmp_path: Path) -> None:
    input_file = tmp_path / "input.pdf"
    input_file.write_text("not supported", encoding="utf-8")
    workspace = tmp_path / "workspace"

    result = run_cli(*ingest_args(input_file, workspace), cwd=Path.cwd())

    assert result.returncode == 2
    assert ".md or .txt" in result.stderr


def test_ingest_rejects_missing_input(tmp_path: Path) -> None:
    result = run_cli(
        *ingest_args(tmp_path / "missing.md", tmp_path / "workspace"),
        cwd=Path.cwd(),
    )

    assert result.returncode == 2
    assert "input file does not exist" in result.stderr


def test_ingest_does_not_overwrite_without_flag(tmp_path: Path) -> None:
    input_file = tmp_path / "input.md"
    input_file.write_text("new doc", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text("existing doc", encoding="utf-8")

    result = run_cli(*ingest_args(input_file, workspace), cwd=Path.cwd())

    assert result.returncode == 2
    assert "already exists" in result.stderr
    assert (workspace / "raw-doc.md").read_text(encoding="utf-8") == "existing doc"


def test_ingest_overwrites_with_flag(tmp_path: Path) -> None:
    input_file = tmp_path / "input.md"
    input_file.write_text("new doc", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "raw-doc.md").write_text("existing doc", encoding="utf-8")

    result = run_cli(
        *ingest_args(input_file, workspace),
        "--overwrite",
        cwd=Path.cwd(),
    )

    assert result.returncode == 0, result.stderr
    assert (workspace / "raw-doc.md").read_text(encoding="utf-8") == "new doc"
