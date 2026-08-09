from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Mapping

from .artifact_validation import ValidationIssue, build_validation_result, issue


LOGGER = logging.getLogger(__name__)

SCHEMAIR_CONTRACT_VERSION = "schemair/v2"
RESULT_CONTRACT_VERSION = "schemair-validation-result/v2"
FUNCTION_TYPES = {"ASSEMBLY", "PARSE"}
NODE_KINDS = {"XML_ELEMENT", "XML_ATTRIBUTE", "SCALAR"}
DATA_TYPES = {"string", "integer", "decimal", "boolean", "date", "datetime", "object", "array"}
EVIDENCE_KINDS = {"DIRECT", "DERIVED", "ASSUMED"}
ARTIFACT_STATUSES = {"DRAFT", "FINAL"}
REVIEW_STATUSES = {"PENDING", "APPROVED"}
ENCODING_SOURCE_KINDS = {"HUMAN_BANK_CONFIRMATION", "SOURCE_DOCUMENT", "XML_DECLARATION"}
ENCODING_DISPOSITIONS = {"SUPPORTS", "UNRESOLVED_CONFLICT", "RESOLVED_CONFLICT"}
CONDITION_OPERATORS = {"EQUALS", "IS_EMPTY"}
CONDITION_EFFECTS = {"REQUIRED"}

TOP_LEVEL_PROPERTIES = {
    "contractVersion",
    "schemaId",
    "schemaVersion",
    "status",
    "review",
    "interfaceCode",
    "interfaceName",
    "messageFormat",
    "protocolVersion",
    "sourceDocument",
    "envelope",
    "messages",
}
ENVELOPE_PROPERTIES = {"rootPath", "description", "fields"}
MESSAGE_PROPERTIES = {
    "functionType",
    "messageName",
    "rootPath",
    "xmlEncoding",
    "xmlEncodingEvidence",
    "description",
    "fields",
    "conditionalConstraints",
}
FIELD_PROPERTIES = {
    "path",
    "fieldName",
    "displayName",
    "parentPath",
    "level",
    "nodeKind",
    "dataType",
    "format",
    "length",
    "required",
    "multiple",
    "hasChildren",
    "occurs",
    "description",
    "conditionText",
    "sourceText",
    "evidence",
    "confidence",
    "uncertain",
    "uncertainReason",
    "reviewNote",
}
LENGTH_PROPERTIES = {"min", "max", "raw"}
EVIDENCE_PROPERTIES = {"kind", "note"}
REVIEW_PROPERTIES = {"status", "reviewer", "reviewedAt", "note"}
ENCODING_EVIDENCE_PROPERTIES = {"sourceKind", "sourceRef", "observedValue", "disposition", "reviewNote"}
CONDITION_PROPERTIES = {
    "controllingFieldPath",
    "operator",
    "literal",
    "targetFieldPath",
    "effect",
    "sourceText",
    "evidence",
    "review",
}
OCCURS_PATTERN = re.compile(r"^(0|[1-9]\d*)\.\.(1|[1-9]\d*|n)$")


def validate_schemair(schemair: object) -> dict[str, Any]:
    schema_id = schemair.get("schemaId") if isinstance(schemair, Mapping) else None
    LOGGER.debug(
        "Validating SchemaIR",
        extra={"component": "schemair_validator", "artifact_id": schema_id, "outcome": "started"},
    )

    issues: list[ValidationIssue] = []
    if not isinstance(schemair, dict):
        issue(issues, "ERROR", "INVALID_SCHEMAIR_ROOT", None, "SchemaIR root must be an object.")
        result = _result(schemair, [], [], issues)
        _log_result(result)
        return result

    _validate_top_level(schemair, issues)
    _validate_lifecycle(schemair, issues)

    envelope = schemair.get("envelope")
    envelope_fields = _fields_from(envelope)
    if isinstance(envelope, dict):
        _validate_envelope(envelope, issues)

    messages_value = schemair.get("messages")
    messages = messages_value if isinstance(messages_value, list) else []

    message_parent_paths = [
        field.get("parentPath")
        for message in messages
        if isinstance(message, dict)
        for field in _fields_from(message)
        if isinstance(field, dict) and isinstance(field.get("parentPath"), str)
    ]
    envelope_paths = _validate_field_set(
        envelope_fields,
        issues,
        function_type=None,
        inherited_paths={"Root"},
        additional_child_parents=message_parent_paths,
    )
    if isinstance(envelope, dict):
        envelope_root = envelope.get("rootPath")
        if isinstance(envelope_root, str) and envelope_root not in envelope_paths:
            issue(
                issues,
                "ERROR",
                "UNKNOWN_ENVELOPE_ROOT",
                "envelope.rootPath",
                "envelope.rootPath must reference an envelope field.",
            )
    seen_function_types: set[str] = set()
    for index, message in enumerate(messages):
        message_path = f"messages[{index}]"
        if not isinstance(message, dict):
            issue(issues, "ERROR", "INVALID_MESSAGE", message_path, "Message must be an object.")
            continue
        function_type = message.get("functionType")
        if isinstance(function_type, str):
            if function_type in seen_function_types:
                issue(
                    issues,
                    "ERROR",
                    "DUPLICATE_FUNCTION_TYPE",
                    message_path,
                    "Each direction may appear only once in SchemaIR messages.",
                )
            seen_function_types.add(function_type)
        _validate_message(message, issues, path=message_path)
        message_paths = _validate_field_set(
            _fields_from(message),
            issues,
            function_type=function_type if isinstance(function_type, str) else None,
            inherited_paths=envelope_paths | {"Root"},
        )
        _validate_message_root(message, message_paths, issues, path=message_path)
        _validate_xml_encoding(message, schemair, issues, path=message_path)
        _validate_conditions(
            message,
            schemair,
            envelope_paths | message_paths,
            issues,
            path=message_path,
        )

    result = _result(schemair, envelope_fields, messages, issues)
    _log_result(result)
    return result


