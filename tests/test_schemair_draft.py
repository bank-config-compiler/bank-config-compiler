import json
from copy import deepcopy
from pathlib import Path

import pytest

from bank_config_compiler.draft_generation import DraftGenerationError
from bank_config_compiler.ir_materialization import (
    materialize_schemair_candidate,
    parse_final_docir_structure,
)
from bank_config_compiler.schemair_draft import (
    BankXmlSchemaIRProfile,
    SCHEMAIR_FIELD_SEMANTICS_SEGMENT_CONTRACT,
    SCHEMAIR_METADATA_SEGMENT_CONTRACT,
    build_schemair_field_batches,
    merge_schemair_semantic_segments,
    render_schemair_review_notes,
    validate_schemair_field_semantics_segment,
    validate_schemair_metadata_segment,
)
from bank_config_compiler.segmented_artifact import (
    NormalizationDiagnostic,
    SegmentDisposition,
)
from bank_config_compiler.schemair_validator import validate_schemair


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE = REPO_ROOT / "samples" / "draft-generation" / "b2eboc-b2e0061"


def _docir() -> str:
    return (CASE / "docir-final.md").read_text(encoding="utf-8")


def _candidate() -> dict:
    return json.loads((CASE / "artifacts/schemair-draft.json").read_text(encoding="utf-8"))


def _metadata_segment(candidate: dict) -> dict:
    return {
        "contractVersion": SCHEMAIR_METADATA_SEGMENT_CONTRACT,
        "envelope": {"description": candidate["envelope"]["description"]},
        "messages": [
            {key: deepcopy(value) for key, value in message.items() if key != "fields"}
            for message in candidate["messages"]
        ],
    }


def _field_segments(candidate: dict, structure: dict, *, batch_size: int = 8) -> dict[str, list[dict]]:
    source_fields = {
        "ENVELOPE": candidate["envelope"]["fields"],
        **{message["functionType"]: message["fields"] for message in candidate["messages"]},
    }
    result: dict[str, list[dict]] = {}
    for section, batches in build_schemair_field_batches(
        structure, batch_size=batch_size
    ).items():
        fields = source_fields[section]
        result[section] = []
        offset = 0
        for batch_index, selectors in enumerate(batches, start=1):
            segment_fields = []
            for selector, field in zip(
                selectors, fields[offset : offset + len(selectors)], strict=True
            ):
                segment_fields.append({"selector": selector["selector"], **deepcopy(field)})
            offset += len(selectors)
            result[section].append(
                {
                    "contractVersion": SCHEMAIR_FIELD_SEMANTICS_SEGMENT_CONTRACT,
                    "section": section,
                    "batchIndex": batch_index,
                    "fields": segment_fields,
                }
            )
    return result


def test_schemair_field_batches_are_bounded_and_code_owned() -> None:
    structure = parse_final_docir_structure(_docir())

    batches = build_schemair_field_batches(structure, batch_size=8)

    assert [len(batch) for batch in batches["ENVELOPE"]] == [8, 5]
    assert [len(batch) for batch in batches["ASSEMBLY"]] == [8, 8, 8, 3]
    assert [len(batch) for batch in batches["PARSE"]] == [8, 2]
    assert batches["ENVELOPE"][0][0] == {
        "selector": "envelope:1",
        "fieldName": "bocb2e",
        "path": "Root.bocb2e",
        "nodeKind": "XML_ELEMENT",
        "dataType": "object",
    }


def test_bank_xml_profile_default_sized_plan_has_five_logical_segments() -> None:
    structure = parse_final_docir_structure(_docir())

    plan = BankXmlSchemaIRProfile().build_segment_plan(structure, batch_size=16)

    assert [spec.segment_id for spec in plan] == [
        "schemair-metadata",
        "schemair-envelope-fields-001",
        "schemair-assembly-fields-001",
        "schemair-assembly-fields-002",
        "schemair-parse-fields-001",
    ]
    assert all(spec.payload_hash.startswith("sha256:") for spec in plan)
    assert plan[1].selector_hash is not None


def test_schemair_segments_merge_to_existing_candidate_and_materialize() -> None:
    docir = _docir()
    structure = parse_final_docir_structure(docir)
    candidate = _candidate()
    metadata = validate_schemair_metadata_segment(
        _metadata_segment(candidate), structure=structure
    )
    details = _field_segments(candidate, structure)
    validated_details = {
        section: [
            validate_schemair_field_semantics_segment(
                segment,
                section=section,
                batch_index=index,
                expected_selectors=selectors,
            )
            for index, (segment, selectors) in enumerate(
                zip(
                    segments,
                    build_schemair_field_batches(structure, batch_size=8)[section],
                    strict=True,
                ),
                start=1,
            )
        ]
        for section, segments in details.items()
    }

    merged = merge_schemair_semantic_segments(
        metadata=metadata,
        field_segments=validated_details,
        structure=structure,
        batch_size=8,
    )

    assert merged == candidate
    draft = materialize_schemair_candidate(
        merged,
        docir_final=docir,
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
        interface_code="b2e0061",
    )
    assert validate_schemair(draft)["summary"]["errorCount"] == 0


