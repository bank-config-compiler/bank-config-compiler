from __future__ import annotations

from collections import Counter
from typing import Any


CONTRACT_VERSION = "schemair-validation-result/v1"
MESSAGE_FORMATS = {"XML", "JSON"}
FUNCTION_TYPES = {"ASSEMBLY", "PARSE"}
NODE_KINDS = {"XML_ELEMENT", "XML_ATTRIBUTE", "JSON_OBJECT", "JSON_ARRAY", "SCALAR"}
DATA_TYPES = {"string", "integer", "decimal", "boolean", "date", "datetime", "object", "array"}
EVIDENCE_KINDS = {"DIRECT", "DERIVED", "ASSUMED"}
TOP_LEVEL_REQUIRED = ("interfaceCode", "messageFormat", "envelope", "messages")
MESSAGE_REQUIRED = ("functionType", "messageName", "rootPath", "fields")
FIELD_REQUIRED = (
    "path",
    "fieldName",
    "nodeKind",
    "dataType",
    "sourceText",
    "evidence",
    "required",
    "multiple",
    "hasChildren",
    "uncertain",
    "confidence",
)
BOOLEAN_FIELDS = ("required", "multiple", "hasChildren", "uncertain")


def validate_schemair(schemair: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    _validate_top_level(schemair, issues)

    envelope_fields = _fields_from(schemair.get("envelope"))
    messages = schemair.get("messages") if isinstance(schemair.get("messages"), list) else []

    _validate_field_set(envelope_fields, issues, function_type=None)
    for message in messages:
        if not isinstance(message, dict):
            _issue(issues, "ERROR", "INVALID_MESSAGE", None, "Message must be an object.", None)
            continue
        _validate_message(message, issues)
        _validate_field_set(_fields_from(message), issues, function_type=message.get("functionType"))

    return _result(schemair, envelope_fields, messages, issues)


def _validate_top_level(schemair: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    _require(issues, TOP_LEVEL_REQUIRED, schemair, code="MISSING_TOP_LEVEL_PROPERTY")
    if schemair.get("messageFormat") not in (None, *MESSAGE_FORMATS):
        _issue(issues, "ERROR", "INVALID_MESSAGE_FORMAT", None, "messageFormat is not supported.", None)
    if "envelope" in schemair and not isinstance(schemair["envelope"], dict):
        _issue(issues, "ERROR", "INVALID_ENVELOPE", None, "envelope must be an object.", None)
    if "messages" in schemair and not isinstance(schemair["messages"], list):
        _issue(issues, "ERROR", "INVALID_MESSAGES", None, "messages must be an array.", None)


def _validate_message(message: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    function_type = message.get("functionType")
    root_path = message.get("rootPath")
    _require(
        issues,
        MESSAGE_REQUIRED,
        message,
        code="MISSING_MESSAGE_PROPERTY",
        path=root_path if isinstance(root_path, str) else None,
        function_type=function_type,
    )
    if function_type not in (None, *FUNCTION_TYPES):
        _issue(issues, "ERROR", "INVALID_FUNCTION_TYPE", root_path, "functionType is not supported.", function_type)
    if "fields" in message and not isinstance(message["fields"], list):
        _issue(issues, "ERROR", "INVALID_MESSAGE_FIELDS", root_path, "message.fields must be an array.", function_type)


def _validate_field_set(fields: list[Any], issues: list[dict[str, Any]], *, function_type: str | None) -> None:
    seen_paths: set[str] = set()
    for field in fields:
        if not isinstance(field, dict):
            _issue(issues, "ERROR", "INVALID_FIELD", None, "Field must be an object.", function_type)
            continue
        _validate_field(field, issues, function_type=function_type)

        path = field.get("path")
        if not isinstance(path, str) or not path:
            continue
        if path in seen_paths:
            _issue(issues, "ERROR", "DUPLICATE_FIELD_PATH", path, "Field path is duplicated.", function_type)
        seen_paths.add(path)


def _validate_field(field: dict[str, Any], issues: list[dict[str, Any]], *, function_type: str | None) -> None:
    path = field.get("path") if isinstance(field.get("path"), str) else None
    _require(issues, FIELD_REQUIRED, field, code="MISSING_FIELD_PROPERTY", path=path, function_type=function_type)

    for name in BOOLEAN_FIELDS:
        if name in field and not isinstance(field[name], bool):
            _issue(issues, "ERROR", "INVALID_FIELD_TYPE", path, f"{name} must be boolean.", function_type)

    _validate_enum(issues, field.get("nodeKind"), NODE_KINDS, "INVALID_NODE_KIND", path, function_type)
    _validate_enum(issues, field.get("dataType"), DATA_TYPES, "INVALID_DATA_TYPE", path, function_type)
    _validate_confidence(field, issues, path=path, function_type=function_type)
    _validate_evidence(field, issues, path=path, function_type=function_type)
    _validate_parent_path(field, issues, path=path, function_type=function_type)
    _add_review_signals(field, issues, path=path, function_type=function_type)


def _validate_enum(
    issues: list[dict[str, Any]],
    value: Any,
    allowed: set[str],
    code: str,
    path: str | None,
    function_type: str | None,
) -> None:
    if value is not None and value not in allowed:
        _issue(issues, "ERROR", code, path, f"Value must be one of {sorted(allowed)}.", function_type)


def _validate_confidence(
    field: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    path: str | None,
    function_type: str | None,
) -> None:
    confidence = field.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
        _issue(issues, "ERROR", "INVALID_CONFIDENCE", path, "confidence must be a number between 0 and 1.", function_type)


def _validate_evidence(
    field: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    path: str | None,
    function_type: str | None,
) -> None:
    evidence = field.get("evidence")
    if not isinstance(evidence, dict):
        if "evidence" in field:
            _issue(issues, "ERROR", "INVALID_EVIDENCE", path, "evidence must be an object.", function_type)
        return
    if evidence.get("kind") not in EVIDENCE_KINDS:
        _issue(issues, "ERROR", "INVALID_EVIDENCE_KIND", path, "evidence.kind is not supported.", function_type)


def _validate_parent_path(
    field: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    path: str | None,
    function_type: str | None,
) -> None:
    parent_path = field.get("parentPath")
    if isinstance(path, str) and isinstance(parent_path, str) and parent_path and not path.startswith(parent_path):
        _issue(issues, "ERROR", "INVALID_PARENT_PATH", path, "path must be explainable from parentPath.", function_type)


def _add_review_signals(
    field: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    path: str | None,
    function_type: str | None,
) -> None:
    # Review 信号不阻断 trusted chain，但需要稳定输出给 Workbook Warnings 复用。
    if field.get("uncertain") is True:
        _issue(issues, "WARNING", "UNCERTAIN_FIELD", path, "Field is marked uncertain.", function_type)

    confidence = field.get("confidence")
    if isinstance(confidence, int | float) and not isinstance(confidence, bool) and confidence < 0.9:
        _issue(issues, "WARNING", "LOW_CONFIDENCE", path, "Field confidence is below 0.9.", function_type)

    evidence = field.get("evidence")
    evidence_kind = evidence.get("kind") if isinstance(evidence, dict) else None
    if evidence_kind in EVIDENCE_KINDS and evidence_kind != "DIRECT":
        _issue(issues, "WARNING", "NON_DIRECT_EVIDENCE", path, "Field evidence is not DIRECT.", function_type)

    if field.get("conditionText"):
        _issue(issues, "INFO", "CONDITIONAL_FIELD", path, "Field has conditionText.", function_type)


def _result(schemair: dict[str, Any], envelope_fields: list[Any], messages: list[Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(issue["severity"] for issue in issues)
    error_count = counts["ERROR"]
    warning_count = counts["WARNING"]
    message_objects = [message for message in messages if isinstance(message, dict)]
    field_counts = _field_counts_by_function_type(message_objects)

    return {
        "contractVersion": CONTRACT_VERSION,
        "status": "failed" if error_count else "passed_with_warnings" if warning_count else "passed",
        "summary": {
            "interfaceCode": schemair.get("interfaceCode"),
            "messageFormat": schemair.get("messageFormat"),
            "messageCount": len(message_objects),
            "fieldCount": len(envelope_fields) + sum(field_counts.values()),
            "errorCount": error_count,
            "warningCount": warning_count,
            "infoCount": counts["INFO"],
        },
        "coverage": {
            "envelopeFieldCount": len(envelope_fields),
            "messageFieldCount": sum(field_counts.values()),
            "fieldsByFunctionType": field_counts,
        },
        "issues": issues,
    }


def _field_counts_by_function_type(messages: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for message in messages:
        function_type = message.get("functionType")
        if isinstance(function_type, str):
            counts[function_type] = counts.get(function_type, 0) + len(_fields_from(message))
    return counts


def _require(
    issues: list[dict[str, Any]],
    names: tuple[str, ...],
    container: dict[str, Any],
    *,
    code: str,
    path: str | None = None,
    function_type: Any = None,
) -> None:
    for name in names:
        if name not in container or container[name] in ("", None):
            _issue(issues, "ERROR", code, path, f"Missing property: {name}.", function_type)


def _fields_from(container: Any) -> list[Any]:
    if isinstance(container, dict) and isinstance(container.get("fields"), list):
        return container["fields"]
    return []


def _issue(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    path: str | None,
    message: str,
    function_type: Any,
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "path": path,
            "message": message,
            "functionType": function_type if isinstance(function_type, str) else None,
        }
    )
