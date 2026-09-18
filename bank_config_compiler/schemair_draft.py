from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .draft_generation import DraftGenerationError
from .segmented_artifact import (
    NormalizationDiagnostic,
    SegmentDisposition,
    SegmentSpec,
    SegmentValidationResult,
    canonical_segment_hash,
)


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
_NULLABLE_FIELD_PROPERTIES = {
    "format",
    "conditionText",
    "uncertainReason",
    "reviewNote",
}
_CODE_OWNED_FIELD_PROPERTIES = {
    "path",
    "parentPath",
    "nodeKind",
    "dataType",
    "fieldId",
    "level",
    "multiple",
    "hasChildren",
    "occurs",
    "identity",
    "lifecycle",
}


class BankXmlSchemaIRProfile:
    """银行 XML SchemaIR 的内置规则；只归一化可由代码证明的属性。"""

    def build_segment_plan(
        self, structure: Mapping[str, Any], *, batch_size: int
    ) -> tuple[SegmentSpec, ...]:
        batches = build_schemair_field_batches(structure, batch_size=batch_size)
        path_catalogs = {
            section: [selector["path"] for batch in batches[section] for selector in batch]
            for section in SCHEMAIR_SECTIONS
        }
        metadata_payload = {"pathCatalogs": path_catalogs}
        specs = [
            SegmentSpec(
                segment_id="schemair-metadata",
                contract_version=SCHEMAIR_METADATA_SEGMENT_CONTRACT,
                payload=metadata_payload,
                payload_hash=canonical_segment_hash(metadata_payload),
            )
        ]
        for section in SCHEMAIR_SECTIONS:
            for batch_index, selectors in enumerate(batches[section], start=1):
                payload = {
                    "section": section,
                    "batchIndex": batch_index,
                    "selectors": selectors,
                }
                specs.append(
                    SegmentSpec(
                        segment_id=(
                            f"schemair-{section.lower()}-fields-{batch_index:03d}"
                        ),
                        contract_version=SCHEMAIR_FIELD_SEMANTICS_SEGMENT_CONTRACT,
                        payload=payload,
                        payload_hash=canonical_segment_hash(payload),
                        selector_hash=canonical_segment_hash({"selectors": selectors}),
                        dependencies=("schemair-metadata",),
                    )
                )
        return tuple(specs)

    def validate_segment(
        self,
        spec: SegmentSpec,
        value: Any,
        *,
        structure: Mapping[str, Any],
    ) -> SegmentValidationResult:
        if spec.segment_id == "schemair-metadata":
            return _profile_validate_metadata_segment(
                value,
                structure=structure,
                segment_name=spec.segment_id,
            )
        payload = spec.payload
        section = payload.get("section")
        batch_index = payload.get("batchIndex")
        selectors = payload.get("selectors")
        if (
            section not in SCHEMAIR_SECTIONS
            or not isinstance(batch_index, int)
            or not isinstance(selectors, list)
        ):
            return SegmentValidationResult(
                SegmentDisposition.HARD_FAIL,
                None,
                detail=f"invalid code-owned segment spec: {spec.segment_id}",
            )
        return self.validate_field_segment(
            value,
            section=section,
            batch_index=batch_index,
            expected_selectors=selectors,
            segment_id=spec.segment_id,
        )

    def validate_field_segment(
        self,
        value: Any,
        *,
        section: str,
        batch_index: int,
        expected_selectors: list[dict[str, str]],
        segment_id: str | None = None,
    ) -> SegmentValidationResult:
        segment_name = segment_id or f"schemair-{section.lower()}-fields-{batch_index:03d}"
        if not isinstance(value, dict):
            return SegmentValidationResult(
                SegmentDisposition.RETRY_SEGMENT,
                None,
                detail="SchemaIR field semantics segment must be an object",
            )
        normalized = deepcopy(value)
        fields = normalized.get("fields")
        if not isinstance(fields, list) or len(fields) != len(expected_selectors):
            return SegmentValidationResult(
                SegmentDisposition.RETRY_SEGMENT,
                None,
                detail="SchemaIR field semantics segment must exactly cover target selectors",
            )
        diagnostics: list[NormalizationDiagnostic] = []
        invalid_draft = False
        for position, (field_value, expected) in enumerate(
            zip(fields, expected_selectors, strict=True)
        ):
            if not isinstance(field_value, dict):
                return SegmentValidationResult(
                    SegmentDisposition.RETRY_SEGMENT,
                    None,
                    detail=f"SchemaIR {section} fields[{position}] must be an object",
                )
            if field_value.get("selector") != expected["selector"]:
                return SegmentValidationResult(
                    SegmentDisposition.RETRY_SEGMENT,
                    None,
                    detail=f"SchemaIR {section} fields[{position}] selector does not match",
                )
            if field_value.get("fieldName") != expected["fieldName"]:
                return SegmentValidationResult(
                    SegmentDisposition.RETRY_SEGMENT,
                    None,
                    detail=f"SchemaIR {section} fields[{position}] fieldName does not match",
                )
            selector = expected["selector"]
            for property_name in sorted(_CODE_OWNED_FIELD_PROPERTIES & field_value.keys()):
                field_value.pop(property_name)
                diagnostics.append(
                    NormalizationDiagnostic(
                        segment=segment_name,
                        selector=selector,
                        path=expected["path"],
                        code="CODE_OWNED_PROPERTY_REMOVED",
                        action=f"removed {property_name}",
                        severity="WARNING",
                    )
                )
            if expected["dataType"] != "object" and "required" in field_value:
                field_value.pop("required")
                diagnostics.append(
                    NormalizationDiagnostic(
                        segment=segment_name,
                        selector=selector,
                        path=expected["path"],
                        code="SCALAR_REQUIRED_REMOVED",
                        action="removed required",
                        severity="WARNING",
                    )
                )
            allowed = set(SCHEMAIR_CANDIDATE_FIELD_PROPERTIES) | {"selector"}
            if expected["dataType"] == "object":
                allowed.add("required")
            unknown = sorted(field_value.keys() - allowed)
            if unknown:
                return SegmentValidationResult(
                    SegmentDisposition.RETRY_SEGMENT,
                    None,
                    tuple(diagnostics),
                    detail=(
                        f"SchemaIR {section} fields[{position}] has unknown properties: "
                        + ", ".join(unknown)
                    ),
                )
            for property_name in sorted(
                SCHEMAIR_CANDIDATE_FIELD_PROPERTIES - field_value.keys()
            ):
                if property_name == "length":
                    field_value[property_name] = {"min": None, "max": None, "raw": None}
                elif property_name == "evidence":
                    field_value[property_name] = {"kind": None, "note": None}
                else:
                    field_value[property_name] = None
                severity = (
                    "WARNING" if property_name in _NULLABLE_FIELD_PROPERTIES else "ERROR"
                )
                invalid_draft = invalid_draft or severity == "ERROR"
                diagnostics.append(
                    NormalizationDiagnostic(
                        segment=segment_name,
                        selector=selector,
                        path=expected["path"],
                        code="MISSING_SEMANTIC_PROPERTY_FILLED_NULL",
                        action=f"filled {property_name} with null placeholder",
                        severity=severity,
                    )
                )
            if expected["dataType"] == "object" and not isinstance(
                field_value.get("required"), bool
            ):
                field_value["required"] = None
                invalid_draft = True
                diagnostics.append(
                    NormalizationDiagnostic(
                        segment=segment_name,
                        selector=selector,
                        path=expected["path"],
                        code="OBJECT_REQUIRED_UNKNOWN",
                        action="replaced required with null placeholder",
                        severity="ERROR",
                    )
                )
            retry_detail = self._normalize_nested_field_slots(
                field_value,
                segment_name=segment_name,
                selector=selector,
                path=expected["path"],
                diagnostics=diagnostics,
            )
            if retry_detail is not None:
                return SegmentValidationResult(
                    SegmentDisposition.RETRY_SEGMENT,
                    None,
                    tuple(diagnostics),
                    detail=retry_detail,
                )
            invalid_draft = invalid_draft or any(
                diagnostic.severity == "ERROR"
                for diagnostic in diagnostics
                if diagnostic.selector == selector
            )
        try:
            validated = validate_schemair_field_semantics_segment(
                normalized,
                section=section,
                batch_index=batch_index,
                expected_selectors=expected_selectors,
            )
        except DraftGenerationError as exc:
            return SegmentValidationResult(
                SegmentDisposition.RETRY_SEGMENT,
                None,
                tuple(diagnostics),
                detail=str(exc),
            )
        disposition = (
            SegmentDisposition.INVALID_DRAFT
            if invalid_draft
            else SegmentDisposition.NORMALIZED
            if diagnostics
            else SegmentDisposition.ACCEPT
        )
        return SegmentValidationResult(disposition, validated, tuple(diagnostics))

    @staticmethod
    def _normalize_nested_field_slots(
        field: dict[str, Any],
        *,
        segment_name: str,
        selector: str,
        path: str,
        diagnostics: list[NormalizationDiagnostic],
    ) -> str | None:
        for property_name, slots in (
            ("length", SCHEMAIR_CANDIDATE_LENGTH_PROPERTIES),
            ("evidence", SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES),
        ):
            nested = field[property_name]
            if not isinstance(nested, dict):
                field[property_name] = {slot: None for slot in slots}
                diagnostics.append(
                    NormalizationDiagnostic(
                        segment=segment_name,
                        selector=selector,
                        path=path,
                        code="INVALID_NESTED_VALUE_REPLACED",
                        action=f"replaced {property_name} with null placeholders",
                        severity="ERROR",
                    )
                )
                continue
            unknown = sorted(nested.keys() - slots)
            if unknown:
                return (
                    f"SchemaIR field {selector} {property_name} has unknown properties: "
                    + ", ".join(unknown)
                )
            for slot in sorted(slots - nested.keys()):
                nested[slot] = None
                diagnostics.append(
                    NormalizationDiagnostic(
                        segment=segment_name,
                        selector=selector,
                        path=path,
                        code="MISSING_NESTED_SLOT_FILLED_NULL",
                        action=f"filled {property_name}.{slot} with null placeholder",
                        severity="ERROR",
                    )
                )
        return None

    def merge(
        self,
        segments: Mapping[str, dict[str, Any]],
        *,
        structure: Mapping[str, Any],
        batch_size: int,
    ) -> dict[str, Any]:
        metadata = segments.get("schemair-metadata")
        field_segments: dict[str, list[dict[str, Any]]] = {
            section: [] for section in SCHEMAIR_SECTIONS
        }
        plan = self.build_segment_plan(structure, batch_size=batch_size)
        for spec in plan[1:]:
            segment = segments.get(spec.segment_id)
            if segment is None:
                raise DraftGenerationError(
                    f"SchemaIR segment is missing during merge: {spec.segment_id}"
                )
            section = spec.payload["section"]
            field_segments[section].append(segment)
        return merge_schemair_semantic_segments(
            metadata=metadata,
            field_segments=field_segments,
            structure=structure,
            batch_size=batch_size,
            metadata_is_profile_validated=True,
        )


