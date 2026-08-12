from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path

import pytest

from bank_config_compiler.artifact_validation import content_hash
from bank_config_compiler.configuration_rules import RulePackage, load_rule_package
from bank_config_compiler.interface_standard_validator import validate_interface_standard


RULE_PACKAGE_DIR = Path(__file__).parents[1] / "configuration-rules" / "v1"


@pytest.fixture(scope="module")
def rule_package() -> RulePackage:
    return load_rule_package(RULE_PACKAGE_DIR)


def review(*, approved: bool) -> dict:
    return {
        "status": "APPROVED" if approved else "PENDING",
        "reviewer": "deng" if approved else None,
        "reviewedAt": "2026-08-09T10:00:00+08:00" if approved else None,
        "note": "测试确认。" if approved else None,
    }


def schema_field(
    *,
    path: str,
    field_name: str,
    parent_path: str,
    level: int,
    data_type: str,
    node_kind: str = "XML_ELEMENT",
    required: bool = True,
    has_children: bool = False,
    multiple: bool = False,
    occurs: str = "1..1",
    length_min: int | None = None,
    length_max: int | None = None,
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
        "length": {"min": length_min, "max": length_max, "raw": None},
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


def valid_schemair() -> dict:
    return {
        "contractVersion": "schemair/v2",
        "schemaId": "test-interface-schema",
        "schemaVersion": "v1",
        "status": "FINAL",
        "review": review(approved=True),
        "interfaceCode": "test001",
        "interfaceName": "测试接口",
        "messageFormat": "XML",
        "protocolVersion": "100",
        "sourceDocument": "tests/fixtures/test.md",
        "envelope": {
            "rootPath": "Root.message",
            "description": "测试 envelope",
            "fields": [
                schema_field(
                    path="Root.message",
                    field_name="message",
                    parent_path="Root",
                    level=1,
                    data_type="object",
                    has_children=True,
                ),
                schema_field(
                    path="Root.message.@version",
                    field_name="@version",
                    parent_path="Root.message",
                    level=2,
                    data_type="string",
                    node_kind="XML_ATTRIBUTE",
                    required=False,
                    occurs="0..1",
                ),
            ],
        },
        "messages": [
            {
                "functionType": "ASSEMBLY",
                "messageName": "request",
                "rootPath": "Root.message.request",
                "xmlEncoding": "UTF-8",
                "xmlEncodingEvidence": [
                    {
                        "sourceKind": "HUMAN_BANK_CONFIRMATION",
                        "sourceRef": "test-confirmation",
                        "observedValue": "UTF-8",
                        "disposition": "SUPPORTS",
                        "reviewNote": None,
                    }
                ],
                "description": "测试请求",
                "fields": [
                    schema_field(
                        path="Root.message.request",
                        field_name="request",
                        parent_path="Root.message",
                        level=2,
                        data_type="object",
                        has_children=True,
                    ),
                    schema_field(
                        path="Root.message.request.mode",
                        field_name="mode",
                        parent_path="Root.message.request",
                        level=3,
                        data_type="string",
                        required=False,
                        occurs="0..1",
                        length_min=0,
                        length_max=1,
                    ),
                    schema_field(
                        path="Root.message.request.value",
                        field_name="value",
                        parent_path="Root.message.request",
                        level=3,
                        data_type="string",
                        required=False,
                        occurs="0..1",
                    ),
                ],
                "conditionalConstraints": [],
            }
        ],
    }


def no_constraint() -> dict:
    return {"state": "NO_CONSTRAINT", "value": None}


def length_constraint(
    *,
    state: str = "NO_CONSTRAINT",
    minimum: int | None = None,
    maximum: int | None = None,
    precision: int | None = None,
    scale: int | None = None,
) -> dict:
    return {
        "state": state,
        "min": minimum,
        "max": maximum,
        "precision": precision,
        "scale": scale,
    }


def standard_field(
    *,
    field_id: str,
    sequence: int,
    field_name: str,
    parent_path: str,
    full_path: str,
    schema_path: str,
    data_type: str,
    required: bool = True,
    length_limit: dict | None = None,
    xml_keys: list[dict] | None = None,
) -> dict:
    rule_references = [
        "STD.FIELD.PARENT_PATH",
        "STD.FIELD.FULL_PATH",
        "STD.FIELD.SEQUENCE",
        "STD.FIELD.DATA_TYPE",
        "STD.CONSTRAINT.VALUE_STATE",
    ]
    if xml_keys:
        rule_references.append("STD.FIELD.XML_KEYS")
    return {
        "fieldId": field_id,
        "sequence": sequence,
        "fieldName": field_name,
        "fieldDescription": field_name,
        "conditionText": None,
        "parentPath": parent_path,
        "fullPath": full_path,
        "required": required,
        "lengthLimit": length_limit or length_constraint(),
        "illegalCharacters": no_constraint(),
        "regex": no_constraint(),
        "dataType": data_type,
        "xmlKeys": xml_keys or [],
        "schemaIrFieldPath": schema_path,
        "conditionalConstraints": [],
        "ruleReferences": rule_references,
        "differences": [],
        "evidence": [
            {
                "kind": "FINAL_SCHEMA_IR",
                "sourceRef": schema_path,
                "note": "测试投影。",
            }
        ],
        "confidence": 1.0,
        "uncertain": False,
        "uncertainReason": None,
        "reviewNote": None,
    }


def valid_standard(schemair: dict, *, final: bool = True) -> dict:
    return {
        "contractVersion": "interface-standard/v1",
        "standardId": "test001-assembly-standard",
        "standardVersion": "v1",
        "status": "FINAL" if final else "DRAFT",
        "review": review(approved=final),
        "interfaceCode": "test001",
        "direction": "ASSEMBLY",
        "schemaIrRef": {
            "schemaId": "test-interface-schema",
            "schemaVersion": "v1",
            "contractVersion": "schemair/v2",
            "contentHash": content_hash(schemair),
        },
        "rulePackageVersion": "v1",
        "xmlEncodingRef": {"functionType": "ASSEMBLY", "value": "UTF-8"},
        "fields": [
            standard_field(
                field_id="test001-assembly-message",
                sequence=1,
                field_name="message",
                parent_path="Root",
                full_path="Root.message",
                schema_path="Root.message",
                data_type="Object",
                xml_keys=[
                    {"name": "@version", "schemaIrFieldPath": "Root.message.@version"}
                ],
            ),
            standard_field(
                field_id="test001-assembly-request",
                sequence=1,
                field_name="request",
                parent_path="Root.message",
                full_path="Root.message.request",
                schema_path="Root.message.request",
                data_type="Object",
            ),
            standard_field(
                field_id="test001-assembly-mode",
                sequence=1,
                field_name="mode",
                parent_path="Root.message.request",
                full_path="Root.message.request.mode",
                schema_path="Root.message.request.mode",
                data_type="String",
                required=False,
                length_limit=length_constraint(state="VALUE", minimum=0, maximum=1),
            ),
            standard_field(
                field_id="test001-assembly-value",
                sequence=2,
                field_name="value",
                parent_path="Root.message.request",
                full_path="Root.message.request.value",
                schema_path="Root.message.request.value",
                data_type="String",
                required=False,
            ),
        ],
    }


def issue_codes(result: dict) -> set[str]:
    return {item["code"] for item in result["issues"]}


def validate(standard: object, schemair: object, rule_package: RulePackage) -> dict:
    return validate_interface_standard(
        standard,
        schemair=schemair,
        rule_package=rule_package,
    )


def test_final_standard_passes_and_binds_dependencies(rule_package: RulePackage) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)

    result = validate(standard, schemair, rule_package)

    assert result["contractVersion"] == "interface-standard-validation-result/v1"
    assert result["validatedArtifact"] == {
        "kind": "InterfaceStandardIR",
        "artifactId": "test001-assembly-standard",
        "artifactVersion": "v1",
        "artifactContractVersion": "interface-standard/v1",
        "contentHash": content_hash(standard),
    }
    assert result["status"] == "passed"
    assert result["finalEligible"] is True
    assert result["summary"] == {
        "standardId": "test001-assembly-standard",
        "interfaceCode": "test001",
        "direction": "ASSEMBLY",
        "rulePackageVersion": "v1",
        "fieldCount": 4,
        "errorCount": 0,
        "warningCount": 0,
        "infoCount": 0,
        "blockingCount": 0,
    }
    assert result["coverage"] == {
        "scalarFieldCount": 2,
        "containerFieldCount": 2,
        "xmlKeyCount": 1,
        "conditionalConstraintCount": 0,
        "differenceCount": 0,
        "uncertainFieldCount": 0,
    }


