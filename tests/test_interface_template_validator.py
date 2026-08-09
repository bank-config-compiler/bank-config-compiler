from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bank_config_compiler.artifact_validation import content_hash
from bank_config_compiler.configuration_rules import RulePackage, load_rule_package
from bank_config_compiler.interface_template_validator import (
    TemplateValueError,
    apply_mapping,
    apply_replacement,
    validate_interface_template,
)


FIXTURE_DIR = Path("samples/trusted-chain/b2eboc-b2e0061")
RULE_PACKAGE_DIR = Path("configuration-rules/v2")
SCALAR_TYPES = {"String", "Boolean", "Date", "Number"}


@pytest.fixture(scope="module")
def rule_package() -> RulePackage:
    return load_rule_package(RULE_PACKAGE_DIR)


def load_standard(direction: str) -> dict[str, Any]:
    return json.loads(
        (
            FIXTURE_DIR
            / "standards"
            / direction.lower()
            / "v1"
            / "standard-final.json"
        ).read_text(encoding="utf-8")
    )


def review(*, approved: bool) -> dict[str, Any]:
    return {
        "status": "APPROVED" if approved else "PENDING",
        "reviewer": "deng" if approved else None,
        "reviewedAt": "2026-08-09T16:30:00+08:00" if approved else None,
        "note": "测试确认。" if approved else None,
    }


def expression(mode: str, **values: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "mode": mode,
        "sequence": values.pop("sequence", 1),
        "ruleReferences": values.pop("ruleReferences", [f"TPL.VALUE.{mode}"]),
    }
    result.update(values)
    return result


def projection(field: dict[str, Any]) -> dict[str, Any]:
    return {
        "required": field["required"],
        "length": deepcopy(field["lengthLimit"]),
        "dataType": field["dataType"],
    }


def policies(*, replacement: str | None = None) -> dict[str, Any]:
    return {
        "emptyHandling": "BLANK",
        "overlengthHandling": "INTERCEPT",
        "rowLimit": 1,
        "chineseCharacterLength": "STANDARD_1",
        "replacementRuleName": replacement,
    }


def field_config(
    field: dict[str, Any],
    *,
    direction: str,
    binding_kind: str = "VALUE",
    value_expression: dict[str, Any] | None = None,
    parse_target: dict[str, Any] | None = None,
    xml_key_expressions: dict[str, dict[str, Any]] | None = None,
    replacement: str | None = None,
    uncertain: bool = False,
) -> dict[str, Any]:
    binding_rule = {
        "VALUE": None,
        "STRUCTURE_ONLY": "TPL.BIND.STRUCTURE_ONLY",
        "COLLECTION_ITEM": "TPL.BIND.COLLECTION_ITEM",
    }[binding_kind]
    rule_references = [
        f"TPL.BIND.{direction}",
        "TPL.BIND.STANDARD_PROJECTION",
        "TPL.PROCESS.EMPTY_HANDLING",
        "TPL.PROCESS.OVERLENGTH",
        "TPL.PROCESS.ROW_LIMIT",
        "TPL.PROCESS.CHAR_LENGTH",
    ]
    if binding_rule:
        rule_references.append(binding_rule)
    if replacement:
        rule_references.append("TPL.PROCESS.REPLACEMENT")
    config = {
        "bindingKind": binding_kind,
        "valueExpression": value_expression,
        "processingPolicies": policies(replacement=replacement),
        "ruleReferences": rule_references,
        "evidence": [
            {
                "kind": "FINAL_STANDARD",
                "sourceRef": field["fieldId"],
                "note": "来自测试 Final Standard。",
            }
        ],
        "confidence": 0.75 if uncertain else 1.0,
        "uncertain": uncertain,
        "uncertainReason": "需要 Human Review。" if uncertain else None,
        "reviewNote": None,
    }
    if direction == "ASSEMBLY":
        config["standardTarget"] = {
            "standardFieldRef": field["fieldId"],
            "standardProjection": projection(field),
        }
        config["xmlKeyExpressions"] = xml_key_expressions or {}
    else:
        config["parseTarget"] = parse_target
        if binding_kind == "COLLECTION_ITEM":
            config["standardSource"] = {"standardFieldRef": field["fieldId"]}
    return config


