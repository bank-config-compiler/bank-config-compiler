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


def _materialized_draft() -> dict:
    return materialize_schemair_candidate(
        _candidate(),
        docir_final=_docir(),
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
        interface_code="b2e0061",
    )


def _validation_result(*issues: dict) -> dict:
    issue_list = list(issues)
    return {
        "contractVersion": "schemair-validation-result/v1",
        "status": "failed" if any(item.get("blocking") for item in issue_list) else "passed",
        "validatedArtifact": {
            "contentHash": "sha256:" + "1" * 64,
        },
        "summary": {
            "errorCount": sum(item["severity"] == "ERROR" for item in issue_list),
            "warningCount": sum(item["severity"] == "WARNING" for item in issue_list),
            "infoCount": sum(item["severity"] == "INFO" for item in issue_list),
            "blockingCount": sum(item.get("blocking") is True for item in issue_list),
        },
        "issues": issue_list,
    }


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
    draft = _materialized_draft()
    field = draft["envelope"]["fields"][1]
    field["uncertain"] = True
    field["uncertainReason"] = "模型原始说明。"
    field["reviewNote"] = "需要人工确认。"
    field["confidence"] = 0.72
    field["evidence"] = {"kind": "DERIVED", "note": "从原文上下文推导。"}
    validation = _validation_result(
        {
            "severity": "WARNING",
            "blocking": True,
            "code": "UNCERTAIN_FIELD",
            "path": field["path"],
            "message": "English validator message.",
        },
        {
            "severity": "WARNING",
            "blocking": False,
            "code": "LOW_CONFIDENCE",
            "path": field["path"],
            "message": "English validator message.",
        },
        {
            "severity": "WARNING",
            "blocking": False,
            "code": "NON_DIRECT_EVIDENCE",
            "path": field["path"],
            "message": "English validator message.",
        },
    )

    first = render_schemair_review_notes(draft, validation)
    second = render_schemair_review_notes(deepcopy(draft), deepcopy(validation))

    assert first == second
    assert first.startswith("# SchemaIR Draft 校验审查说明\n")
    assert "内容 hash: `sha256:" in first
    assert "状态: `failed`" in first
    assert "ERROR=0，WARNING=3，INFO=0，BLOCKING=1" in first
    assert "### 必须处理（Blocking）" in first
    assert first.count(f"`{field['path']}`") == 1
    assert "`UNCERTAIN_FIELD`、`LOW_CONFIDENCE`、`NON_DIRECT_EVIDENCE`" in first
    assert "evidence.kind=`DERIVED`" in first
    assert "confidence=`0.72`" in first
    assert "uncertain=`true`" in first
    assert "English validator message." not in first
    assert "模型原始说明。" in first


def test_schemair_review_notes_order_blocking_items_and_group_info_by_direction() -> None:
    draft = _materialized_draft()
    envelope = draft["envelope"]["fields"][1]
    assembly = draft["messages"][0]["fields"][1]
    parse = draft["messages"][1]["fields"][2]
    validation = _validation_result(
        {
            "severity": "WARNING",
            "blocking": True,
            "code": "REVIEW_NOT_APPROVED",
            "path": "review.status",
            "message": "ignored",
        },
        {
            "severity": "WARNING",
            "blocking": True,
            "code": "UNCERTAIN_FIELD",
            "path": parse["path"],
            "message": "ignored",
        },
        {
            "severity": "INFO",
            "blocking": False,
            "code": "CONDITIONAL_FIELD",
            "path": parse["path"],
            "message": "ignored",
        },
        {
            "severity": "WARNING",
            "blocking": True,
            "code": "UNCERTAIN_FIELD",
            "path": envelope["path"],
            "message": "ignored",
        },
        {
            "severity": "INFO",
            "blocking": False,
            "code": "CONDITIONAL_FIELD",
            "path": assembly["path"],
            "message": "ignored",
        },
        {
            "severity": "WARNING",
            "blocking": True,
            "code": "UNCERTAIN_FIELD",
            "path": assembly["path"],
            "message": "ignored",
        },
    )

    notes = render_schemair_review_notes(draft, validation)

    assert notes.index("[Envelope]") < notes.index("[ASSEMBLY]")
    assert notes.index("[ASSEMBLY]") < notes.index("[PARSE]")
    assert notes.index("[PARSE]") < notes.index("[生命周期]")
    assert f"ASSEMBLY：条件字段 1 个：`{assembly['fieldName']}`" in notes
    assert f"PARSE：条件字段 1 个：`{parse['fieldName']}`" in notes
    assert "完整逐条路径请查看 `schemair-validation-result.json`" in notes


def test_schemair_review_notes_use_chinese_fallback_for_unknown_issue_code() -> None:
    validation = _validation_result(
        {
            "severity": "INFO",
            "blocking": False,
            "code": "FUTURE_SCHEMAIR_ISSUE",
            "path": "future.path",
            "message": "Do not surface this English sentence.",
        }
    )

    notes = render_schemair_review_notes(_materialized_draft(), validation)

    assert "`FUTURE_SCHEMAIR_ISSUE`" in notes
    assert "Validator 报告了尚未注册中文解释的问题" in notes
    assert "schemair-validation-result.json" in notes
    assert "Do not surface this English sentence." not in notes


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
        _materialized_draft(),
        _validation_result(),
        normalization_diagnostics=(diagnostic,),
    )

    assert "## 确定性归一化记录" in notes
    assert "SCALAR_REQUIRED_REMOVED" in notes
    assert "parse:2" in notes
    assert "已删除仅适用于 Object 字段的 `required` 属性" in notes
    assert "removed required" not in notes


def test_schemair_review_notes_include_metadata_notes_and_non_direct_conditions() -> None:
    draft = _materialized_draft()
    assembly = draft["messages"][0]
    assembly["xmlEncodingEvidence"][0]["reviewNote"] = "确认 encoding 冲突处置。"
    assembly["conditionalConstraints"][0]["evidence"] = {
        "kind": "DERIVED",
        "note": "条件 path 由原文位置推导。",
    }

    notes = render_schemair_review_notes(draft, _validation_result())

    assert "## 显式 Review 证据" in notes
    assert "[ASSEMBLY] XML encoding 证据 1" in notes
    assert "确认 encoding 冲突处置。" in notes
    assert "[ASSEMBLY] 条件 1" in notes
    assert "evidence.kind=`DERIVED`" in notes
    assert "条件 path 由原文位置推导。" in notes
