from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .artifact_validation import content_hash
from .configuration_rules import RulePackage
from .docir_draft import validate_docir_markdown
from .interface_standard_validator import validate_interface_standard
from .interface_template_validator import validate_interface_template
from .schemair_validator import validate_schemair
from .workspace import (
    WorkspaceError,
    artifact_path,
    ensure_workspace_dir,
    load_task_manifest,
    read_json_artifact,
)


DRAFT_APPROVAL_RESULT_CONTRACT = "draft-approval-result/v1"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_DOCIR_INTERFACE_CODE = re.compile(r"^\| Interface Code \| ([^|]*) \|", re.MULTILINE)


class DraftReviewError(Exception):
    """Raised when validation or approval cannot preserve the Draft trust boundary."""


def validate_current_draft(
    workspace_path: Path,
    artifact_kind: str,
    *,
    direction: str | None = None,
    standard_version: str | None = None,
    template_id: str | None = None,
    template_version: str | None = None,
    rule_package: RulePackage | None = None,
) -> dict[str, Any]:
    workspace = workspace_path.resolve()
    task = load_task_manifest(workspace)
    names = _review_artifact_names(
        artifact_kind,
        direction=direction,
        standard_version=standard_version,
        template_id=template_id,
        template_version=template_version,
    )
    draft_path = artifact_path(workspace, names["draft"])
    draft_bytes = _read_bytes(draft_path)
    result = _validate_draft_bytes(
        workspace,
        task,
        artifact_kind,
        draft_bytes,
        names=names,
        direction=direction,
        standard_version=standard_version,
        rule_package=rule_package,
    )
    notes = _render_validation_notes(result)
    _atomic_replace_set(
        {
            "notes": artifact_path(workspace, names["notes"]),
            # validation result 最后发布，作为 notes 与当前 Draft hash 已同步的提交标记。
            "validation": artifact_path(workspace, names["validation"]),
        },
        {
            "notes": notes.encode("utf-8"),
            "validation": _json_bytes(result),
        },
        overwrite=True,
        label=f"{artifact_kind} validation outputs",
    )
    return result


