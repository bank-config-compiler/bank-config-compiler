from __future__ import annotations

from copy import deepcopy

import pytest

from bank_config_compiler.docir_draft import (
    DocIRDraftError,
    build_docir_field_batches,
    merge_docir_extraction_segments,
    render_docir_extraction,
    render_docir_review_notes,
    validate_docir_field_details_segment,
    validate_docir_interface_envelope_segment,
    validate_docir_markdown,
    validate_docir_messages_outline_segment,
    validate_docir_markdown_wire,
)


def metadata(key: str, value: str, review_note: str = "") -> dict[str, str]:
    return {"key": key, "value": value, "reviewNote": review_note}


def field(
    index: str,
    item: str,
    *,
    multiplicity: str,
    field_type: str,
    required: str,
) -> dict[str, str]:
    return {
        "index": index,
        "or": "",
        "item": item,
        "multiplicity": multiplicity,
        "type": field_type,
        "required": required,
        "description": f"{item} description",
        "preValidation": "source format",
        "platformValidation": "platform check",
        "review": "",
    }


def docir_extraction() -> dict:
    return {
        "contractVersion": "docir-extraction/v1",
        "interface": {
            "metadata": [
                metadata("Source Document", "raw-doc.md", "logical source"),
                metadata("Version", "120", "source version"),
                metadata("Message Format", "XML", "source format"),
                metadata("Interface Name", "测试接口", "source title"),
                metadata("Interface Code", "b2e9999", "source title"),
            ]
        },
        "sourceContext": ["仅使用显式来源。", "通用示例不投影交易字段。"],
        "envelope": {
            "metadata": [
                metadata("Evidence Scope", "通用结构章节", "explicit source"),
                metadata("Applies To", "ASSEMBLY, PARSE"),
                metadata("Root Path", "bocb2e", "derived path"),
                metadata("Envelope Name", "bocb2e"),
            ],
            "fields": [
                field("1", "bocb2e", multiplicity="[1..1]", field_type="Object", required="Y"),
                field(
                    "1.1",
                    "@version",
                    multiplicity="[0..1]",
                    field_type="String",
                    required="N",
                ),
            ],
        },
        "assembly": {
            "metadata": [
                metadata("Description", "请求报文"),
                metadata("Root Path", "bocb2e/trans/trn-test-rq", "derived path"),
                metadata("Function Type", "ASSEMBLY"),
                metadata("Message Name", "test-rq"),
            ],
            "fields": [
                field("2", "trn-test-rq", multiplicity="[1..1]", field_type="Object", required="Y"),
                field("2.1", "request", multiplicity="[1..1]", field_type="String", required="Y"),
            ],
            "conditions": ["仅保留来源明确的请求条件。"],
        },
        "parse": {
            "metadata": [
                metadata("Description", "响应报文"),
                metadata("Root Path", "bocb2e/trans/trn-test-rs", "derived path"),
                metadata("Function Type", "PARSE"),
                metadata("Message Name", "test-rs"),
            ],
            "fields": [
                field("3", "trn-test-rs", multiplicity="[1..1]", field_type="Object", required="Y"),
                field("3.1", "status", multiplicity="[1..1]", field_type="Object", required="Y"),
                field("3.1.1", "code", multiplicity="[1..1]", field_type="String", required="Y"),
            ],
            "conditions": ["响应状态码来自来源文档。"],
        },
    }


def test_render_docir_extraction_produces_deterministic_frozen_markdown_wire() -> None:
    rendered = render_docir_extraction(docir_extraction())

    assert [line for line in rendered.splitlines() if line.startswith("# ")] == [
        "# Interface",
        "# Source Context / 来源上下文",
        "# Envelope",
        "# Message: ASSEMBLY",
        "# Message: PARSE",
    ]
    assert rendered.count("| Key | Value | Review Note |") == 4
    assert (
        rendered.count(
            "| Index | Or | Message Item | Mult. | Type | Required | 说明 | "
            "前置机校验点/格式 | 接口平台校验点 | Review |"
        )
        == 3
    )
    assert "| Interface Code | b2e9999 | source title |" in rendered
    assert "| 1.1 |  | 　`@version` | [0..1] | String | N |" in rendered
    assert "| 3.1.1 |  | 　　`code` | [1..1] | String | Y |" in rendered
    assert "## Conditions\n\n- 仅保留来源明确的请求条件。" in rendered
    assert "Path | Tag" not in rendered
    assert rendered.endswith("\n")
    validate_docir_markdown_wire(rendered)


def test_historical_non_repeating_ranges_remain_valid() -> None:
    result = validate_docir_markdown(render_docir_extraction(docir_extraction()))

    assert result["summary"]["errorCount"] == 0


def test_markdown_validator_rejects_type_that_conflicts_with_tree() -> None:
    rendered = render_docir_extraction(docir_extraction())
    rendered = rendered.replace(
        "| 3.1 |  | 　`status` | [1..1] | Object | Y |",
        "| 3.1 |  | 　`status` | [1..1] | String | Y |",
    )

    result = validate_docir_markdown(rendered)

    assert "DOCIR_TYPE_STRUCTURE" in {issue["code"] for issue in result["issues"]}