def test_draft_is_valid_but_not_final_eligible(rule_package: RulePackage) -> None:
    schemair = valid_schemair()

    result = validate(valid_standard(schemair, final=False), schemair, rule_package)

    assert result["status"] == "passed_with_warnings"
    assert result["finalEligible"] is False
    assert issue_codes(result) == {"ARTIFACT_NOT_FINAL", "REVIEW_NOT_APPROVED"}
    assert all(item["blocking"] for item in result["issues"])


def test_contract_is_strict_and_bool_is_not_an_integer(rule_package: RulePackage) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["generatorHint"] = "unsupported"
    del standard["xmlEncodingRef"]
    standard["fields"][0]["sequence"] = True
    standard["fields"][0]["lengthLimit"]["extra"] = 1

    result = validate(standard, schemair, rule_package)

    assert {
        "UNKNOWN_TOP_LEVEL_PROPERTY",
        "MISSING_TOP_LEVEL_PROPERTY",
        "INVALID_FIELD_SEQUENCE",
        "UNKNOWN_LENGTH_PROPERTY",
    } <= issue_codes(result)


def test_dependency_identity_hash_direction_and_rule_version_are_exact(
    rule_package: RulePackage,
) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["interfaceCode"] = "wrong"
    standard["direction"] = "PARSE"
    standard["schemaIrRef"]["schemaVersion"] = "v2"
    standard["schemaIrRef"]["contentHash"] = "sha256:" + "0" * 64
    standard["rulePackageVersion"] = "v2"

    result = validate(standard, schemair, rule_package)

    assert {
        "INTERFACE_CODE_MISMATCH",
        "DIRECTION_NOT_IN_SCHEMAIR",
        "SCHEMAIR_REFERENCE_MISMATCH",
        "SCHEMAIR_HASH_MISMATCH",
        "RULE_PACKAGE_VERSION_MISMATCH",
    } <= issue_codes(result)