def _validate_top_level(schemair: dict[str, Any], issues: list[ValidationIssue]) -> None:
    _object_contract(
        schemair,
        TOP_LEVEL_PROPERTIES,
        TOP_LEVEL_PROPERTIES,
        issues,
        path=None,
        missing_code="MISSING_TOP_LEVEL_PROPERTY",
        unknown_code="UNKNOWN_TOP_LEVEL_PROPERTY",
    )
    _enum(schemair.get("contractVersion"), {SCHEMAIR_CONTRACT_VERSION}, issues, "INVALID_CONTRACT_VERSION", "contractVersion")
    _stable_id(schemair.get("schemaId"), issues, "INVALID_SCHEMA_ID", "schemaId")
    _version(schemair.get("schemaVersion"), issues, "INVALID_SCHEMA_VERSION", "schemaVersion")
    _enum(schemair.get("status"), ARTIFACT_STATUSES, issues, "INVALID_ARTIFACT_STATUS", "status")
    _required_string(schemair.get("interfaceCode"), issues, "INVALID_INTERFACE_CODE", "interfaceCode")
    _required_string(schemair.get("interfaceName"), issues, "INVALID_INTERFACE_NAME", "interfaceName")
    _enum(schemair.get("messageFormat"), {"XML"}, issues, "INVALID_MESSAGE_FORMAT", "messageFormat")
    _required_string(schemair.get("protocolVersion"), issues, "INVALID_PROTOCOL_VERSION", "protocolVersion")
    _required_string(schemair.get("sourceDocument"), issues, "INVALID_SOURCE_DOCUMENT", "sourceDocument")
    if "envelope" in schemair and not isinstance(schemair["envelope"], dict):
        issue(issues, "ERROR", "INVALID_ENVELOPE", "envelope", "envelope must be an object.")
    if "messages" in schemair:
        if not isinstance(schemair["messages"], list):
            issue(issues, "ERROR", "INVALID_MESSAGES", "messages", "messages must be an array.")
        elif not schemair["messages"]:
            issue(issues, "ERROR", "EMPTY_MESSAGES", "messages", "messages must contain at least one direction.")


def _validate_lifecycle(schemair: dict[str, Any], issues: list[ValidationIssue]) -> None:
    review = schemair.get("review")
    if not isinstance(review, dict):
        if "review" in schemair:
            issue(issues, "ERROR", "INVALID_REVIEW", "review", "review must be an object.")
        return
    _validate_review(review, issues, path="review")

    status = schemair.get("status")
    review_status = review.get("status")
    if status == "DRAFT":
        issue(
            issues,
            "WARNING",
            "ARTIFACT_NOT_FINAL",
            "status",
            "Draft artifacts are not eligible for the trusted chain.",
            blocking=True,
        )
    if review_status != "APPROVED":
        issue(
            issues,
            "WARNING",
            "REVIEW_NOT_APPROVED",
            "review.status",
            "Human Review must be approved before Final use.",
            blocking=True,
        )
    if status == "FINAL" and review_status != "APPROVED":
        issue(
            issues,
            "ERROR",
            "FINAL_REQUIRES_APPROVED_REVIEW",
            "review.status",
            "FINAL status requires an approved Human Review.",
        )