def approve_draft(
    workspace_path: Path,
    artifact_kind: str,
    *,
    reviewer: str,
    review_note: str,
    expected_content_hash: str,
    reviewed_at: datetime | None = None,
    direction: str | None = None,
    standard_version: str | None = None,
    template_id: str | None = None,
    template_version: str | None = None,
    rule_package: RulePackage | None = None,
) -> dict[str, Any]:
    reviewer = _non_empty(reviewer, label="reviewer")
    review_note = _non_empty(review_note, label="review note")
    if not isinstance(expected_content_hash, str) or not SHA256_PATTERN.fullmatch(
        expected_content_hash
    ):
        raise DraftReviewError("expected content hash must be a SHA-256 hash")
    timestamp = reviewed_at or datetime.now().astimezone()
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise DraftReviewError("reviewed_at must include a timezone")

    workspace = workspace_path.resolve()
    ensure_workspace_dir(workspace)
    names = _review_artifact_names(
        artifact_kind,
        direction=direction,
        standard_version=standard_version,
        template_id=template_id,
        template_version=template_version,
    )
    lock_path = artifact_path(workspace, names["lock"])
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise DraftReviewError(
            f"another {artifact_kind} approval is already in progress"
        ) from exc
    try:
        os.close(descriptor)
        task = load_task_manifest(workspace)
        draft_path = artifact_path(workspace, names["draft"])
        dependency_path = (
            artifact_path(workspace, names["dependency"])
            if names["dependency"]
            else None
        )
        initial_dependency_bytes = (
            _read_bytes(dependency_path) if dependency_path is not None else None
        )
        initial_bytes = _read_bytes(draft_path)
        initial_artifact = _decode_artifact(artifact_kind, initial_bytes)
        actual_hash = _artifact_hash(artifact_kind, initial_bytes, initial_artifact)
        if actual_hash != expected_content_hash:
            raise DraftReviewError(
                "current Draft does not match the expected content hash"
            )

        try:
            stored_result = read_json_artifact(
                workspace, names["validation"]
            )
        except WorkspaceError as exc:
            raise DraftReviewError(
                f"{artifact_kind} approval requires a current validation result"
            ) from exc
        validated_artifact = stored_result.get("validatedArtifact")
        stored_hash = (
            validated_artifact.get("contentHash")
            if isinstance(validated_artifact, dict)
            else None
        )
        if stored_hash != actual_hash:
            raise DraftReviewError(
                f"{artifact_kind} validation result does not match current Draft; run validate-draft again"
            )
        summary = stored_result.get("summary")
        if not isinstance(summary, dict) or summary.get("errorCount") != 0:
            raise DraftReviewError(
                f"{artifact_kind} approval requires a validation result with zero ERROR"
            )

        # 不信任磁盘上的 result 内容；发布前对锁定快照执行同一 Final Validator。
        if artifact_kind == "docir":
            final_artifact = initial_artifact
            final_bytes = initial_bytes
        else:
            final_artifact = deepcopy(initial_artifact)
            final_artifact["status"] = "FINAL"
            final_artifact["review"] = {
                "status": "APPROVED",
                "reviewer": reviewer,
                "reviewedAt": timestamp.isoformat(timespec="seconds"),
                "note": review_note,
            }
            final_bytes = _json_bytes(final_artifact)
        final_result = _validate_draft_bytes(
            workspace,
            task,
            artifact_kind,
            final_bytes,
            names=names,
            direction=direction,
            standard_version=standard_version,
            rule_package=rule_package,
        )
        if final_result["summary"]["errorCount"] != 0 or (
            artifact_kind != "docir" and final_result.get("finalEligible") is not True
        ):
            raise DraftReviewError(f"{artifact_kind} Final Validator rejected approval")

        current_bytes = _read_bytes(draft_path)
        if current_bytes != initial_bytes:
            raise DraftReviewError(f"{artifact_kind} Draft changed during approval")
        if dependency_path is not None and (
            _read_bytes(dependency_path) != initial_dependency_bytes
        ):
            raise DraftReviewError(
                f"{artifact_kind} upstream Final changed during approval"
            )

        approval = {
            "contractVersion": DRAFT_APPROVAL_RESULT_CONTRACT,
            "taskId": task["taskId"],
            "interfaceCode": task["interfaceCode"],
            "artifactKind": artifact_kind,
            "approvedDraftHash": actual_hash,
            "reviewer": reviewer,
            "reviewNote": review_note,
            "reviewedAt": timestamp.isoformat(timespec="seconds"),
            "finalArtifact": names["final"],
            "finalHash": _artifact_hash(artifact_kind, final_bytes, final_artifact),
        }
        final_path = artifact_path(workspace, names["final"])
        approval_path = artifact_path(workspace, names["approval"])
        validation_path = artifact_path(workspace, names["validation"])
        _atomic_replace_set(
            {
                "final": final_path,
                "validation": validation_path,
                # approval result 最后发布，作为 Final 与 Final validation 均已落盘的提交标记。
                "approval": approval_path,
            },
            {
                "final": final_bytes,
                "validation": _json_bytes(final_result),
                "approval": _json_bytes(approval),
            },
            overwrite=False,
            label=f"{artifact_kind} approval outputs",
            replace_existing={"validation"},
        )
        published_bytes = _read_bytes(final_path)
        published_artifact = _decode_artifact(artifact_kind, published_bytes)
        if _artifact_hash(artifact_kind, published_bytes, published_artifact) != approval[
            "finalHash"
        ]:
            raise DraftReviewError(f"published {artifact_kind} Final hash verification failed")
        return approval
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def _validate_docir_bytes(
    workspace: Path,
    task: dict[str, Any],
    draft_bytes: bytes,
) -> dict[str, Any]:
    if draft_bytes.startswith(b"\xef\xbb\xbf"):
        text = draft_bytes.decode("utf-8-sig", errors="replace")
    else:
        try:
            text = draft_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = draft_bytes.decode("utf-8", errors="replace")
    result = validate_docir_markdown(text)
    result["validatedArtifact"]["contentHash"] = _bytes_hash(draft_bytes)

    identity_match = _DOCIR_INTERFACE_CODE.search(text)
    actual_interface_code = (
        identity_match.group(1).strip() if identity_match is not None else None
    )
    if actual_interface_code != task["interfaceCode"]:
        _append_issue(
            result,
            code="DOCIR_INTERFACE_CODE_MISMATCH",
            path="Interface.Metadata[Interface Code]",
            message="DocIR Interface Code does not match locked task.json identity",
        )

    try:
        generation = read_json_artifact(workspace, "docir-generation-result.json")
    except WorkspaceError:
        _append_issue(
            result,
            code="DOCIR_GENERATION_LINEAGE_MISSING",
            path=None,
            message="DocIR Draft requires draft-generation-result/v1 lineage",
        )
    else:
        expected = {
            "contractVersion": "draft-generation-result/v1",
            "taskId": task["taskId"],
            "interfaceCode": task["interfaceCode"],
            "artifactKind": "docir",
            "sourceHash": task["sourceHash"],
        }
        mismatches = [
            key for key, expected_value in expected.items() if generation.get(key) != expected_value
        ]
        if mismatches:
            _append_issue(
                result,
                code="DOCIR_GENERATION_LINEAGE_MISMATCH",
                path=None,
                message="DocIR generation lineage mismatches: " + ", ".join(mismatches),
            )
    return result