def test_required_and_explicit_lower_bound_conflict_is_a_warning() -> None:
    rendered = render_docir_extraction(docir_extraction())
    rendered = rendered.replace(
        "| 1.1 |  | 　`@version` | [0..1] | String | N |",
        "| 1.1 |  | 　`@version` | [1..1] | String | N |",
    )

    result = validate_docir_markdown(rendered)

    assert result["summary"]["errorCount"] == 0
    assert result["summary"]["warningCount"] == 1
    assert {issue["code"] for issue in result["issues"]} == {
        "DOCIR_REQUIRED_MULTIPLICITY_CONFLICT"
    }


@pytest.mark.parametrize(
    ("property_name", "invalid_value", "message"),
    [
        ("multiplicity", "0..1", "multiplicity"),
        ("type", "container", "type"),
        ("required", "是", "required"),
        ("item", "<request>", "item"),
    ],
)
def test_render_docir_extraction_rejects_invalid_field_wire_values(
    property_name: str,
    invalid_value: str,
    message: str,
) -> None:
    extraction = docir_extraction()
    extraction["assembly"]["fields"][1][property_name] = invalid_value

    with pytest.raises(DocIRDraftError, match=message):
        render_docir_extraction(extraction)


def test_render_docir_extraction_rejects_unknown_properties() -> None:
    extraction = docir_extraction()
    extraction["goldenPath"] = "samples/golden/docir.expected.md"

    with pytest.raises(DocIRDraftError, match="unknown properties"):
        render_docir_extraction(extraction)


def test_render_docir_extraction_requires_review_when_wire_value_is_unknown() -> None:
    extraction = docir_extraction()
    response_field = extraction["parse"]["fields"][2]
    response_field["required"] = ""
    response_field["review"] = ""

    with pytest.raises(DocIRDraftError, match="原文未说明，待人工确认"):
        render_docir_extraction(extraction)


def test_render_docir_extraction_rejects_missing_parent_index() -> None:
    extraction = docir_extraction()
    extraction["assembly"]["fields"][1]["index"] = "2.1.1"

    with pytest.raises(DocIRDraftError, match="parent index"):
        render_docir_extraction(extraction)


def test_render_docir_extraction_rejects_out_of_order_sibling_indexes() -> None:
    extraction = docir_extraction()
    extraction["assembly"]["fields"].extend(
        [
            field("2.2", "second", multiplicity="[1..1]", field_type="String", required="Y"),
        ]
    )
    extraction["assembly"]["fields"][1:] = reversed(
        extraction["assembly"]["fields"][1:]
    )

    with pytest.raises(DocIRDraftError, match="index order"):
        render_docir_extraction(extraction)


def test_markdown_wire_validator_rejects_missing_ideographic_indentation() -> None:
    rendered = render_docir_extraction(docir_extraction())
    invalid = rendered.replace("　`@version`", "`@version`")

    with pytest.raises(DocIRDraftError, match="indentation"):
        validate_docir_markdown_wire(invalid)


def test_render_docir_review_notes_is_deterministic_and_preserves_locations() -> None:
    extraction = docir_extraction()
    extraction["interface"]["metadata"][0]["reviewNote"] = "核对来源。"
    extraction["envelope"]["metadata"][0]["reviewNote"] = "核对来源。"
    extraction["assembly"]["fields"][1]["review"] = "核对来源。"

    notes = render_docir_review_notes(extraction)

    assert notes == (
        "# 待人工确认\n\n"
        "## 固定检查清单\n\n"
        "- 核对 Interface、Envelope、ASSEMBLY、PARSE 的字段和父子层级是否完整忠实于 raw-doc。\n"
        "- 核对 Source Context 的适用范围，确认通用 XML 示例或其他交易代码未污染目标交易字段。\n"
        "- 核对所有冲突、空值和“原文未说明”项均已显式保留，未被模型静默推断。\n"
        "- 核对 ASSEMBLY 与 PARSE Conditions 是否完整且仅包含 raw-doc 支持的条件。\n\n"
        "## 提取项\n\n"
        "- Interface.Metadata[Interface Code]: source title\n"
        "- Interface.Metadata[Interface Name]: source title\n"
        "- Interface.Metadata[Message Format]: source format\n"
        "- Interface.Metadata[Version]: source version\n"
        "- Interface.Metadata[Source Document]: 核对来源。\n"
        "- Envelope.Metadata[Root Path]: derived path\n"
        "- Envelope.Metadata[Evidence Scope]: 核对来源。\n"
        "- ASSEMBLY.Metadata[Root Path]: derived path\n"
        "- PARSE.Metadata[Root Path]: derived path\n"
        "- ASSEMBLY[2.1 request]: 核对来源。\n"
    )
    assert notes.count("核对来源。") == 3
    assert render_docir_review_notes(extraction) == notes


