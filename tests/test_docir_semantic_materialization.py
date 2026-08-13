from __future__ import annotations

from copy import deepcopy

import pytest

from bank_config_compiler.docir_draft import (
    DOCIR_MATERIALIZER_CONTRACT,
    DocIRDraftError,
    UNKNOWN_REVIEW_MARKER,
    materialize_docir_semantic_candidate,
    render_docir_extraction,
    validate_docir_markdown,
)


def _metadata(key: str, value: str) -> dict[str, str]:
    return {"key": key, "value": value, "reviewNote": ""}


def _node(
    selector: str,
    item: str,
    node_kind: str,
    *,
    children: list[dict] | None = None,
    multiplicity: str = "[1..1]",
    field_type: str = "Object",
    required: str = "Y",
) -> dict:
    return {
        "selector": selector,
        "item": item,
        "nodeKind": node_kind,
        "children": children or [],
        "or": "",
        "multiplicity": multiplicity,
        "type": field_type,
        "required": required,
        "description": f"{item} description",
        "validation": "",
        "review": "",
    }


def semantic_candidate() -> dict:
    return {
        "contractVersion": "docir-semantic-candidate/v2",
        "interface": {
            "metadata": [
                _metadata("Interface Code", "b2e9999"),
                _metadata("Interface Name", "测试接口"),
                _metadata("Message Format", "XML"),
                _metadata("Version", "120"),
                _metadata("Source Document", "raw-doc.md"),
            ]
        },
        "sourceContext": ["仅使用显式来源。"],
        "envelope": {
            "metadata": [
                _metadata("Envelope Name", "bocb2e"),
                _metadata("Root Path", "bocb2e"),
                _metadata("Applies To", "ASSEMBLY, PARSE"),
                _metadata("Evidence Scope", "通用结构章节"),
            ],
            "nodes": [
                _node(
                    "envelope:1",
                    "bocb2e",
                    "XML_ELEMENT",
                    children=[
                        _node(
                            "envelope:1.1",
                            "@version",
                            "XML_ATTRIBUTE",
                            field_type="String",
                            required="N",
                        ),
                        _node(
                            "envelope:1.2",
                            "head",
                            "XML_ELEMENT",
                            children=[
                                _node(
                                    "envelope:1.2.1",
                                    "requestId",
                                    "XML_ELEMENT",
                                    field_type="String",
                                )
                            ],
                        ),
                    ],
                )
            ],
        },
        "assembly": {
            "metadata": [
                _metadata("Message Name", "test-rq"),
                _metadata("Function Type", "ASSEMBLY"),
                _metadata("Root Path", "bocb2e/trans/trn-test-rq"),
                _metadata("Description", "请求报文"),
            ],
            "conditions": ["仅保留来源明确的请求条件。"],
            "nodes": [
                _node(
                    "assembly:1",
                    "trn-test-rq",
                    "XML_ELEMENT",
                    children=[
                        _node(
                            "assembly:1.1",
                            "request",
                            "XML_ELEMENT",
                            field_type="String",
                        )
                    ],
                )
            ],
        },
        "parse": {
            "metadata": [
                _metadata("Message Name", "test-rs"),
                _metadata("Function Type", "PARSE"),
                _metadata("Root Path", "bocb2e/trans/trn-test-rs"),
                _metadata("Description", "响应报文"),
            ],
            "conditions": ["仅保留来源明确的响应条件。"],
            "nodes": [
                _node(
                    "parse:1",
                    "trn-test-rs",
                    "XML_ELEMENT",
                    children=[
                        _node(
                            "parse:1.1",
                            "status",
                            "XML_ELEMENT",
                            field_type="String",
                        )
                    ],
                )
            ],
        },
    }


def test_semantic_tree_materializes_canonical_indexes_and_stable_bytes() -> None:
    candidate = semantic_candidate()

    first = materialize_docir_semantic_candidate(candidate)
    second = materialize_docir_semantic_candidate(deepcopy(candidate))

    assert DOCIR_MATERIALIZER_CONTRACT == "docir-semantic-materializer/v3"
    assert [row["index"] for row in first["envelope"]["fields"]] == [
        "1",
        "1.1",
        "1.2",
        "1.2.1",
    ]
    assert [row["index"] for row in first["assembly"]["fields"]] == ["2", "2.1"]
    assert render_docir_extraction(first).encode("utf-8") == render_docir_extraction(
        second
    ).encode("utf-8")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value["assembly"]["nodes"][0]["children"].append(
                deepcopy(value["assembly"]["nodes"][0]["children"][0])
            ),
            "duplicate sibling",
        ),
        (
            lambda value: value["envelope"]["nodes"][0]["children"][0][
                "children"
            ].append(
                _node(
                    "envelope:1.1.1",
                    "illegal",
                    "XML_ELEMENT",
                    field_type="String",
                )
            ),
            "attribute nodes cannot have children",
        ),
        (lambda value: value["parse"].update(nodes=[]), "exactly one root"),
        (
            lambda value: value["assembly"]["nodes"][0].update(
                selector="assembly:7"
            ),
            "selector",
        ),
    ],
)
def test_semantic_tree_rejects_ambiguous_or_incomplete_structure(
    mutation, message: str
) -> None:
    candidate = semantic_candidate()
    mutation(candidate)

    with pytest.raises(DocIRDraftError, match=message):
        materialize_docir_semantic_candidate(candidate)