def _profile_validate_metadata_segment(
    value: Any,
    *,
    structure: Mapping[str, Any],
    segment_name: str,
) -> SegmentValidationResult:
    if not isinstance(value, dict):
        return _retry_segment("SchemaIR metadata segment must be an object")
    metadata = deepcopy(value)
    if set(metadata) != _METADATA_PROPERTIES:
        return _retry_segment(_property_mismatch(metadata, _METADATA_PROPERTIES))
    if metadata.get("contractVersion") != SCHEMAIR_METADATA_SEGMENT_CONTRACT:
        return _retry_segment("SchemaIR metadata segment contractVersion does not match")
    envelope = metadata.get("envelope")
    if not isinstance(envelope, dict):
        return _retry_segment("SchemaIR metadata envelope must be an object")
    unknown_envelope = sorted(envelope.keys() - _METADATA_ENVELOPE_PROPERTIES)
    if unknown_envelope:
        return _retry_segment(
            "SchemaIR metadata envelope has unknown properties: "
            + ", ".join(unknown_envelope)
        )

    diagnostics: list[NormalizationDiagnostic] = []
    if "description" not in envelope:
        envelope["description"] = None
        diagnostics.append(
            _normalization_diagnostic(
                segment_name,
                "MISSING_METADATA_PROPERTY_FILLED_NULL",
                "filled envelope.description with null placeholder",
                path="envelope.description",
            )
        )
    messages = metadata.get("messages")
    if not isinstance(messages, list) or len(messages) != 2:
        return _retry_segment(
            "SchemaIR metadata segment must contain exactly ASSEMBLY and PARSE messages"
        )
    allowed_paths = {
        direction: _structure_paths(structure, "envelope")
        | _structure_paths(structure, direction.lower())
        for direction in ("ASSEMBLY", "PARSE")
    }
    by_direction: dict[str, dict[str, Any]] = {}
    for index, message_value in enumerate(messages):
        if not isinstance(message_value, dict):
            return _retry_segment(f"SchemaIR metadata messages[{index}] must be an object")
        direction = message_value.get("functionType")
        if direction not in {"ASSEMBLY", "PARSE"} or direction in by_direction:
            return _retry_segment(
                "SchemaIR metadata segment must contain one unambiguous ASSEMBLY and PARSE message"
            )
        unknown = sorted(message_value.keys() - _METADATA_MESSAGE_PROPERTIES)
        if unknown:
            return _retry_segment(
                f"SchemaIR metadata messages[{direction}] has unknown properties: "
                + ", ".join(unknown)
            )
        for property_name in sorted(
            _METADATA_MESSAGE_PROPERTIES - message_value.keys() - {"functionType"}
        ):
            message_value[property_name] = None
            diagnostics.append(
                _normalization_diagnostic(
                    segment_name,
                    "MISSING_METADATA_PROPERTY_FILLED_NULL",
                    f"filled messages[{direction}].{property_name} with null placeholder",
                    path=f"messages[{direction}].{property_name}",
                )
            )
        retry_detail = _normalize_metadata_list(
            message_value,
            property_name="xmlEncodingEvidence",
            slots=SCHEMAIR_CANDIDATE_ENCODING_EVIDENCE_PROPERTIES,
            segment_name=segment_name,
            direction=direction,
            diagnostics=diagnostics,
        )
        if retry_detail is not None:
            return _retry_segment(retry_detail, diagnostics)
        retry_detail = _normalize_metadata_list(
            message_value,
            property_name="conditionalConstraints",
            slots=SCHEMAIR_CANDIDATE_CONDITION_PROPERTIES,
            segment_name=segment_name,
            direction=direction,
            diagnostics=diagnostics,
            nested_evidence=True,
        )
        if retry_detail is not None:
            return _retry_segment(retry_detail, diagnostics)
        conditions = message_value.get("conditionalConstraints")
        if isinstance(conditions, list):
            for condition_index, condition in enumerate(conditions):
                if not isinstance(condition, dict):
                    continue
                for property_name in ("controllingFieldPath", "targetFieldPath"):
                    path_value = condition.get(property_name)
                    if path_value not in allowed_paths[direction]:
                        diagnostics.append(
                            _normalization_diagnostic(
                                segment_name,
                                "UNKNOWN_CONDITION_PATH",
                                f"preserved {property_name} for public Validator",
                                path=(
                                    f"messages[{direction}].conditionalConstraints"
                                    f"[{condition_index}].{property_name}"
                                ),
                            )
                        )
        by_direction[direction] = message_value
    metadata["messages"] = [by_direction[direction] for direction in ("ASSEMBLY", "PARSE")]
    disposition = (
        SegmentDisposition.INVALID_DRAFT
        if diagnostics
        else SegmentDisposition.ACCEPT
    )
    return SegmentValidationResult(disposition, metadata, tuple(diagnostics))