def test_paths_sequences_sources_and_coverage_are_closed(rule_package: RulePackage) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["fields"][2]["sequence"] = 3
    standard["fields"][2]["parentPath"] = "Root.wrong"
    standard["fields"][2]["schemaIrFieldPath"] = "Root.message.request.missing"
    standard["fields"][1]["conditionText"] = "不得覆盖银行原始条件。"
    standard["fields"].pop()

    result = validate(standard, schemair, rule_package)

    assert {
        "NON_CONTIGUOUS_FIELD_SEQUENCE",
        "FULL_PATH_PARENT_MISMATCH",
        "UNKNOWN_SCHEMAIR_FIELD_REFERENCE",
        "MISSING_SCHEMAIR_FIELD",
        "CONDITION_TEXT_MISMATCH",
    } <= issue_codes(result)


def test_sequence_is_recomputed_against_schemair_sibling_order(
    rule_package: RulePackage,
) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["fields"][2]["sequence"] = 2
    standard["fields"][3]["sequence"] = 1

    result = validate(standard, schemair, rule_package)

    assert "NON_CONTIGUOUS_FIELD_SEQUENCE" not in issue_codes(result)
    assert "DUPLICATE_FIELD_SEQUENCE" not in issue_codes(result)
    assert "SCHEMAIR_SEQUENCE_PROJECTION_MISMATCH" in issue_codes(result)


def test_xml_keys_must_exactly_cover_schemair_attributes(rule_package: RulePackage) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["fields"][0]["xmlKeys"] = [
        {"name": "@unknown", "schemaIrFieldPath": "Root.message.@unknown"}
    ]

    result = validate(standard, schemair, rule_package)

    assert {"UNKNOWN_XML_KEY_REFERENCE", "MISSING_SCHEMAIR_XML_KEY"} <= issue_codes(result)


