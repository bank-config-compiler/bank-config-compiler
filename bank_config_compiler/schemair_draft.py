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
    candidate: Mapping[str, Any],
    validation_result: Mapping[str, Any] | None = None,
    *,
    normalization_diagnostics: tuple[NormalizationDiagnostic, ...] = (),
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
    parts.extend(["", "## Normalization Diagnostics", ""])
    if not normalization_diagnostics:
        parts.append("- 未执行确定性归一化。")
    else:
        for diagnostic in normalization_diagnostics:
            location = diagnostic.selector or diagnostic.path or "segment"
            parts.append(
                f"- [{diagnostic.severity}] `{diagnostic.code}` "
                f"`{diagnostic.segment}` `{location}`: {diagnostic.action}"
            )
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