def _normalize_metadata_list(
    message: dict[str, Any],
    *,
    property_name: str,
    slots: set[str],
    segment_name: str,
    direction: str,
    diagnostics: list[NormalizationDiagnostic],
    nested_evidence: bool = False,
) -> str | None:
    value = message.get(property_name)
    if value is None:
        return None
    if not isinstance(value, list):
        diagnostics.append(
            _normalization_diagnostic(
                segment_name,
                "INVALID_METADATA_COLLECTION_PRESERVED",
                f"preserved invalid {property_name} for public Validator",
                path=f"messages[{direction}].{property_name}",
            )
        )
        return None
    for index, item in enumerate(value):
        item_path = f"messages[{direction}].{property_name}[{index}]"
        if not isinstance(item, dict):
            value[index] = {slot: None for slot in slots}
            diagnostics.append(
                _normalization_diagnostic(
                    segment_name,
                    "INVALID_METADATA_ITEM_REPLACED",
                    f"replaced {property_name} item with null placeholders",
                    path=item_path,
                )
            )
            item = value[index]
        unknown = sorted(item.keys() - slots)
        if unknown:
            return f"{item_path} has unknown properties: {', '.join(unknown)}"
        for slot in sorted(slots - item.keys()):
            item[slot] = None
            diagnostics.append(
                _normalization_diagnostic(
                    segment_name,
                    "MISSING_NESTED_SLOT_FILLED_NULL",
                    f"filled {property_name}.{slot} with null placeholder",
                    path=f"{item_path}.{slot}",
                )
            )
        if nested_evidence:
            evidence = item.get("evidence")
            if not isinstance(evidence, dict):
                item["evidence"] = {
                    slot: None for slot in SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES
                }
                diagnostics.append(
                    _normalization_diagnostic(
                        segment_name,
                        "INVALID_NESTED_VALUE_REPLACED",
                        "replaced condition evidence with null placeholders",
                        path=f"{item_path}.evidence",
                    )
                )
            else:
                unknown_evidence = sorted(
                    evidence.keys() - SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES
                )
                if unknown_evidence:
                    return (
                        f"{item_path}.evidence has unknown properties: "
                        + ", ".join(unknown_evidence)
                    )
                for slot in sorted(
                    SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES - evidence.keys()
                ):
                    evidence[slot] = None
                    diagnostics.append(
                        _normalization_diagnostic(
                            segment_name,
                            "MISSING_NESTED_SLOT_FILLED_NULL",
                            f"filled condition evidence.{slot} with null placeholder",
                            path=f"{item_path}.evidence.{slot}",
                        )
                    )
    return None