def test_render_docir_review_notes_rejects_invalid_extraction() -> None:
    with pytest.raises(DocIRDraftError, match="must be an object"):
        render_docir_review_notes("确认版本。")


def segmented_extraction() -> tuple[dict, dict, list[dict], list[dict]]:
    extraction = docir_extraction()
    interface_envelope = {
        "contractVersion": "docir-interface-envelope-segment/v1",
        "interface": extraction["interface"],
        "sourceContext": extraction["sourceContext"],
        "envelope": extraction["envelope"],
    }
    messages_outline = {
        "contractVersion": "docir-messages-outline-segment/v1",
        "assembly": {
            "metadata": extraction["assembly"]["metadata"],
            "conditions": extraction["assembly"]["conditions"],
            "fields": [
                {"index": row["index"], "item": row["item"]}
                for row in extraction["assembly"]["fields"]
            ],
        },
        "parse": {
            "metadata": extraction["parse"]["metadata"],
            "conditions": extraction["parse"]["conditions"],
            "fields": [
                {"index": row["index"], "item": row["item"]}
                for row in extraction["parse"]["fields"]
            ],
        },
    }
    assembly_details = [
        {
            "contractVersion": "docir-field-details-segment/v1",
            "direction": "ASSEMBLY",
            "batchIndex": 1,
            "fields": extraction["assembly"]["fields"],
        }
    ]
    parse_details = [
        {
            "contractVersion": "docir-field-details-segment/v1",
            "direction": "PARSE",
            "batchIndex": 1,
            "fields": extraction["parse"]["fields"],
        }
    ]
    return interface_envelope, messages_outline, assembly_details, parse_details


def test_segmented_extraction_merges_to_existing_docir_contract() -> None:
    interface_envelope, messages_outline, assembly_details, parse_details = (
        segmented_extraction()
    )

    merged = merge_docir_extraction_segments(
        interface_envelope=interface_envelope,
        messages_outline=messages_outline,
        assembly_details=assembly_details,
        parse_details=parse_details,
    )

    assert render_docir_extraction(merged) == render_docir_extraction(docir_extraction())
    assert merged["interface"]["metadata"][0]["key"] == "Interface Code"
    assert merged["assembly"]["fields"] == docir_extraction()["assembly"]["fields"]


def test_docir_field_batches_are_contiguous_and_bounded() -> None:
    outline = [
        {"index": "2", "item": "root"},
        *[
            {"index": f"2.{index}", "item": f"field{index}"}
            for index in range(1, 18)
        ],
    ]

    batches = build_docir_field_batches(outline, batch_size=16)

    assert [len(batch) for batch in batches] == [16, 2]
    assert [row for batch in batches for row in batch] == outline


@pytest.mark.parametrize("batch_size", [0, -1, True, 1.5])
def test_docir_field_batches_reject_invalid_batch_size(batch_size: object) -> None:
    with pytest.raises(DocIRDraftError, match="positive integer"):
        build_docir_field_batches([{"index": "2", "item": "root"}], batch_size=batch_size)


def test_messages_outline_rejects_missing_parent() -> None:
    _, messages_outline, _, _ = segmented_extraction()
    messages_outline["assembly"]["fields"][1]["index"] = "2.1.1"

    with pytest.raises(DocIRDraftError, match="parent index"):
        validate_docir_messages_outline_segment(messages_outline)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda fields: fields.pop(),
        lambda fields: fields.append(deepcopy(fields[-1])),
        lambda fields: fields.reverse(),
        lambda fields: fields[0].update(item="different"),
    ],
)
def test_field_details_must_exactly_match_target_outline(mutation) -> None:
    _, messages_outline, assembly_details, _ = segmented_extraction()
    expected = messages_outline["assembly"]["fields"]
    mutation(assembly_details[0]["fields"])

    with pytest.raises(DocIRDraftError, match="target outline"):
        validate_docir_field_details_segment(
            assembly_details[0],
            direction="ASSEMBLY",
            batch_index=1,
            expected_outline=expected,
        )


def test_segment_validators_normalize_complete_sections() -> None:
    interface_envelope, messages_outline, assembly_details, _ = segmented_extraction()

    normalized_interface = validate_docir_interface_envelope_segment(interface_envelope)
    normalized_outline = validate_docir_messages_outline_segment(messages_outline)
    assert normalized_interface["interface"]["metadata"][0]["key"] == "Interface Code"
    assert normalized_interface["envelope"]["fields"] == interface_envelope["envelope"]["fields"]
    assert normalized_outline["assembly"]["metadata"][0]["key"] == "Message Name"
    assert normalized_outline["parse"]["fields"] == messages_outline["parse"]["fields"]
    assert validate_docir_field_details_segment(
        assembly_details[0],
        direction="ASSEMBLY",
        batch_index=1,
        expected_outline=messages_outline["assembly"]["fields"],
    ) == assembly_details[0]