def _validate_draft_bytes(
    workspace: Path,
    task: dict[str, Any],
    artifact_kind: str,
    draft_bytes: bytes,
    *,
    names: dict[str, str],
    direction: str | None,
    standard_version: str | None,
    rule_package: RulePackage | None,
) -> dict[str, Any]:
    if artifact_kind == "docir":
        return _validate_docir_bytes(workspace, task, draft_bytes)
    artifact = _decode_artifact(artifact_kind, draft_bytes)
    if artifact_kind == "schemair":
        result = validate_schemair(artifact)
    elif artifact_kind == "standard":
        if not isinstance(rule_package, RulePackage):
            raise DraftReviewError("standard validation requires --rule-package")
        schemair = read_json_artifact(workspace, "schemair-final.json")
        result = validate_interface_standard(
            artifact, schemair=schemair, rule_package=rule_package
        )
    elif artifact_kind == "template":
        if not isinstance(rule_package, RulePackage):
            raise DraftReviewError("template validation requires --rule-package")
        standard = read_json_artifact(workspace, names["dependency"])
        result = validate_interface_template(
            artifact, standard=standard, rule_package=rule_package
        )
    else:
        raise DraftReviewError(f"unsupported Draft kind: {artifact_kind}")
    if artifact.get("interfaceCode") != task["interfaceCode"]:
        _append_issue(
            result,
            code="LOCKED_INTERFACE_CODE_MISMATCH",
            path="interfaceCode",
            message="Draft interfaceCode does not match locked task.json identity",
        )
    if direction is not None and artifact.get("direction") != direction:
        _append_issue(
            result,
            code="LOCKED_DIRECTION_MISMATCH",
            path="direction",
            message="Draft direction does not match the selected workspace target",
        )
    if standard_version is not None and artifact_kind == "standard" and (
        artifact.get("standardVersion") != standard_version
    ):
        _append_issue(
            result,
            code="LOCKED_STANDARD_VERSION_MISMATCH",
            path="standardVersion",
            message="Draft standardVersion does not match the selected workspace target",
        )
    if artifact_kind == "template":
        expected_template_identity = {
            "templateId": (
                names["template_id"],
                "LOCKED_TEMPLATE_ID_MISMATCH",
            ),
            "templateVersion": (
                names["template_version"],
                "LOCKED_TEMPLATE_VERSION_MISMATCH",
            ),
        }
        for key, (expected_value, code) in expected_template_identity.items():
            if artifact.get(key) != expected_value:
                _append_issue(
                    result,
                    code=code,
                    path=key,
                    message=f"Draft {key} does not match the selected workspace target",
                )
    _validate_generation_lineage(
        workspace,
        task,
        result,
        names,
        artifact_kind,
        artifact,
        direction=direction,
        standard_version=standard_version,
        rule_package=rule_package,
    )
    return result


def _append_issue(
    result: dict[str, Any],
    *,
    code: str,
    path: str | None,
    message: str,
) -> None:
    result["issues"].append(
        {
            "severity": "ERROR",
            "blocking": True,
            "code": code,
            "path": path,
            "message": message,
        }
    )
    result["issues"].sort(
        key=lambda item: (item["path"] or "", item["code"], item["message"])
    )
    counts = Counter(item["severity"] for item in result["issues"])
    result["summary"].update(
        {
            "errorCount": counts["ERROR"],
            "warningCount": counts["WARNING"],
            "infoCount": counts["INFO"],
            "blockingCount": sum(1 for item in result["issues"] if item["blocking"]),
        }
    )
    result["status"] = "failed"
    result["finalEligible"] = False