def _normalization_diagnostic(
    segment: str,
    code: str,
    action: str,
    *,
    path: str,
) -> NormalizationDiagnostic:
    return NormalizationDiagnostic(
        segment=segment,
        code=code,
        action=action,
        severity="ERROR",
        path=path,
    )


def _retry_segment(
    detail: str,
    diagnostics: list[NormalizationDiagnostic] | None = None,
) -> SegmentValidationResult:
    return SegmentValidationResult(
        SegmentDisposition.RETRY_SEGMENT,
        None,
        tuple(diagnostics or ()),
        detail=detail,
    )


def _property_mismatch(value: Mapping[str, Any], expected: set[str]) -> str:
    missing = sorted(expected - value.keys())
    unknown = sorted(value.keys() - expected)
    details = []
    if missing:
        details.append("missing properties: " + ", ".join(missing))
    if unknown:
        details.append("unknown properties: " + ", ".join(unknown))
    return "SchemaIR metadata segment has invalid properties (" + "; ".join(details) + ")"


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
        if expected["dataType"] == "object" and field.get("required") is not None and not isinstance(field.get("required"), bool):
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
    metadata_is_profile_validated: bool = False,
) -> dict[str, Any]:
    validated_metadata = (
        deepcopy(metadata)
        if metadata_is_profile_validated
        else validate_schemair_metadata_segment(metadata, structure=structure)
    )
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
    artifact: Mapping[str, Any],
    validation_result: Mapping[str, Any] | None = None,
    *,
    normalization_diagnostics: tuple[NormalizationDiagnostic, ...] | None = (),
) -> str:
    validation = validation_result if isinstance(validation_result, Mapping) else {}
    validated = validation.get("validatedArtifact")
    summary = validation.get("summary")
    content_hash = validated.get("contentHash") if isinstance(validated, Mapping) else None
    status = validation.get("status")
    counts = summary if isinstance(summary, Mapping) else {}
    parts = [
        "# SchemaIR Draft 校验审查说明",
        "",
        f"内容 hash: {_markdown_code(content_hash or '未提供')}",
        "",
        f"状态: {_markdown_code(status or 'unknown')}",
        "",
        (
            "校验汇总: "
            f"ERROR={counts.get('errorCount', 0)}，"
            f"WARNING={counts.get('warningCount', 0)}，"
            f"INFO={counts.get('infoCount', 0)}，"
            f"BLOCKING={counts.get('blockingCount', 0)}"
        ),
        "",
        "## 问题清单",
        "",
    ]

    contexts, ordered_contexts = _schemair_review_contexts(artifact)
    raw_issues = validation.get("issues")
    issues = [item for item in raw_issues if isinstance(item, Mapping)] if isinstance(raw_issues, list) else []
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    unbound: list[Mapping[str, Any]] = []
    conditional_info: list[Mapping[str, Any]] = []
    other_info: list[Mapping[str, Any]] = []
    for issue in issues:
        if issue.get("severity") == "INFO":
            if issue.get("code") == "CONDITIONAL_FIELD":
                conditional_info.append(issue)
            else:
                other_info.append(issue)
            continue
        context_key = _matching_schemair_context_key(issue.get("path"), contexts)
        if context_key is None:
            unbound.append(issue)
        else:
            grouped.setdefault(context_key, []).append(issue)

    detailed_contexts: set[str] = set()
    blocking_entries: list[tuple[tuple[Any, ...], str | None, list[Mapping[str, Any]]]] = []
    reminder_entries: list[tuple[tuple[Any, ...], str | None, list[Mapping[str, Any]]]] = []
    for context_key, context_issues in grouped.items():
        context = contexts[context_key]
        entry = (context["sortKey"], context_key, context_issues)
        if any(item.get("blocking") is True for item in context_issues):
            blocking_entries.append(entry)
        elif any(item.get("severity") != "INFO" for item in context_issues):
            reminder_entries.append(entry)
    for issue in unbound:
        entry = (
            (4, str(issue.get("path") or ""), str(issue.get("code") or "")),
            None,
            [issue],
        )
        if issue.get("blocking") is True:
            blocking_entries.append(entry)
        elif issue.get("severity") != "INFO":
            reminder_entries.append(entry)

    parts.extend(["### 必须处理（Blocking）", ""])
    if not blocking_entries:
        parts.append("- 无 blocking issue。")
    else:
        for _, context_key, entry_issues in sorted(blocking_entries, key=lambda item: item[0]):
            _append_schemair_issue_entry(parts, contexts.get(context_key), entry_issues)
            if context_key is not None:
                detailed_contexts.add(context_key)

    parts.extend(["", "### 非阻塞提醒", ""])
    if not reminder_entries:
        parts.append("- 无非阻塞 WARNING。")
    else:
        for _, context_key, entry_issues in sorted(reminder_entries, key=lambda item: item[0]):
            _append_schemair_issue_entry(parts, contexts.get(context_key), entry_issues)
            if context_key is not None:
                detailed_contexts.add(context_key)

    parts.extend(["", "### 信息项（按方向汇总）", ""])
    _append_schemair_info_summary(parts, conditional_info, other_info, contexts)

    parts.extend(["", "## 确定性归一化记录", ""])
    if normalization_diagnostics is None:
        parts.append("- 未取得可信归一化记录；Validator 结果不受影响，请核对当前 generation lineage 对应的 attempt evidence。")
    elif not normalization_diagnostics:
        parts.append("- 未执行确定性归一化。")
    else:
        for diagnostic in normalization_diagnostics:
            location = diagnostic.selector or diagnostic.path or "segment"
            parts.append(
                f"- [{diagnostic.severity}] {_markdown_code(diagnostic.code)} "
                f"{_markdown_code(diagnostic.segment)} {_markdown_code(location)}："
                f"{_normalization_action_zh(diagnostic.code)}"
            )

    parts.extend(["", "## 显式 Review 证据", ""])
    evidence_items = _schemair_explicit_review_evidence(
        ordered_contexts, detailed_contexts=detailed_contexts
    )
    parts.extend(evidence_items or ["- 未发现未重复呈现的显式 Review 证据。"])
    return "\n".join(parts) + "\n"


