from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Mapping

from .artifact_validation import ValidationIssue, build_validation_result, content_hash, issue
from .configuration_rules import RulePackage


LOGGER = logging.getLogger(__name__)

TEMPLATE_CONTRACT_VERSION = "interface-template/v1"
RESULT_CONTRACT_VERSION = "interface-template-validation-result/v1"
STANDARD_CONTRACT_VERSION = "interface-standard/v1"
DIRECTIONS = {"ASSEMBLY", "PARSE"}
ARTIFACT_STATUSES = {"DRAFT", "FINAL"}
REVIEW_STATUSES = {"PENDING", "APPROVED"}
OMISSION_DISPOSITIONS = {"PENDING", "ACCEPTED", "REJECTED"}
BINDING_KINDS = {"VALUE", "STRUCTURE_ONLY", "COLLECTION_ITEM"}
SCALAR_TYPES = {"String", "Boolean", "Date", "Number"}
CONTAINER_TYPES = {"Node", "Object"}
VALUE_MODES = {"FIXED_VALUE", "EMPTY", "FIELD", "FUNCTION", "MAPPING", "CONCATENATE"}
EVIDENCE_KINDS = {"FINAL_STANDARD", "TARGET_SYSTEM_FORMAL_EXPORT", "HUMAN_CONFIRMATION"}

TOP_LEVEL_PROPERTIES = {
    "contractVersion",
    "templateId",
    "templateVersion",
    "status",
    "interfaceCode",
    "direction",
    "standardRef",
    "rulePackageVersion",
    "fieldConfigs",
    "omissions",
    "review",
}
STANDARD_REF_PROPERTIES = {"standardId", "standardVersion", "contentHash"}
REVIEW_PROPERTIES = {"status", "reviewer", "reviewedAt", "note"}
COMMON_FIELD_CONFIG_PROPERTIES = {
    "bindingKind",
    "valueExpression",
    "processingPolicies",
    "ruleReferences",
    "evidence",
    "confidence",
    "uncertain",
    "uncertainReason",
    "reviewNote",
}
ASSEMBLY_FIELD_CONFIG_PROPERTIES = COMMON_FIELD_CONFIG_PROPERTIES | {
    "standardTarget",
    "xmlKeyExpressions",
}
PARSE_FIELD_CONFIG_PROPERTIES = COMMON_FIELD_CONFIG_PROPERTIES | {
    "parseTarget",
    "standardSource",
}
STANDARD_TARGET_PROPERTIES = {"standardFieldRef", "standardProjection"}
STANDARD_SOURCE_PROPERTIES = {"standardFieldRef"}
STANDARD_PROJECTION_PROPERTIES = {"required", "length", "dataType"}
PARSE_TARGET_PROPERTIES = {"parseFieldRef", "name", "parentPath", "fullPath", "dataType"}
PROCESSING_PROPERTIES = {
    "emptyHandling",
    "overlengthHandling",
    "rowLimit",
    "chineseCharacterLength",
    "replacementRuleName",
}
EVIDENCE_PROPERTIES = {"kind", "sourceRef", "note"}
OMISSION_PROPERTIES = {
    "standardFieldRef",
    "reason",
    "reviewDisposition",
    "reviewer",
    "reviewedAt",
    "reviewNote",
}
PAYLOAD_PROPERTIES = {"kind", "value"}
EXPRESSION_COMMON_PROPERTIES = {"mode", "sequence", "ruleReferences"}

STABLE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^v[1-9]\d*$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SECURE_REFERENCE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
REDACTED_VALUE = "<REDACTED>"


class TemplateValueError(ValueError):
    """Raised when deterministic Mapping or Replacement evaluation cannot continue."""


def validate_interface_template(
    template: object,
    *,
    standard: object,
    rule_package: RulePackage,
) -> dict[str, Any]:
    template_id = template.get("templateId") if isinstance(template, Mapping) else None
    direction = template.get("direction") if isinstance(template, Mapping) else None
    LOGGER.debug(
        "Validating InterfaceTemplateIR",
        extra={
            "component": "interface_template_validator",
            "artifact_id": template_id,
            "direction": direction,
            "outcome": "started",
        },
    )

    issues: list[ValidationIssue] = []
    if not isinstance(template, dict):
        issue(issues, "ERROR", "INVALID_TEMPLATE_ROOT", None, "InterfaceTemplateIR root must be an object.")
        result = _result(template, [], [], Counter(), issues)
        _log_result(result)
        return result

    _validate_top_level(template, issues)
    _validate_lifecycle(template, issues)
    context = _validate_dependencies(template, standard, rule_package, issues)

    raw_configs = template.get("fieldConfigs")
    configs = raw_configs if isinstance(raw_configs, list) else []
    counters: Counter[str] = Counter()
    validated_configs = _validate_field_configs(
        configs,
        template=template,
        context=context,
        rule_package=rule_package,
        counters=counters,
        issues=issues,
    )

    raw_omissions = template.get("omissions")
    omissions = raw_omissions if isinstance(raw_omissions, list) else []
    _validate_coverage_and_omissions(
        template,
        validated_configs,
        omissions,
        context,
        counters,
        issues,
    )
    _validate_collection_context(
        validated_configs,
        rule_package,
        context["standard_fields"],
        issues,
    )

    result = _result(template, configs, omissions, counters, issues)
    _log_result(result)
    return result


def apply_mapping(value: str, mapping_rule_name: str, *, rule_package: RulePackage) -> str:
    """Apply one whole-value exact Mapping rule from a validated package."""

    mapping = _executable_mapping(value, mapping_rule_name, rule_package)
    for entry in mapping["entries"]:
        if entry["source"] == value:
            return entry["target"]
    raise TemplateValueError("mapping rule has no exact source match")


def apply_replacement(value: str, mapping_rule_name: str, *, rule_package: RulePackage) -> str:
    """Apply the catalog entries as ordered substring replacements."""

    mapping = _executable_mapping(value, mapping_rule_name, rule_package)
    result = value
    for entry in mapping["entries"]:
        result = result.replace(entry["source"], entry["target"])
    return result


def _executable_mapping(
    value: object,
    mapping_rule_name: object,
    rule_package: object,
) -> dict[str, Any]:
    if not isinstance(value, str):
        raise TemplateValueError("mapping input must be a String")
    if not isinstance(mapping_rule_name, str) or not mapping_rule_name:
        raise TemplateValueError("mapping rule name must be a non-empty String")
    if not isinstance(rule_package, RulePackage):
        raise TemplateValueError("a validated rule package is required")
    mapping = rule_package.mappings_by_name.get(mapping_rule_name)
    if mapping is None:
        raise TemplateValueError("unknown mapping rule")
    # redacted catalog targets are evidence only and must never enter executable output.
    if mapping.get("redacted") is True:
        raise TemplateValueError("redacted mapping rule is not executable")
    return mapping


def _validate_top_level(template: dict[str, Any], issues: list[ValidationIssue]) -> None:
    _object_contract(
        template,
        TOP_LEVEL_PROPERTIES,
        TOP_LEVEL_PROPERTIES,
        issues,
        path=None,
        missing_code="MISSING_TOP_LEVEL_PROPERTY",
        unknown_code="UNKNOWN_TOP_LEVEL_PROPERTY",
    )
    _enum(
        template.get("contractVersion"),
        {TEMPLATE_CONTRACT_VERSION},
        issues,
        "INVALID_CONTRACT_VERSION",
        "contractVersion",
    )
    _stable_id(template.get("templateId"), issues, "INVALID_TEMPLATE_ID", "templateId")
    _version(template.get("templateVersion"), issues, "INVALID_TEMPLATE_VERSION", "templateVersion")
    _enum(template.get("status"), ARTIFACT_STATUSES, issues, "INVALID_ARTIFACT_STATUS", "status")
    _required_string(template.get("interfaceCode"), issues, "INVALID_INTERFACE_CODE", "interfaceCode")
    _enum(template.get("direction"), DIRECTIONS, issues, "INVALID_DIRECTION", "direction")
    _required_string(
        template.get("rulePackageVersion"),
        issues,
        "INVALID_RULE_PACKAGE_VERSION",
        "rulePackageVersion",
    )

    if "fieldConfigs" in template and not isinstance(template["fieldConfigs"], list):
        issue(issues, "ERROR", "INVALID_FIELD_CONFIGS", "fieldConfigs", "fieldConfigs must be an array.")
    if "omissions" in template and not isinstance(template["omissions"], list):
        issue(issues, "ERROR", "INVALID_OMISSIONS", "omissions", "omissions must be an array.")

    review = template.get("review")
    if isinstance(review, dict):
        _validate_review(review, REVIEW_STATUSES, issues, path="review")
    elif "review" in template:
        issue(issues, "ERROR", "INVALID_REVIEW", "review", "review must be an object.")