def test_schemair_field_segment_rejects_missing_and_reordered_selectors() -> None:
    structure = parse_final_docir_structure(_docir())
    selectors = build_schemair_field_batches(structure, batch_size=8)["ENVELOPE"][0]
    segment = _field_segments(_candidate(), structure)["ENVELOPE"][0]

    missing = deepcopy(segment)
    missing["fields"].pop()
    with pytest.raises(DraftGenerationError, match="exactly cover target selectors"):
        validate_schemair_field_semantics_segment(
            missing,
            section="ENVELOPE",
            batch_index=1,
            expected_selectors=selectors,
        )

    reordered = deepcopy(segment)
    reordered["fields"][0], reordered["fields"][1] = (
        reordered["fields"][1],
        reordered["fields"][0],
    )
    with pytest.raises(DraftGenerationError, match="selector does not match"):
        validate_schemair_field_semantics_segment(
            reordered,
            section="ENVELOPE",
            batch_index=1,
            expected_selectors=selectors,
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("extra", "exactly cover target selectors"),
        ("duplicate", "selector does not match"),
        ("section", "section does not match"),
        ("batch", "batchIndex does not match"),
        ("field-name", "fieldName does not match"),
        ("length-shape", "invalid properties"),
        ("evidence-shape", "invalid properties"),
    ],
)
def test_schemair_field_segment_rejects_identity_and_nested_shape_changes(
    change: str, message: str
) -> None:
    structure = parse_final_docir_structure(_docir())
    selectors = build_schemair_field_batches(structure, batch_size=8)["ENVELOPE"][0]
    segment = deepcopy(_field_segments(_candidate(), structure)["ENVELOPE"][0])

    if change == "extra":
        segment["fields"].append(deepcopy(segment["fields"][-1]))
    elif change == "duplicate":
        segment["fields"][1] = deepcopy(segment["fields"][0])
    elif change == "section":
        segment["section"] = "ASSEMBLY"
    elif change == "batch":
        segment["batchIndex"] = 2
    elif change == "field-name":
        segment["fields"][0]["fieldName"] = "wrong"
    elif change == "length-shape":
        segment["fields"][0]["length"]["extra"] = None
    elif change == "evidence-shape":
        segment["fields"][0]["evidence"].pop("note")

    with pytest.raises(DraftGenerationError, match=message):
        validate_schemair_field_semantics_segment(
            segment,
            section="ENVELOPE",
            batch_index=1,
            expected_selectors=selectors,
        )

def test_schemair_field_segment_enforces_object_and_scalar_required_shape() -> None:
    structure = parse_final_docir_structure(_docir())
    selectors = build_schemair_field_batches(structure, batch_size=8)["ENVELOPE"][0]
    segment = _field_segments(_candidate(), structure)["ENVELOPE"][0]

    object_without_required = deepcopy(segment)
    object_without_required["fields"][0].pop("required")
    with pytest.raises(DraftGenerationError, match="missing properties: required"):
        validate_schemair_field_semantics_segment(
            object_without_required,
            section="ENVELOPE",
            batch_index=1,
            expected_selectors=selectors,
        )

    scalar_with_required = deepcopy(segment)
    scalar_with_required["fields"][1]["required"] = False
    with pytest.raises(DraftGenerationError, match="unknown properties: required"):
        validate_schemair_field_semantics_segment(
            scalar_with_required,
            section="ENVELOPE",
            batch_index=1,
            expected_selectors=selectors,
        )


def test_bank_xml_profile_normalizes_scalar_required_with_diagnostic() -> None:
    structure = parse_final_docir_structure(_docir())
    selectors = build_schemair_field_batches(structure, batch_size=8)["ENVELOPE"][0]
    segment = deepcopy(_field_segments(_candidate(), structure)["ENVELOPE"][0])
    segment["fields"][1]["required"] = None

    result = BankXmlSchemaIRProfile().validate_field_segment(
        segment,
        section="ENVELOPE",
        batch_index=1,
        expected_selectors=selectors,
    )

    assert result.disposition == SegmentDisposition.NORMALIZED
    assert result.value is not None
    assert "required" not in result.value["fields"][1]
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "SCALAR_REQUIRED_REMOVED"
    ]
    assert result.diagnostics[0].selector == "envelope:2"


