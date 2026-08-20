from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .draft_generation import DraftGenerationError


SCHEMAIR_METADATA_SEGMENT_CONTRACT = "schemair-metadata-segment/v1"
SCHEMAIR_FIELD_SEMANTICS_SEGMENT_CONTRACT = "schemair-field-semantics-segment/v1"
SCHEMAIR_SECTIONS = ("ENVELOPE", "ASSEMBLY", "PARSE")

SCHEMAIR_CANDIDATE_FIELD_PROPERTIES = {
    "fieldName",
    "displayName",
    "format",
    "length",
    "description",
    "conditionText",
    "sourceText",
    "evidence",
    "confidence",
    "uncertain",
    "uncertainReason",
    "reviewNote",
}
SCHEMAIR_CANDIDATE_LENGTH_PROPERTIES = {"min", "max", "raw"}
SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES = {"kind", "note"}
SCHEMAIR_CANDIDATE_ENCODING_EVIDENCE_PROPERTIES = {
    "sourceKind",
    "sourceRef",
    "observedValue",
    "disposition",
    "reviewNote",
}
SCHEMAIR_CANDIDATE_CONDITION_PROPERTIES = {
    "controllingFieldPath",
    "operator",
    "literal",
    "targetFieldPath",
    "effect",
    "sourceText",
    "evidence",
}
_METADATA_PROPERTIES = {"contractVersion", "envelope", "messages"}
_METADATA_ENVELOPE_PROPERTIES = {"description"}
_METADATA_MESSAGE_PROPERTIES = {
    "functionType",
    "xmlEncoding",
    "xmlEncodingEvidence",
    "description",
    "conditionalConstraints",
}
_FIELD_SEGMENT_PROPERTIES = {
    "contractVersion",
    "section",
    "batchIndex",
    "fields",
}
_SELECTOR_PROPERTIES = {"selector", "fieldName", "path", "nodeKind", "dataType"}


def build_schemair_field_batches(
    structure: Mapping[str, Any], *, batch_size: int
) -> dict[str, list[list[dict[str, str]]]]:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise DraftGenerationError("SchemaIR field batch size must be a positive integer")
    result: dict[str, list[list[dict[str, str]]]] = {}
    for section in SCHEMAIR_SECTIONS:
        structure_key = section.lower()
        section_value = _require_object(
            structure.get(structure_key), label=f"Final DocIR {section} structure"
        )
        fields = section_value.get("fields")
        if not isinstance(fields, list):
            raise DraftGenerationError(f"Final DocIR {section} fields must be an array")
        selectors: list[dict[str, str]] = []
        for position, field_value in enumerate(fields, start=1):
            field = _require_object(
                field_value, label=f"Final DocIR {section} fields[{position - 1}]"
            )
            selector = {
                "selector": f"{structure_key}:{position}",
                "fieldName": _required_string(field.get("fieldName"), "fieldName"),
                "path": _required_string(field.get("path"), "path"),
                "nodeKind": _required_string(field.get("nodeKind"), "nodeKind"),
                "dataType": _required_string(field.get("dataType"), "dataType"),
            }
            _require_exact_properties(
                selector,
                allowed=_SELECTOR_PROPERTIES,
                required=_SELECTOR_PROPERTIES,
                label=f"SchemaIR {section} selector",
            )
            selectors.append(selector)
        result[section] = [
            selectors[start : start + batch_size]
            for start in range(0, len(selectors), batch_size)
        ]
    return result


