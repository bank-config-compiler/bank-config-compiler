from __future__ import annotations

import logging
from copy import deepcopy

import pytest

from bank_config_compiler.artifact_validation import ArtifactIntegrityError, canonical_json_bytes, content_hash
from bank_config_compiler.schemair_validator import validate_schemair


def review(*, approved: bool) -> dict:
    return {
        "status": "APPROVED" if approved else "PENDING",
        "reviewer": "deng" if approved else None,
        "reviewedAt": "2026-08-09T10:00:00+08:00" if approved else None,
        "note": "测试确认。" if approved else None,
    }


def field(
    *,
    path: str,
    field_name: str,
    parent_path: str,
    level: int,
    node_kind: str,
    data_type: str,
    required: bool = True,
    multiple: bool = False,
    has_children: bool = False,
    occurs: str = "1..1",
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
        "required": required,
        "multiple": multiple,
        "hasChildren": has_children,
        "occurs": occurs,
        "description": field_name,
        "conditionText": None,
        "sourceText": f"| <{field_name}> | {field_name} |",
        "evidence": {"kind": "DIRECT", "note": "来自测试 fixture。"},
        "confidence": 1.0,
        "uncertain": False,
        "uncertainReason": None,
        "reviewNote": None,
    }


def valid_schemair(*, final: bool = True) -> dict:
    return {
        "contractVersion": "schemair/v2",
        "schemaId": "b2eboc-b2e0061-schema",
        "schemaVersion": "v1",
        "status": "FINAL" if final else "DRAFT",
        "review": review(approved=final),
        "interfaceCode": "b2e0061",
        "interfaceName": "公对私转账汇款",
        "messageFormat": "XML",
        "protocolVersion": "120",
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
                field(
                    path="Root.bocb2e.@version",
                    field_name="@version",
                    parent_path="Root.bocb2e",
                    level=2,
                    node_kind="XML_ATTRIBUTE",
                    data_type="string",
                ),
            ],
        },
        "messages": [
            {
                "functionType": "ASSEMBLY",
                "messageName": "request",
                "rootPath": "Root.bocb2e.request",
                "xmlEncoding": "UTF-8",
                "xmlEncodingEvidence": [
                    {
                        "sourceKind": "HUMAN_BANK_CONFIRMATION",
                        "sourceRef": "human-bank-offline-confirmation:2026-08-06",
                        "observedValue": "UTF-8",
                        "disposition": "SUPPORTS",
                        "reviewNote": None,
                    }
                ],
                "description": "请求报文",
                "fields": [
                    field(
                        path="Root.bocb2e.request",
                        field_name="request",
                        parent_path="Root.bocb2e",
                        level=2,
                        node_kind="XML_ELEMENT",
                        data_type="object",
                        has_children=True,
                    ),
                    field(
                        path="Root.bocb2e.request.value",
                        field_name="value",
                        parent_path="Root.bocb2e.request",
                        level=3,
                        node_kind="XML_ELEMENT",
                        data_type="string",
                    ),
                ],
                "conditionalConstraints": [],
            }
        ],
    }


def issue_codes(result: dict) -> list[str]:
    return [item["code"] for item in result["issues"]]


def test_final_schemair_passes_and_binds_complete_content() -> None:
    schemair = valid_schemair()

    result = validate_schemair(schemair)

    assert result["contractVersion"] == "schemair-validation-result/v2"
    assert result["validatedArtifact"] == {
        "kind": "SchemaIR",
        "artifactId": "b2eboc-b2e0061-schema",
        "artifactVersion": "v1",
        "artifactContractVersion": "schemair/v2",
        "contentHash": content_hash(schemair),
    }
    assert result["status"] == "passed"
    assert result["finalEligible"] is True
    assert result["summary"] == {
        "schemaId": "b2eboc-b2e0061-schema",
        "interfaceCode": "b2e0061",
        "messageFormat": "XML",
        "messageCount": 1,
        "fieldCount": 4,
        "errorCount": 0,
        "warningCount": 0,
        "infoCount": 0,
        "blockingCount": 0,
    }


def test_draft_is_valid_but_not_final_eligible() -> None:
    result = validate_schemair(valid_schemair(final=False))

    assert result["status"] == "passed_with_warnings"
    assert result["finalEligible"] is False
    assert set(issue_codes(result)) == {"ARTIFACT_NOT_FINAL", "REVIEW_NOT_APPROVED"}
    assert all(item["blocking"] for item in result["issues"])


def test_legacy_contract_and_json_product_enum_are_rejected() -> None:
    schemair = valid_schemair()
    schemair["contractVersion"] = "schemair/v1"
    schemair["messageFormat"] = "JSON"
    schemair["messages"][0]["fields"][1]["nodeKind"] = "JSON_OBJECT"

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert {"INVALID_CONTRACT_VERSION", "INVALID_MESSAGE_FORMAT", "INVALID_NODE_KIND"} <= set(issue_codes(result))


def test_unknown_property_is_rejected_fail_closed() -> None:
    schemair = valid_schemair()
    schemair["generatorHint"] = "do not accept"

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "UNKNOWN_TOP_LEVEL_PROPERTY" in issue_codes(result)


def test_stable_id_requires_lowercase_kebab_case() -> None:
    schemair = valid_schemair()
    schemair["schemaId"] = "B2E0061 Schema"

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "INVALID_SCHEMA_ID" in issue_codes(result)


def test_bool_does_not_satisfy_integer_field_level() -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["fields"][1]["level"] = True

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "INVALID_FIELD_LEVEL" in issue_codes(result)