def test_missing_required_is_the_only_default_semantic_blocker() -> None:
    candidate = semantic_candidate()
    node = candidate["parse"]["nodes"][0]["children"][0]
    node.pop("required")
    node["multiplicity"] = ""
    node.pop("type")
    node["review"] = "来源仅展示示例。"

    extraction = materialize_docir_semantic_candidate(candidate)
    field = extraction["parse"]["fields"][1]
    markdown = render_docir_extraction(extraction)
    result = validate_docir_markdown(markdown)

    assert field["required"] == ""
    assert field["multiplicity"] == ""
    assert field["type"] == "String"
    assert field["review"] == f"来源仅展示示例。；{UNKNOWN_REVIEW_MARKER}"
    assert result["contractVersion"] == "docir-validation-result/v1"
    assert result["status"] == "failed"
    assert result["summary"]["errorCount"] == 1
    assert {item["code"] for item in result["issues"]} == {
        "DOCIR_SEMANTIC_VALUE_MISSING"
    }


def test_type_is_derived_from_tree_and_explicit_scalar_semantics() -> None:
    candidate = semantic_candidate()
    root = candidate["envelope"]["nodes"][0]
    container = root["children"][1]
    attribute = root["children"][0]
    leaf = container["children"][0]
    root.pop("type")
    container["type"] = "String"
    attribute.pop("type")
    leaf["type"] = "Date"

    extraction = materialize_docir_semantic_candidate(candidate)
    fields = {field["item"]: field for field in extraction["envelope"]["fields"]}
    result = validate_docir_markdown(render_docir_extraction(extraction))

    assert fields["bocb2e"]["type"] == "Object"
    assert fields["head"]["type"] == "Object"
    assert fields["@version"]["type"] == "String"
    assert fields["requestId"]["type"] == "Date"
    assert "候选 Type 与结构规范不一致，已按规范物化，待人工复核" in fields["head"]["review"]
    assert result["summary"]["errorCount"] == 0
    assert result["summary"]["warningCount"] == 1
    assert {issue["code"] for issue in result["issues"]} == {
        "DOCIR_TYPE_NORMALIZED"
    }


def test_non_repeating_multiplicity_is_blank_but_repeated_object_is_preserved() -> None:
    candidate = semantic_candidate()
    candidate["envelope"]["nodes"][0]["multiplicity"] = "[1..1]"
    candidate["parse"]["nodes"][0].update(
        multiplicity="[0..1000]",
        required="N",
    )

    extraction = materialize_docir_semantic_candidate(candidate)
    envelope_root = extraction["envelope"]["fields"][0]
    parse_root = extraction["parse"]["fields"][0]
    result = validate_docir_markdown(render_docir_extraction(extraction))

    assert envelope_root["multiplicity"] == ""
    assert parse_root["multiplicity"] == "[0..1000]"
    assert result["summary"]["errorCount"] == 0


def test_invalid_multiplicity_remains_distinct_from_valid_blank() -> None:
    candidate = semantic_candidate()
    candidate["parse"]["nodes"][0]["multiplicity"] = "[]"

    extraction = materialize_docir_semantic_candidate(candidate)
    field = extraction["parse"]["fields"][0]
    markdown = render_docir_extraction(extraction)
    result = validate_docir_markdown(markdown)

    assert field["multiplicity"] == ""
    assert "候选 Mult. 不符合规范，已留空，待人工确认" in field["review"]
    assert result["status"] == "failed"
    assert {item["code"] for item in result["issues"]} == {
        "DOCIR_MULTIPLICITY_REJECTED"
    }


def test_invalid_required_remains_a_missing_human_decision() -> None:
    candidate = semantic_candidate()
    candidate["parse"]["nodes"][0]["required"] = "UNKNOWN"

    extraction = materialize_docir_semantic_candidate(candidate)
    field = extraction["parse"]["fields"][0]
    result = validate_docir_markdown(render_docir_extraction(extraction))

    assert field["required"] == ""
    assert UNKNOWN_REVIEW_MARKER in field["review"]
    assert result["status"] == "failed"
    assert {item["code"] for item in result["issues"]} == {
        "DOCIR_SEMANTIC_VALUE_MISSING"
    }


def test_markdown_validator_aggregates_independent_wire_errors() -> None:
    markdown = render_docir_extraction(
        materialize_docir_semantic_candidate(semantic_candidate())
    )
    invalid = markdown.replace("　`request`", "`request`").replace(
        "　`status`", "`status`"
    )

    result = validate_docir_markdown(invalid)

    assert result["status"] == "failed"
    assert result["summary"]["errorCount"] == 2
    assert [item["path"] for item in result["issues"]] == [
        "ASSEMBLY.Fields[2.1]",
        "PARSE.Fields[3.1]",
    ]