def _validate_lifecycle(template: dict[str, Any], issues: list[ValidationIssue]) -> None:
    status = template.get("status")
    review = template.get("review")
    review_status = review.get("status") if isinstance(review, dict) else None
    if status == "DRAFT":
        issue(
            issues,
            "WARNING",
            "ARTIFACT_NOT_FINAL",
            "status",
            "Draft artifacts are not eligible for the trusted chain.",
            blocking=True,
        )
    if review_status != "APPROVED":
        issue(
            issues,
            "WARNING",
            "REVIEW_NOT_APPROVED",
            "review.status",
            "Human Review must approve the complete Template before Final use.",
            blocking=True,
        )
    if status == "FINAL" and review_status != "APPROVED":
        issue(
            issues,
            "ERROR",
            "FINAL_REQUIRES_APPROVED_REVIEW",
            "review.status",
            "FINAL status requires an approved Human Review.",
        )


def _validate_dependencies(
    template: dict[str, Any],
    standard: object,
    rule_package: object,
    issues: list[ValidationIssue],
) -> dict[str, Any]:
    context: dict[str, Any] = {"standard": None, "standard_fields": {}}
    if not isinstance(standard, dict):
        issue(
            issues,
            "ERROR",
            "INVALID_STANDARD_DEPENDENCY",
            "standardRef",
            "InterfaceTemplateIR requires a Final InterfaceStandardIR object.",
        )
        return context

    context["standard"] = standard
    standard_review = standard.get("review")
    if (
        standard.get("contractVersion") != STANDARD_CONTRACT_VERSION
        or standard.get("status") != "FINAL"
        or not isinstance(standard_review, dict)
        or standard_review.get("status") != "APPROVED"
    ):
        issue(
            issues,
            "ERROR",
            "STANDARD_NOT_FINAL",
            "standardRef",
            "InterfaceTemplateIR requires a reviewed Final InterfaceStandardIR dependency.",
        )

    if template.get("interfaceCode") != standard.get("interfaceCode"):
        issue(
            issues,
            "ERROR",
            "INTERFACE_CODE_MISMATCH",
            "interfaceCode",
            "InterfaceTemplateIR interfaceCode must match the bound Standard.",
        )
    if template.get("direction") != standard.get("direction"):
        issue(
            issues,
            "ERROR",
            "DIRECTION_MISMATCH",
            "direction",
            "InterfaceTemplateIR direction must match the bound Standard.",
        )

    reference = template.get("standardRef")
    if isinstance(reference, dict):
        _object_contract(
            reference,
            STANDARD_REF_PROPERTIES,
            STANDARD_REF_PROPERTIES,
            issues,
            path="standardRef",
            missing_code="MISSING_STANDARD_REFERENCE_PROPERTY",
            unknown_code="UNKNOWN_STANDARD_REFERENCE_PROPERTY",
        )
        _stable_id(reference.get("standardId"), issues, "INVALID_STANDARD_REFERENCE", "standardRef.standardId")
        _version(
            reference.get("standardVersion"),
            issues,
            "INVALID_STANDARD_REFERENCE",
            "standardRef.standardVersion",
        )
        hash_value = reference.get("contentHash")
        if not isinstance(hash_value, str) or not SHA256_PATTERN.fullmatch(hash_value):
            issue(
                issues,
                "ERROR",
                "INVALID_STANDARD_CONTENT_HASH",
                "standardRef.contentHash",
                "Standard contentHash must be a canonical SHA-256 value.",
            )
        if (
            reference.get("standardId") != standard.get("standardId")
            or reference.get("standardVersion") != standard.get("standardVersion")
        ):
            issue(
                issues,
                "ERROR",
                "STANDARD_REFERENCE_MISMATCH",
                "standardRef",
                "Standard identity and version reference must match the dependency.",
            )
        if hash_value != content_hash(standard):
            issue(
                issues,
                "ERROR",
                "STANDARD_HASH_MISMATCH",
                "standardRef.contentHash",
                "Standard contentHash must match the complete dependency content.",
            )
    elif "standardRef" in template:
        issue(issues, "ERROR", "INVALID_STANDARD_REFERENCE", "standardRef", "standardRef must be an object.")

    raw_fields = standard.get("fields")
    if not isinstance(raw_fields, list):
        issue(
            issues,
            "ERROR",
            "INVALID_STANDARD_DEPENDENCY",
            "standardRef",
            "Bound Standard fields must be an array.",
        )
    else:
        fields = [field for field in raw_fields if isinstance(field, dict)]
        duplicates = [ref for ref, count in Counter(field.get("fieldId") for field in fields).items() if ref and count > 1]
        if duplicates:
            issue(
                issues,
                "ERROR",
                "INVALID_STANDARD_DEPENDENCY",
                "standardRef",
                "Bound Standard field IDs must be unique.",
            )
        context["standard_fields"] = {
            field["fieldId"]: field
            for field in fields
            if isinstance(field.get("fieldId"), str) and field.get("fieldId")
        }

    if not isinstance(rule_package, RulePackage):
        issue(
            issues,
            "ERROR",
            "INVALID_RULE_PACKAGE",
            "rulePackageVersion",
            "A validated configuration rule package is required.",
        )
    else:
        if rule_package.status != "RELEASED":
            issue(
                issues,
                "ERROR",
                "RULE_PACKAGE_NOT_RELEASED",
                "rulePackageVersion",
                "Final-capable validation requires a RELEASED rule package.",
            )
        if template.get("rulePackageVersion") != rule_package.version:
            issue(
                issues,
                "ERROR",
                "RULE_PACKAGE_VERSION_MISMATCH",
                "rulePackageVersion",
                "InterfaceTemplateIR rulePackageVersion must match the loaded package.",
            )
    return context


