from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .configuration_rules import RulePackage
from .configuration_workbook import validate_configuration_workbook_inputs


RAW_DOC_ARTIFACT = "raw-doc.md"
TASK_ARTIFACT = "task.json"
TASK_CONTRACT_VERSION = "phase0-task/v1"
TEXT_ARTIFACTS = {
    "raw-doc.md",
    "docir-draft.md",
    "docir-final.md",
}
RAW_PROFILE_ARTIFACTS = (TASK_ARTIFACT, RAW_DOC_ARTIFACT)
SUPPORTED_RAW_DOC_SUFFIXES = {".md", ".txt"}
UTF8_BOM = b"\xef\xbb\xbf"
VERSION_PATTERN = re.compile(r"^v[1-9]\d*$")
STABLE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorkspaceError(Exception):
    """Raised when CLI input or workspace artifacts fail validation."""


@dataclass(frozen=True, slots=True)
class Phase0Selection:
    direction: str
    standard_version: str
    template_id: str
    template_version: str

    def __post_init__(self) -> None:
        if self.direction not in {"assembly", "parse"}:
            raise WorkspaceError("phase0 direction must be exactly assembly or parse")
        if not isinstance(self.standard_version, str) or not VERSION_PATTERN.fullmatch(self.standard_version):
            raise WorkspaceError("phase0 standard_version must match v<positive integer>")
        if not isinstance(self.template_id, str) or not STABLE_ID_PATTERN.fullmatch(self.template_id):
            raise WorkspaceError("phase0 template_id must be a kebab-case stable ID")
        if not isinstance(self.template_version, str) or not VERSION_PATTERN.fullmatch(self.template_version):
            raise WorkspaceError("phase0 template_version must match v<positive integer>")


@dataclass(frozen=True, slots=True)
class Phase0Artifacts:
    schemair: dict[str, Any]
    schemair_validation_result: dict[str, Any]
    standard: dict[str, Any]
    standard_validation_result: dict[str, Any]
    template: dict[str, Any]
    template_validation_result: dict[str, Any]


def ingest_raw_doc(
    input_path: Path,
    workspace_path: Path,
    *,
    task_id: str,
    interface_code: str,
    overwrite: bool = False,
) -> Path:
    # task manifest 与 raw-doc 必须作为同一身份边界发布，避免目录名被误当成 task identity。
    input_path = input_path.resolve()
    workspace_path = workspace_path.resolve()

    raw_doc = read_raw_input(input_path)
    _stable_id(task_id, label="task_id")
    _interface_code(interface_code)
    ensure_workspace_dir(workspace_path)
    raw_bytes = raw_doc.encode("utf-8")
    manifest = {
        "contractVersion": TASK_CONTRACT_VERSION,
        "taskId": task_id,
        "interfaceCode": interface_code,
        "messageFormat": "XML",
        "sourceDocument": RAW_DOC_ARTIFACT,
        "sourceHash": _bytes_hash(raw_bytes),
    }
    outputs = {
        "raw": artifact_path(workspace_path, RAW_DOC_ARTIFACT),
        "task": artifact_path(workspace_path, TASK_ARTIFACT),
    }
    payloads = {
        "raw": raw_bytes,
        "task": _json_bytes(manifest),
    }
    _atomic_write_set(outputs, payloads, overwrite=overwrite, label="workspace input")
    return outputs["raw"]


