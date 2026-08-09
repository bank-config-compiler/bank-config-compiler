from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Iterable, Mapping, TypedDict


SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2}


class ArtifactIntegrityError(ValueError):
    """Raised when a value cannot participate in the trusted-chain hash contract."""


class ValidationIssue(TypedDict):
    severity: str
    blocking: bool
    code: str
    path: str | None
    message: str


def canonical_json_bytes(value: object) -> bytes:
    """Return the only JSON representation used for trusted-chain content hashes."""

    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ArtifactIntegrityError("artifact must contain only finite JSON values") from exc
    return serialized.encode("utf-8")


def content_hash(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


def issue(
    issues: list[ValidationIssue],
    severity: str,
    code: str,
    path: str | None,
    message: str,
    *,
    blocking: bool | None = None,
) -> None:
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"unknown validation issue severity: {severity}")
    issues.append(
        {
            "severity": severity,
            "blocking": severity == "ERROR" if blocking is None else blocking,
            "code": code,
            "path": path,
            "message": message,
        }
    )


def build_validation_result(
    artifact: object,
    *,
    result_contract_version: str,
    artifact_kind: str,
    artifact_id_field: str,
    artifact_version_field: str,
    issues: Iterable[ValidationIssue],
    summary: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> dict[str, Any]:
    ordered_issues = sorted(
        issues,
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]],
            item["path"] or "",
            item["code"],
            item["message"],
        ),
    )
    counts = Counter(item["severity"] for item in ordered_issues)
    artifact_object = artifact if isinstance(artifact, Mapping) else {}
    review = artifact_object.get("review")
    review_status = review.get("status") if isinstance(review, Mapping) else None
    final_eligible = (
        artifact_object.get("status") == "FINAL"
        and review_status == "APPROVED"
        and not any(item["severity"] == "ERROR" for item in ordered_issues)
        and not any(item["blocking"] for item in ordered_issues)
    )

    error_count = counts["ERROR"]
    warning_count = counts["WARNING"]
    result_status = "failed" if error_count else "passed_with_warnings" if warning_count else "passed"

    return {
        "contractVersion": result_contract_version,
        "validatedArtifact": {
            "kind": artifact_kind,
            "artifactId": artifact_object.get(artifact_id_field),
            "artifactVersion": artifact_object.get(artifact_version_field),
            "artifactContractVersion": artifact_object.get("contractVersion"),
            "contentHash": content_hash(artifact),
        },
        "status": result_status,
        "finalEligible": final_eligible,
        "summary": {
            **summary,
            "errorCount": error_count,
            "warningCount": warning_count,
            "infoCount": counts["INFO"],
            "blockingCount": sum(1 for item in ordered_issues if item["blocking"]),
        },
        "coverage": dict(coverage),
        "issues": ordered_issues,
    }