_SCHEMAIR_SECTION_RANK = {"Envelope": 0, "ASSEMBLY": 1, "PARSE": 2, "生命周期": 3}
_SCHEMAIR_ISSUE_CODE_RANK = {
    "UNCERTAIN_FIELD": 0,
    "LOW_CONFIDENCE": 1,
    "NON_DIRECT_EVIDENCE": 2,
}
_SCHEMAIR_ISSUE_TEXT = {
    "UNCERTAIN_FIELD": ("字段被标记为不确定，不能进入 Final。", "对照 Final DocIR 确认语义后，更新不确定性标记和说明。"),
    "LOW_CONFIDENCE": ("字段置信度低于当前审查阈值。", "复核来源证据，并确认置信度是否准确。"),
    "NON_DIRECT_EVIDENCE": ("字段证据不是直接证据。", "确认推导或假设是否成立；必要时补充直接证据。"),
    "XML_ENCODING_CONFLICT": ("XML encoding 证据与规范值存在未解决冲突。", "确认银行实际编码并记录冲突处置。"),
    "RESOLVED_XML_ENCODING_CONFLICT": ("XML encoding 冲突已声明解决，仍需人工复核。", "核对解决依据和 Review Note。"),
    "CONDITION_REVIEW_NOT_APPROVED": ("结构化条件尚未通过 Human Review。", "逐项核对控制字段、目标字段和条件后批准该条件。"),
    "REVIEW_NOT_APPROVED": ("SchemaIR 尚未通过 Human Review。", "先清除全部 blocking issue，再对准确 Draft hash 执行批准。"),
    "ARTIFACT_NOT_FINAL": ("当前产物仍为 Draft，不能进入可信链。", "完成校验和 Human Review 后再生成 Final。"),
    "CONDITIONAL_FIELD": ("字段包含条件语义。", "按方向核对 conditionText；完整路径以 Validation Result 为准。"),
    "DOCIR_APPROVAL_EVIDENCE_INVALID": ("上游 Final DocIR 的批准证据无效。", "恢复准确的 DocIR approval evidence 后重新校验。"),
    "DRAFT_GENERATION_LINEAGE_MISSING": ("缺少 Draft generation lineage。", "恢复与当前 Draft 匹配的 generation result。"),
    "DRAFT_GENERATION_LINEAGE_MISMATCH": ("Draft generation lineage 与当前任务或依赖不一致。", "核对 task、source、selector 和当前 Draft 后重新生成或恢复正确 lineage。"),
}