def validate_schemair_metadata_segment(
    value: Any, *, structure: Mapping[str, Any]
) -> dict[str, Any]:
    metadata = _require_exact_object(
        value,
        allowed=_METADATA_PROPERTIES,
        required=_METADATA_PROPERTIES,
        label="SchemaIR metadata segment",
    )
    if metadata.get("contractVersion") != SCHEMAIR_METADATA_SEGMENT_CONTRACT:
        raise DraftGenerationError(
            "SchemaIR metadata segment contractVersion must be "
            f"{SCHEMAIR_METADATA_SEGMENT_CONTRACT}"
        )
    envelope = _require_exact_object(
        metadata.get("envelope"),
        allowed=_METADATA_ENVELOPE_PROPERTIES,
        required=_METADATA_ENVELOPE_PROPERTIES,
        label="SchemaIR metadata envelope",
    )
    messages_value = metadata.get("messages")
    if not isinstance(messages_value, list) or len(messages_value) != 2:
        raise DraftGenerationError(
            "SchemaIR metadata segment must contain exactly ASSEMBLY and PARSE messages"
        )
    envelope_paths = _structure_paths(structure, "envelope")
    by_direction: dict[str, dict[str, Any]] = {}
    for index, message_value in enumerate(messages_value):
        message = _require_exact_object(
            message_value,
            allowed=_METADATA_MESSAGE_PROPERTIES,
            required=_METADATA_MESSAGE_PROPERTIES,
            label=f"SchemaIR metadata messages[{index}]",
        )
        direction = message.get("functionType")
        if direction not in {"ASSEMBLY", "PARSE"} or direction in by_direction:
            raise DraftGenerationError(
                "SchemaIR metadata segment must contain one unambiguous ASSEMBLY and PARSE message"
            )
        _validate_encoding_evidence(
            message.get("xmlEncodingEvidence"),
            label=f"SchemaIR metadata messages[{direction}].xmlEncodingEvidence",
        )
        _validate_conditions(
            message.get("conditionalConstraints"),
            allowed_paths=envelope_paths | _structure_paths(structure, direction.lower()),
            label=f"SchemaIR metadata messages[{direction}].conditionalConstraints",
        )
        by_direction[direction] = message
    if set(by_direction) != {"ASSEMBLY", "PARSE"}:
        raise DraftGenerationError(
            "SchemaIR metadata segment must contain exactly ASSEMBLY and PARSE messages"
        )
    return {
        "contractVersion": SCHEMAIR_METADATA_SEGMENT_CONTRACT,
        "envelope": deepcopy(envelope),
        "messages": [deepcopy(by_direction[direction]) for direction in ("ASSEMBLY", "PARSE")],
    }


def validate_schemair_field_semantics_segment(
    value: Any,
    *,
    section: str,
    batch_index: int,
    expected_selectors: list[dict[str, str]],
) -> dict[str, Any]:
    if section not in SCHEMAIR_SECTIONS:
        raise DraftGenerationError("SchemaIR field segment section is invalid")
    segment = _require_exact_object(
        value,
        allowed=_FIELD_SEGMENT_PROPERTIES,
        required=_FIELD_SEGMENT_PROPERTIES,
        label="SchemaIR field semantics segment",
    )
    if segment.get("contractVersion") != SCHEMAIR_FIELD_SEMANTICS_SEGMENT_CONTRACT:
        raise DraftGenerationError(
            "SchemaIR field semantics segment contractVersion must be "
            f"{SCHEMAIR_FIELD_SEMANTICS_SEGMENT_CONTRACT}"
        )
    if segment.get("section") != section:
        raise DraftGenerationError("SchemaIR field semantics segment section does not match")
    if segment.get("batchIndex") != batch_index:
        raise DraftGenerationError("SchemaIR field semantics segment batchIndex does not match")
    fields = segment.get("fields")
    if not isinstance(fields, list) or len(fields) != len(expected_selectors):
        raise DraftGenerationError(
            "SchemaIR field semantics segment must exactly cover target selectors"
        )
    validated_fields: list[dict[str, Any]] = []
    for position, (field_value, expected) in enumerate(
        zip(fields, expected_selectors, strict=True)
    ):
        field = _require_object(
            field_value, label=f"SchemaIR {section} field segment fields[{position}]"
        )
        if field.get("selector") != expected["selector"]:
            raise DraftGenerationError(
                f"SchemaIR {section} field segment fields[{position}] selector does not match"
            )
        if field.get("fieldName") != expected["fieldName"]:
            raise DraftGenerationError(
                f"SchemaIR {section} field segment fields[{position}] fieldName does not match"
            )
        required = set(SCHEMAIR_CANDIDATE_FIELD_PROPERTIES) | {"selector"}
        if expected["dataType"] == "object":
            required.add("required")
        _require_exact_properties(
            field,
            allowed=required,
            required=required,
            label=f"SchemaIR {section} field segment fields[{position}]",
        )
        if expected["dataType"] == "object" and not isinstance(field.get("required"), bool):
            raise DraftGenerationError(
                f"SchemaIR {section} field segment fields[{position}] Object required must be boolean"
            )
        _require_exact_object(
            field.get("length"),
            allowed=SCHEMAIR_CANDIDATE_LENGTH_PROPERTIES,
            required=SCHEMAIR_CANDIDATE_LENGTH_PROPERTIES,
            label=f"SchemaIR {section} field segment fields[{position}].length",
        )
        _require_exact_object(
            field.get("evidence"),
            allowed=SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
            required=SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
            label=f"SchemaIR {section} field segment fields[{position}].evidence",
        )
        validated_fields.append(deepcopy(field))
    return {
        "contractVersion": SCHEMAIR_FIELD_SEMANTICS_SEGMENT_CONTRACT,
        "section": section,
        "batchIndex": batch_index,
        "fields": validated_fields,
    }


