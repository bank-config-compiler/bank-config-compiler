from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RAW_DOC_ARTIFACT = "raw-doc.md"
TEXT_ARTIFACTS = {
    "raw-doc.md",
    "docir-draft.md",
    "docir-final.md",
}
JSON_ARTIFACTS = {
    "schemair-draft.json",
    "schemair-validation-result.json",
    "schemair-final.json",
}
PHASE0A_ARTIFACTS = (
    "raw-doc.md",
    "docir-draft.md",
    "docir-final.md",
    "schemair-draft.json",
    "schemair-validation-result.json",
    "schemair-final.json",
)
RAW_PROFILE_ARTIFACTS = (RAW_DOC_ARTIFACT,)
KNOWN_ARTIFACTS = TEXT_ARTIFACTS | JSON_ARTIFACTS
SUPPORTED_RAW_DOC_SUFFIXES = {".md", ".txt"}
UTF8_BOM = b"\xef\xbb\xbf"


class WorkspaceError(Exception):
    """Raised when CLI input or workspace artifacts fail validation."""


def ingest_raw_doc(input_path: Path, workspace_path: Path, *, overwrite: bool = False) -> Path:
    input_path = input_path.resolve()
    workspace_path = workspace_path.resolve()

    raw_doc = read_raw_input(input_path)
    ensure_workspace_dir(workspace_path)

    output_path = artifact_path(workspace_path, RAW_DOC_ARTIFACT)
    if output_path.exists() and not overwrite:
        raise WorkspaceError(f"{RAW_DOC_ARTIFACT} already exists; pass --overwrite to replace it")

    return write_text_artifact(workspace_path, RAW_DOC_ARTIFACT, raw_doc)


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


def check_workspace(workspace_path: Path, *, profile: str) -> int:
    workspace_path = workspace_path.resolve()
    if not workspace_path.exists():
        raise WorkspaceError(f"workspace path does not exist: {workspace_path}")
    if not workspace_path.is_dir():
        raise WorkspaceError(f"workspace path is not a directory: {workspace_path}")

    artifacts = artifacts_for_profile(profile)
    for artifact_name in artifacts:
        if artifact_name in JSON_ARTIFACTS:
            read_json_artifact(workspace_path, artifact_name)
        else:
            read_text_artifact(workspace_path, artifact_name)
    return len(artifacts)


def artifacts_for_profile(profile: str) -> tuple[str, ...]:
    if profile == "raw":
        return RAW_PROFILE_ARTIFACTS
    if profile == "phase0a":
        return PHASE0A_ARTIFACTS
    raise WorkspaceError(f"unknown workspace profile: {profile}")


def write_text_artifact(workspace_path: Path, artifact_name: str, content: str) -> Path:
    if artifact_name not in TEXT_ARTIFACTS:
        raise WorkspaceError(f"unknown artifact: {artifact_name}")
    ensure_workspace_dir(workspace_path)
    output_path = artifact_path(workspace_path, artifact_name)
    # 写入固定 artifact 名称，避免后续阶段依赖用户输入文件名。
    output_path.write_text(content, encoding="utf-8", newline="")
    return output_path


def read_text_artifact(workspace_path: Path, artifact_name: str) -> str:
    if artifact_name not in TEXT_ARTIFACTS:
        raise WorkspaceError(f"unknown artifact: {artifact_name}")
    data = read_artifact_bytes(workspace_path, artifact_name)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceError(f"{artifact_name} must be valid UTF-8") from exc


def read_json_artifact(workspace_path: Path, artifact_name: str) -> Any:
    if artifact_name not in JSON_ARTIFACTS:
        raise WorkspaceError(f"unknown artifact: {artifact_name}")
    data = read_artifact_bytes(workspace_path, artifact_name)
    try:
        return json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise WorkspaceError(f"{artifact_name} must be valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"{artifact_name} must contain valid JSON") from exc


def read_artifact_bytes(workspace_path: Path, artifact_name: str) -> bytes:
    path = artifact_path(workspace_path, artifact_name)
    if not path.exists():
        raise WorkspaceError(f"{artifact_name} is missing")
    if not path.is_file():
        raise WorkspaceError(f"{artifact_name} is not a file")
    data = path.read_bytes()
    if data.startswith(UTF8_BOM):
        raise WorkspaceError(f"{artifact_name} must be UTF-8 without BOM")
    return data


def artifact_path(workspace_path: Path, artifact_name: str) -> Path:
    if artifact_name not in KNOWN_ARTIFACTS:
        raise WorkspaceError(f"unknown artifact: {artifact_name}")
    return workspace_path.resolve() / artifact_name
