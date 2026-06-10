from __future__ import annotations

from pathlib import Path


RAW_DOC_ARTIFACT = "raw-doc.md"
SUPPORTED_RAW_DOC_SUFFIXES = {".md", ".txt"}
UTF8_BOM = b"\xef\xbb\xbf"


class WorkspaceError(Exception):
    """Raised when CLI input or workspace artifacts fail validation."""


def ingest_raw_doc(input_path: Path, workspace_path: Path, *, overwrite: bool = False) -> Path:
    input_path = input_path.resolve()
    workspace_path = workspace_path.resolve()

    raw_doc = read_raw_input(input_path)
    ensure_workspace_dir(workspace_path)

    output_path = workspace_path / RAW_DOC_ARTIFACT
    if output_path.exists() and not overwrite:
        raise WorkspaceError(f"{RAW_DOC_ARTIFACT} already exists; pass --overwrite to replace it")

    # 写入固定 artifact 名称，避免后续阶段依赖用户输入文件名。
    output_path.write_text(raw_doc, encoding="utf-8", newline="")
    return output_path


def read_raw_input(input_path: Path) -> str:
    if not input_path.exists():
        raise WorkspaceError(f"input file does not exist: {input_path}")
    if not input_path.is_file():
        raise WorkspaceError(f"input path is not a file: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_RAW_DOC_SUFFIXES:
        raise WorkspaceError("input file must use .md or .txt extension")

    data = input_path.read_bytes()
    if data.startswith(UTF8_BOM):
        raise WorkspaceError("input file must be UTF-8 without BOM")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceError(f"input file is not valid UTF-8: {input_path}") from exc


def ensure_workspace_dir(workspace_path: Path) -> None:
    if workspace_path.exists() and not workspace_path.is_dir():
        raise WorkspaceError(f"workspace path is not a directory: {workspace_path}")
    workspace_path.mkdir(parents=True, exist_ok=True)