def merge_schemair_semantic_segments(
    *,
    metadata: Any,
    field_segments: Mapping[str, list[dict[str, Any]]],
    structure: Mapping[str, Any],
    batch_size: int,
) -> dict[str, Any]:
    validated_metadata = validate_schemair_metadata_segment(metadata, structure=structure)
    expected_batches = build_schemair_field_batches(structure, batch_size=batch_size)
    if set(field_segments) != set(SCHEMAIR_SECTIONS):
        raise DraftGenerationError(
            "SchemaIR field segments must contain exactly ENVELOPE, ASSEMBLY and PARSE"
        )
    merged_fields: dict[str, list[dict[str, Any]]] = {}
    for section in SCHEMAIR_SECTIONS:
        segments = field_segments[section]
        expected = expected_batches[section]
        if not isinstance(segments, list) or len(segments) != len(expected):
            raise DraftGenerationError(
                f"SchemaIR {section} field segments must exactly cover Final DocIR batches"
            )
        merged_fields[section] = []
        for batch_index, (segment, selectors) in enumerate(
            zip(segments, expected, strict=True), start=1
        ):
            validated = validate_schemair_field_semantics_segment(
                segment,
                section=section,
                batch_index=batch_index,
                expected_selectors=selectors,
            )
            for field in validated["fields"]:
                merged_fields[section].append(
                    {key: deepcopy(value) for key, value in field.items() if key != "selector"}
                )
    messages = {
        message["functionType"]: message for message in validated_metadata["messages"]
    }
    return {
        "envelope": {
            "description": deepcopy(validated_metadata["envelope"]["description"]),
            "fields": merged_fields["ENVELOPE"],
        },
        "messages": [
            {**deepcopy(messages[direction]), "fields": merged_fields[direction]}
            for direction in ("ASSEMBLY", "PARSE")
        ],
    }


def render_schemair_review_notes(
    candidate: Mapping[str, Any], validation_result: Mapping[str, Any] | None = None
) -> str:
    parts = ["# SchemaIR Candidate Review Notes", "", "## Candidate Review Items", ""]
    review_items: list[str] = []
    sections: list[tuple[str, Any]] = [("envelope", candidate.get("envelope"))]
    messages = candidate.get("messages")
    if isinstance(messages, list):
        for message in messages:
            if isinstance(message, dict):
                direction = message.get("functionType")
                label = direction.lower() if isinstance(direction, str) else "message"
                sections.append((label, message))
    for section_label, section_value in sections:
        if not isinstance(section_value, dict):
            continue
        encoding_evidence = section_value.get("xmlEncodingEvidence")
        if isinstance(encoding_evidence, list):
            for index, evidence in enumerate(encoding_evidence):
                if not isinstance(evidence, dict):
                    continue
                review_note = _optional_text(evidence.get("reviewNote"))
                if review_note is not None:
                    review_items.append(
                        f"- {section_label}.xmlEncodingEvidence[{index}]: "
                        f"review={review_note}"
                    )
        conditions = section_value.get("conditionalConstraints")
        if isinstance(conditions, list):
            for index, condition in enumerate(conditions):
                if not isinstance(condition, dict):
                    continue
                evidence = condition.get("evidence")
                if not isinstance(evidence, dict) or evidence.get("kind") == "DIRECT":
                    continue
                evidence_kind = evidence.get("kind") or "UNKNOWN"
                evidence_note = _optional_text(evidence.get("note"))
                detail = f"evidence={evidence_kind}"
                if evidence_note is not None:
                    detail += f"; note={evidence_note}"
                review_items.append(
                    f"- {section_label}.conditionalConstraints[{index}]: {detail}"
                )
        fields = section_value.get("fields")
        if not isinstance(fields, list):
            continue
        for index, field in enumerate(fields):
            if not isinstance(field, dict):
                continue
            evidence = field.get("evidence")
            evidence_kind = evidence.get("kind") if isinstance(evidence, dict) else None
            uncertain = field.get("uncertain") is True
            uncertain_reason = _optional_text(field.get("uncertainReason"))
            review_note = _optional_text(field.get("reviewNote"))
            if not uncertain and evidence_kind == "DIRECT" and review_note is None:
                continue
            field_name = field.get("fieldName")
            details = [f"evidence={evidence_kind or 'UNKNOWN'}", f"uncertain={str(uncertain).lower()}"]
            if uncertain_reason is not None:
                details.append(f"reason={uncertain_reason}")
            if review_note is not None:
                details.append(f"review={review_note}")
            review_items.append(
                f"- {section_label}.fields[{index}] `{field_name}`: " + "; ".join(details)
            )
    parts.extend(review_items or ["- Candidate 未声明额外不确定项；Human 仍需对照 Final DocIR 审查语义。"])
    parts.extend(["", "## Validator Issues", ""])
    issues = validation_result.get("issues") if isinstance(validation_result, Mapping) else None
    if not isinstance(issues, list) or not issues:
        parts.append("- Validator 未报告 issue。")
    else:
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            path = f" `{issue.get('path')}`" if issue.get("path") else ""
            parts.append(
                f"- [{issue.get('severity')}] `{issue.get('code')}`{path}: {issue.get('message')}"
            )
    return "\n".join(parts) + "\n"