def test_message_cannot_redefine_envelope_field_path() -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["fields"][0]["path"] = "Root.bocb2e"
    schemair["messages"][0]["fields"][0]["fieldName"] = "bocb2e"
    schemair["messages"][0]["fields"][0]["parentPath"] = "Root"
    schemair["messages"][0]["fields"][0]["level"] = 1
    schemair["messages"][0]["rootPath"] = "Root.bocb2e"

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert "FIELD_PATH_SHADOWS_PARENT_SCOPE" in issue_codes(result)


def test_uncertain_field_is_a_blocking_warning() -> None:
    schemair = valid_schemair()
    target = schemair["messages"][0]["fields"][1]
    target["uncertain"] = True
    target["uncertainReason"] = "需要 Human Review。"

    result = validate_schemair(schemair)

    uncertain = next(item for item in result["issues"] if item["code"] == "UNCERTAIN_FIELD")
    assert result["status"] == "passed_with_warnings"
    assert result["finalEligible"] is False
    assert uncertain["blocking"] is True


def test_required_occurs_conflict_is_blocking_while_fact_is_uncertain() -> None:
    schemair = valid_schemair()
    target = schemair["messages"][0]["fields"][0]
    target["multiple"] = True
    target["occurs"] = "0..1000"
    target["required"] = True
    target["uncertain"] = True
    target["uncertainReason"] = "最小出现次数待确认。"

    result = validate_schemair(schemair)

    assert "REQUIRED_OCCURS_CONFLICT" in issue_codes(result)
    assert result["finalEligible"] is False


def test_unresolved_xml_encoding_conflict_blocks_final() -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["xmlEncodingEvidence"].append(
        {
            "sourceKind": "SOURCE_DOCUMENT",
            "sourceRef": "bank-doc:new-version",
            "observedValue": "GBK",
            "disposition": "UNRESOLVED_CONFLICT",
            "reviewNote": None,
        }
    )

    result = validate_schemair(schemair)

    conflict = next(item for item in result["issues"] if item["code"] == "XML_ENCODING_CONFLICT")
    assert conflict["severity"] == "WARNING"
    assert conflict["blocking"] is True
    assert result["finalEligible"] is False


def test_resolved_xml_encoding_conflict_remains_non_blocking_warning() -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["xmlEncodingEvidence"].append(
        {
            "sourceKind": "SOURCE_DOCUMENT",
            "sourceRef": "bank-doc:historical-example",
            "observedValue": "GBK",
            "disposition": "RESOLVED_CONFLICT",
            "reviewNote": "Human 与银行重新确认当前接口仍使用 UTF-8。",
        }
    )

    result = validate_schemair(schemair)

    assert result["status"] == "passed_with_warnings"
    assert result["finalEligible"] is True
    assert result["issues"][0]["code"] == "RESOLVED_XML_ENCODING_CONFLICT"
    assert result["issues"][0]["blocking"] is False


def test_structured_condition_requires_existing_paths_and_human_review() -> None:
    schemair = valid_schemair(final=False)
    schemair["messages"][0]["conditionalConstraints"].append(
        {
            "controllingFieldPath": "Root.bocb2e.request.value",
            "operator": "EQUALS",
            "literal": "2",
            "targetFieldPath": "Root.bocb2e.request.missing",
            "effect": "REQUIRED",
            "sourceText": "value=2 时目标字段必输。",
            "evidence": {"kind": "DIRECT", "note": "来自银行文档。"},
            "review": review(approved=False),
        }
    )

    result = validate_schemair(schemair)

    assert "UNKNOWN_TARGET_FIELD" in issue_codes(result)
    assert "CONDITION_REVIEW_NOT_APPROVED" in issue_codes(result)
    assert result["finalEligible"] is False


def test_issue_order_is_deterministic() -> None:
    schemair = valid_schemair()
    schemair["messageFormat"] = "JSON"
    schemair["schemaVersion"] = "1"
    schemair["messages"][0]["xmlEncodingEvidence"].append(
        {
            "sourceKind": "SOURCE_DOCUMENT",
            "sourceRef": "bank-doc:new-version",
            "observedValue": "GBK",
            "disposition": "UNRESOLVED_CONFLICT",
            "reviewNote": None,
        }
    )

    first = validate_schemair(schemair)
    second = validate_schemair(deepcopy(schemair))

    assert first["issues"] == second["issues"]
    assert [item["severity"] for item in first["issues"]] == sorted(
        [item["severity"] for item in first["issues"]],
        key={"ERROR": 0, "WARNING": 1, "INFO": 2}.get,
    )


def test_validation_logs_do_not_include_artifact_content(caplog: pytest.LogCaptureFixture) -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["description"] = "SENSITIVE-DESCRIPTION"
    schemair["messages"][0]["fields"][1]["sourceText"] = "RAW-YAML-OR-BANK-TEXT"

    with caplog.at_level(logging.DEBUG):
        validate_schemair(schemair)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "SENSITIVE-DESCRIPTION" not in log_text
    assert "RAW-YAML-OR-BANK-TEXT" not in log_text


def test_canonical_hash_uses_semantic_json_content() -> None:
    left = {"z": [1, 2], "中文": {"b": True, "a": None}}
    right = {"中文": {"a": None, "b": True}, "z": [1, 2]}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert content_hash(left) == content_hash(right)
    assert content_hash(left) != content_hash({**left, "z": [1, 3]})


def test_canonical_hash_rejects_non_finite_values() -> None:
    with pytest.raises(ArtifactIntegrityError):
        content_hash({"value": float("nan")})