def parse_target(rule_package: RulePackage, code: str) -> dict[str, Any]:
    entry = rule_package.fields_by_direction["PARSE"][code]
    return {
        "parseFieldRef": code,
        "name": code,
        "parentPath": entry["parentPath"],
        "fullPath": entry["fullPath"],
        "dataType": entry["dataType"],
    }


def valid_assembly_template(
    standard: dict[str, Any],
    *,
    final: bool = True,
) -> dict[str, Any]:
    field_configs: list[dict[str, Any]] = []
    for field in standard["fields"]:
        if field["fullPath"] == "Root.bocb2e":
            field_configs.append(
                field_config(
                    field,
                    direction="ASSEMBLY",
                    binding_kind="STRUCTURE_ONLY",
                    xml_key_expressions={
                        key: expression(
                            "FIXED_VALUE",
                            payload={"kind": "LITERAL", "value": "test"},
                        )
                        for key in ("@version", "@security", "@locale")
                    },
                )
            )
        elif field["dataType"] in SCALAR_TYPES:
            field_configs.append(
                field_config(
                    field,
                    direction="ASSEMBLY",
                    value_expression=expression("EMPTY"),
                )
            )
    return {
        "contractVersion": "interface-template/v1",
        "templateId": "b2e0061-assembly-common",
        "templateVersion": "v1",
        "status": "FINAL" if final else "DRAFT",
        "interfaceCode": standard["interfaceCode"],
        "direction": "ASSEMBLY",
        "standardRef": {
            "standardId": standard["standardId"],
            "standardVersion": standard["standardVersion"],
            "contentHash": content_hash(standard),
        },
        "rulePackageVersion": "v2",
        "fieldConfigs": field_configs,
        "omissions": [],
        "review": review(approved=final),
    }


def valid_parse_template(
    standard: dict[str, Any],
    rule_package: RulePackage,
    *,
    final: bool = True,
) -> dict[str, Any]:
    fields = {field["fieldName"]: field for field in standard["fields"]}
    collection = fields["b2e0061-rs"]
    instruction_id = fields["insid"]
    return {
        "contractVersion": "interface-template/v1",
        "templateId": "b2e0061-parse-common",
        "templateVersion": "v1",
        "status": "FINAL" if final else "DRAFT",
        "interfaceCode": standard["interfaceCode"],
        "direction": "PARSE",
        "standardRef": {
            "standardId": standard["standardId"],
            "standardVersion": standard["standardVersion"],
            "contentHash": content_hash(standard),
        },
        "rulePackageVersion": "v2",
        "fieldConfigs": [
            field_config(
                collection,
                direction="PARSE",
                binding_kind="COLLECTION_ITEM",
                parse_target=parse_target(rule_package, "paymentLineList"),
            ),
            field_config(
                instruction_id,
                direction="PARSE",
                parse_target=parse_target(rule_package, "instructionId"),
                value_expression=expression(
                    "FIELD", standardFieldRef=instruction_id["fieldId"]
                ),
            ),
        ],
        "omissions": [],
        "review": review(approved=final),
    }


def validate(
    template: object,
    standard: object,
    rule_package: RulePackage,
) -> dict[str, Any]:
    return validate_interface_template(
        template,
        standard=standard,
        rule_package=rule_package,
    )


def issue_codes(result: dict[str, Any]) -> set[str]:
    return {item["code"] for item in result["issues"]}