def test_unknown_constraint_and_uncertain_field_block_final(rule_package: RulePackage) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["fields"][3]["regex"] = {"state": "UNKNOWN", "value": None}
    standard["fields"][3]["uncertain"] = True
    standard["fields"][3]["uncertainReason"] = "目标正则需确认。"

    result = validate(standard, schemair, rule_package)

    assert {"UNKNOWN_CONSTRAINT", "UNCERTAIN_STANDARD_FIELD"} <= issue_codes(result)
    assert result["finalEligible"] is False


def test_schemair_difference_requires_exact_values_rules_and_review(
    rule_package: RulePackage,
) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    target = standard["fields"][3]
    target["lengthLimit"] = length_constraint(state="VALUE", minimum=0, maximum=50)

    missing = validate(standard, schemair, rule_package)
    assert "UNRECORDED_STANDARD_DIFFERENCE" in issue_codes(missing)

    target["differences"] = [
        {
            "property": "lengthLimit",
            "schemaIrValue": length_constraint(),
            "standardValue": deepcopy(target["lengthLimit"]),
            "reason": "目标系统采用已确认默认长度。",
            "ruleReferences": ["STD.DIFFERENCE.PRESERVE"],
            "review": review(approved=False),
        }
    ]
    pending = validate(standard, schemair, rule_package)

    assert "DIFFERENCE_REVIEW_NOT_APPROVED" in issue_codes(pending)
    assert "UNRECORDED_STANDARD_DIFFERENCE" not in issue_codes(pending)
    assert pending["finalEligible"] is False

    target["differences"][0]["review"] = review(approved=True)
    approved = validate(standard, schemair, rule_package)
    assert approved["status"] == "passed"
    assert approved["finalEligible"] is True


def test_list_and_unknown_rule_reference_are_rejected(rule_package: RulePackage) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["fields"][3]["dataType"] = "List"
    standard["fields"][3]["ruleReferences"] = ["TPL.VALUE.FIELD", "STD.UNKNOWN"]

    result = validate(standard, schemair, rule_package)

    assert {
        "INVALID_STANDARD_DATA_TYPE",
        "INVALID_RULE_REFERENCE_DOMAIN",
        "UNKNOWN_RULE_REFERENCE",
    } <= issue_codes(result)


def test_each_field_requires_complete_governing_rules_and_schema_evidence(
    rule_package: RulePackage,
) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["fields"][3]["ruleReferences"].remove("STD.FIELD.PARENT_PATH")
    standard["fields"][3]["evidence"][0]["sourceRef"] = "Root.message.request.wrong"

    result = validate(standard, schemair, rule_package)

    assert {"MISSING_REQUIRED_RULE_REFERENCE", "SCHEMAIR_EVIDENCE_MISMATCH"} <= issue_codes(result)


def test_invalid_schemair_messages_are_reported_without_raising(rule_package: RulePackage) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    schemair["messages"] = {}
    standard["schemaIrRef"]["contentHash"] = content_hash(schemair)

    result = validate(standard, schemair, rule_package)

    assert {"SCHEMAIR_NOT_FINAL_ELIGIBLE", "DIRECTION_NOT_IN_SCHEMAIR"} <= issue_codes(result)


