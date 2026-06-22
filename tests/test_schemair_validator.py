from __future__ import annotations

from copy import deepcopy

from bank_config_compiler.schemair_validator import validate_schemair


def valid_schemair() -> dict:
    return {
        "interfaceCode": "b2e0061",
        "interfaceName": "公对私转账汇款",
        "messageFormat": "XML",
        "version": "120",
        "sourceDocument": "samples/golden/b2eboc-b2e0061/raw-doc.md",
        "envelope": {
            "rootPath": "Root.bocb2e",
            "description": "BOCB2E envelope",
            "fields": [
                field(
                    path="Root.bocb2e",
                    field_name="bocb2e",
                    parent_path="Root",
                    level=1,
                    node_kind="XML_ELEMENT",
                    data_type="object",
                    has_children=True,
                ),
            ],
        },
        "messages": [
            {
                "functionType": "ASSEMBLY",
                "messageName": "b2e0061-rq",
                "rootPath": "Root.bocb2e.trans.trn-b2e0061-rq",
                "description": "请求报文",
                "fields": [
                    field(
                        path="Root.bocb2e.trans.trn-b2e0061-rq",
                        field_name="trn-b2e0061-rq",
                        parent_path="Root.bocb2e.trans",
                        level=3,
                        node_kind="XML_ELEMENT",
                        data_type="object",
                        has_children=True,
                    ),
                ],
            },
        ],
    }


def field(
    *,
    path: str,
    field_name: str,
    parent_path: str,
    level: int,
    node_kind: str,
    data_type: str,
    has_children: bool = False,
) -> dict:
    return {
        "path": path,
        "fieldName": field_name,
        "displayName": field_name,
        "parentPath": parent_path,
        "level": level,
        "nodeKind": node_kind,
        "dataType": data_type,
        "format": None,
        "length": {"min": None, "max": None, "raw": None},
        "required": True,
        "multiple": False,
        "hasChildren": has_children,
        "occurs": "1..1",
        "description": field_name,
        "conditionText": None,
        "sourceText": f"| <{field_name}> | {field_name} |",
        "evidence": {"kind": "DIRECT", "note": "来自测试 fixture。"},
        "confidence": 1.0,
        "uncertain": False,
        "uncertainReason": None,
        "reviewNote": None,
        "configGuidance": None,
    }


def issue_codes(result: dict) -> list[str]:
    return [issue["code"] for issue in result["issues"]]


def test_valid_schemair_passes_without_warnings() -> None:
    result = validate_schemair(valid_schemair())

    assert result["contractVersion"] == "schemair-validation-result/v1"
    assert result["status"] == "passed"
    assert result["summary"] == {
        "interfaceCode": "b2e0061",
        "messageFormat": "XML",
        "messageCount": 1,
        "fieldCount": 2,
        "errorCount": 0,
        "warningCount": 0,
        "infoCount": 0,
    }
    assert result["coverage"] == {
        "envelopeFieldCount": 1,
        "messageFieldCount": 1,
        "fieldsByFunctionType": {"ASSEMBLY": 1},
    }
    assert result["issues"] == []


def test_invalid_message_format_returns_error() -> None:
    schemair = valid_schemair()
    schemair["messageFormat"] = "CSV"

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "INVALID_MESSAGE_FORMAT" in issue_codes(result)
    assert result["summary"]["errorCount"] == 1


def test_missing_field_path_returns_field_level_error() -> None:
    schemair = valid_schemair()
    del schemair["envelope"]["fields"][0]["path"]

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert result["issues"][0]["severity"] == "ERROR"
    assert result["issues"][0]["code"] == "MISSING_FIELD_PROPERTY"
    assert result["issues"][0]["path"] is None


def test_invalid_boolean_property_returns_error() -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["fields"][0]["required"] = "true"

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "INVALID_FIELD_TYPE" in issue_codes(result)


def test_confidence_out_of_range_returns_error() -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["fields"][0]["confidence"] = 1.2

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "INVALID_CONFIDENCE" in issue_codes(result)


def test_duplicate_path_within_same_field_set_returns_error() -> None:
    schemair = valid_schemair()
    duplicate = deepcopy(schemair["messages"][0]["fields"][0])
    schemair["messages"][0]["fields"].append(duplicate)

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "DUPLICATE_FIELD_PATH" in issue_codes(result)


def test_invalid_evidence_kind_returns_error() -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["fields"][0]["evidence"]["kind"] = "OBSERVED"

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "INVALID_EVIDENCE_KIND" in issue_codes(result)


def test_review_signals_return_passed_with_warnings_and_info() -> None:
    schemair = valid_schemair()
    schemair["envelope"]["fields"][0]["uncertain"] = True
    schemair["envelope"]["fields"][0]["uncertainReason"] = "需要人工确认。"
    schemair["messages"][0]["fields"][0]["confidence"] = 0.8
    schemair["messages"][0]["fields"][0]["evidence"]["kind"] = "DERIVED"
    schemair["messages"][0]["fields"][0]["conditionText"] = "条件必填。"

    result = validate_schemair(schemair)

    assert result["status"] == "passed_with_warnings"
    assert result["summary"]["errorCount"] == 0
    assert result["summary"]["warningCount"] == 3
    assert result["summary"]["infoCount"] == 1
    assert issue_codes(result) == [
        "UNCERTAIN_FIELD",
        "LOW_CONFIDENCE",
        "NON_DIRECT_EVIDENCE",
        "CONDITIONAL_FIELD",
    ]