def _validate_review(review: dict[str, Any], issues: list[ValidationIssue], *, path: str) -> None:
    _object_contract(
        review,
        REVIEW_PROPERTIES,
        REVIEW_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_REVIEW_PROPERTY",
        unknown_code="UNKNOWN_REVIEW_PROPERTY",
    )
    status = review.get("status")
    _enum(status, REVIEW_STATUSES, issues, "INVALID_REVIEW_STATUS", f"{path}.status")
    reviewer = review.get("reviewer")
    reviewed_at = review.get("reviewedAt")
    note = review.get("note")
    if note is not None and not isinstance(note, str):
        issue(issues, "ERROR", "INVALID_REVIEW_NOTE", f"{path}.note", "review.note must be a string or null.")
    if status == "PENDING":
        if reviewer is not None or reviewed_at is not None:
            issue(
                issues,
                "ERROR",
                "PENDING_REVIEW_HAS_APPROVAL",
                path,
                "Pending review cannot carry reviewer or reviewedAt values.",
            )
        return
    if status == "APPROVED":
        _required_string(reviewer, issues, "INVALID_REVIEWER", f"{path}.reviewer")
        if not isinstance(reviewed_at, str) or not _is_offset_datetime(reviewed_at):
            issue(
                issues,
                "ERROR",
                "INVALID_REVIEWED_AT",
                f"{path}.reviewedAt",
                "reviewedAt must be an RFC 3339 timestamp with a timezone offset.",
            )


def _validate_envelope(envelope: dict[str, Any], issues: list[ValidationIssue]) -> None:
    _object_contract(
        envelope,
        ENVELOPE_PROPERTIES,
        ENVELOPE_PROPERTIES,
        issues,
        path="envelope",
        missing_code="MISSING_ENVELOPE_PROPERTY",
        unknown_code="UNKNOWN_ENVELOPE_PROPERTY",
    )
    _required_string(envelope.get("rootPath"), issues, "INVALID_ENVELOPE_ROOT_PATH", "envelope.rootPath")
    _required_string(envelope.get("description"), issues, "INVALID_ENVELOPE_DESCRIPTION", "envelope.description")
    if "fields" in envelope and not isinstance(envelope["fields"], list):
        issue(issues, "ERROR", "INVALID_ENVELOPE_FIELDS", "envelope.fields", "envelope.fields must be an array.")


def _validate_message(message: dict[str, Any], issues: list[ValidationIssue], *, path: str) -> None:
    _object_contract(
        message,
        MESSAGE_PROPERTIES,
        MESSAGE_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_MESSAGE_PROPERTY",
        unknown_code="UNKNOWN_MESSAGE_PROPERTY",
    )
    _enum(message.get("functionType"), FUNCTION_TYPES, issues, "INVALID_FUNCTION_TYPE", f"{path}.functionType")
    _required_string(message.get("messageName"), issues, "INVALID_MESSAGE_NAME", f"{path}.messageName")
    _required_string(message.get("rootPath"), issues, "INVALID_MESSAGE_ROOT_PATH", f"{path}.rootPath")
    _required_string(message.get("description"), issues, "INVALID_MESSAGE_DESCRIPTION", f"{path}.description")
    for name in ("fields", "xmlEncodingEvidence", "conditionalConstraints"):
        if name in message and not isinstance(message[name], list):
            issue(issues, "ERROR", "INVALID_MESSAGE_ARRAY", f"{path}.{name}", f"message.{name} must be an array.")