def test_condition_must_match_schemair_and_reference_standard_fields(
    rule_package: RulePackage,
) -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["conditionalConstraints"] = [
        {
            "controllingFieldPath": "Root.message.request.mode",
            "operator": "EQUALS",
            "literal": "2",
            "targetFieldPath": "Root.message.request.value",
            "effect": "REQUIRED",
            "sourceText": "mode=2 时 value 必填。",
            "evidence": {"kind": "DIRECT", "note": "来自测试 fixture。"},
            "review": review(approved=True),
        }
    ]
    standard = valid_standard(schemair)
    standard["schemaIrRef"]["contentHash"] = content_hash(schemair)
    standard["fields"][3]["conditionalConstraints"] = [
        {
            "conditionId": "test001-value-required",
            "schemaIrConditionIndex": 0,
            "controllingFieldRef": "test001-assembly-mode",
            "operator": "EQUALS",
            "literal": "2",
            "targetFieldRef": "test001-assembly-value",
            "effect": "REQUIRED",
            "sourceText": "mode=2 时 value 必填。",
            "evidence": {"kind": "DIRECT", "note": "来自测试 fixture。"},
            "review": review(approved=True),
            "ruleReferences": ["STD.CONSTRAINT.BANK_CONDITION"],
        }
    ]

    passed = validate(standard, schemair, rule_package)
    assert passed["status"] == "passed"

    standard["fields"][3]["conditionalConstraints"][0]["controllingFieldRef"] = "missing"
    failed = validate(standard, schemair, rule_package)
    assert {"UNKNOWN_CONDITION_FIELD_REFERENCE", "SCHEMAIR_CONDITION_MISMATCH"} <= issue_codes(failed)


def test_condition_must_preserve_schemair_source_text_and_evidence(
    rule_package: RulePackage,
) -> None:
    schemair = valid_schemair()
    schemair["messages"][0]["conditionalConstraints"] = [
        {
            "controllingFieldPath": "Root.message.request.mode",
            "operator": "EQUALS",
            "literal": "2",
            "targetFieldPath": "Root.message.request.value",
            "effect": "REQUIRED",
            "sourceText": "mode=2 时 value 必填。",
            "evidence": {"kind": "DIRECT", "note": "来自测试 fixture。"},
            "review": review(approved=True),
        }
    ]
    standard = valid_standard(schemair)
    standard["schemaIrRef"]["contentHash"] = content_hash(schemair)
    standard["fields"][3]["conditionalConstraints"] = [
        {
            "conditionId": "test001-value-required",
            "schemaIrConditionIndex": 0,
            "controllingFieldRef": "test001-assembly-mode",
            "operator": "EQUALS",
            "literal": "2",
            "targetFieldRef": "test001-assembly-value",
            "effect": "REQUIRED",
            "sourceText": "被修改的银行条件。",
            "evidence": {"kind": "DERIVED", "note": "不是原始证据。"},
            "review": review(approved=True),
            "ruleReferences": ["STD.CONSTRAINT.BANK_CONDITION"],
        }
    ]

    result = validate(standard, schemair, rule_package)

    assert "SCHEMAIR_CONDITION_SOURCE_MISMATCH" in issue_codes(result)


def test_difference_rejects_properties_without_verifiable_schema_projection(
    rule_package: RulePackage,
) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    target = standard["fields"][3]
    target["regex"] = {"state": "VALUE", "value": "^[0-9]+$"}
    target["differences"] = [
        {
            "property": "regex",
            "schemaIrValue": "invented source value",
            "standardValue": deepcopy(target["regex"]),
            "reason": "测试不受支持的差异属性。",
            "ruleReferences": ["STD.DIFFERENCE.PRESERVE"],
            "review": review(approved=True),
        }
    ]

    result = validate(standard, schemair, rule_package)

    assert "INVALID_DIFFERENCE_PROPERTY" in issue_codes(result)


def test_invalid_root_is_aggregated(rule_package: RulePackage) -> None:
    result = validate([], valid_schemair(), rule_package)

    assert result["status"] == "failed"
    assert issue_codes(result) == {"INVALID_STANDARD_ROOT"}


def test_logs_exclude_standard_and_bank_content(
    rule_package: RulePackage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    schemair = valid_schemair()
    standard = valid_standard(schemair)
    standard["fields"][3]["fieldDescription"] = "SENSITIVE-STANDARD-DESCRIPTION"
    schemair["messages"][0]["fields"][2]["sourceText"] = "SENSITIVE-BANK-SOURCE"
    standard["schemaIrRef"]["contentHash"] = content_hash(schemair)

    with caplog.at_level(logging.DEBUG, logger="bank_config_compiler.interface_standard_validator"):
        validate(standard, schemair, rule_package)

    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert "SENSITIVE-STANDARD-DESCRIPTION" not in rendered
    assert "SENSITIVE-BANK-SOURCE" not in rendered
    assert [record.outcome for record in caplog.records] == ["started", "succeeded"]