def test_final_assembly_template_is_valid(rule_package: RulePackage) -> None:
    standard = load_standard("assembly")

    result = validate(valid_assembly_template(standard), standard, rule_package)

    assert result["status"] == "passed"
    assert result["finalEligible"] is True
    assert result["summary"]["templateId"] == "b2e0061-assembly-common"
    assert result["summary"]["interfaceCode"] == "b2e0061"
    assert result["summary"]["direction"] == "ASSEMBLY"
    assert result["summary"]["rulePackageVersion"] == "v2"
    assert result["summary"]["fieldConfigCount"] == 30
    assert result["summary"]["errorCount"] == 0
    assert result["summary"]["warningCount"] == 0
    assert result["summary"]["infoCount"] == 0
    assert result["summary"]["blockingCount"] == 0
    assert result["coverage"] == {
        "valueBindingCount": 29,
        "structureBindingCount": 1,
        "collectionBindingCount": 0,
        "fieldValueExpressionCount": 29,
        "xmlKeyExpressionCount": 3,
        "omissionCount": 0,
        "approvedOmissionCount": 0,
        "uncertainFieldConfigCount": 0,
        "functionInvocationCount": 0,
        "mappingExpressionCount": 0,
        "replacementCount": 0,
    }


def test_draft_is_valid_but_not_final_eligible(rule_package: RulePackage) -> None:
    standard = load_standard("assembly")

    result = validate(valid_assembly_template(standard, final=False), standard, rule_package)

    assert result["status"] == "passed_with_warnings"
    assert result["finalEligible"] is False
    assert issue_codes(result) == {"ARTIFACT_NOT_FINAL", "REVIEW_NOT_APPROVED"}
    assert all(item["blocking"] for item in result["issues"])


def test_contract_is_strict_and_bool_is_not_an_integer(rule_package: RulePackage) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    template["condition"] = {"unsupported": True}
    del template["omissions"]
    template["fieldConfigs"][0]["generatorHint"] = "unsupported"
    template["fieldConfigs"][0]["processingPolicies"]["rowLimit"] = True

    result = validate(template, standard, rule_package)

    assert {
        "UNKNOWN_TOP_LEVEL_PROPERTY",
        "MISSING_TOP_LEVEL_PROPERTY",
        "UNKNOWN_FIELD_CONFIG_PROPERTY",
        "INVALID_ROW_LIMIT",
    } <= issue_codes(result)