def _validate_generation_lineage(
    workspace: Path,
    task: dict[str, Any],
    result: dict[str, Any],
    names: dict[str, str],
    artifact_kind: str,
    artifact: dict[str, Any],
    *,
    direction: str | None,
    standard_version: str | None,
    rule_package: RulePackage | None,
) -> None:
    try:
        generation = read_json_artifact(workspace, names["generation"])
    except WorkspaceError:
        _append_issue(
            result,
            code="DRAFT_GENERATION_LINEAGE_MISSING",
            path=None,
            message=f"{artifact_kind} Draft requires draft-generation-result/v1 lineage",
        )
        return
    expected = {
        "contractVersion": "draft-generation-result/v1",
        "taskId": task["taskId"],
        "interfaceCode": task["interfaceCode"],
        "artifactKind": artifact_kind,
        "sourceHash": _dependency_hash(workspace, names["dependency"]),
        "selectors": _expected_generation_selectors(
            artifact_kind,
            artifact,
            names=names,
            direction=direction,
            standard_version=standard_version,
            rule_package=rule_package,
        ),
    }
    mismatches = [key for key, value in expected.items() if generation.get(key) != value]
    if mismatches:
        _append_issue(
            result,
            code="DRAFT_GENERATION_LINEAGE_MISMATCH",
            path=None,
            message="Draft generation lineage mismatches: " + ", ".join(mismatches),
        )


def _dependency_hash(workspace: Path, artifact_name: str) -> str:
    dependency_bytes = _read_bytes(artifact_path(workspace, artifact_name))
    if artifact_name.endswith(".md"):
        return _bytes_hash(dependency_bytes)
    dependency = _decode_artifact("dependency", dependency_bytes)
    return content_hash(dependency)


def _expected_generation_selectors(
    artifact_kind: str,
    artifact: dict[str, Any],
    *,
    names: dict[str, str],
    direction: str | None,
    standard_version: str | None,
    rule_package: RulePackage | None,
) -> dict[str, Any]:
    if artifact_kind == "schemair":
        return {
            "schemaId": artifact.get("schemaId"),
            "schemaVersion": artifact.get("schemaVersion"),
        }
    selectors: dict[str, Any] = {
        "direction": direction,
        "standardVersion": standard_version,
        "rulePackageVersion": (
            rule_package.version if isinstance(rule_package, RulePackage) else None
        ),
    }
    if artifact_kind == "standard":
        selectors["standardId"] = artifact.get("standardId")
    else:
        selectors.update(
            {
                "templateId": names["template_id"],
                "templateVersion": names["template_version"],
            }
        )
    return selectors


def _review_artifact_names(
    artifact_kind: str,
    *,
    direction: str | None,
    standard_version: str | None,
    template_id: str | None,
    template_version: str | None,
) -> dict[str, str]:
    if artifact_kind == "docir":
        return {
            "draft": "docir-draft.md",
            "final": "docir-final.md",
            "validation": "docir-validation-result.json",
            "notes": "docir-review-notes.md",
            "generation": "docir-generation-result.json",
            "approval": "docir-approval-result.json",
            "lock": ".docir-approval.lock",
            "dependency": "",
        }
    if artifact_kind == "schemair":
        return {
            "draft": "schemair-draft.json",
            "final": "schemair-final.json",
            "validation": "schemair-validation-result.json",
            "notes": "schemair-review-notes.md",
            "generation": "schemair-generation-result.json",
            "approval": "schemair-approval-result.json",
            "lock": ".schemair-approval.lock",
            "dependency": "docir-final.md",
            "template_id": "",
            "template_version": "",
        }
    if direction not in {"ASSEMBLY", "PARSE"}:
        raise DraftReviewError(f"{artifact_kind} review requires direction")
    if not isinstance(standard_version, str) or not standard_version:
        raise DraftReviewError(f"{artifact_kind} review requires standard_version")
    direction_path = direction.lower()
    if artifact_kind == "standard":
        root = f"standards/{direction_path}/{standard_version}"
        return {
            "draft": f"{root}/standard-draft.json",
            "final": f"{root}/standard-final.json",
            "validation": f"{root}/standard-validation-result.json",
            "notes": f"{root}/standard-review-notes.md",
            "generation": f"{root}/standard-generation-result.json",
            "approval": f"{root}/standard-approval-result.json",
            "lock": f"{root}/.standard-approval.lock",
            "dependency": "schemair-final.json",
            "template_id": "",
            "template_version": "",
        }
    if artifact_kind == "template":
        if not isinstance(template_id, str) or not template_id:
            raise DraftReviewError("template review requires template_id")
        if not isinstance(template_version, str) or not template_version:
            raise DraftReviewError("template review requires template_version")
        root = f"templates/{direction_path}/{template_id}/{template_version}"
        standard_root = f"standards/{direction_path}/{standard_version}"
        return {
            "draft": f"{root}/template-draft.json",
            "final": f"{root}/template-final.json",
            "validation": f"{root}/template-validation-result.json",
            "notes": f"{root}/template-review-notes.md",
            "generation": f"{root}/template-generation-result.json",
            "approval": f"{root}/template-approval-result.json",
            "lock": f"{root}/.template-approval.lock",
            "dependency": f"{standard_root}/standard-final.json",
            "template_id": template_id,
            "template_version": template_version,
        }
    raise DraftReviewError(f"unsupported Draft kind: {artifact_kind}")