def _schemair_review_contexts(
    artifact: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    contexts: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []

    def add(path: str, section: str, label: str, value: Mapping[str, Any], order: int) -> None:
        context = {
            "path": path,
            "section": section,
            "label": label,
            "value": value,
            "sortKey": (_SCHEMAIR_SECTION_RANK[section], order, path),
        }
        contexts[path] = context
        ordered.append(context)

    envelope = artifact.get("envelope")
    sections: list[tuple[str, Mapping[str, Any], int | None]] = []
    if isinstance(envelope, Mapping):
        add("envelope", "Envelope", "Envelope 元数据", envelope, 0)
        sections.append(("Envelope", envelope, None))
    messages = artifact.get("messages")
    if isinstance(messages, list):
        for message_index, message in enumerate(messages):
            if not isinstance(message, Mapping):
                continue
            direction = message.get("functionType")
            if direction in {"ASSEMBLY", "PARSE"}:
                add(
                    f"messages[{message_index}]",
                    str(direction),
                    f"{direction} 元数据",
                    message,
                    0,
                )
                sections.append((str(direction), message, message_index))
    for section, value, message_index in sections:
        fields = value.get("fields")
        if isinstance(fields, list):
            for index, field in enumerate(fields):
                if not isinstance(field, Mapping) or not isinstance(field.get("path"), str):
                    continue
                field_name = field.get("fieldName")
                add(
                    str(field["path"]),
                    section,
                    f"字段 {_markdown_code(field_name)}",
                    field,
                    1000 + index,
                )
        if section == "Envelope":
            continue
        assert message_index is not None
        encoding = value.get("xmlEncodingEvidence")
        if isinstance(encoding, list):
            for index, item in enumerate(encoding):
                if isinstance(item, Mapping):
                    path = f"messages[{message_index}].xmlEncodingEvidence[{index}]"
                    add(path, section, f"XML encoding 证据 {index + 1}", item, 100 + index)
        conditions = value.get("conditionalConstraints")
        if isinstance(conditions, list):
            for index, item in enumerate(conditions):
                if isinstance(item, Mapping):
                    path = f"messages[{message_index}].conditionalConstraints[{index}]"
                    add(path, section, f"条件 {index + 1}", item, 500 + index)
    lifecycle = artifact.get("review")
    if isinstance(lifecycle, Mapping):
        add("review.status", "生命周期", "Review 状态", lifecycle, 1)
    add("status", "生命周期", "Artifact 状态", artifact, 0)
    return contexts, ordered


def _matching_schemair_context_key(
    path: Any, contexts: Mapping[str, Mapping[str, Any]]
) -> str | None:
    if not isinstance(path, str):
        return None
    matches = [
        key for key in contexts if path == key or path.startswith(f"{key}.")
    ]
    return max(matches, key=len) if matches else None


def _append_schemair_issue_entry(
    parts: list[str],
    context: Mapping[str, Any] | None,
    issues: list[Mapping[str, Any]],
) -> None:
    codes = sorted(
        {str(item.get("code") or "UNKNOWN") for item in issues},
        key=lambda code: (_SCHEMAIR_ISSUE_CODE_RANK.get(code, 100), code),
    )
    issue_path = str(issues[0].get("path") or "未提供")
    if context is None:
        parts.append(f"- [未绑定] {_markdown_code(issue_path)}")
        value: Mapping[str, Any] = {}
    else:
        parts.append(
            f"- [{context['section']}] {context['label']} {_markdown_code(context['path'])}"
        )
        value = context["value"] if isinstance(context.get("value"), Mapping) else {}
    parts.append("  - Issue code: " + "、".join(_markdown_code(code) for code in codes))
    explanations: list[str] = []
    actions: list[str] = []
    for code in codes:
        explanation, action = _schemair_issue_text(code)
        if explanation not in explanations:
            explanations.append(explanation)
        if action not in actions:
            actions.append(action)
    parts.append("  - 说明：" + _join_chinese_sentences(explanations))
    structured = _schemair_structured_values(value)
    if structured:
        parts.append("  - 当前结构化值：" + "；".join(structured))
    model_notes = _schemair_model_notes(value)
    if model_notes:
        parts.append("  - 模型原始说明：" + "；".join(model_notes))
    evidence_notes = _schemair_evidence_notes(value)
    if evidence_notes:
        parts.append("  - 来源证据：" + "；".join(evidence_notes))
    parts.append("  - 建议动作：" + _join_chinese_sentences(actions))


def _schemair_issue_text(code: str) -> tuple[str, str]:
    known = _SCHEMAIR_ISSUE_TEXT.get(code)
    if known is not None:
        return known
    if code.startswith("MISSING_"):
        return ("SchemaIR 缺少公开 contract 要求的属性或证据。", "在不伪造事实的前提下补齐该属性并重新校验。")
    if code.startswith("UNKNOWN_"):
        return ("SchemaIR 含有公开 contract 未声明的属性或引用。", "核对来源并删除或修正未声明内容。")
    if code.startswith("INVALID_"):
        return ("SchemaIR 的结构化值不符合公开 contract。", "按 issue code/path 修正结构化值后重新校验。")
    if "DUPLICATE" in code:
        return ("SchemaIR 存在不允许的重复结构或引用。", "定位重复项并保留唯一、来源准确的表达。")
    if code.endswith("_MISMATCH") or code.endswith("_CONFLICT"):
        return ("SchemaIR 的相关结构化事实彼此不一致。", "对照 Final DocIR 解决冲突后重新校验。")
    return (
        "Validator 报告了尚未注册中文解释的问题；原始详情保留在 `schemair-validation-result.json`。",
        "按相同 issue code/path 查看原始 Validation Result，并由 Human 决定处置。",
    )


def _schemair_structured_values(value: Mapping[str, Any]) -> list[str]:
    details: list[str] = []
    evidence = value.get("evidence")
    if isinstance(evidence, Mapping):
        details.append(f"evidence.kind={_markdown_code(evidence.get('kind'))}")
    for key in ("confidence", "uncertain", "required", "occurs"):
        if key not in value:
            continue
        current = value.get(key)
        if isinstance(current, bool):
            rendered = str(current).lower()
        elif current is None:
            rendered = "null"
        else:
            rendered = str(current)
        details.append(f"{key}={_markdown_code(rendered)}")
    for key in ("sourceKind", "observedValue", "disposition", "operator", "literal", "effect"):
        if key in value:
            current = "null" if value.get(key) is None else str(value.get(key))
            details.append(f"{key}={_markdown_code(current)}")
    return details


def _schemair_model_notes(value: Mapping[str, Any]) -> list[str]:
    notes: list[str] = []
    candidates = [
        ("uncertainReason", value.get("uncertainReason")),
        ("reviewNote", value.get("reviewNote")),
    ]
    for label, raw in candidates:
        text = _optional_text(raw)
        if text is not None:
            notes.append(f"{label}={_markdown_safe_prose(text)}")
    return notes


def _schemair_evidence_notes(value: Mapping[str, Any]) -> list[str]:
    evidence = value.get("evidence")
    note = _optional_text(evidence.get("note")) if isinstance(evidence, Mapping) else None
    return [_markdown_safe_prose(note)] if note is not None else []


def _join_chinese_sentences(values: list[str]) -> str:
    normalized = [value.rstrip("。；") for value in values]
    return "；".join(normalized) + "。"


def _markdown_safe_prose(value: str) -> str:
    """将不可信原文约束在当前 Markdown 列表项内，不改变其语言。"""

    flattened = " ".join(
        line.strip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()
    )
    escaped = flattened.replace("\\", "\\\\")
    for character in ("`", "*", "_", "[", "]", "(", ")", "#"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("<", "&lt;").replace(">", "&gt;")


def _markdown_code(value: Any) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    fence = "`"
    while fence in text:
        fence += "`"
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def _append_schemair_info_summary(
    parts: list[str],
    conditional_issues: list[Mapping[str, Any]],
    other_issues: list[Mapping[str, Any]],
    contexts: Mapping[str, Mapping[str, Any]],
) -> None:
    by_section: dict[str, list[str]] = {"Envelope": [], "ASSEMBLY": [], "PARSE": []}
    unbound: list[Mapping[str, Any]] = []
    for issue in conditional_issues:
        key = _matching_schemair_context_key(issue.get("path"), contexts)
        context = contexts.get(key) if key is not None else None
        if context is None or context.get("section") not in by_section:
            unbound.append(issue)
            continue
        value = context.get("value")
        field_name = value.get("fieldName") if isinstance(value, Mapping) else None
        name = str(field_name or context.get("path"))
        if name not in by_section[str(context["section"])]:
            by_section[str(context["section"])].append(name)
    emitted = False
    for section in ("Envelope", "ASSEMBLY", "PARSE"):
        names = by_section[section]
        if not names:
            continue
        emitted = True
        rendered = "、".join(_markdown_code(name) for name in names)
        parts.append(
            f"- {section}：条件字段 {len(names)} 个：{rendered}。完整逐条路径请查看 `schemair-validation-result.json`。"
        )
    for issue in sorted(unbound, key=lambda item: (str(item.get("path") or ""), str(item.get("code") or ""))):
        emitted = True
        explanation, _ = _schemair_issue_text(str(issue.get("code") or "UNKNOWN"))
        parts.append(
            f"- [未绑定] {_markdown_code(issue.get('code'))} "
            f"{_markdown_code(issue.get('path') or '未提供')}：{explanation}"
        )
    for issue in sorted(
        other_issues,
        key=lambda item: (str(item.get("path") or ""), str(item.get("code") or "")),
    ):
        emitted = True
        context_key = _matching_schemair_context_key(issue.get("path"), contexts)
        context = contexts.get(context_key) if context_key is not None else None
        section = context.get("section") if context is not None else "未绑定"
        explanation, _ = _schemair_issue_text(str(issue.get("code") or "UNKNOWN"))
        parts.append(
            f"- [{section}] {_markdown_code(issue.get('code'))} "
            f"{_markdown_code(issue.get('path') or '未提供')}：{explanation}"
        )
    if not emitted:
        parts.append("- Validator 未报告 INFO。")


def _normalization_action_zh(code: str) -> str:
    if code == "SCALAR_REQUIRED_REMOVED":
        return "已删除仅适用于 Object 字段的 `required` 属性；未复制被删除的原始值。"
    if code == "NULLABLE_PROPERTY_FILLED":
        return "已为缺失的 nullable 属性补入 `null`；未补造业务事实。"
    if code == "NESTED_WIRE_SLOT_FILLED":
        return "已为缺失的嵌套 wire slot 补入显式 `null` placeholder。"
    return "已按内置 Profile 执行确定性归一化；未在 Notes 中复制原始值。"


def _schemair_explicit_review_evidence(
    contexts: list[Mapping[str, Any]],
    *,
    detailed_contexts: set[str],
) -> list[str]:
    items: list[str] = []
    for context in sorted(contexts, key=lambda item: item["sortKey"]):
        path = str(context["path"])
        if path in detailed_contexts or context["section"] == "生命周期":
            continue
        value = context.get("value")
        if not isinstance(value, Mapping):
            continue
        evidence = value.get("evidence")
        evidence_kind = evidence.get("kind") if isinstance(evidence, Mapping) else None
        review_note = _optional_text(value.get("reviewNote"))
        uncertain_reason = _optional_text(value.get("uncertainReason"))
        evidence_note = _optional_text(evidence.get("note")) if isinstance(evidence, Mapping) else None
        is_condition = context["label"].startswith("条件 ")
        if is_condition and evidence_kind == "DIRECT":
            continue
        if not is_condition and review_note is None and uncertain_reason is None and evidence_kind in {None, "DIRECT"}:
            continue
        details: list[str] = []
        if evidence_kind is not None:
            details.append(f"evidence.kind=`{evidence_kind}`")
        if review_note is not None:
            details.append(f"reviewNote={_markdown_safe_prose(review_note)}")
        if uncertain_reason is not None:
            details.append(f"uncertainReason={_markdown_safe_prose(uncertain_reason)}")
        if evidence_note is not None:
            details.append(f"evidence.note={_markdown_safe_prose(evidence_note)}")
        if details:
            items.append(
                f"- [{context['section']}] {context['label']} {_markdown_code(path)}："
                + "；".join(details)
            )
    return items


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