def test_standard_identity_version_hash_direction_and_rule_version_are_exact(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    template["interfaceCode"] = "wrong"
    template["direction"] = "PARSE"
    template["standardRef"]["standardVersion"] = "v2"
    template["standardRef"]["contentHash"] = "sha256:" + "0" * 64
    template["rulePackageVersion"] = "v1"

    result = validate(template, standard, rule_package)

    assert {
        "INTERFACE_CODE_MISMATCH",
        "DIRECTION_MISMATCH",
        "STANDARD_REFERENCE_MISMATCH",
        "STANDARD_HASH_MISMATCH",
        "RULE_PACKAGE_VERSION_MISMATCH",
    } <= issue_codes(result)


def test_standard_projection_and_binding_kind_must_match(rule_package: RulePackage) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    scalar = next(
        config for config in template["fieldConfigs"] if config["bindingKind"] == "VALUE"
    )
    scalar["standardTarget"]["standardProjection"]["required"] = not scalar[
        "standardTarget"
    ]["standardProjection"]["required"]
    scalar["bindingKind"] = "STRUCTURE_ONLY"

    result = validate(template, standard, rule_package)

    assert {
        "STANDARD_PROJECTION_MISMATCH",
        "INVALID_SCALAR_BINDING_KIND",
        "SCALAR_VALUE_EXPRESSION_FORBIDDEN",
    } <= issue_codes(result)


def test_assembly_omissions_are_explicit_and_reviewed(rule_package: RulePackage) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    removed = next(
        config
        for config in template["fieldConfigs"]
        if config["standardTarget"]["standardFieldRef"].endswith("-email")
    )
    template["fieldConfigs"].remove(removed)

    missing_record = validate(template, standard, rule_package)
    assert {"MISSING_TEMPLATE_FIELD", "MISSING_OMISSION_RECORD"} <= issue_codes(missing_record)

    template["omissions"] = [
        {
            "standardFieldRef": removed["standardTarget"]["standardFieldRef"],
            "reason": "当前业务场景不报送邮箱。",
            "reviewDisposition": "PENDING",
            "reviewer": None,
            "reviewedAt": None,
            "reviewNote": None,
        }
    ]
    pending = validate(template, standard, rule_package)
    assert issue_codes(pending) == {"MISSING_TEMPLATE_FIELD", "OMISSION_REVIEW_NOT_APPROVED"}
    assert pending["finalEligible"] is False

    template["omissions"][0].update(
        {
            "reviewDisposition": "ACCEPTED",
            "reviewer": "deng",
            "reviewedAt": "2026-08-09T16:30:00+08:00",
            "reviewNote": "确认该业务场景省略邮箱。",
        }
    )
    approved = validate(template, standard, rule_package)
    assert issue_codes(approved) == {"MISSING_TEMPLATE_FIELD"}
    assert approved["issues"][0]["blocking"] is False
    assert approved["finalEligible"] is True


def test_parse_uses_configured_targets_only_and_collection_context(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("parse")
    template = valid_parse_template(standard, rule_package)

    passed = validate(template, standard, rule_package)
    assert passed["status"] == "passed"
    assert passed["finalEligible"] is True
    assert passed["coverage"]["collectionBindingCount"] == 1

    template["fieldConfigs"].pop(0)
    failed = validate(template, standard, rule_package)
    assert "MISSING_COLLECTION_CONTEXT" in issue_codes(failed)
    assert "MISSING_TEMPLATE_FIELD" not in issue_codes(failed)


def test_parse_collection_target_rejects_standard_source_outside_collection(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("parse")
    template = valid_parse_template(standard, rule_package)
    header_terminal = next(
        field for field in standard["fields"] if field["fullPath"] == "Root.bocb2e.head.termid"
    )
    template["fieldConfigs"][1]["valueExpression"] = expression(
        "CONCATENATE",
        children=[
            expression(
                "FIELD",
                sequence=1,
                standardFieldRef=header_terminal["fieldId"],
            )
        ],
    )

    result = validate(template, standard, rule_package)

    assert "STANDARD_SOURCE_OUTSIDE_COLLECTION" in issue_codes(result)


def test_parse_target_snapshot_and_field_reference_are_exact(rule_package: RulePackage) -> None:
    standard = load_standard("parse")
    template = valid_parse_template(standard, rule_package)
    value_config = template["fieldConfigs"][1]
    value_config["parseTarget"]["fullPath"] = "Root.wrong"
    value_config["valueExpression"]["standardFieldRef"] = "missing-standard-field"

    result = validate(template, standard, rule_package)

    assert {"PARSE_TARGET_MISMATCH", "UNKNOWN_STANDARD_FIELD_REFERENCE"} <= issue_codes(result)


def test_parse_expression_owns_zero_or_multiple_standard_sources(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("parse")
    template = valid_parse_template(standard, rule_package)
    fields = {
        field["fullPath"]: field
        for field in standard["fields"]
    }
    response_code = fields["Root.bocb2e.trans.trn-b2e0061-rs.status.rspcod"]
    response_message = fields["Root.bocb2e.trans.trn-b2e0061-rs.status.rspmsg"]
    value_config = template["fieldConfigs"][1]
    value_config["parseTarget"] = parse_target(rule_package, "failReason")
    value_config["valueExpression"] = expression(
        "CONCATENATE",
        children=[
            expression(
                "FIELD", sequence=1, standardFieldRef=response_code["fieldId"]
            ),
            expression(
                "FIXED_VALUE",
                sequence=2,
                payload={"kind": "LITERAL", "value": "-"},
            ),
            expression(
                "FIELD", sequence=3, standardFieldRef=response_message["fieldId"]
            ),
        ],
    )

    multiple_sources = validate(template, standard, rule_package)

    assert multiple_sources["status"] == "passed"
    assert "standardFieldRef" not in value_config
    assert "standardProjection" not in value_config
    assert "standardSources" not in value_config

    value_config["parseTarget"] = parse_target(rule_package, "sourceMessageId")
    value_config["valueExpression"] = expression("EMPTY")

    zero_sources = validate(template, standard, rule_package)

    assert zero_sources["status"] == "passed"


def test_directional_field_config_wire_is_fail_closed(rule_package: RulePackage) -> None:
    assembly_standard = load_standard("assembly")
    assembly = valid_assembly_template(assembly_standard)
    assembly_config = assembly["fieldConfigs"][1]
    target = assembly_config.pop("standardTarget")
    assembly_config["standardFieldRef"] = target["standardFieldRef"]
    assembly_config["standardProjection"] = target["standardProjection"]

    assembly_result = validate(assembly, assembly_standard, rule_package)

    assert {
        "MISSING_STANDARD_TARGET",
        "UNKNOWN_FIELD_CONFIG_PROPERTY",
    } <= issue_codes(assembly_result)

    parse_standard = load_standard("parse")
    parse = valid_parse_template(parse_standard, rule_package)
    parse_config = parse["fieldConfigs"][1]
    parse_config["standardTarget"] = {
        "standardFieldRef": parse_config["valueExpression"]["standardFieldRef"],
        "standardProjection": projection(
            next(
                field
                for field in parse_standard["fields"]
                if field["fieldId"]
                == parse_config["valueExpression"]["standardFieldRef"]
            )
        ),
    }

    parse_result = validate(parse, parse_standard, rule_package)

    assert "UNKNOWN_FIELD_CONFIG_PROPERTY" in issue_codes(parse_result)


def test_xml_key_expressions_are_assembly_only_and_exact(rule_package: RulePackage) -> None:
    assembly_standard = load_standard("assembly")
    assembly = valid_assembly_template(assembly_standard)
    root = assembly["fieldConfigs"][0]
    root["xmlKeyExpressions"].pop("@security")
    root["xmlKeyExpressions"]["@unknown"] = expression("EMPTY")

    assembly_result = validate(assembly, assembly_standard, rule_package)
    assert {"MISSING_XML_KEY_EXPRESSION", "UNKNOWN_XML_KEY_EXPRESSION"} <= issue_codes(
        assembly_result
    )

    parse_standard = load_standard("parse")
    parse = valid_parse_template(parse_standard, rule_package)
    parse["fieldConfigs"][0]["xmlKeyExpressions"] = {"@version": expression("EMPTY")}
    parse_result = validate(parse, parse_standard, rule_package)
    assert "PARSE_XML_KEY_EXPRESSION_FORBIDDEN" in issue_codes(parse_result)


def test_all_expression_modes_and_recursive_concatenate_are_supported(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    configs = [config for config in template["fieldConfigs"] if config["bindingKind"] == "VALUE"]
    configs[0]["valueExpression"] = expression(
        "FIXED_VALUE",
        payload={"kind": "LITERAL", "value": "literal"},
    )
    configs[1]["valueExpression"] = expression(
        "FIELD", assemblyFieldRef="debtorAccountNo"
    )
    configs[2]["valueExpression"] = expression(
        "FUNCTION",
        functionCode="DateFormat",
        arguments=[
            {
                "position": 1,
                "kind": "FIELD_REF",
                "assemblyFieldRef": "valueDate",
            },
            {"position": 2, "kind": "LITERAL", "value": "yyyy-MM-dd"},
            {"position": 3, "kind": "LITERAL", "value": "yyyyMMdd"},
        ],
    )
    configs[3]["valueExpression"] = expression(
        "MAPPING",
        assemblyFieldRef="chargeBearer",
        mappingRuleName="BDC-ChargeBearer-List",
    )
    configs[4]["valueExpression"] = expression(
        "CONCATENATE",
        children=[
            expression(
                "FIELD", sequence=1, assemblyFieldRef="creditorBankName"
            ),
            expression(
                "CONCATENATE",
                sequence=2,
                children=[
                    expression(
                        "FIXED_VALUE",
                        sequence=1,
                        payload={"kind": "LITERAL", "value": "-"},
                    ),
                    expression(
                        "FIELD",
                        sequence=2,
                        assemblyFieldRef="creditorBankBranchName",
                    ),
                ],
            ),
        ],
    )

    result = validate(template, standard, rule_package)

    assert result["status"] == "passed"
    assert result["coverage"]["functionInvocationCount"] == 1
    assert result["coverage"]["mappingExpressionCount"] == 1


def test_expression_shape_function_arguments_and_recursion_fail_closed(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    configs = [config for config in template["fieldConfigs"] if config["bindingKind"] == "VALUE"]
    configs[0]["valueExpression"] = expression(
        "FIELD", assemblyFieldRef="missing"
    )
    configs[1]["valueExpression"] = expression(
        "FUNCTION",
        functionCode="DateFormat",
        arguments=[
            {"position": 1, "kind": "LITERAL", "value": "wrong kind"},
            {"position": 3, "kind": "LITERAL", "value": "yyyyMMdd"},
        ],
    )
    configs[2]["valueExpression"] = expression(
        "CONCATENATE",
        children=[expression("EMPTY", sequence=2)],
    )
    configs[3]["valueExpression"]["children"] = [expression("EMPTY")]

    result = validate(template, standard, rule_package)

    assert {
        "UNKNOWN_ASSEMBLY_FIELD_REFERENCE",
        "FUNCTION_ARGUMENT_MISMATCH",
        "NON_CONTIGUOUS_EXPRESSION_SEQUENCE",
        "UNKNOWN_EXPRESSION_PROPERTY",
    } <= issue_codes(result)


def test_mapping_and_function_field_sources_must_be_string(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("parse")
    template = valid_parse_template(standard, rule_package)
    collection = next(
        field
        for field in standard["fields"]
        if field["fullPath"].endswith(".b2e0061-rs")
    )
    config = template["fieldConfigs"][1]
    config["parseTarget"] = parse_target(rule_package, "failReason")
    config["valueExpression"] = expression(
        "MAPPING",
        standardFieldRef=collection["fieldId"],
        mappingRuleName="BDC-ChargeBearer-List",
    )

    mapping_result = validate(template, standard, rule_package)
    assert "MAPPING_REQUIRES_STRING_SOURCE" in issue_codes(mapping_result)

    config["valueExpression"] = expression(
        "FUNCTION",
        functionCode="DateFormat",
        arguments=[
            {
                "position": 1,
                "kind": "FIELD_REF",
                "standardFieldRef": collection["fieldId"],
            },
            {"position": 2, "kind": "LITERAL", "value": "yyyy-MM-dd"},
            {"position": 3, "kind": "LITERAL", "value": "yyyyMMdd"},
        ],
    )

    function_result = validate(template, standard, rule_package)
    assert "FUNCTION_ARGUMENT_TYPE_MISMATCH" in issue_codes(function_result)


def test_fixed_value_secure_reference_does_not_accept_secret_or_redaction(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    configs = [config for config in template["fieldConfigs"] if config["bindingKind"] == "VALUE"]
    configs[0]["valueExpression"] = expression(
        "FIXED_VALUE",
        payload={"kind": "SECURE_INPUT_REF", "value": "secrets.boc.termid"},
    )
    passed = validate(template, standard, rule_package)
    assert passed["status"] == "passed"

    configs[0]["valueExpression"]["payload"]["value"] = "<REDACTED>"
    failed = validate(template, standard, rule_package)
    assert "INVALID_SECURE_INPUT_REFERENCE" in issue_codes(failed)


def test_processing_policies_and_required_rule_references_are_validated(
    rule_package: RulePackage,
) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    config = next(item for item in template["fieldConfigs"] if item["bindingKind"] == "VALUE")
    config["processingPolicies"]["emptyHandling"] = "UNKNOWN"
    config["processingPolicies"]["chineseCharacterLength"] = "STANDARD_7"
    config["processingPolicies"]["replacementRuleName"] = "missing"
    config["ruleReferences"].remove("TPL.PROCESS.ROW_LIMIT")

    result = validate(template, standard, rule_package)

    assert {
        "INVALID_EMPTY_HANDLING",
        "INVALID_CHINESE_CHARACTER_LENGTH",
        "UNKNOWN_REPLACEMENT_RULE",
        "MISSING_REQUIRED_RULE_REFERENCE",
    } <= issue_codes(result)


def test_mapping_and_replacement_helpers_use_distinct_semantics(rule_package: RulePackage) -> None:
    assert apply_mapping("DEBT", "BDC-ChargeBearer-List", rule_package=rule_package) == "OUR"
    with pytest.raises(TemplateValueError, match="no exact source match"):
        apply_mapping("DEBT-extra", "BDC-ChargeBearer-List", rule_package=rule_package)

    assert (
        apply_replacement(
            "ABC#(123)",
            "Swift_illegalCharacter_List_For_ING_Turkey",
            rule_package=rule_package,
        )
        == "ABC123"
    )


def test_mapping_helpers_reject_unknown_redacted_and_non_string_input(
    rule_package: RulePackage,
) -> None:
    with pytest.raises(TemplateValueError, match="unknown mapping rule"):
        apply_mapping("value", "missing", rule_package=rule_package)
    with pytest.raises(TemplateValueError, match="redacted mapping rule"):
        apply_mapping("ATTIJARI", "Swift-CompanyName-List", rule_package=rule_package)
    with pytest.raises(TemplateValueError, match="must be a String"):
        apply_replacement(1, "BDC-ChargeBearer-List", rule_package=rule_package)  # type: ignore[arg-type]


def test_final_template_rejects_redacted_mapping_reference(rule_package: RulePackage) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    config = next(item for item in template["fieldConfigs"] if item["bindingKind"] == "VALUE")
    config["valueExpression"] = expression(
        "MAPPING",
        assemblyFieldRef="creditorAccountName",
        mappingRuleName="Swift-CompanyName-List",
    )

    result = validate(template, standard, rule_package)

    assert "REDACTED_MAPPING_FORBIDDEN_IN_FINAL" in issue_codes(result)
    assert result["finalEligible"] is False


def test_duplicate_targets_and_template_condition_are_rejected(rule_package: RulePackage) -> None:
    assembly_standard = load_standard("assembly")
    assembly = valid_assembly_template(assembly_standard)
    duplicate = deepcopy(assembly["fieldConfigs"][1])
    duplicate["condition"] = {"operator": "unsupported"}
    assembly["fieldConfigs"].append(duplicate)

    assembly_result = validate(assembly, assembly_standard, rule_package)
    assert {"DUPLICATE_ASSEMBLY_TARGET", "UNKNOWN_FIELD_CONFIG_PROPERTY"} <= issue_codes(
        assembly_result
    )

    parse_standard = load_standard("parse")
    parse = valid_parse_template(parse_standard, rule_package)
    parse["fieldConfigs"].append(deepcopy(parse["fieldConfigs"][1]))
    parse_result = validate(parse, parse_standard, rule_package)
    assert "DUPLICATE_PARSE_TARGET" in issue_codes(parse_result)


def test_uncertain_field_config_blocks_final(rule_package: RulePackage) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    template["fieldConfigs"][1]["uncertain"] = True
    template["fieldConfigs"][1]["uncertainReason"] = "需要确认。"

    result = validate(template, standard, rule_package)

    assert "UNCERTAIN_FIELD_CONFIG" in issue_codes(result)
    assert result["finalEligible"] is False


def test_invalid_root_is_aggregated(rule_package: RulePackage) -> None:
    result = validate([], load_standard("assembly"), rule_package)

    assert result["status"] == "failed"
    assert issue_codes(result) == {"INVALID_TEMPLATE_ROOT"}


def test_logs_exclude_template_values_and_standard_content(
    rule_package: RulePackage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    standard = load_standard("assembly")
    template = valid_assembly_template(standard)
    config = next(item for item in template["fieldConfigs"] if item["bindingKind"] == "VALUE")
    config["valueExpression"] = expression(
        "FIXED_VALUE",
        payload={"kind": "LITERAL", "value": "SENSITIVE-TEMPLATE-VALUE"},
    )
    standard["fields"][0]["fieldDescription"] = "SENSITIVE-STANDARD-DESCRIPTION"
    template["standardRef"]["contentHash"] = content_hash(standard)

    with caplog.at_level(logging.DEBUG, logger="bank_config_compiler.interface_template_validator"):
        validate(template, standard, rule_package)

    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert "SENSITIVE-TEMPLATE-VALUE" not in rendered
    assert "SENSITIVE-STANDARD-DESCRIPTION" not in rendered
    assert [record.outcome for record in caplog.records] == ["started", "succeeded"]