def test_bank_xml_profile_materializes_unknown_object_required_as_invalid_draft() -> None:
    docir = _docir()
    structure = parse_final_docir_structure(docir)
    candidate = _candidate()
    segments = _field_segments(candidate, structure)
    segments["ENVELOPE"][0]["fields"][0].pop("required")
    profile = BankXmlSchemaIRProfile()
    normalized = profile.validate_field_segment(
        segments["ENVELOPE"][0],
        section="ENVELOPE",
        batch_index=1,
        expected_selectors=build_schemair_field_batches(structure, batch_size=8)[
            "ENVELOPE"
        ][0],
    )

    assert normalized.disposition == SegmentDisposition.INVALID_DRAFT
    assert normalized.value is not None
    assert normalized.value["fields"][0]["required"] is None
    segments["ENVELOPE"][0] = normalized.value
    merged = merge_schemair_semantic_segments(
        metadata=_metadata_segment(candidate),
        field_segments=segments,
        structure=structure,
        batch_size=8,
    )
    draft = materialize_schemair_candidate(
        merged,
        docir_final=docir,
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
        interface_code="b2e0061",
    )

    root = draft["envelope"]["fields"][0]
    assert root["required"] is None
    assert root["occurs"] is None
    validation = validate_schemair(draft)
    assert validation["summary"]["errorCount"] >= 2
    assert {issue["code"] for issue in validation["issues"]} >= {
        "INVALID_FIELD_TYPE",
        "INVALID_OCCURS",
    }


def test_bank_xml_profile_retries_unknown_non_code_owned_property() -> None:
    structure = parse_final_docir_structure(_docir())
    selectors = build_schemair_field_batches(structure, batch_size=8)["ENVELOPE"][0]
    segment = deepcopy(_field_segments(_candidate(), structure)["ENVELOPE"][0])
    segment["fields"][1]["inventedBankFact"] = "do not keep"

    result = BankXmlSchemaIRProfile().validate_field_segment(
        segment,
        section="ENVELOPE",
        batch_index=1,
        expected_selectors=selectors,
    )

    assert result.disposition == SegmentDisposition.RETRY_SEGMENT
    assert result.value is None
    assert "inventedBankFact" in (result.detail or "")


def test_schemair_metadata_rejects_condition_paths_outside_direction_scope() -> None:
    structure = parse_final_docir_structure(_docir())
    metadata = _metadata_segment(_candidate())
    assembly = next(
        message for message in metadata["messages"] if message["functionType"] == "ASSEMBLY"
    )
    assembly["conditionalConstraints"][0]["targetFieldPath"] = "unknown.path"

    with pytest.raises(DraftGenerationError, match="unknown targetFieldPath"):
        validate_schemair_metadata_segment(metadata, structure=structure)


def test_bank_xml_profile_keeps_unknown_condition_path_for_invalid_draft() -> None:
    structure = parse_final_docir_structure(_docir())
    metadata = _metadata_segment(_candidate())
    assembly = next(
        message for message in metadata["messages"] if message["functionType"] == "ASSEMBLY"
    )
    assembly["conditionalConstraints"][0]["targetFieldPath"] = "unknown.path"
    spec = BankXmlSchemaIRProfile().build_segment_plan(structure, batch_size=16)[0]

    result = BankXmlSchemaIRProfile().validate_segment(
        spec, metadata, structure=structure
    )

    assert result.disposition == SegmentDisposition.INVALID_DRAFT
    assert result.value is not None
    assert (
        result.value["messages"][0]["conditionalConstraints"][0]["targetFieldPath"]
        == "unknown.path"
    )
    assert any(
        diagnostic.code == "UNKNOWN_CONDITION_PATH"
        for diagnostic in result.diagnostics
    )


def test_schemair_review_notes_are_deterministic_and_include_validator_issues() -> None:
    candidate = _candidate()
    validation = {
        "issues": [
            {
                "severity": "ERROR",
                "code": "TEST_ISSUE",
                "path": "messages[0].fields[0]",
                "message": "Test validation issue.",
            }
        ]
    }

    first = render_schemair_review_notes(candidate, validation)
    second = render_schemair_review_notes(deepcopy(candidate), deepcopy(validation))

    assert first == second
    assert "envelope.fields[1] `@version`" in first
    assert "TEST_ISSUE" in first
    assert "Test validation issue." in first


def test_schemair_review_notes_include_normalization_diagnostics_without_values() -> None:
    diagnostic = NormalizationDiagnostic(
        segment="schemair-parse-fields-001",
        selector="parse:2",
        path="Root.bocb2e.trans.trn-b2e0061-rs.status",
        code="SCALAR_REQUIRED_REMOVED",
        action="removed required",
        severity="WARNING",
    )

    notes = render_schemair_review_notes(
        _candidate(), normalization_diagnostics=(diagnostic,)
    )

    assert "## Normalization Diagnostics" in notes
    assert "SCALAR_REQUIRED_REMOVED" in notes
    assert "parse:2" in notes
    assert "removed required" in notes


def test_schemair_review_notes_include_metadata_notes_and_non_direct_conditions() -> None:
    candidate = _candidate()
    assembly = candidate["messages"][0]
    assembly["xmlEncodingEvidence"][0]["reviewNote"] = "确认 encoding 冲突处置。"
    assembly["conditionalConstraints"][0]["evidence"] = {
        "kind": "DERIVED",
        "note": "条件 path 由原文位置推导。",
    }

    notes = render_schemair_review_notes(candidate)

    assert "assembly.xmlEncodingEvidence[0]" in notes
    assert "确认 encoding 冲突处置。" in notes
    assert "assembly.conditionalConstraints[0]" in notes
    assert "evidence=DERIVED" in notes
    assert "条件 path 由原文位置推导。" in notes