def _decode_artifact(artifact_kind: str, value: bytes) -> str | dict[str, Any]:
    if artifact_kind == "docir":
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DraftReviewError("DocIR Draft must be valid UTF-8") from exc
    try:
        artifact = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DraftReviewError(f"{artifact_kind} Draft must contain valid UTF-8 JSON") from exc
    if not isinstance(artifact, dict):
        raise DraftReviewError(f"{artifact_kind} Draft root must be an object")
    return artifact


def _artifact_hash(
    artifact_kind: str,
    raw: bytes,
    artifact: str | dict[str, Any],
) -> str:
    if artifact_kind == "docir":
        return _bytes_hash(raw)
    return content_hash(artifact)


def _render_validation_notes(result: dict[str, Any]) -> str:
    validated = result["validatedArtifact"]
    summary = result["summary"]
    parts = [
        "# Draft Validation Review Notes",
        "",
        f"Content hash: `{validated['contentHash']}`",
        "",
        f"Status: `{result['status']}`",
        "",
        (
            "Summary: "
            f"ERROR={summary['errorCount']}, WARNING={summary['warningCount']}, "
            f"INFO={summary['infoCount']}"
        ),
        "",
    ]
    if not result["issues"]:
        parts.append("Validator 未发现 ERROR 或 WARNING。Human 仍需对照 raw-doc 审查语义完整性。")
    else:
        parts.extend(["## Issues", ""])
        for item in result["issues"]:
            location = f" `{item['path']}`" if item["path"] else ""
            parts.append(
                f"- [{item['severity']}] `{item['code']}`{location}: {item['message']}"
            )
    return "\n".join(parts) + "\n"


def _atomic_replace_set(
    outputs: dict[str, Path],
    payloads: dict[str, bytes],
    *,
    overwrite: bool,
    label: str,
    replace_existing: set[str] | None = None,
) -> None:
    if set(outputs) != set(payloads):
        raise DraftReviewError(f"{label} are internally inconsistent")
    replaceable = replace_existing or set()
    existing_keys = {key for key, path in outputs.items() if path.exists()}
    existing = [
        path
        for key, path in outputs.items()
        if key in existing_keys and key not in replaceable
    ]
    if existing and not overwrite:
        raise DraftReviewError(
            f"{label} already exist: " + ", ".join(path.name for path in existing)
        )
    staged: dict[str, Path] = {}
    published: list[Path] = []
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
            published.append(output)
    except (OSError, ValueError, TypeError) as exc:
        for temporary in staged.values():
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        if not overwrite:
            for output in published:
                key = next(key for key, value in outputs.items() if value == output)
                if key in existing_keys:
                    continue
                try:
                    output.unlink(missing_ok=True)
                except OSError:
                    pass
        raise DraftReviewError(f"failed to publish {label}: {type(exc).__name__}") from exc


def _read_bytes(path: Path) -> bytes:
    try:
        if not path.is_file():
            raise DraftReviewError(f"required artifact is missing: {path.name}")
        return path.read_bytes()
    except OSError as exc:
        raise DraftReviewError(
            f"failed to read {path.name}: {type(exc).__name__}"
        ) from exc


def _json_bytes(value: dict[str, Any]) -> bytes:
    try:
        return (
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DraftReviewError("review result must contain finite JSON values") from exc


def _bytes_hash(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _non_empty(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DraftReviewError(f"{label} must be non-empty")
    return value.strip()