def load_task_manifest(workspace_path: Path) -> dict[str, Any]:
    manifest = read_json_artifact(workspace_path, TASK_ARTIFACT)
    required = {
        "contractVersion",
        "taskId",
        "interfaceCode",
        "messageFormat",
        "sourceDocument",
        "sourceHash",
    }
    if set(manifest) != required:
        raise WorkspaceError("task.json must contain the exact phase0-task/v1 properties")
    if manifest.get("contractVersion") != TASK_CONTRACT_VERSION:
        raise WorkspaceError(f"task.json contractVersion must be {TASK_CONTRACT_VERSION}")
    _stable_id(manifest.get("taskId"), label="task.json taskId")
    _interface_code(manifest.get("interfaceCode"))
    if manifest.get("messageFormat") != "XML":
        raise WorkspaceError("task.json messageFormat must be XML")
    if manifest.get("sourceDocument") != RAW_DOC_ARTIFACT:
        raise WorkspaceError("task.json sourceDocument must be raw-doc.md")
    source_hash = manifest.get("sourceHash")
    if not isinstance(source_hash, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", source_hash):
        raise WorkspaceError("task.json sourceHash must be a SHA-256 hash")
    actual_hash = _bytes_hash(read_artifact_bytes(workspace_path, RAW_DOC_ARTIFACT))
    if source_hash != actual_hash:
        raise WorkspaceError("task.json sourceHash does not match raw-doc.md")
    return manifest


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


def check_workspace(
    workspace_path: Path,
    *,
    profile: str,
    selection: Phase0Selection | None = None,
    standard_rule_package: RulePackage | None = None,
    template_rule_package: RulePackage | None = None,
) -> int:
    workspace_path = workspace_path.resolve()
    _require_existing_workspace(workspace_path)

    if profile == "raw":
        load_task_manifest(workspace_path)
        return len(RAW_PROFILE_ARTIFACTS)
    if profile == "phase0":
        if selection is None:
            raise WorkspaceError("phase0 profile requires an explicit selection")
        if not isinstance(standard_rule_package, RulePackage) or not isinstance(
            template_rule_package, RulePackage
        ):
            raise WorkspaceError(
                "phase0 profile requires validated Standard and Template rule packages"
            )
        artifacts = load_phase0_artifacts(workspace_path, selection)
        validate_configuration_workbook_inputs(
            schemair=artifacts.schemair,
            schemair_validation_result=artifacts.schemair_validation_result,
            standard=artifacts.standard,
            standard_validation_result=artifacts.standard_validation_result,
            template=artifacts.template,
            template_validation_result=artifacts.template_validation_result,
            standard_rule_package=standard_rule_package,
            template_rule_package=template_rule_package,
        )
        return 6
    raise WorkspaceError(f"unknown workspace profile: {profile}")


def artifacts_for_profile(profile: str) -> tuple[str, ...]:
    if profile == "raw":
        return RAW_PROFILE_ARTIFACTS
    raise WorkspaceError(f"unknown workspace profile: {profile}")


def load_phase0_artifacts(workspace_path: Path, selection: Phase0Selection) -> Phase0Artifacts:
    workspace_path = workspace_path.resolve()
    _require_existing_workspace(workspace_path)
    paths = _phase0_artifact_names(selection)
    artifacts = Phase0Artifacts(
        schemair=read_json_artifact(workspace_path, paths["schemair"]),
        schemair_validation_result=read_json_artifact(workspace_path, paths["schemair_validation_result"]),
        standard=read_json_artifact(workspace_path, paths["standard"]),
        standard_validation_result=read_json_artifact(workspace_path, paths["standard_validation_result"]),
        template=read_json_artifact(workspace_path, paths["template"]),
        template_validation_result=read_json_artifact(workspace_path, paths["template_validation_result"]),
    )
    expected_direction = selection.direction.upper()
    mismatches: list[str] = []
    if artifacts.standard.get("direction") != expected_direction:
        mismatches.append("standard.direction")
    if artifacts.standard.get("standardVersion") != selection.standard_version:
        mismatches.append("standard.standardVersion")
    if artifacts.template.get("direction") != expected_direction:
        mismatches.append("template.direction")
    if artifacts.template.get("templateId") != selection.template_id:
        mismatches.append("template.templateId")
    if artifacts.template.get("templateVersion") != selection.template_version:
        mismatches.append("template.templateVersion")
    if mismatches:
        raise WorkspaceError(f"phase0 selector does not match loaded artifact: {', '.join(mismatches)}")
    return artifacts


def phase0_workbook_path(workspace_path: Path, selection: Phase0Selection) -> Path:
    return artifact_path(workspace_path, _phase0_artifact_names(selection)["workbook"])


def _phase0_artifact_names(selection: Phase0Selection) -> dict[str, str]:
    standard_root = f"standards/{selection.direction}/{selection.standard_version}"
    template_root = (
        f"templates/{selection.direction}/{selection.template_id}/{selection.template_version}"
    )
    return {
        "schemair": "schemair-final.json",
        "schemair_validation_result": "schemair-validation-result.json",
        "standard": f"{standard_root}/standard-final.json",
        "standard_validation_result": f"{standard_root}/standard-validation-result.json",
        "template": f"{template_root}/template-final.json",
        "template_validation_result": f"{template_root}/template-validation-result.json",
        "workbook": f"{template_root}/configuration-workbook.xlsx",
    }


def _require_existing_workspace(workspace_path: Path) -> None:
    if not workspace_path.exists():
        raise WorkspaceError(f"workspace path does not exist: {workspace_path}")
    if not workspace_path.is_dir():
        raise WorkspaceError(f"workspace path is not a directory: {workspace_path}")


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


def _stable_id(value: Any, *, label: str) -> None:
    if not isinstance(value, str) or not STABLE_ID_PATTERN.fullmatch(value):
        raise WorkspaceError(f"{label} must be a lowercase kebab-case stable ID")


def _interface_code(value: Any) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) is None:
        raise WorkspaceError("interface_code must contain only letters, digits, dot, underscore or hyphen")


def _bytes_hash(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _json_bytes(value: dict[str, Any]) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise WorkspaceError("JSON artifact must contain only finite JSON values") from exc


def _atomic_write_set(
    outputs: dict[str, Path],
    payloads: dict[str, bytes],
    *,
    overwrite: bool,
    label: str,
) -> None:
    existing = [path for path in outputs.values() if path.exists()]
    if existing and not overwrite:
        names = ", ".join(path.name for path in existing)
        raise WorkspaceError(f"{label} already exists: {names}; pass --overwrite to replace it")
    staged: dict[str, Path] = {}
    try:
        for key, output in outputs.items():
            output.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=output.parent,
                prefix=f".{output.name}.",
                suffix=".tmp",
            )
            temporary = Path(temporary_name)
            staged[key] = temporary
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payloads[key])
                handle.flush()
                os.fsync(handle.fileno())
        for key, output in outputs.items():
            os.replace(staged[key], output)
            staged.pop(key)
    except OSError as exc:
        for temporary in staged.values():
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise WorkspaceError(f"failed to publish {label}: {type(exc).__name__}") from exc