def _validate_message_root(
    message: dict[str, Any],
    message_paths: set[str],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    root_path = message.get("rootPath")
    if isinstance(root_path, str) and root_path not in message_paths:
        issue(
            issues,
            "ERROR",
            "UNKNOWN_MESSAGE_ROOT",
            f"{path}.rootPath",
            "message.rootPath must reference a field in the same message.",
        )


def _validate_field_set(
    fields: list[Any],
    issues: list[ValidationIssue],
    *,
    function_type: str | None,
    inherited_paths: set[str],
    additional_child_parents: list[str] | None = None,
) -> set[str]:
    seen_paths: set[str] = set()
    field_objects: list[dict[str, Any]] = []
    for index, field in enumerate(fields):
        fallback_path = f"{function_type or 'envelope'}.fields[{index}]"
        if not isinstance(field, dict):
            issue(issues, "ERROR", "INVALID_FIELD", fallback_path, "Field must be an object.")
            continue
        field_objects.append(field)
        field_path = field.get("path")
        if isinstance(field_path, str) and field_path:
            if field_path in inherited_paths:
                issue(
                    issues,
                    "ERROR",
                    "FIELD_PATH_SHADOWS_PARENT_SCOPE",
                    field_path,
                    "Field path must not redefine a field from its parent scope.",
                )
            if field_path in seen_paths:
                issue(issues, "ERROR", "DUPLICATE_FIELD_PATH", field_path, "Field path is duplicated.")
            seen_paths.add(field_path)

    available_paths = inherited_paths | seen_paths
    child_counts = Counter(
        field.get("parentPath") for field in field_objects if isinstance(field.get("parentPath"), str)
    )
    child_counts.update(additional_child_parents or [])
    for index, field in enumerate(field_objects):
        path = field.get("path") if isinstance(field.get("path"), str) and field.get("path") else f"{function_type or 'envelope'}.fields[{index}]"
        _validate_field(field, available_paths, child_counts, issues, path=path)
    return seen_paths


def _validate_field(
    field: dict[str, Any],
    available_paths: set[str],
    child_counts: Counter[Any],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    _object_contract(
        field,
        FIELD_PROPERTIES,
        FIELD_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_FIELD_PROPERTY",
        unknown_code="UNKNOWN_FIELD_PROPERTY",
    )
    field_path = field.get("path")
    field_name = field.get("fieldName")
    parent_path = field.get("parentPath")
    _required_string(field_path, issues, "INVALID_FIELD_PATH", path)
    _required_string(field_name, issues, "INVALID_FIELD_NAME", f"{path}.fieldName")
    _required_string(field.get("displayName"), issues, "INVALID_DISPLAY_NAME", f"{path}.displayName")
    _required_string(parent_path, issues, "INVALID_PARENT_PATH", f"{path}.parentPath")
    _required_string(field.get("description"), issues, "INVALID_FIELD_DESCRIPTION", f"{path}.description")
    _required_string(field.get("sourceText"), issues, "INVALID_SOURCE_TEXT", f"{path}.sourceText")

    if isinstance(field_path, str) and isinstance(parent_path, str):
        expected_parent, separator, last_segment = field_path.rpartition(".")
        if not separator or expected_parent != parent_path:
            issue(issues, "ERROR", "INVALID_PARENT_PATH", path, "parentPath must be the direct parent of path.")
        if parent_path not in available_paths:
            issue(issues, "ERROR", "UNKNOWN_PARENT_PATH", path, "parentPath must reference an existing parent field.")
        expected_name = last_segment
        if isinstance(field_name, str) and field_name != expected_name:
            issue(issues, "ERROR", "FIELD_NAME_PATH_MISMATCH", path, "fieldName must match the final path segment.")

        level = field.get("level")
        expected_level = field_path.count(".")
        if isinstance(level, bool) or not isinstance(level, int) or level != expected_level:
            issue(issues, "ERROR", "INVALID_FIELD_LEVEL", path, "level must equal the path depth below Root.")
    elif "level" in field and (isinstance(field["level"], bool) or not isinstance(field["level"], int)):
        issue(issues, "ERROR", "INVALID_FIELD_LEVEL", path, "level must be an integer.")

    for name in ("required", "multiple", "hasChildren", "uncertain"):
        if name in field and not isinstance(field[name], bool):
            issue(issues, "ERROR", "INVALID_FIELD_TYPE", f"{path}.{name}", f"{name} must be boolean.")

    node_kind = field.get("nodeKind")
    data_type = field.get("dataType")
    _enum(node_kind, NODE_KINDS, issues, "INVALID_NODE_KIND", f"{path}.nodeKind")
    _enum(data_type, DATA_TYPES, issues, "INVALID_DATA_TYPE", f"{path}.dataType")
    _validate_field_shape(field, child_counts, issues, path=path)
    _validate_occurs(field, issues, path=path)
    _validate_length(field.get("length"), issues, path=f"{path}.length")
    _validate_evidence(field.get("evidence"), issues, path=f"{path}.evidence")
    _validate_review_signals(field, issues, path=path)

    for nullable_name in ("format", "conditionText", "uncertainReason", "reviewNote"):
        value = field.get(nullable_name)
        if value is not None and not isinstance(value, str):
            issue(
                issues,
                "ERROR",
                "INVALID_NULLABLE_STRING",
                f"{path}.{nullable_name}",
                f"{nullable_name} must be a string or null.",
            )


def _validate_field_shape(
    field: dict[str, Any],
    child_counts: Counter[Any],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    field_path = field.get("path")
    node_kind = field.get("nodeKind")
    data_type = field.get("dataType")
    has_children = field.get("hasChildren")
    multiple = field.get("multiple")
    actual_has_children = isinstance(field_path, str) and child_counts[field_path] > 0
    if isinstance(has_children, bool) and has_children != actual_has_children:
        issue(issues, "ERROR", "HAS_CHILDREN_MISMATCH", path, "hasChildren must match the modeled child fields.")
    if has_children is True and data_type not in {"object", "array"}:
        issue(issues, "ERROR", "CONTAINER_DATA_TYPE_MISMATCH", path, "Fields with children must use object or array.")
    if has_children is False and data_type in {"object", "array"}:
        issue(issues, "ERROR", "SCALAR_DATA_TYPE_MISMATCH", path, "Fields without children cannot use object or array.")
    if multiple is True and data_type != "object":
        issue(issues, "ERROR", "MULTIPLE_DATA_TYPE_MISMATCH", path, "Repeated XML fields must be object containers.")
    if node_kind == "XML_ATTRIBUTE" and (has_children is True or multiple is True or data_type in {"object", "array"}):
        issue(issues, "ERROR", "INVALID_XML_ATTRIBUTE_SHAPE", path, "XML attributes must be scalar and non-repeating.")
    if node_kind == "SCALAR" and has_children is True:
        issue(issues, "ERROR", "INVALID_SCALAR_SHAPE", path, "SCALAR fields cannot have children.")


def _validate_occurs(field: dict[str, Any], issues: list[ValidationIssue], *, path: str) -> None:
    occurs = field.get("occurs")
    if not isinstance(occurs, str):
        issue(issues, "ERROR", "INVALID_OCCURS", f"{path}.occurs", "occurs must use min..max syntax.")
        return
    match = OCCURS_PATTERN.fullmatch(occurs)
    if match is None:
        issue(issues, "ERROR", "INVALID_OCCURS", f"{path}.occurs", "occurs must use min..max syntax.")
        return
    minimum = int(match.group(1))
    maximum_text = match.group(2)
    maximum = None if maximum_text == "n" else int(maximum_text)
    if maximum is not None and maximum < minimum:
        issue(issues, "ERROR", "INVALID_OCCURS_RANGE", f"{path}.occurs", "occurs maximum cannot be below minimum.")
    multiple = field.get("multiple")
    if multiple is False and maximum != 1:
        issue(issues, "ERROR", "MULTIPLE_OCCURS_MISMATCH", path, "Non-repeating fields must have maximum occurrence 1.")
    if multiple is True and maximum == 1:
        issue(issues, "ERROR", "MULTIPLE_OCCURS_MISMATCH", path, "Repeating fields must allow more than one occurrence.")
    required = field.get("required")
    required_from_occurs = minimum > 0
    if isinstance(required, bool) and required != required_from_occurs:
        if field.get("uncertain") is True:
            issue(
                issues,
                "WARNING",
                "REQUIRED_OCCURS_CONFLICT",
                path,
                "required conflicts with occurs and must be resolved by Human Review.",
                blocking=True,
            )
        else:
            issue(issues, "ERROR", "REQUIRED_OCCURS_MISMATCH", path, "required must match the occurs minimum.")


def _validate_length(length: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(length, dict):
        issue(issues, "ERROR", "INVALID_LENGTH", path, "length must be an object.")
        return
    _object_contract(
        length,
        LENGTH_PROPERTIES,
        LENGTH_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_LENGTH_PROPERTY",
        unknown_code="UNKNOWN_LENGTH_PROPERTY",
    )
    for name in ("min", "max"):
        value = length.get(name)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            issue(issues, "ERROR", "INVALID_LENGTH_BOUND", f"{path}.{name}", f"length.{name} must be a non-negative integer or null.")
    raw = length.get("raw")
    if raw is not None and not isinstance(raw, str):
        issue(issues, "ERROR", "INVALID_LENGTH_RAW", f"{path}.raw", "length.raw must be a string or null.")
    minimum = length.get("min")
    maximum = length.get("max")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and isinstance(maximum, int) and not isinstance(maximum, bool) and maximum < minimum:
        issue(issues, "ERROR", "INVALID_LENGTH_RANGE", path, "length.max cannot be below length.min.")


def _validate_evidence(evidence: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(evidence, dict):
        issue(issues, "ERROR", "INVALID_EVIDENCE", path, "evidence must be an object.")
        return
    _object_contract(
        evidence,
        EVIDENCE_PROPERTIES,
        EVIDENCE_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_EVIDENCE_PROPERTY",
        unknown_code="UNKNOWN_EVIDENCE_PROPERTY",
    )
    _enum(evidence.get("kind"), EVIDENCE_KINDS, issues, "INVALID_EVIDENCE_KIND", f"{path}.kind")
    _required_string(evidence.get("note"), issues, "INVALID_EVIDENCE_NOTE", f"{path}.note")


def _validate_review_signals(field: dict[str, Any], issues: list[ValidationIssue], *, path: str) -> None:
    uncertain = field.get("uncertain")
    uncertain_reason = field.get("uncertainReason")
    if uncertain is True:
        if not isinstance(uncertain_reason, str) or not uncertain_reason.strip():
            issue(issues, "ERROR", "MISSING_UNCERTAIN_REASON", f"{path}.uncertainReason", "uncertain fields require a reason.")
        issue(
            issues,
            "WARNING",
            "UNCERTAIN_FIELD",
            path,
            "Field is marked uncertain and cannot enter a Final artifact.",
            blocking=True,
        )
    elif uncertain is False and uncertain_reason is not None:
        issue(issues, "ERROR", "UNEXPECTED_UNCERTAIN_REASON", f"{path}.uncertainReason", "certain fields must not carry uncertainReason.")

    confidence = field.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
        issue(issues, "ERROR", "INVALID_CONFIDENCE", f"{path}.confidence", "confidence must be a number between 0 and 1.")
    elif confidence < 0.9:
        issue(
            issues,
            "WARNING",
            "LOW_CONFIDENCE",
            path,
            "Field confidence is below 0.9.",
            blocking=False,
        )

    evidence = field.get("evidence")
    evidence_kind = evidence.get("kind") if isinstance(evidence, dict) else None
    if evidence_kind in EVIDENCE_KINDS and evidence_kind != "DIRECT":
        issue(
            issues,
            "WARNING",
            "NON_DIRECT_EVIDENCE",
            path,
            "Field evidence is not DIRECT.",
            blocking=False,
        )
    if field.get("conditionText"):
        issue(issues, "INFO", "CONDITIONAL_FIELD", path, "Field has conditionText.", blocking=False)


def _validate_xml_encoding(
    message: dict[str, Any],
    schemair: dict[str, Any],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    encoding = message.get("xmlEncoding")
    if encoding != "UTF-8":
        issue(issues, "ERROR", "UNSUPPORTED_XML_ENCODING", f"{path}.xmlEncoding", "P0 SchemaIR supports the canonical UTF-8 value only.")
    evidence_items = message.get("xmlEncodingEvidence")
    if not isinstance(evidence_items, list):
        return
    if not evidence_items:
        issue(issues, "ERROR", "MISSING_XML_ENCODING_EVIDENCE", f"{path}.xmlEncodingEvidence", "xmlEncoding requires explicit evidence.")
        return

    seen: set[tuple[str, str, str]] = set()
    has_human_support = False
    for index, item in enumerate(evidence_items):
        item_path = f"{path}.xmlEncodingEvidence[{index}]"
        if not isinstance(item, dict):
            issue(issues, "ERROR", "INVALID_XML_ENCODING_EVIDENCE", item_path, "Encoding evidence must be an object.")
            continue
        _object_contract(
            item,
            ENCODING_EVIDENCE_PROPERTIES,
            ENCODING_EVIDENCE_PROPERTIES,
            issues,
            path=item_path,
            missing_code="MISSING_XML_ENCODING_EVIDENCE_PROPERTY",
            unknown_code="UNKNOWN_XML_ENCODING_EVIDENCE_PROPERTY",
        )
        source_kind = item.get("sourceKind")
        source_ref = item.get("sourceRef")
        observed_value = item.get("observedValue")
        disposition = item.get("disposition")
        review_note = item.get("reviewNote")
        _enum(source_kind, ENCODING_SOURCE_KINDS, issues, "INVALID_XML_ENCODING_SOURCE_KIND", f"{item_path}.sourceKind")
        _required_string(source_ref, issues, "INVALID_XML_ENCODING_SOURCE_REF", f"{item_path}.sourceRef")
        _required_string(observed_value, issues, "INVALID_XML_ENCODING_OBSERVED_VALUE", f"{item_path}.observedValue")
        _enum(disposition, ENCODING_DISPOSITIONS, issues, "INVALID_XML_ENCODING_DISPOSITION", f"{item_path}.disposition")
        if review_note is not None and not isinstance(review_note, str):
            issue(issues, "ERROR", "INVALID_XML_ENCODING_REVIEW_NOTE", f"{item_path}.reviewNote", "reviewNote must be a string or null.")

        if all(isinstance(value, str) for value in (source_kind, source_ref, observed_value)):
            key = (source_kind, source_ref, observed_value)
            if key in seen:
                issue(issues, "ERROR", "DUPLICATE_XML_ENCODING_EVIDENCE", item_path, "Encoding evidence is duplicated.")
            seen.add(key)

        if disposition == "SUPPORTS":
            if observed_value != encoding:
                issue(issues, "ERROR", "INVALID_SUPPORTING_XML_ENCODING_EVIDENCE", item_path, "Supporting evidence must match xmlEncoding.")
            if source_kind == "HUMAN_BANK_CONFIRMATION" and observed_value == encoding:
                has_human_support = True
        elif disposition == "UNRESOLVED_CONFLICT":
            if observed_value == encoding:
                issue(issues, "ERROR", "INVALID_XML_ENCODING_CONFLICT", item_path, "Conflict evidence must differ from xmlEncoding.")
            issue(
                issues,
                "WARNING",
                "XML_ENCODING_CONFLICT",
                item_path,
                "Encoding evidence conflicts with the confirmed value and requires Human Review.",
                blocking=True,
            )
        elif disposition == "RESOLVED_CONFLICT":
            if observed_value == encoding:
                issue(issues, "ERROR", "INVALID_XML_ENCODING_CONFLICT", item_path, "Resolved conflict evidence must differ from xmlEncoding.")
            if not isinstance(review_note, str) or not review_note.strip():
                issue(issues, "ERROR", "MISSING_XML_ENCODING_RESOLUTION", f"{item_path}.reviewNote", "Resolved conflicts require a review note.")
            issue(
                issues,
                "WARNING",
                "RESOLVED_XML_ENCODING_CONFLICT",
                item_path,
                "A reviewed encoding conflict is preserved as evidence.",
                blocking=False,
            )

    if schemair.get("status") == "FINAL" and not has_human_support:
        issue(
            issues,
            "ERROR",
            "FINAL_REQUIRES_ENCODING_CONFIRMATION",
            f"{path}.xmlEncodingEvidence",
            "Final messages require supporting Human and bank confirmation evidence.",
        )


def _validate_conditions(
    message: dict[str, Any],
    schemair: dict[str, Any],
    available_paths: set[str],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    conditions = message.get("conditionalConstraints")
    if not isinstance(conditions, list):
        return
    seen: set[tuple[Any, Any, Any, Any, Any]] = set()
    for index, condition in enumerate(conditions):
        condition_path = f"{path}.conditionalConstraints[{index}]"
        if not isinstance(condition, dict):
            issue(issues, "ERROR", "INVALID_CONDITIONAL_CONSTRAINT", condition_path, "Conditional constraint must be an object.")
            continue
        _object_contract(
            condition,
            CONDITION_PROPERTIES,
            CONDITION_PROPERTIES,
            issues,
            path=condition_path,
            missing_code="MISSING_CONDITIONAL_CONSTRAINT_PROPERTY",
            unknown_code="UNKNOWN_CONDITIONAL_CONSTRAINT_PROPERTY",
        )
        controlling_path = condition.get("controllingFieldPath")
        target_path = condition.get("targetFieldPath")
        operator = condition.get("operator")
        literal = condition.get("literal")
        effect = condition.get("effect")
        _required_string(controlling_path, issues, "INVALID_CONTROLLING_FIELD_PATH", f"{condition_path}.controllingFieldPath")
        _required_string(target_path, issues, "INVALID_TARGET_FIELD_PATH", f"{condition_path}.targetFieldPath")
        _enum(operator, CONDITION_OPERATORS, issues, "INVALID_CONDITION_OPERATOR", f"{condition_path}.operator")
        _enum(effect, CONDITION_EFFECTS, issues, "INVALID_CONDITION_EFFECT", f"{condition_path}.effect")
        _required_string(condition.get("sourceText"), issues, "INVALID_CONDITION_SOURCE_TEXT", f"{condition_path}.sourceText")
        _validate_evidence(condition.get("evidence"), issues, path=f"{condition_path}.evidence")
        review = condition.get("review")
        if isinstance(review, dict):
            _validate_review(review, issues, path=f"{condition_path}.review")
            if review.get("status") != "APPROVED":
                issue(
                    issues,
                    "WARNING",
                    "CONDITION_REVIEW_NOT_APPROVED",
                    f"{condition_path}.review.status",
                    "Structured bank conditions require Human Review.",
                    blocking=True,
                )
        else:
            issue(issues, "ERROR", "INVALID_CONDITION_REVIEW", f"{condition_path}.review", "condition.review must be an object.")

        if isinstance(controlling_path, str) and controlling_path not in available_paths:
            issue(issues, "ERROR", "UNKNOWN_CONTROLLING_FIELD", f"{condition_path}.controllingFieldPath", "Condition references an unknown controlling field.")
        if isinstance(target_path, str) and target_path not in available_paths:
            issue(issues, "ERROR", "UNKNOWN_TARGET_FIELD", f"{condition_path}.targetFieldPath", "Condition references an unknown target field.")
        if operator == "EQUALS" and not isinstance(literal, str):
            issue(issues, "ERROR", "INVALID_CONDITION_LITERAL", f"{condition_path}.literal", "EQUALS requires a String literal.")
        if operator == "IS_EMPTY" and literal is not None:
            issue(issues, "ERROR", "INVALID_CONDITION_LITERAL", f"{condition_path}.literal", "IS_EMPTY requires a null literal.")

        key = (controlling_path, operator, literal, target_path, effect)
        if key in seen:
            issue(issues, "ERROR", "DUPLICATE_CONDITIONAL_CONSTRAINT", condition_path, "Conditional constraint is duplicated.")
        seen.add(key)

        if schemair.get("status") == "FINAL" and isinstance(review, dict) and review.get("status") != "APPROVED":
            issue(issues, "ERROR", "FINAL_REQUIRES_CONDITION_REVIEW", condition_path, "Final conditions require approved Human Review.")


def _result(
    schemair: object,
    envelope_fields: list[Any],
    messages: list[Any],
    issues: list[ValidationIssue],
) -> dict[str, Any]:
    message_objects = [message for message in messages if isinstance(message, dict)]
    field_counts = _field_counts_by_function_type(message_objects)
    schemair_object = schemair if isinstance(schemair, dict) else {}
    return build_validation_result(
        schemair,
        result_contract_version=RESULT_CONTRACT_VERSION,
        artifact_kind="SchemaIR",
        artifact_id_field="schemaId",
        artifact_version_field="schemaVersion",
        issues=issues,
        summary={
            "schemaId": schemair_object.get("schemaId"),
            "interfaceCode": schemair_object.get("interfaceCode"),
            "messageFormat": schemair_object.get("messageFormat"),
            "messageCount": len(message_objects),
            "fieldCount": len(envelope_fields) + sum(field_counts.values()),
        },
        coverage={
            "envelopeFieldCount": len(envelope_fields),
            "messageFieldCount": sum(field_counts.values()),
            "fieldsByFunctionType": field_counts,
        },
    )


def _field_counts_by_function_type(messages: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for message in messages:
        function_type = message.get("functionType")
        if isinstance(function_type, str):
            counts[function_type] = counts.get(function_type, 0) + len(_fields_from(message))
    return counts


def _fields_from(container: Any) -> list[Any]:
    if isinstance(container, dict) and isinstance(container.get("fields"), list):
        return container["fields"]
    return []


def _object_contract(
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
    issues: list[ValidationIssue],
    *,
    path: str | None,
    missing_code: str,
    unknown_code: str,
) -> None:
    for name in sorted(required - value.keys()):
        property_path = f"{path}.{name}" if path else name
        issue(issues, "ERROR", missing_code, property_path, f"Missing property: {name}.")
    for name in sorted(value.keys() - allowed):
        property_path = f"{path}.{name}" if path else name
        issue(issues, "ERROR", unknown_code, property_path, f"Unknown property: {name}.")


def _required_string(value: Any, issues: list[ValidationIssue], code: str, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        issue(issues, "ERROR", code, path, "Value must be a non-empty string.")


def _version(value: Any, issues: list[ValidationIssue], code: str, path: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"v[1-9]\d*", value) is None:
        issue(issues, "ERROR", code, path, "Artifact version must use v<positive integer> syntax.")


def _stable_id(value: Any, issues: list[ValidationIssue], code: str, path: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is None:
        issue(issues, "ERROR", code, path, "Stable ID must be a non-empty lowercase kebab-case string.")


def _enum(value: Any, allowed: set[str], issues: list[ValidationIssue], code: str, path: str) -> None:
    if value not in allowed:
        issue(issues, "ERROR", code, path, f"Value must be one of {sorted(allowed)}.")


def _is_offset_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _log_result(result: dict[str, Any]) -> None:
    artifact = result["validatedArtifact"]
    summary = result["summary"]
    extra = {
        "component": "schemair_validator",
        "artifact_id": artifact["artifactId"],
        "artifact_version": artifact["artifactVersion"],
        "content_hash": artifact["contentHash"],
        "validation_status": result["status"],
        "final_eligible": result["finalEligible"],
        "error_count": summary["errorCount"],
        "warning_count": summary["warningCount"],
        "outcome": "rejected" if result["status"] == "failed" else "completed",
    }
    if result["status"] == "failed":
        LOGGER.warning("SchemaIR validation rejected input", extra=extra)
    else:
        LOGGER.info("SchemaIR validation completed", extra=extra)