def _validate_field_configs(
    configs: list[Any],
    *,
    template: dict[str, Any],
    context: dict[str, Any],
    rule_package: object,
    counters: Counter[str],
    issues: list[ValidationIssue],
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    standard_fields: dict[str, dict[str, Any]] = context["standard_fields"]
    direction = template.get("direction")

    for index, value in enumerate(configs):
        path = f"fieldConfigs[{index}]"
        if not isinstance(value, dict):
            issue(issues, "ERROR", "INVALID_FIELD_CONFIG", path, "Field config must be an object.")
            continue
        validated.append(value)
        if direction == "ASSEMBLY":
            required_properties = ASSEMBLY_FIELD_CONFIG_PROPERTIES
            allowed_properties = ASSEMBLY_FIELD_CONFIG_PROPERTIES
        elif direction == "PARSE":
            required_properties = COMMON_FIELD_CONFIG_PROPERTIES | {"parseTarget"}
            allowed_properties = PARSE_FIELD_CONFIG_PROPERTIES
        else:
            required_properties = COMMON_FIELD_CONFIG_PROPERTIES
            allowed_properties = COMMON_FIELD_CONFIG_PROPERTIES
        _object_contract(
            value,
            required_properties,
            allowed_properties,
            issues,
            path=path,
            missing_code="MISSING_FIELD_CONFIG_PROPERTY",
            unknown_code="UNKNOWN_FIELD_CONFIG_PROPERTY",
        )

        binding_kind = _enum(
            value.get("bindingKind"),
            BINDING_KINDS,
            issues,
            "INVALID_BINDING_KIND",
            f"{path}.bindingKind",
        )
        if binding_kind:
            counters[f"binding:{binding_kind}"] += 1

        standard_field: dict[str, Any] | None = None
        if direction == "ASSEMBLY":
            standard_field = _validate_standard_target(
                value.get("standardTarget"),
                standard_fields,
                issues,
                path=f"{path}.standardTarget",
            )
            if binding_kind == "COLLECTION_ITEM":
                issue(
                    issues,
                    "ERROR",
                    "INVALID_ASSEMBLY_BINDING_KIND",
                    f"{path}.bindingKind",
                    "ASSEMBLY supports VALUE and STRUCTURE_ONLY bindings only.",
                )
        elif direction == "PARSE":
            if binding_kind == "STRUCTURE_ONLY":
                issue(
                    issues,
                    "ERROR",
                    "INVALID_PARSE_BINDING_KIND",
                    f"{path}.bindingKind",
                    "PARSE supports VALUE and COLLECTION_ITEM bindings only.",
                )
            if binding_kind == "COLLECTION_ITEM":
                standard_field = _validate_standard_source(
                    value.get("standardSource"),
                    standard_fields,
                    issues,
                    path=f"{path}.standardSource",
                )
            elif "standardSource" in value:
                issue(
                    issues,
                    "ERROR",
                    "PARSE_STANDARD_SOURCE_FORBIDDEN",
                    f"{path}.standardSource",
                    "PARSE VALUE expressions own their zero or more Standard sources.",
                )

        parse_target = _validate_parse_target(
            value.get("parseTarget"),
            direction=direction,
            binding_kind=binding_kind,
            rule_package=rule_package,
            issues=issues,
            path=f"{path}.parseTarget",
        )
        value_expression = value.get("valueExpression")

        if direction == "ASSEMBLY":
            data_type = standard_field.get("dataType") if standard_field else None
            if data_type in SCALAR_TYPES:
                if binding_kind != "VALUE":
                    issue(
                        issues,
                        "ERROR",
                        "INVALID_SCALAR_BINDING_KIND",
                        f"{path}.bindingKind",
                        "Scalar Standard targets require VALUE binding.",
                    )
                if binding_kind == "VALUE" and not isinstance(value_expression, dict):
                    issue(
                        issues,
                        "ERROR",
                        "MISSING_SCALAR_VALUE_EXPRESSION",
                        f"{path}.valueExpression",
                        "Scalar VALUE binding requires a field value expression.",
                    )
                elif binding_kind != "VALUE" and value_expression is not None:
                    issue(
                        issues,
                        "ERROR",
                        "SCALAR_VALUE_EXPRESSION_FORBIDDEN",
                        f"{path}.valueExpression",
                        "A non-VALUE scalar binding cannot contain a field value expression.",
                    )
            elif data_type in CONTAINER_TYPES:
                if binding_kind != "STRUCTURE_ONLY":
                    issue(
                        issues,
                        "ERROR",
                        "INVALID_CONTAINER_BINDING_KIND",
                        f"{path}.bindingKind",
                        "ASSEMBLY Node/Object targets require STRUCTURE_ONLY binding.",
                    )
                if value_expression is not None:
                    issue(
                        issues,
                        "ERROR",
                        "CONTAINER_VALUE_EXPRESSION_FORBIDDEN",
                        f"{path}.valueExpression",
                        "Node/Object targets do not have field value expressions.",
                    )
        elif direction == "PARSE":
            if binding_kind == "VALUE" and not isinstance(value_expression, dict):
                issue(
                    issues,
                    "ERROR",
                    "MISSING_PARSE_VALUE_EXPRESSION",
                    f"{path}.valueExpression",
                    "PARSE VALUE binding requires a value expression.",
                )
            if binding_kind == "VALUE" and isinstance(parse_target, dict) and parse_target.get("dataType") == "LIST":
                issue(
                    issues,
                    "ERROR",
                    "INVALID_PARSE_VALUE_TARGET",
                    f"{path}.parseTarget",
                    "PARSE VALUE binding cannot target a LIST.",
                )
            if binding_kind == "COLLECTION_ITEM":
                if standard_field is not None and standard_field.get("dataType") != "Node":
                    issue(
                        issues,
                        "ERROR",
                        "INVALID_COLLECTION_BINDING",
                        f"{path}.standardSource",
                        "COLLECTION_ITEM requires a PARSE Standard Node source.",
                    )
                if not isinstance(parse_target, dict) or parse_target.get("dataType") != "LIST":
                    issue(
                        issues,
                        "ERROR",
                        "INVALID_COLLECTION_TARGET",
                        f"{path}.parseTarget",
                        "COLLECTION_ITEM requires a Parse LIST target.",
                    )
                if value_expression is not None:
                    issue(
                        issues,
                        "ERROR",
                        "COLLECTION_VALUE_EXPRESSION_FORBIDDEN",
                        f"{path}.valueExpression",
                        "COLLECTION_ITEM establishes context and cannot contain a value expression.",
                    )

        if isinstance(value_expression, dict):
            counters["fieldValueExpressionCount"] += 1
            _validate_expression(
                value_expression,
                direction=direction,
                template_status=template.get("status"),
                standard_fields=standard_fields,
                rule_package=rule_package,
                counters=counters,
                issues=issues,
                path=f"{path}.valueExpression",
                root=True,
            )

        if direction == "ASSEMBLY":
            _validate_xml_key_expressions(
                value.get("xmlKeyExpressions"),
                template_status=template.get("status"),
                standard_field=standard_field,
                standard_fields=standard_fields,
                rule_package=rule_package,
                counters=counters,
                issues=issues,
                path=f"{path}.xmlKeyExpressions",
            )
        elif "xmlKeyExpressions" in value:
            issue(
                issues,
                "ERROR",
                "PARSE_XML_KEY_EXPRESSION_FORBIDDEN",
                f"{path}.xmlKeyExpressions",
                "xmlKeyExpressions are ASSEMBLY-only.",
            )
        # Replacement 处理表达式的最终赋值结果，因此按方向校验实际 target，而不是 PARSE 的任一 source。
        replacement = _validate_processing_policies(
            value.get("processingPolicies"),
            template_status=template.get("status"),
            target_data_type=(
                standard_field.get("dataType")
                if direction == "ASSEMBLY" and standard_field is not None
                else parse_target.get("dataType")
                if direction == "PARSE" and isinstance(parse_target, dict)
                else None
            ),
            rule_package=rule_package,
            issues=issues,
            path=f"{path}.processingPolicies",
        )
        if replacement:
            counters["replacementCount"] += 1

        required_rules = {
            f"TPL.BIND.{direction}" if direction in DIRECTIONS else "",
            "TPL.BIND.STANDARD_PROJECTION",
            "TPL.PROCESS.EMPTY_HANDLING",
            "TPL.PROCESS.OVERLENGTH",
            "TPL.PROCESS.ROW_LIMIT",
            "TPL.PROCESS.CHAR_LENGTH",
        }
        if binding_kind == "STRUCTURE_ONLY":
            required_rules.add("TPL.BIND.STRUCTURE_ONLY")
        elif binding_kind == "COLLECTION_ITEM":
            required_rules.add("TPL.BIND.COLLECTION_ITEM")
        if replacement:
            required_rules.add("TPL.PROCESS.REPLACEMENT")
        required_rules.discard("")
        _validate_rule_references(
            value.get("ruleReferences"),
            rule_package,
            issues,
            path=f"{path}.ruleReferences",
            required=required_rules,
        )
        _validate_evidence(value.get("evidence"), issues, path=f"{path}.evidence")
        _validate_review_signals(value, counters, issues, path=path)

    _validate_target_uniqueness(validated, direction, issues)
    return validated


def _validate_standard_target(
    value: Any,
    standard_fields: dict[str, dict[str, Any]],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        issue(
            issues,
            "ERROR",
            "MISSING_STANDARD_TARGET",
            path,
            "ASSEMBLY field config requires a standardTarget object.",
        )
        return None
    _object_contract(
        value,
        STANDARD_TARGET_PROPERTIES,
        STANDARD_TARGET_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_STANDARD_TARGET_PROPERTY",
        unknown_code="UNKNOWN_STANDARD_TARGET_PROPERTY",
    )
    reference = _required_string(
        value.get("standardFieldRef"),
        issues,
        "INVALID_STANDARD_FIELD_REFERENCE",
        f"{path}.standardFieldRef",
    )
    standard_field = standard_fields.get(reference) if reference else None
    if reference and standard_field is None:
        issue(
            issues,
            "ERROR",
            "UNKNOWN_STANDARD_FIELD_REFERENCE",
            f"{path}.standardFieldRef",
            "standardTarget.standardFieldRef must exist in the bound Standard.",
        )
    _validate_standard_projection(
        value.get("standardProjection"),
        standard_field,
        issues,
        path=f"{path}.standardProjection",
    )
    return standard_field


def _validate_standard_source(
    value: Any,
    standard_fields: dict[str, dict[str, Any]],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        issue(
            issues,
            "ERROR",
            "MISSING_STANDARD_SOURCE",
            path,
            "PARSE COLLECTION_ITEM requires a standardSource object.",
        )
        return None
    _object_contract(
        value,
        STANDARD_SOURCE_PROPERTIES,
        STANDARD_SOURCE_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_STANDARD_SOURCE_PROPERTY",
        unknown_code="UNKNOWN_STANDARD_SOURCE_PROPERTY",
    )
    reference = _required_string(
        value.get("standardFieldRef"),
        issues,
        "INVALID_STANDARD_FIELD_REFERENCE",
        f"{path}.standardFieldRef",
    )
    standard_field = standard_fields.get(reference) if reference else None
    if reference and standard_field is None:
        issue(
            issues,
            "ERROR",
            "UNKNOWN_STANDARD_FIELD_REFERENCE",
            f"{path}.standardFieldRef",
            "standardSource.standardFieldRef must exist in the bound Standard.",
        )
    return standard_field


def _validate_standard_projection(
    value: Any,
    standard_field: dict[str, Any] | None,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_STANDARD_PROJECTION", path, "standardProjection must be an object.")
        return
    _object_contract(
        value,
        STANDARD_PROJECTION_PROPERTIES,
        STANDARD_PROJECTION_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_STANDARD_PROJECTION_PROPERTY",
        unknown_code="UNKNOWN_STANDARD_PROJECTION_PROPERTY",
    )
    _boolean(value.get("required"), issues, "INVALID_STANDARD_PROJECTION", f"{path}.required")
    _required_string(value.get("dataType"), issues, "INVALID_STANDARD_PROJECTION", f"{path}.dataType")
    if not isinstance(value.get("length"), dict):
        issue(
            issues,
            "ERROR",
            "INVALID_STANDARD_PROJECTION",
            f"{path}.length",
            "Projected length must be an object.",
        )
    if standard_field is not None:
        expected = {
            "required": standard_field.get("required"),
            "length": standard_field.get("lengthLimit"),
            "dataType": standard_field.get("dataType"),
        }
        if value != expected:
            issue(
                issues,
                "ERROR",
                "STANDARD_PROJECTION_MISMATCH",
                path,
                "standardProjection must exactly mirror required, lengthLimit and dataType from the bound Standard.",
            )


def _validate_parse_target(
    value: Any,
    *,
    direction: Any,
    binding_kind: str | None,
    rule_package: object,
    issues: list[ValidationIssue],
    path: str,
) -> dict[str, Any] | None:
    if direction == "ASSEMBLY":
        if value is not None:
            issue(issues, "ERROR", "ASSEMBLY_PARSE_TARGET_FORBIDDEN", path, "ASSEMBLY bindings do not have Parse targets.")
        return None
    if direction != "PARSE":
        return None
    if binding_kind == "STRUCTURE_ONLY":
        if value is not None:
            issue(issues, "ERROR", "STRUCTURE_PARSE_TARGET_FORBIDDEN", path, "PARSE STRUCTURE_ONLY has no target value.")
        return None
    if not isinstance(value, dict):
        issue(issues, "ERROR", "MISSING_PARSE_TARGET", path, "PARSE VALUE/COLLECTION_ITEM binding requires a Parse target.")
        return None
    _object_contract(
        value,
        PARSE_TARGET_PROPERTIES,
        PARSE_TARGET_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_PARSE_TARGET_PROPERTY",
        unknown_code="UNKNOWN_PARSE_TARGET_PROPERTY",
    )
    reference = _required_string(value.get("parseFieldRef"), issues, "INVALID_PARSE_TARGET", f"{path}.parseFieldRef")
    if not isinstance(rule_package, RulePackage) or reference is None:
        return value
    catalog = rule_package.fields_by_direction.get("PARSE", {})
    expected_entry = catalog.get(reference)
    if expected_entry is None:
        issue(issues, "ERROR", "UNKNOWN_PARSE_FIELD_REFERENCE", f"{path}.parseFieldRef", "Parse target must exist in the PARSE FIELD catalog.")
        return value
    expected = {
        "parseFieldRef": reference,
        "name": reference,
        "parentPath": expected_entry.get("parentPath"),
        "fullPath": expected_entry.get("fullPath"),
        "dataType": expected_entry.get("dataType"),
    }
    if value != expected:
        issue(
            issues,
            "ERROR",
            "PARSE_TARGET_MISMATCH",
            path,
            "Parse target name, path and dataType must exactly match the catalog snapshot.",
        )
    return value


def _validate_xml_key_expressions(
    value: Any,
    *,
    template_status: Any,
    standard_field: dict[str, Any] | None,
    standard_fields: dict[str, dict[str, Any]],
    rule_package: object,
    counters: Counter[str],
    issues: list[ValidationIssue],
    path: str,
) -> None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_XML_KEY_EXPRESSIONS", path, "xmlKeyExpressions must be an object.")
        return
    expected_keys = {
        item.get("name")
        for item in (standard_field.get("xmlKeys", []) if standard_field else [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    actual_keys = set(value)
    for key in sorted(expected_keys - actual_keys):
        issue(issues, "ERROR", "MISSING_XML_KEY_EXPRESSION", path, "Every Standard XML Key requires one ASSEMBLY expression.")
    for key in sorted(actual_keys - expected_keys):
        issue(issues, "ERROR", "UNKNOWN_XML_KEY_EXPRESSION", f"{path}.{key}", "XML Key expression is not declared by the Standard field.")
    for key, expression_value in value.items():
        if isinstance(expression_value, dict):
            counters["xmlKeyExpressionCount"] += 1
            _validate_expression(
                expression_value,
                direction="ASSEMBLY",
                template_status=template_status,
                standard_fields=standard_fields,
                rule_package=rule_package,
                counters=counters,
                issues=issues,
                path=f"{path}.{key}",
                root=True,
            )
        else:
            issue(issues, "ERROR", "INVALID_VALUE_EXPRESSION", f"{path}.{key}", "XML Key expression must be an object.")


def _validate_expression(
    value: dict[str, Any],
    *,
    direction: Any,
    template_status: Any,
    standard_fields: dict[str, dict[str, Any]],
    rule_package: object,
    counters: Counter[str],
    issues: list[ValidationIssue],
    path: str,
    root: bool,
) -> None:
    mode = value.get("mode")
    if mode not in VALUE_MODES:
        issue(issues, "ERROR", "INVALID_VALUE_MODE", f"{path}.mode", "Expression mode is outside the supported set.")
        allowed = EXPRESSION_COMMON_PROPERTIES
    else:
        allowed = _expression_properties(mode, direction)
    _object_contract(
        value,
        allowed,
        allowed,
        issues,
        path=path,
        missing_code="MISSING_EXPRESSION_PROPERTY",
        unknown_code="UNKNOWN_EXPRESSION_PROPERTY",
    )
    sequence = value.get("sequence")
    if not _is_positive_integer(sequence):
        issue(issues, "ERROR", "INVALID_EXPRESSION_SEQUENCE", f"{path}.sequence", "Expression sequence must be a positive integer.")
    elif root and sequence != 1:
        issue(issues, "ERROR", "INVALID_EXPRESSION_SEQUENCE", f"{path}.sequence", "Root expression sequence must be 1.")

    expected_rule = f"TPL.VALUE.{mode}" if mode in VALUE_MODES else None
    _validate_rule_references(
        value.get("ruleReferences"),
        rule_package,
        issues,
        path=f"{path}.ruleReferences",
        required={expected_rule} if expected_rule else set(),
    )

    if mode == "FIXED_VALUE":
        _validate_fixed_payload(value.get("payload"), issues, path=f"{path}.payload")
    elif mode == "FIELD":
        reference_property = _expression_reference_property(direction)
        _validate_expression_field_reference(
            value.get(reference_property),
            direction,
            standard_fields,
            rule_package,
            issues,
            path=f"{path}.{reference_property}",
        )
    elif mode == "FUNCTION":
        counters["functionInvocationCount"] += 1
        _validate_function(
            value,
            direction=direction,
            standard_fields=standard_fields,
            rule_package=rule_package,
            issues=issues,
            path=path,
        )
    elif mode == "MAPPING":
        counters["mappingExpressionCount"] += 1
        reference_property = _expression_reference_property(direction)
        source_data_type = _validate_expression_field_reference(
            value.get(reference_property),
            direction,
            standard_fields,
            rule_package,
            issues,
            path=f"{path}.{reference_property}",
        )
        if source_data_type is not None and source_data_type != "String":
            issue(
                issues,
                "ERROR",
                "MAPPING_REQUIRES_STRING_SOURCE",
                f"{path}.{reference_property}",
                "MAPPING requires a String FIELD source.",
            )
        _validate_mapping_reference(
            value.get("mappingRuleName"),
            template_status=template_status,
            rule_package=rule_package,
            issues=issues,
            path=f"{path}.mappingRuleName",
            unknown_code="UNKNOWN_MAPPING_RULE",
        )
    elif mode == "CONCATENATE":
        children = value.get("children")
        if not isinstance(children, list) or not children:
            issue(issues, "ERROR", "INVALID_CONCATENATE_CHILDREN", f"{path}.children", "CONCATENATE requires one or more child expressions.")
            return
        child_objects = [child for child in children if isinstance(child, dict)]
        if len(child_objects) != len(children):
            issue(issues, "ERROR", "INVALID_VALUE_EXPRESSION", f"{path}.children", "Every CONCATENATE child must be an object.")
        sequences = [child.get("sequence") for child in child_objects]
        if sequences != list(range(1, len(child_objects) + 1)):
            issue(
                issues,
                "ERROR",
                "NON_CONTIGUOUS_EXPRESSION_SEQUENCE",
                f"{path}.children",
                "CONCATENATE child sequence must be contiguous and ordered from 1.",
            )
        for index, child in enumerate(child_objects):
            _validate_expression(
                child,
                direction=direction,
                template_status=template_status,
                standard_fields=standard_fields,
                rule_package=rule_package,
                counters=counters,
                issues=issues,
                path=f"{path}.children[{index}]",
                root=False,
            )


def _expression_reference_property(direction: Any) -> str:
    return "assemblyFieldRef" if direction == "ASSEMBLY" else "standardFieldRef"


def _expression_properties(mode: str, direction: Any) -> set[str]:
    reference_property = _expression_reference_property(direction)
    mode_properties = {
        "FIXED_VALUE": {"payload"},
        "EMPTY": set(),
        "FIELD": {reference_property},
        "FUNCTION": {"functionCode", "arguments"},
        "MAPPING": {reference_property, "mappingRuleName"},
        "CONCATENATE": {"children"},
    }
    return EXPRESSION_COMMON_PROPERTIES | mode_properties[mode]


def _validate_fixed_payload(value: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_FIXED_VALUE_PAYLOAD", path, "FIXED_VALUE payload must be an object.")
        return
    _object_contract(
        value,
        PAYLOAD_PROPERTIES,
        PAYLOAD_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_FIXED_VALUE_PAYLOAD_PROPERTY",
        unknown_code="UNKNOWN_FIXED_VALUE_PAYLOAD_PROPERTY",
    )
    kind = _enum(
        value.get("kind"),
        {"LITERAL", "SECURE_INPUT_REF"},
        issues,
        "INVALID_FIXED_VALUE_PAYLOAD_KIND",
        f"{path}.kind",
    )
    payload = _required_string(value.get("value"), issues, "INVALID_FIXED_VALUE_PAYLOAD", f"{path}.value")
    if payload is None:
        return
    if kind == "LITERAL" and payload == REDACTED_VALUE:
        issue(issues, "ERROR", "REDACTED_LITERAL_FORBIDDEN", f"{path}.value", "Redaction placeholders are not executable literals.")
    if kind == "SECURE_INPUT_REF" and (
        payload == REDACTED_VALUE or not SECURE_REFERENCE_PATTERN.fullmatch(payload)
    ):
        issue(
            issues,
            "ERROR",
            "INVALID_SECURE_INPUT_REFERENCE",
            f"{path}.value",
            "SECURE_INPUT_REF must contain only a safe reference identifier, never a secret or redaction placeholder.",
        )


def _validate_expression_field_reference(
    value: Any,
    direction: Any,
    standard_fields: dict[str, dict[str, Any]],
    rule_package: object,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> str | None:
    reference = _required_string(value, issues, "INVALID_FIELD_REFERENCE", path)
    if reference is None:
        return None
    if direction == "ASSEMBLY":
        entry = (
            rule_package.fields_by_direction.get("ASSEMBLY", {}).get(reference)
            if isinstance(rule_package, RulePackage)
            else None
        )
        if entry is None:
            issue(issues, "ERROR", "UNKNOWN_ASSEMBLY_FIELD_REFERENCE", path, "ASSEMBLY FIELD reference must exist in the loaded catalog.")
            return None
        return entry.get("dataType") if isinstance(entry.get("dataType"), str) else None
    if direction == "PARSE":
        standard_field = standard_fields.get(reference)
        if standard_field is None:
            issue(issues, "ERROR", "UNKNOWN_STANDARD_FIELD_REFERENCE", path, "PARSE FIELD reference must identify a bound Standard source field.")
            return None
        return standard_field.get("dataType") if isinstance(standard_field.get("dataType"), str) else None
    return None


def _validate_function(
    expression_value: dict[str, Any],
    *,
    direction: Any,
    standard_fields: dict[str, dict[str, Any]],
    rule_package: object,
    issues: list[ValidationIssue],
    path: str,
) -> None:
    code = _required_string(expression_value.get("functionCode"), issues, "INVALID_FUNCTION_REFERENCE", f"{path}.functionCode")
    function = (
        rule_package.functions_by_code.get(code)
        if isinstance(rule_package, RulePackage) and code is not None
        else None
    )
    if code is not None and function is None:
        issue(issues, "ERROR", "UNKNOWN_FUNCTION_REFERENCE", f"{path}.functionCode", "Function must exist in the loaded catalog.")

    arguments = expression_value.get("arguments")
    if not isinstance(arguments, list):
        issue(issues, "ERROR", "INVALID_FUNCTION_ARGUMENTS", f"{path}.arguments", "Function arguments must be an array.")
        return
    if function is None:
        return
    parameters = function.get("parameters", [])
    if len(arguments) != len(parameters):
        issue(issues, "ERROR", "FUNCTION_ARGUMENT_MISMATCH", f"{path}.arguments", "Function argument count must match the catalog signature.")
    for index, argument in enumerate(arguments):
        argument_path = f"{path}.arguments[{index}]"
        if not isinstance(argument, dict):
            issue(issues, "ERROR", "INVALID_FUNCTION_ARGUMENT", argument_path, "Function argument must be an object.")
            continue
        raw_kind = argument.get("kind")
        value_property = (
            _expression_reference_property(direction)
            if raw_kind == "FIELD_REF"
            else "value"
        )
        argument_properties = {"position", "kind", value_property}
        _object_contract(
            argument,
            argument_properties,
            argument_properties,
            issues,
            path=argument_path,
            missing_code="MISSING_FUNCTION_ARGUMENT_PROPERTY",
            unknown_code="UNKNOWN_FUNCTION_ARGUMENT_PROPERTY",
        )
        position = argument.get("position")
        if not _is_positive_integer(position):
            issue(issues, "ERROR", "INVALID_FUNCTION_ARGUMENT", f"{argument_path}.position", "Argument position must be a positive integer.")
        kind = _enum(
            argument.get("kind"),
            {"FIELD_REF", "LITERAL"},
            issues,
            "INVALID_FUNCTION_ARGUMENT",
            f"{argument_path}.kind",
        )
        argument_value = _required_string(
            argument.get(value_property),
            issues,
            "INVALID_FUNCTION_ARGUMENT",
            f"{argument_path}.{value_property}",
        )
        if index >= len(parameters):
            continue
        parameter = parameters[index]
        if position != parameter.get("position") or kind not in parameter.get("allowedArgumentKinds", []):
            issue(
                issues,
                "ERROR",
                "FUNCTION_ARGUMENT_MISMATCH",
                argument_path,
                "Function argument position and kind must match the catalog signature.",
            )
        if kind == "FIELD_REF" and argument_value is not None:
            source_data_type = _validate_expression_field_reference(
                argument_value,
                direction,
                standard_fields,
                rule_package,
                issues,
                path=f"{argument_path}.{value_property}",
            )
            parameter_data_type = parameter.get("dataType")
            if (
                source_data_type is not None
                and isinstance(parameter_data_type, str)
                and source_data_type != parameter_data_type
            ):
                issue(
                    issues,
                    "ERROR",
                    "FUNCTION_ARGUMENT_TYPE_MISMATCH",
                    f"{argument_path}.{value_property}",
                    "FIELD_REF dataType must match the function parameter dataType.",
                )


def _validate_processing_policies(
    value: Any,
    *,
    template_status: Any,
    target_data_type: Any,
    rule_package: object,
    issues: list[ValidationIssue],
    path: str,
) -> str | None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_PROCESSING_POLICIES", path, "processingPolicies must be an object.")
        return None
    _object_contract(
        value,
        PROCESSING_PROPERTIES,
        PROCESSING_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_PROCESSING_POLICY",
        unknown_code="UNKNOWN_PROCESSING_POLICY",
    )
    policies = _policy_contract(rule_package)
    _enum(
        value.get("emptyHandling"),
        policies["emptyHandling"],
        issues,
        "INVALID_EMPTY_HANDLING",
        f"{path}.emptyHandling",
    )
    _enum(
        value.get("overlengthHandling"),
        policies["overlengthHandling"],
        issues,
        "INVALID_OVERLENGTH_HANDLING",
        f"{path}.overlengthHandling",
    )
    row_limit = value.get("rowLimit")
    if not _is_positive_integer(row_limit):
        issue(issues, "ERROR", "INVALID_ROW_LIMIT", f"{path}.rowLimit", "rowLimit must be a positive integer.")
    _enum(
        value.get("chineseCharacterLength"),
        policies["chineseCharacterLength"],
        issues,
        "INVALID_CHINESE_CHARACTER_LENGTH",
        f"{path}.chineseCharacterLength",
    )

    replacement = value.get("replacementRuleName")
    if replacement is not None:
        parsed = _required_string(replacement, issues, "INVALID_REPLACEMENT_RULE", f"{path}.replacementRuleName")
        if parsed is not None:
            _validate_mapping_reference(
                parsed,
                template_status=template_status,
                rule_package=rule_package,
                issues=issues,
                path=f"{path}.replacementRuleName",
                unknown_code="UNKNOWN_REPLACEMENT_RULE",
            )
            if target_data_type is not None and target_data_type != "String":
                issue(
                    issues,
                    "ERROR",
                    "REPLACEMENT_REQUIRES_STRING_TARGET",
                    f"{path}.replacementRuleName",
                    "Replacement applies only to String target values.",
                )
            return parsed
    return None


def _policy_contract(rule_package: object) -> dict[str, set[str]]:
    defaults = {
        "emptyHandling": {"BLANK", "DELETE"},
        "overlengthHandling": {"INTERCEPT", "TRUNCATE_FRONT", "OVERLONG_LINE_BREAK", "TRUNCATE_BACK"},
        "chineseCharacterLength": {f"STANDARD_{index}" for index in range(1, 7)},
    }
    if not isinstance(rule_package, RulePackage):
        return defaults
    policies = rule_package.documents.get("rules.yaml", {}).get("processingPolicies")
    if not isinstance(policies, dict):
        return defaults
    for target, source in (
        ("emptyHandling", "emptyHandling"),
        ("overlengthHandling", "overlengthHandling"),
        ("chineseCharacterLength", "chineseCharacterLength"),
    ):
        contract = policies.get(source)
        allowed = contract.get("allowedValues") if isinstance(contract, dict) else None
        if isinstance(allowed, list) and all(isinstance(item, str) for item in allowed):
            defaults[target] = set(allowed)
    return defaults


def _validate_mapping_reference(
    value: Any,
    *,
    template_status: Any,
    rule_package: object,
    issues: list[ValidationIssue],
    path: str,
    unknown_code: str,
) -> None:
    reference = _required_string(value, issues, "INVALID_MAPPING_RULE", path)
    if reference is None or not isinstance(rule_package, RulePackage):
        return
    mapping = rule_package.mappings_by_name.get(reference)
    if mapping is None:
        issue(issues, "ERROR", unknown_code, path, "mappingRuleName must exist in the loaded catalog.")
        return
    if template_status == "FINAL" and mapping.get("redacted") is True:
        issue(
            issues,
            "ERROR",
            "REDACTED_MAPPING_FORBIDDEN_IN_FINAL",
            path,
            "Final Template cannot reference a redacted Mapping rule.",
        )


def _validate_rule_references(
    value: Any,
    rule_package: object,
    issues: list[ValidationIssue],
    *,
    path: str,
    required: set[str],
) -> None:
    if not isinstance(value, list) or not value:
        issue(issues, "ERROR", "INVALID_RULE_REFERENCES", path, "ruleReferences must be a non-empty array.")
        return
    references: list[str] = []
    for index, reference in enumerate(value):
        parsed = _required_string(reference, issues, "INVALID_RULE_REFERENCE", f"{path}[{index}]")
        if parsed is not None:
            references.append(parsed)
    if len(references) != len(set(references)):
        issue(issues, "ERROR", "DUPLICATE_RULE_REFERENCE", path, "ruleReferences must not contain duplicates.")
    if isinstance(rule_package, RulePackage):
        for reference in references:
            rule = rule_package.rules_by_id.get(reference)
            if rule is None:
                issue(issues, "ERROR", "UNKNOWN_RULE_REFERENCE", path, "Rule reference must exist in the loaded package.")
            elif rule.get("domain") != "TEMPLATE":
                issue(issues, "ERROR", "INVALID_RULE_REFERENCE_DOMAIN", path, "Template may reference only TEMPLATE rules.")
    for reference in sorted(required - set(references)):
        issue(
            issues,
            "ERROR",
            "MISSING_REQUIRED_RULE_REFERENCE",
            path,
            "Field config or expression is missing a governing Template Rule ID.",
        )


def _validate_evidence(value: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(value, list) or not value:
        issue(issues, "ERROR", "INVALID_EVIDENCE", path, "evidence must be a non-empty array.")
        return
    for index, entry in enumerate(value):
        entry_path = f"{path}[{index}]"
        if not isinstance(entry, dict):
            issue(issues, "ERROR", "INVALID_EVIDENCE", entry_path, "Evidence must be an object.")
            continue
        _object_contract(
            entry,
            EVIDENCE_PROPERTIES,
            EVIDENCE_PROPERTIES,
            issues,
            path=entry_path,
            missing_code="MISSING_EVIDENCE_PROPERTY",
            unknown_code="UNKNOWN_EVIDENCE_PROPERTY",
        )
        _enum(entry.get("kind"), EVIDENCE_KINDS, issues, "INVALID_EVIDENCE_KIND", f"{entry_path}.kind")
        _required_string(entry.get("sourceRef"), issues, "INVALID_EVIDENCE", f"{entry_path}.sourceRef")
        _required_string(entry.get("note"), issues, "INVALID_EVIDENCE", f"{entry_path}.note")


def _validate_review_signals(
    value: dict[str, Any],
    counters: Counter[str],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    confidence = value.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        issue(issues, "ERROR", "INVALID_CONFIDENCE", f"{path}.confidence", "confidence must be a number from 0 to 1.")
    uncertain = _boolean(value.get("uncertain"), issues, "INVALID_UNCERTAIN", f"{path}.uncertain")
    reason = _nullable_string(
        value.get("uncertainReason"), issues, "INVALID_UNCERTAIN_REASON", f"{path}.uncertainReason"
    )
    _nullable_string(value.get("reviewNote"), issues, "INVALID_REVIEW_NOTE", f"{path}.reviewNote")
    if uncertain is True:
        counters["uncertainFieldConfigCount"] += 1
        if reason is None:
            issue(issues, "ERROR", "MISSING_UNCERTAIN_REASON", f"{path}.uncertainReason", "uncertain=true requires a reason.")
        issue(
            issues,
            "WARNING",
            "UNCERTAIN_FIELD_CONFIG",
            path,
            "Uncertain field config requires Human Review before Final use.",
            blocking=True,
        )
    elif uncertain is False and reason is not None:
        issue(issues, "ERROR", "UNEXPECTED_UNCERTAIN_REASON", f"{path}.uncertainReason", "uncertain=false requires a null reason.")


def _validate_target_uniqueness(
    configs: list[dict[str, Any]],
    direction: Any,
    issues: list[ValidationIssue],
) -> None:
    if direction == "ASSEMBLY":
        references = [
            target.get("standardFieldRef")
            for config in configs
            for target in [config.get("standardTarget")]
            if isinstance(target, dict)
        ]
        code = "DUPLICATE_ASSEMBLY_TARGET"
        path = "fieldConfigs"
    elif direction == "PARSE":
        references = [
            target.get("parseFieldRef")
            for config in configs
            for target in [config.get("parseTarget")]
            if isinstance(target, dict)
        ]
        code = "DUPLICATE_PARSE_TARGET"
        path = "fieldConfigs"
    else:
        return
    if any(reference and count > 1 for reference, count in Counter(references).items()):
        issue(issues, "ERROR", code, path, "Template target references must be unique within one direction.")


def _validate_coverage_and_omissions(
    template: dict[str, Any],
    configs: list[dict[str, Any]],
    omissions: list[Any],
    context: dict[str, Any],
    counters: Counter[str],
    issues: list[ValidationIssue],
) -> None:
    direction = template.get("direction")
    standard_fields: dict[str, dict[str, Any]] = context["standard_fields"]
    configured = {
        target.get("standardFieldRef")
        for config in configs
        for target in [config.get("standardTarget")]
        if isinstance(target, dict) and isinstance(target.get("standardFieldRef"), str)
    }
    omission_by_ref: dict[str, dict[str, Any]] = {}
    if direction == "PARSE" and omissions:
        issue(issues, "ERROR", "PARSE_OMISSION_FORBIDDEN", "omissions", "PARSE uses configured-targets-only and must not invent omissions.")

    for index, value in enumerate(omissions):
        path = f"omissions[{index}]"
        if not isinstance(value, dict):
            issue(issues, "ERROR", "INVALID_OMISSION", path, "Omission must be an object.")
            continue
        counters["omissionCount"] += 1
        _object_contract(
            value,
            OMISSION_PROPERTIES,
            OMISSION_PROPERTIES,
            issues,
            path=path,
            missing_code="MISSING_OMISSION_PROPERTY",
            unknown_code="UNKNOWN_OMISSION_PROPERTY",
        )
        reference = _required_string(
            value.get("standardFieldRef"), issues, "INVALID_OMISSION_REFERENCE", f"{path}.standardFieldRef"
        )
        _required_string(value.get("reason"), issues, "INVALID_OMISSION_REASON", f"{path}.reason")
        if reference:
            if reference in omission_by_ref:
                issue(issues, "ERROR", "DUPLICATE_OMISSION", f"{path}.standardFieldRef", "Each Standard field may have at most one omission.")
            omission_by_ref[reference] = value
            field = standard_fields.get(reference)
            if field is None:
                issue(issues, "ERROR", "UNKNOWN_OMISSION_REFERENCE", f"{path}.standardFieldRef", "Omission must reference a bound Standard field.")
            elif field.get("dataType") not in SCALAR_TYPES:
                issue(issues, "ERROR", "CONTAINER_OMISSION_FORBIDDEN", f"{path}.standardFieldRef", "Node/Object do not participate in omission coverage.")
            if reference in configured:
                issue(issues, "ERROR", "OMISSION_FOR_CONFIGURED_FIELD", f"{path}.standardFieldRef", "A configured field cannot also be omitted.")
        disposition = _enum(
            value.get("reviewDisposition"),
            OMISSION_DISPOSITIONS,
            issues,
            "INVALID_OMISSION_DISPOSITION",
            f"{path}.reviewDisposition",
        )
        reviewer = _nullable_string(
            value.get("reviewer"), issues, "INVALID_OMISSION_REVIEWER", f"{path}.reviewer"
        )
        reviewed_at = _nullable_string(
            value.get("reviewedAt"), issues, "INVALID_OMISSION_REVIEWED_AT", f"{path}.reviewedAt"
        )
        review_note = _nullable_string(
            value.get("reviewNote"), issues, "INVALID_OMISSION_REVIEW_NOTE", f"{path}.reviewNote"
        )
        if reviewed_at is not None and not _is_offset_datetime(reviewed_at):
            issue(
                issues,
                "ERROR",
                "INVALID_OMISSION_REVIEWED_AT",
                f"{path}.reviewedAt",
                "Omission reviewedAt must be an ISO-8601 datetime with offset.",
            )
        if disposition in {"ACCEPTED", "REJECTED"} and (
            reviewer is None or reviewed_at is None or review_note is None
        ):
            issue(
                issues,
                "ERROR",
                "INCOMPLETE_OMISSION_REVIEW",
                path,
                "Reviewed omission requires reviewer, reviewedAt and reviewNote.",
            )
        if disposition == "PENDING" and (
            reviewer is not None or reviewed_at is not None or review_note is not None
        ):
            issue(
                issues,
                "ERROR",
                "INCONSISTENT_OMISSION_REVIEW",
                path,
                "Pending omission must not carry completed Review metadata.",
            )
        if disposition == "ACCEPTED":
            counters["approvedOmissionCount"] += 1
        else:
            issue(
                issues,
                "WARNING",
                "OMISSION_REVIEW_NOT_APPROVED",
                f"{path}.reviewDisposition",
                "Omission requires an approved Human Review before Final use.",
                blocking=True,
            )

    if direction != "ASSEMBLY":
        return
    scalar_refs = {
        reference for reference, field in standard_fields.items() if field.get("dataType") in SCALAR_TYPES
    }
    for reference in sorted(scalar_refs - configured):
        omission = omission_by_ref.get(reference)
        approved = (
            isinstance(omission, dict)
            and omission.get("reviewDisposition") == "ACCEPTED"
        )
        issue(
            issues,
            "WARNING",
            "MISSING_TEMPLATE_FIELD",
            f"omissions.{reference}",
            "ASSEMBLY scalar Standard field is intentionally not represented by a Template row.",
            blocking=not approved,
        )
        if omission is None:
            issue(
                issues,
                "ERROR",
                "MISSING_OMISSION_RECORD",
                f"omissions.{reference}",
                "Every missing ASSEMBLY scalar field requires an explicit omission record.",
            )

    # XML Key configuration is an ASSEMBLY structure requirement, not omission coverage.
    for reference, field in standard_fields.items():
        if field.get("xmlKeys") and reference not in configured:
            issue(
                issues,
                "ERROR",
                "MISSING_XML_KEY_CONTAINER_CONFIG",
                f"fieldConfigs.{reference}",
                "ASSEMBLY Standard container with XML Keys requires a STRUCTURE_ONLY config.",
            )


def _validate_collection_context(
    configs: list[dict[str, Any]],
    rule_package: object,
    standard_fields: dict[str, dict[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(rule_package, RulePackage):
        return
    parse_catalog = rule_package.fields_by_direction.get("PARSE", {})
    list_entries = {
        code: entry for code, entry in parse_catalog.items() if entry.get("dataType") == "LIST"
    }
    collection_configs: dict[str, dict[str, Any]] = {}
    for config in configs:
        target = config.get("parseTarget")
        if config.get("bindingKind") == "COLLECTION_ITEM" and isinstance(target, dict):
            reference = target.get("parseFieldRef")
            if isinstance(reference, str):
                collection_configs[reference] = config

    for index, config in enumerate(configs):
        if config.get("bindingKind") != "VALUE":
            continue
        target = config.get("parseTarget")
        if not isinstance(target, dict):
            continue
        target_path = target.get("fullPath")
        if not isinstance(target_path, str):
            continue
        ancestors = [
            (code, entry)
            for code, entry in list_entries.items()
            if isinstance(entry.get("fullPath"), str) and target_path.startswith(f"{entry['fullPath']}.")
        ]
        if not ancestors:
            continue
        collection_ref, collection_entry = max(ancestors, key=lambda item: len(item[1]["fullPath"]))
        collection = collection_configs.get(collection_ref)
        collection_source = next(
            (
                item
                for item in configs
                if item.get("bindingKind") == "COLLECTION_ITEM"
                and item.get("parseTarget", {}).get("parseFieldRef") == collection_ref
            ),
            None,
        )
        collection_standard_source = (
            collection_source.get("standardSource")
            if isinstance(collection_source, dict)
            else None
        )
        collection_standard = (
            standard_fields.get(collection_standard_source.get("standardFieldRef"))
            if isinstance(collection_standard_source, dict)
            else None
        )
        collection_source_path = collection_standard.get("fullPath") if collection_standard else None
        if collection is None or not isinstance(collection_source_path, str):
            issue(
                issues,
                "ERROR",
                "MISSING_COLLECTION_CONTEXT",
                f"fieldConfigs[{index}].parseTarget",
                "Parse target below a LIST requires a matching COLLECTION_ITEM Standard ancestor.",
            )
            continue

        # PARSE 的 Standard source 属于表达式，而不是 field config 顶层；空表达式可以没有 source。
        for reference in sorted(_standard_references_in_expression(config.get("valueExpression"))):
            source = standard_fields.get(reference)
            source_path = source.get("fullPath") if source else None
            if not (
                isinstance(source_path, str)
                and source_path.startswith(f"{collection_source_path}.")
            ):
                issue(
                    issues,
                    "ERROR",
                    "STANDARD_SOURCE_OUTSIDE_COLLECTION",
                    f"fieldConfigs[{index}].valueExpression",
                    "Every PARSE Standard source for a LIST item target must be below the matching collection source.",
                )


def _standard_references_in_expression(value: Any) -> set[str]:
    if not isinstance(value, dict):
        return set()
    references: set[str] = set()
    if value.get("mode") in {"FIELD", "MAPPING"}:
        reference = value.get("standardFieldRef")
        if isinstance(reference, str):
            references.add(reference)
    if value.get("mode") == "FUNCTION":
        arguments = value.get("arguments")
        if isinstance(arguments, list):
            for argument in arguments:
                if isinstance(argument, dict) and argument.get("kind") == "FIELD_REF":
                    reference = argument.get("standardFieldRef")
                    if isinstance(reference, str):
                        references.add(reference)
    if value.get("mode") == "CONCATENATE":
        children = value.get("children")
        if isinstance(children, list):
            for child in children:
                references.update(_standard_references_in_expression(child))
    return references


def _validate_review(
    value: dict[str, Any],
    statuses: set[str],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    _object_contract(
        value,
        REVIEW_PROPERTIES,
        REVIEW_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_REVIEW_PROPERTY",
        unknown_code="UNKNOWN_REVIEW_PROPERTY",
    )
    status = _enum(value.get("status"), statuses, issues, "INVALID_REVIEW_STATUS", f"{path}.status")
    reviewer = _nullable_string(value.get("reviewer"), issues, "INVALID_REVIEWER", f"{path}.reviewer")
    reviewed_at = _nullable_string(value.get("reviewedAt"), issues, "INVALID_REVIEWED_AT", f"{path}.reviewedAt")
    note = _nullable_string(value.get("note"), issues, "INVALID_REVIEW_NOTE", f"{path}.note")
    if reviewed_at is not None and not _is_offset_datetime(reviewed_at):
        issue(issues, "ERROR", "INVALID_REVIEWED_AT", f"{path}.reviewedAt", "reviewedAt must be an ISO-8601 datetime with offset.")
    if status == "APPROVED" and (reviewer is None or reviewed_at is None or note is None):
        issue(issues, "ERROR", "INCOMPLETE_APPROVED_REVIEW", path, "Approved Review requires reviewer, reviewedAt and note.")
    if status in {"PENDING", "REJECTED"} and (reviewer is not None or reviewed_at is not None):
        issue(issues, "ERROR", "INCONSISTENT_REVIEW_METADATA", path, "Only approved Review may carry reviewer and reviewedAt.")


def _object_contract(
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
    issues: list[ValidationIssue],
    *,
    path: str | None,
    missing_code: str,
    unknown_code: str,
) -> None:
    for name in sorted(required - value.keys()):
        issue(issues, "ERROR", missing_code, _path(path, name), "Required property is missing.")
    for name in sorted(value.keys() - allowed):
        issue(issues, "ERROR", unknown_code, _path(path, name), "Unknown property is not allowed by the contract.")


def _required_string(
    value: Any,
    issues: list[ValidationIssue],
    code: str,
    path: str,
) -> str | None:
    if not isinstance(value, str) or not value:
        issue(issues, "ERROR", code, path, "Property must be a non-empty string.")
        return None
    return value


def _nullable_string(
    value: Any,
    issues: list[ValidationIssue],
    code: str,
    path: str,
) -> str | None:
    if value is None:
        return None
    return _required_string(value, issues, code, path)


def _boolean(
    value: Any,
    issues: list[ValidationIssue],
    code: str,
    path: str,
) -> bool | None:
    if not isinstance(value, bool):
        issue(issues, "ERROR", code, path, "Property must be boolean.")
        return None
    return value


def _enum(
    value: Any,
    allowed: set[str],
    issues: list[ValidationIssue],
    code: str,
    path: str,
) -> str | None:
    parsed = _required_string(value, issues, code, path)
    if parsed is not None and parsed not in allowed:
        issue(issues, "ERROR", code, path, "Property is outside the supported value set.")
        return None
    return parsed


def _stable_id(value: Any, issues: list[ValidationIssue], code: str, path: str) -> None:
    parsed = _required_string(value, issues, code, path)
    if parsed is not None and not STABLE_ID_PATTERN.fullmatch(parsed):
        issue(issues, "ERROR", code, path, "Stable IDs must use lowercase kebab-case.")


def _version(value: Any, issues: list[ValidationIssue], code: str, path: str) -> None:
    parsed = _required_string(value, issues, code, path)
    if parsed is not None and not VERSION_PATTERN.fullmatch(parsed):
        issue(issues, "ERROR", code, path, "Artifact versions must use v followed by a positive integer.")


def _is_positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _is_offset_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _path(parent: str | None, child: str) -> str:
    return f"{parent}.{child}" if parent else child


def _result(
    template: object,
    configs: list[Any],
    omissions: list[Any],
    counters: Counter[str],
    issues: list[ValidationIssue],
) -> dict[str, Any]:
    config_objects = [config for config in configs if isinstance(config, dict)]
    return build_validation_result(
        template,
        result_contract_version=RESULT_CONTRACT_VERSION,
        artifact_kind="InterfaceTemplateIR",
        artifact_id_field="templateId",
        artifact_version_field="templateVersion",
        issues=issues,
        summary={
            "templateId": template.get("templateId") if isinstance(template, Mapping) else None,
            "interfaceCode": template.get("interfaceCode") if isinstance(template, Mapping) else None,
            "direction": template.get("direction") if isinstance(template, Mapping) else None,
            "rulePackageVersion": template.get("rulePackageVersion") if isinstance(template, Mapping) else None,
            "fieldConfigCount": len(config_objects),
        },
        coverage={
            "valueBindingCount": counters["binding:VALUE"],
            "structureBindingCount": counters["binding:STRUCTURE_ONLY"],
            "collectionBindingCount": counters["binding:COLLECTION_ITEM"],
            "fieldValueExpressionCount": counters["fieldValueExpressionCount"],
            "xmlKeyExpressionCount": counters["xmlKeyExpressionCount"],
            "omissionCount": counters["omissionCount"],
            "approvedOmissionCount": counters["approvedOmissionCount"],
            "uncertainFieldConfigCount": counters["uncertainFieldConfigCount"],
            "functionInvocationCount": counters["functionInvocationCount"],
            "mappingExpressionCount": counters["mappingExpressionCount"],
            "replacementCount": counters["replacementCount"],
        },
    )


def _log_result(result: dict[str, Any]) -> None:
    summary = result["summary"]
    outcome = "succeeded" if result["status"] != "failed" else "failed"
    log = LOGGER.info if outcome == "succeeded" else LOGGER.warning
    log(
        "InterfaceTemplateIR validation completed",
        extra={
            "component": "interface_template_validator",
            "artifact_id": summary.get("templateId"),
            "direction": summary.get("direction"),
            "outcome": outcome,
            "field_config_count": summary.get("fieldConfigCount"),
            "error_count": summary.get("errorCount"),
            "warning_count": summary.get("warningCount"),
            "blocking_count": summary.get("blockingCount"),
        },
    )