def _validate_encoding_evidence(value: Any, *, label: str) -> None:
    if not isinstance(value, list):
        raise DraftGenerationError(f"{label} must be an array")
    for index, item in enumerate(value):
        _require_exact_object(
            item,
            allowed=SCHEMAIR_CANDIDATE_ENCODING_EVIDENCE_PROPERTIES,
            required=SCHEMAIR_CANDIDATE_ENCODING_EVIDENCE_PROPERTIES,
            label=f"{label}[{index}]",
        )


def _validate_conditions(value: Any, *, allowed_paths: set[str], label: str) -> None:
    if not isinstance(value, list):
        raise DraftGenerationError(f"{label} must be an array")
    for index, item in enumerate(value):
        condition = _require_exact_object(
            item,
            allowed=SCHEMAIR_CANDIDATE_CONDITION_PROPERTIES,
            required=SCHEMAIR_CANDIDATE_CONDITION_PROPERTIES,
            label=f"{label}[{index}]",
        )
        controlling = condition.get("controllingFieldPath")
        target = condition.get("targetFieldPath")
        if controlling not in allowed_paths:
            raise DraftGenerationError(f"{label}[{index}] has unknown controllingFieldPath")
        if target not in allowed_paths:
            raise DraftGenerationError(f"{label}[{index}] has unknown targetFieldPath")
        _require_exact_object(
            condition.get("evidence"),
            allowed=SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
            required=SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
            label=f"{label}[{index}].evidence",
        )


def _structure_paths(structure: Mapping[str, Any], key: str) -> set[str]:
    section = _require_object(structure.get(key), label=f"Final DocIR {key} structure")
    fields = section.get("fields")
    if not isinstance(fields, list):
        raise DraftGenerationError(f"Final DocIR {key} fields must be an array")
    return {
        _required_string(_require_object(field, label=f"Final DocIR {key} field").get("path"), "path")
        for field in fields
    }


def _require_exact_object(
    value: Any, *, allowed: set[str], required: set[str], label: str
) -> dict[str, Any]:
    result = _require_object(value, label=label)
    _require_exact_properties(result, allowed=allowed, required=required, label=label)
    return result


def _require_exact_properties(
    value: Mapping[str, Any], *, allowed: set[str], required: set[str], label: str
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - allowed)
    if not missing and not unknown:
        return
    details: list[str] = []
    if missing:
        details.append(f"missing properties: {', '.join(missing)}")
    if unknown:
        details.append(f"unknown properties: {', '.join(unknown)}")
    raise DraftGenerationError(f"{label} has invalid properties ({'; '.join(details)})")


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DraftGenerationError(f"{label} must be an object")
    return value


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DraftGenerationError(f"{label} must be a non-empty string")
    return value


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
