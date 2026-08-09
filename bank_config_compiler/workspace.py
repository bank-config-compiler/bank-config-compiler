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
RAW_PROFILE_ARTIFACTS = (RAW_DOC_ARTIFACT,)
SUPPORTED_RAW_DOC_SUFFIXES = {".md", ".txt"}
UTF8_BOM = b"\xef\xbb\xbf"


class WorkspaceError(Exception):
    """Raised when CLI input or workspace artifacts fail validation."""


def ingest_raw_doc(input_path: Path, workspace_path: Path, *, overwrite: bool = False) -> Path:
    # 只导入原始文档，避免把后续 DocIR / SchemaIR 生成语义混入 ingest。
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
        read_text_artifact(workspace_path, artifact_name)
    return len(artifacts)


def artifacts_for_profile(profile: str) -> tuple[str, ...]:
    if profile == "raw":
        return RAW_PROFILE_ARTIFACTS
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


def read_json_artifact(workspace_path: Path, artifact_name: str) -> dict[str, Any]:
    if Path(artifact_name).suffix.lower() != ".json":
        raise WorkspaceError("JSON artifact path must use the .json extension")
    data = read_artifact_bytes(workspace_path, artifact_name)
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_non_finite_json_number,
        )
    except UnicodeDecodeError as exc:
        raise WorkspaceError(f"{artifact_name} must be valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"{artifact_name} must contain valid JSON") from exc
    except ValueError as exc:
        raise WorkspaceError(f"{artifact_name} must contain strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkspaceError(f"{artifact_name} JSON root must be an object")
    return value


def write_json_artifact(
    workspace_path: Path,
    artifact_name: str,
    content: dict[str, Any],
    *,
    overwrite: bool = False,
) -> Path:
    if Path(artifact_name).suffix.lower() != ".json":
        raise WorkspaceError("JSON artifact path must use the .json extension")
    ensure_workspace_dir(workspace_path)
    output_path = artifact_path(workspace_path, artifact_name)
    if output_path.exists() and not overwrite:
        raise WorkspaceError(f"{artifact_name} already exists; pass overwrite=True to replace it")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        serialized = json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise WorkspaceError("JSON artifact must contain only finite JSON values") from exc
    output_path.write_text(f"{serialized}\n", encoding="utf-8", newline="")
    return output_path


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
    relative_path = Path(artifact_name)
    if relative_path.is_absolute() or not relative_path.parts or ".." in relative_path.parts:
        raise WorkspaceError(f"artifact path must stay within the workspace: {artifact_name}")
    workspace_root = workspace_path.resolve()
    output_path = (workspace_root / relative_path).resolve()
    try:
        output_path.relative_to(workspace_root)
    except ValueError as exc:
        raise WorkspaceError(f"artifact path must stay within the workspace: {artifact_name}") from exc
    return output_path


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object property: {key}")
        result[key] = value
    return result


def _reject_non_finite_json_number(value: str) -> None:
    raise ValueError(f"non-finite number is not allowed: {value}")
