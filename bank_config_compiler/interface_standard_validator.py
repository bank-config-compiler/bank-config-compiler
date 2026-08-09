from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Mapping

from .artifact_validation import ValidationIssue, build_validation_result, content_hash, issue
from .configuration_rules import RulePackage
from .schemair_validator import validate_schemair


LOGGER = logging.getLogger(__name__)

STANDARD_CONTRACT_VERSION = "interface-standard/v1"
RESULT_CONTRACT_VERSION = "interface-standard-validation-result/v1"
DIRECTIONS = {"ASSEMBLY", "PARSE"}
ARTIFACT_STATUSES = {"DRAFT", "FINAL"}
REVIEW_STATUSES = {"PENDING", "APPROVED"}
STANDARD_DATA_TYPES = {"String", "Boolean", "Date", "Number", "Node", "Object"}
CONSTRAINT_STATES = {"VALUE", "NO_CONSTRAINT", "UNKNOWN"}
EVIDENCE_KINDS = {"FINAL_SCHEMA_IR", "HUMAN_CONFIRMATION", "TARGET_SYSTEM_FORMAL_EXPORT"}
SCHEMA_EVIDENCE_KINDS = {"DIRECT", "DERIVED", "ASSUMED"}
CONDITION_OPERATORS = {"EQUALS", "IS_EMPTY"}
CONDITION_EFFECTS = {"REQUIRED"}
# 只有能从 Final SchemaIR 确定性计算源值的属性才允许记录 difference；
# 否则 Human Review 会在无法机器核对的任意 schemaIrValue 上形成虚假闭环。
DIFFERENCE_PROPERTIES = {"required", "lengthLimit", "dataType"}
COMMON_FIELD_RULE_REFERENCES = {
    "STD.FIELD.PARENT_PATH",
    "STD.FIELD.FULL_PATH",
    "STD.FIELD.SEQUENCE",
    "STD.FIELD.DATA_TYPE",
    "STD.CONSTRAINT.VALUE_STATE",
}

TOP_LEVEL_PROPERTIES = {
    "contractVersion",
    "standardId",
    "standardVersion",
    "status",
    "review",
    "interfaceCode",
    "direction",
    "schemaIrRef",
    "rulePackageVersion",
    "xmlEncodingRef",
    "fields",
}
SCHEMAIR_REF_PROPERTIES = {"schemaId", "schemaVersion", "contractVersion", "contentHash"}
XML_ENCODING_REF_PROPERTIES = {"functionType", "value"}
REVIEW_PROPERTIES = {"status", "reviewer", "reviewedAt", "note"}
FIELD_PROPERTIES = {
    "fieldId",
    "sequence",
    "fieldName",
    "fieldDescription",
    "conditionText",
    "parentPath",
    "fullPath",
    "required",
    "lengthLimit",
    "illegalCharacters",
    "regex",
    "dataType",
    "xmlKeys",
    "schemaIrFieldPath",
    "conditionalConstraints",
    "ruleReferences",
    "differences",
    "evidence",
    "confidence",
    "uncertain",
    "uncertainReason",
    "reviewNote",
}
LENGTH_PROPERTIES = {"state", "min", "max", "precision", "scale"}
TEXT_CONSTRAINT_PROPERTIES = {"state", "value"}
XML_KEY_PROPERTIES = {"name", "schemaIrFieldPath"}
EVIDENCE_PROPERTIES = {"kind", "sourceRef", "note"}
SCHEMA_EVIDENCE_PROPERTIES = {"kind", "note"}
DIFFERENCE_PROPERTIES_SET = {
    "property",
    "schemaIrValue",
    "standardValue",
    "reason",
    "ruleReferences",
    "review",
}
CONDITION_PROPERTIES = {
    "conditionId",
    "schemaIrConditionIndex",
    "controllingFieldRef",
    "operator",
    "literal",
    "targetFieldRef",
    "effect",
    "sourceText",
    "evidence",
    "review",
    "ruleReferences",
}
STABLE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^v[1-9]\d*$")
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
DECIMAL_FORMAT_PATTERN = re.compile(r"^decimal\(([1-9]\d*),([0-9]\d*)\)$")


def validate_interface_standard(
    standard: object,
    *,
    schemair: object,
    rule_package: RulePackage,
) -> dict[str, Any]:
    standard_id = standard.get("standardId") if isinstance(standard, Mapping) else None
    direction = standard.get("direction") if isinstance(standard, Mapping) else None
    LOGGER.debug(
        "Validating InterfaceStandardIR",
        extra={
            "component": "interface_standard_validator",
            "artifact_id": standard_id,
            "direction": direction,
            "outcome": "started",
        },
    )

    issues: list[ValidationIssue] = []
    if not isinstance(standard, dict):
        issue(issues, "ERROR", "INVALID_STANDARD_ROOT", None, "InterfaceStandardIR root must be an object.")
        result = _result(standard, [], issues)
        _log_result(result)
        return result

    _validate_top_level(standard, issues)
    _validate_lifecycle(standard, issues)
    context = _validate_dependencies(standard, schemair, rule_package, issues)
    fields_value = standard.get("fields")
    fields = fields_value if isinstance(fields_value, list) else []
    _validate_fields(fields, context, rule_package, issues)

    result = _result(standard, fields, issues)
    _log_result(result)
    return result


def _validate_top_level(standard: dict[str, Any], issues: list[ValidationIssue]) -> None:
    _object_contract(
        standard,
        TOP_LEVEL_PROPERTIES,
        TOP_LEVEL_PROPERTIES,
        issues,
        path=None,
        missing_code="MISSING_TOP_LEVEL_PROPERTY",
        unknown_code="UNKNOWN_TOP_LEVEL_PROPERTY",
    )
    _enum(
        standard.get("contractVersion"),
        {STANDARD_CONTRACT_VERSION},
        issues,
        "INVALID_CONTRACT_VERSION",
        "contractVersion",
    )
    _stable_id(standard.get("standardId"), issues, "INVALID_STANDARD_ID", "standardId")
    _version(standard.get("standardVersion"), issues, "INVALID_STANDARD_VERSION", "standardVersion")
    _enum(standard.get("status"), ARTIFACT_STATUSES, issues, "INVALID_ARTIFACT_STATUS", "status")
    _required_string(standard.get("interfaceCode"), issues, "INVALID_INTERFACE_CODE", "interfaceCode")
    _enum(standard.get("direction"), DIRECTIONS, issues, "INVALID_DIRECTION", "direction")
    _required_string(
        standard.get("rulePackageVersion"),
        issues,
        "INVALID_RULE_PACKAGE_VERSION",
        "rulePackageVersion",
    )
    if "fields" in standard:
        if not isinstance(standard["fields"], list):
            issue(issues, "ERROR", "INVALID_FIELDS", "fields", "fields must be an array.")
        elif not standard["fields"]:
            issue(issues, "ERROR", "EMPTY_FIELDS", "fields", "fields must contain at least one field.")
    review = standard.get("review")
    if isinstance(review, dict):
        _validate_review(review, issues, path="review")
    elif "review" in standard:
        issue(issues, "ERROR", "INVALID_REVIEW", "review", "review must be an object.")


def _validate_lifecycle(standard: dict[str, Any], issues: list[ValidationIssue]) -> None:
    status = standard.get("status")
    review = standard.get("review")
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
            "Human Review must be approved before Final use.",
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
    standard: dict[str, Any],
    schemair: object,
    rule_package: RulePackage,
    issues: list[ValidationIssue],
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "schema_fields": {},
        "schema_attributes": {},
        "schema_conditions": [],
        "message": None,
    }
    schema_result = validate_schemair(schemair)
    if not schema_result.get("finalEligible"):
        issue(
            issues,
            "ERROR",
            "SCHEMAIR_NOT_FINAL_ELIGIBLE",
            "schemaIrRef",
            "InterfaceStandardIR requires a valid Final SchemaIR dependency.",
        )
    if not isinstance(schemair, dict):
        return context

    if standard.get("interfaceCode") != schemair.get("interfaceCode"):
        issue(
            issues,
            "ERROR",
            "INTERFACE_CODE_MISMATCH",
            "interfaceCode",
            "InterfaceStandardIR interfaceCode must match SchemaIR.",
        )

    reference = standard.get("schemaIrRef")
    if isinstance(reference, dict):
        _object_contract(
            reference,
            SCHEMAIR_REF_PROPERTIES,
            SCHEMAIR_REF_PROPERTIES,
            issues,
            path="schemaIrRef",
            missing_code="MISSING_SCHEMAIR_REFERENCE_PROPERTY",
            unknown_code="UNKNOWN_SCHEMAIR_REFERENCE_PROPERTY",
        )
        _stable_id(reference.get("schemaId"), issues, "INVALID_SCHEMAIR_REFERENCE", "schemaIrRef.schemaId")
        _version(
            reference.get("schemaVersion"),
            issues,
            "INVALID_SCHEMAIR_REFERENCE",
            "schemaIrRef.schemaVersion",
        )
        _required_string(
            reference.get("contractVersion"),
            issues,
            "INVALID_SCHEMAIR_REFERENCE",
            "schemaIrRef.contractVersion",
        )
        hash_value = reference.get("contentHash")
        if not isinstance(hash_value, str) or not SHA256_PATTERN.fullmatch(hash_value):
            issue(
                issues,
                "ERROR",
                "INVALID_SCHEMAIR_CONTENT_HASH",
                "schemaIrRef.contentHash",
                "SchemaIR contentHash must be a canonical SHA-256 value.",
            )
        if any(
            reference.get(key) != schemair.get(schema_key)
            for key, schema_key in (
                ("schemaId", "schemaId"),
                ("schemaVersion", "schemaVersion"),
                ("contractVersion", "contractVersion"),
            )
        ):
            issue(
                issues,
                "ERROR",
                "SCHEMAIR_REFERENCE_MISMATCH",
                "schemaIrRef",
                "SchemaIR identity, version and contract reference must match the dependency.",
            )
        if hash_value != content_hash(schemair):
            issue(
                issues,
                "ERROR",
                "SCHEMAIR_HASH_MISMATCH",
                "schemaIrRef.contentHash",
                "SchemaIR contentHash must match the complete dependency content.",
            )
    elif "schemaIrRef" in standard:
        issue(issues, "ERROR", "INVALID_SCHEMAIR_REFERENCE", "schemaIrRef", "schemaIrRef must be an object.")

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
        if standard.get("rulePackageVersion") != rule_package.version:
            issue(
                issues,
                "ERROR",
                "RULE_PACKAGE_VERSION_MISMATCH",
                "rulePackageVersion",
                "InterfaceStandardIR rulePackageVersion must match the loaded package.",
            )

    direction = standard.get("direction")
    messages = schemair.get("messages")
    message_values = messages if isinstance(messages, list) else []
    message = next(
        (
            item
            for item in message_values
            if isinstance(item, dict) and item.get("functionType") == direction
        ),
        None,
    )
    if message is None:
        issue(
            issues,
            "ERROR",
            "DIRECTION_NOT_IN_SCHEMAIR",
            "direction",
            "InterfaceStandardIR direction must exist in SchemaIR messages.",
        )
        return context
    context["message"] = message

    encoding_ref = standard.get("xmlEncodingRef")
    if isinstance(encoding_ref, dict):
        _object_contract(
            encoding_ref,
            XML_ENCODING_REF_PROPERTIES,
            XML_ENCODING_REF_PROPERTIES,
            issues,
            path="xmlEncodingRef",
            missing_code="MISSING_XML_ENCODING_REFERENCE_PROPERTY",
            unknown_code="UNKNOWN_XML_ENCODING_REFERENCE_PROPERTY",
        )
        _enum(
            encoding_ref.get("functionType"),
            DIRECTIONS,
            issues,
            "INVALID_XML_ENCODING_DIRECTION",
            "xmlEncodingRef.functionType",
        )
        _required_string(
            encoding_ref.get("value"),
            issues,
            "INVALID_XML_ENCODING_VALUE",
            "xmlEncodingRef.value",
        )
        if (
            encoding_ref.get("functionType") != direction
            or encoding_ref.get("value") != message.get("xmlEncoding")
        ):
            issue(
                issues,
                "ERROR",
                "XML_ENCODING_REFERENCE_MISMATCH",
                "xmlEncodingRef",
                "xmlEncodingRef must match the selected SchemaIR direction.",
            )
    elif "xmlEncodingRef" in standard:
        issue(
            issues,
            "ERROR",
            "INVALID_XML_ENCODING_REFERENCE",
            "xmlEncodingRef",
            "xmlEncodingRef must be an object.",
        )

    envelope = schemair.get("envelope")
    envelope_fields = envelope.get("fields") if isinstance(envelope, dict) else []
    message_fields = message.get("fields")
    all_fields = [
        field
        for value in (envelope_fields, message_fields)
        if isinstance(value, list)
        for field in value
        if isinstance(field, dict)
    ]
    context["schema_fields"] = {
        field["path"]: field
        for field in all_fields
        if field.get("nodeKind") != "XML_ATTRIBUTE" and isinstance(field.get("path"), str)
    }
    context["schema_attributes"] = {
        field["path"]: field
        for field in all_fields
        if field.get("nodeKind") == "XML_ATTRIBUTE" and isinstance(field.get("path"), str)
    }
    conditions = message.get("conditionalConstraints")
    context["schema_conditions"] = conditions if isinstance(conditions, list) else []
    return context


def _validate_fields(
    fields: list[Any],
    context: dict[str, Any],
    rule_package: RulePackage,
    issues: list[ValidationIssue],
) -> None:
    field_objects = [field for field in fields if isinstance(field, dict)]
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            issue(issues, "ERROR", "INVALID_STANDARD_FIELD", f"fields[{index}]", "Standard field must be an object.")

    field_ids = _unique_index(field_objects, "fieldId", "DUPLICATE_FIELD_ID", issues)
    full_paths = _unique_index(field_objects, "fullPath", "DUPLICATE_STANDARD_FULL_PATH", issues)
    source_paths = _unique_index(
        field_objects,
        "schemaIrFieldPath",
        "DUPLICATE_SCHEMAIR_FIELD_REFERENCE",
        issues,
    )
    schema_fields: dict[str, dict[str, Any]] = context["schema_fields"]
    schema_attributes: dict[str, dict[str, Any]] = context["schema_attributes"]
    mapped_xml_keys: set[str] = set()
    mapped_condition_indexes: set[int] = set()

    for index, field in enumerate(field_objects):
        fallback = f"fields[{index}]"
        field_id = field.get("fieldId")
        path = field_id if isinstance(field_id, str) and field_id else fallback
        _validate_field_contract(field, rule_package, issues, path=path)

        full_path = field.get("fullPath")
        parent_path = field.get("parentPath")
        field_name = field.get("fieldName")
        if isinstance(full_path, str) and isinstance(parent_path, str) and isinstance(field_name, str):
            if full_path != f"{parent_path}.{field_name}":
                issue(
                    issues,
                    "ERROR",
                    "FULL_PATH_PARENT_MISMATCH",
                    f"{path}.fullPath",
                    "fullPath must be parentPath plus fieldName.",
                )
            if parent_path != "Root" and parent_path not in full_paths:
                issue(
                    issues,
                    "ERROR",
                    "UNKNOWN_STANDARD_PARENT_PATH",
                    f"{path}.parentPath",
                    "parentPath must reference another Standard field or Root.",
                )

        source_path = field.get("schemaIrFieldPath")
        source_field = schema_fields.get(source_path) if isinstance(source_path, str) else None
        if source_field is None:
            issue(
                issues,
                "ERROR",
                "UNKNOWN_SCHEMAIR_FIELD_REFERENCE",
                f"{path}.schemaIrFieldPath",
                "schemaIrFieldPath must reference an XML element in the selected direction.",
            )
        else:
            if full_path != source_path:
                issue(
                    issues,
                    "ERROR",
                    "SCHEMAIR_PATH_PROJECTION_MISMATCH",
                    f"{path}.fullPath",
                    "Standard fullPath must preserve the SchemaIR element path.",
                )
            _validate_source_projection(field, source_field, issues, path=path)

        mapped_xml_keys.update(
            _validate_xml_keys(
                field,
                schema_attributes,
                rule_package,
                issues,
                path=path,
            )
        )
        mapped_condition_indexes.update(
            _validate_conditions(
                field,
                field_ids,
                source_paths,
                context["schema_conditions"],
                rule_package,
                issues,
                path=path,
            )
        )

    _validate_sequences(field_objects, issues)
    for missing_path in sorted(set(schema_fields) - set(source_paths)):
        issue(
            issues,
            "ERROR",
            "MISSING_SCHEMAIR_FIELD",
            missing_path,
            "Every SchemaIR XML element in the selected direction must have one Standard field.",
        )
    for missing_path in sorted(set(schema_attributes) - mapped_xml_keys):
        issue(
            issues,
            "ERROR",
            "MISSING_SCHEMAIR_XML_KEY",
            missing_path,
            "Every SchemaIR XML attribute in the selected direction must be projected as an XML Key.",
        )
    for index in sorted(set(range(len(context["schema_conditions"]))) - mapped_condition_indexes):
        issue(
            issues,
            "ERROR",
            "MISSING_SCHEMAIR_CONDITION",
            f"schemaIr.conditions[{index}]",
            "Every structured SchemaIR condition must be projected into the Standard.",
        )


def _validate_field_contract(
    field: dict[str, Any],
    rule_package: RulePackage,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    _object_contract(
        field,
        FIELD_PROPERTIES,
        FIELD_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_FIELD_PROPERTY",
        unknown_code="UNKNOWN_FIELD_PROPERTY",
    )
    _stable_id(field.get("fieldId"), issues, "INVALID_FIELD_ID", f"{path}.fieldId")
    sequence = field.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        issue(
            issues,
            "ERROR",
            "INVALID_FIELD_SEQUENCE",
            f"{path}.sequence",
            "sequence must be a positive integer.",
        )
    for name, code in (
        ("fieldName", "INVALID_FIELD_NAME"),
        ("fieldDescription", "INVALID_FIELD_DESCRIPTION"),
        ("parentPath", "INVALID_PARENT_PATH"),
        ("fullPath", "INVALID_FULL_PATH"),
        ("schemaIrFieldPath", "INVALID_SCHEMAIR_FIELD_REFERENCE"),
    ):
        _required_string(field.get(name), issues, code, f"{path}.{name}")
    _nullable_string(
        field.get("conditionText"),
        issues,
        "INVALID_CONDITION_TEXT",
        f"{path}.conditionText",
    )
    _boolean(field.get("required"), issues, "INVALID_REQUIRED", f"{path}.required")
    _enum(
        field.get("dataType"),
        STANDARD_DATA_TYPES,
        issues,
        "INVALID_STANDARD_DATA_TYPE",
        f"{path}.dataType",
    )
    _validate_length(field.get("lengthLimit"), issues, path=f"{path}.lengthLimit")
    _validate_text_constraint(
        field.get("illegalCharacters"),
        issues,
        path=f"{path}.illegalCharacters",
    )
    _validate_text_constraint(field.get("regex"), issues, path=f"{path}.regex")
    _validate_rule_references(
        field.get("ruleReferences"),
        rule_package,
        issues,
        path=f"{path}.ruleReferences",
    )
    for required_rule in sorted(COMMON_FIELD_RULE_REFERENCES):
        _require_rule_reference(
            field.get("ruleReferences"),
            required_rule,
            rule_package,
            issues,
            path=f"{path}.ruleReferences",
        )
    _validate_evidence(field.get("evidence"), issues, path=f"{path}.evidence")
    _validate_differences(field, rule_package, issues, path=path)

    confidence = field.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        issue(
            issues,
            "ERROR",
            "INVALID_CONFIDENCE",
            f"{path}.confidence",
            "confidence must be a number between 0 and 1.",
        )
    uncertain = _boolean(field.get("uncertain"), issues, "INVALID_UNCERTAIN", f"{path}.uncertain")
    uncertain_reason = field.get("uncertainReason")
    review_note = field.get("reviewNote")
    _nullable_string(uncertain_reason, issues, "INVALID_UNCERTAIN_REASON", f"{path}.uncertainReason")
    _nullable_string(review_note, issues, "INVALID_REVIEW_NOTE", f"{path}.reviewNote")
    if uncertain is True:
        if not isinstance(uncertain_reason, str) or not uncertain_reason:
            issue(
                issues,
                "ERROR",
                "MISSING_UNCERTAIN_REASON",
                f"{path}.uncertainReason",
                "uncertain fields require an uncertainReason.",
            )
        issue(
            issues,
            "WARNING",
            "UNCERTAIN_STANDARD_FIELD",
            path,
            "Uncertain Standard fields cannot enter a Final artifact.",
            blocking=True,
        )
    elif uncertain is False and uncertain_reason is not None:
        issue(
            issues,
            "ERROR",
            "UNEXPECTED_UNCERTAIN_REASON",
            f"{path}.uncertainReason",
            "Certain fields must not carry an uncertainReason.",
        )

    for array_name in ("xmlKeys", "conditionalConstraints", "differences"):
        if array_name in field and not isinstance(field[array_name], list):
            issue(
                issues,
                "ERROR",
                "INVALID_FIELD_ARRAY",
                f"{path}.{array_name}",
                f"{array_name} must be an array.",
            )


def _validate_source_projection(
    field: dict[str, Any],
    source: dict[str, Any],
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    evidence = field.get("evidence")
    evidence_values = evidence if isinstance(evidence, list) else []
    if not any(
        isinstance(item, dict)
        and item.get("kind") == "FINAL_SCHEMA_IR"
        and item.get("sourceRef") == source.get("path")
        for item in evidence_values
    ):
        issue(
            issues,
            "ERROR",
            "SCHEMAIR_EVIDENCE_MISMATCH",
            f"{path}.evidence",
            "Field evidence must include its exact Final SchemaIR source path.",
        )
    if field.get("conditionText") != source.get("conditionText"):
        issue(
            issues,
            "ERROR",
            "CONDITION_TEXT_MISMATCH",
            f"{path}.conditionText",
            "Standard conditionText must preserve the Final SchemaIR text exactly.",
        )
    expected = {
        "required": source.get("required"),
        "lengthLimit": _schema_length_constraint(source),
        "dataType": _schema_data_type(source),
    }
    differences = field.get("differences")
    difference_by_property = {
        item.get("property"): item
        for item in differences
        if isinstance(differences, list) and isinstance(item, dict) and isinstance(item.get("property"), str)
    }
    for property_name, expected_value in expected.items():
        actual_value = field.get(property_name)
        difference = difference_by_property.get(property_name)
        if actual_value == expected_value:
            if difference is not None:
                issue(
                    issues,
                    "ERROR",
                    "UNNECESSARY_STANDARD_DIFFERENCE",
                    f"{path}.differences",
                    "A difference record must describe an actual SchemaIR-to-Standard difference.",
                )
            continue
        if difference is None:
            issue(
                issues,
                "ERROR",
                "UNRECORDED_STANDARD_DIFFERENCE",
                f"{path}.{property_name}",
                "SchemaIR-to-Standard differences must be explicitly recorded.",
            )
            continue
        if difference.get("schemaIrValue") != expected_value or difference.get("standardValue") != actual_value:
            issue(
                issues,
                "ERROR",
                "DIFFERENCE_VALUE_MISMATCH",
                f"{path}.differences",
                "Difference values must match the SchemaIR source and Standard projection.",
            )


def _validate_xml_keys(
    field: dict[str, Any],
    schema_attributes: dict[str, dict[str, Any]],
    rule_package: RulePackage,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> set[str]:
    value = field.get("xmlKeys")
    if not isinstance(value, list):
        return set()
    seen_names: set[str] = set()
    seen_refs: set[str] = set()
    mapped: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{path}.xmlKeys[{index}]"
        if not isinstance(item, dict):
            issue(issues, "ERROR", "INVALID_XML_KEY", item_path, "XML Key must be an object.")
            continue
        _object_contract(
            item,
            XML_KEY_PROPERTIES,
            XML_KEY_PROPERTIES,
            issues,
            path=item_path,
            missing_code="MISSING_XML_KEY_PROPERTY",
            unknown_code="UNKNOWN_XML_KEY_PROPERTY",
        )
        name = item.get("name")
        source_ref = item.get("schemaIrFieldPath")
        _required_string(name, issues, "INVALID_XML_KEY_NAME", f"{item_path}.name")
        _required_string(
            source_ref,
            issues,
            "INVALID_XML_KEY_REFERENCE",
            f"{item_path}.schemaIrFieldPath",
        )
        if isinstance(name, str):
            if not name.startswith("@"):
                issue(
                    issues,
                    "ERROR",
                    "INVALID_XML_KEY_NAME",
                    f"{item_path}.name",
                    "XML Key names must preserve the @ prefix.",
                )
            if name in seen_names:
                issue(issues, "ERROR", "DUPLICATE_XML_KEY", f"{item_path}.name", "XML Key names must be unique per field.")
            seen_names.add(name)
        if isinstance(source_ref, str):
            if source_ref in seen_refs:
                issue(
                    issues,
                    "ERROR",
                    "DUPLICATE_XML_KEY_REFERENCE",
                    f"{item_path}.schemaIrFieldPath",
                    "SchemaIR XML attribute references must be unique.",
                )
            seen_refs.add(source_ref)
            attribute = schema_attributes.get(source_ref)
            if (
                attribute is None
                or attribute.get("parentPath") != field.get("fullPath")
                or attribute.get("fieldName") != name
            ):
                issue(
                    issues,
                    "ERROR",
                    "UNKNOWN_XML_KEY_REFERENCE",
                    f"{item_path}.schemaIrFieldPath",
                    "XML Key must reference a matching SchemaIR attribute on the same element.",
                )
            else:
                mapped.add(source_ref)
    if value:
        _require_rule_reference(
            field.get("ruleReferences"),
            "STD.FIELD.XML_KEYS",
            rule_package,
            issues,
            path=f"{path}.ruleReferences",
        )
    return mapped


def _validate_conditions(
    field: dict[str, Any],
    field_ids: dict[str, dict[str, Any]],
    source_paths: dict[str, dict[str, Any]],
    schema_conditions: list[Any],
    rule_package: RulePackage,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> set[int]:
    value = field.get("conditionalConstraints")
    if not isinstance(value, list):
        return set()
    seen_ids: set[str] = set()
    seen_indexes: set[int] = set()
    for index, condition in enumerate(value):
        condition_path = f"{path}.conditionalConstraints[{index}]"
        if not isinstance(condition, dict):
            issue(issues, "ERROR", "INVALID_CONDITION", condition_path, "Condition must be an object.")
            continue
        _object_contract(
            condition,
            CONDITION_PROPERTIES,
            CONDITION_PROPERTIES,
            issues,
            path=condition_path,
            missing_code="MISSING_CONDITION_PROPERTY",
            unknown_code="UNKNOWN_CONDITION_PROPERTY",
        )
        condition_id = condition.get("conditionId")
        _stable_id(condition_id, issues, "INVALID_CONDITION_ID", f"{condition_path}.conditionId")
        if isinstance(condition_id, str):
            if condition_id in seen_ids:
                issue(
                    issues,
                    "ERROR",
                    "DUPLICATE_CONDITION_ID",
                    f"{condition_path}.conditionId",
                    "conditionId must be unique within a field.",
                )
            seen_ids.add(condition_id)
        source_index = condition.get("schemaIrConditionIndex")
        if isinstance(source_index, bool) or not isinstance(source_index, int) or source_index < 0:
            issue(
                issues,
                "ERROR",
                "INVALID_SCHEMAIR_CONDITION_INDEX",
                f"{condition_path}.schemaIrConditionIndex",
                "schemaIrConditionIndex must be a non-negative integer.",
            )
            source_index = None
        elif source_index in seen_indexes:
            issue(
                issues,
                "ERROR",
                "DUPLICATE_SCHEMAIR_CONDITION_REFERENCE",
                f"{condition_path}.schemaIrConditionIndex",
                "Each SchemaIR condition may be projected only once.",
            )
        else:
            seen_indexes.add(source_index)

        controlling_ref = condition.get("controllingFieldRef")
        target_ref = condition.get("targetFieldRef")
        for name, value_ref in (("controllingFieldRef", controlling_ref), ("targetFieldRef", target_ref)):
            _required_string(
                value_ref,
                issues,
                "INVALID_CONDITION_FIELD_REFERENCE",
                f"{condition_path}.{name}",
            )
            if isinstance(value_ref, str) and value_ref not in field_ids:
                issue(
                    issues,
                    "ERROR",
                    "UNKNOWN_CONDITION_FIELD_REFERENCE",
                    f"{condition_path}.{name}",
                    "Condition field references must resolve inside the Standard.",
                )
        if target_ref != field.get("fieldId"):
            issue(
                issues,
                "ERROR",
                "CONDITION_TARGET_FIELD_MISMATCH",
                f"{condition_path}.targetFieldRef",
                "A field condition must target the field that contains it.",
            )
        operator = condition.get("operator")
        effect = condition.get("effect")
        _enum(operator, CONDITION_OPERATORS, issues, "INVALID_CONDITION_OPERATOR", f"{condition_path}.operator")
        _enum(effect, CONDITION_EFFECTS, issues, "INVALID_CONDITION_EFFECT", f"{condition_path}.effect")
        literal = condition.get("literal")
        if operator == "EQUALS" and (not isinstance(literal, str) or not literal):
            issue(
                issues,
                "ERROR",
                "INVALID_CONDITION_LITERAL",
                f"{condition_path}.literal",
                "EQUALS conditions require a non-empty string literal.",
            )
        if operator == "IS_EMPTY" and literal is not None:
            issue(
                issues,
                "ERROR",
                "INVALID_CONDITION_LITERAL",
                f"{condition_path}.literal",
                "IS_EMPTY conditions require a null literal.",
            )
        _required_string(condition.get("sourceText"), issues, "INVALID_CONDITION_SOURCE", f"{condition_path}.sourceText")
        _validate_condition_evidence(condition.get("evidence"), issues, path=f"{condition_path}.evidence")
        review = condition.get("review")
        if isinstance(review, dict):
            _validate_review(review, issues, path=f"{condition_path}.review")
            if review.get("status") != "APPROVED":
                issue(
                    issues,
                    "WARNING",
                    "CONDITION_REVIEW_NOT_APPROVED",
                    f"{condition_path}.review.status",
                    "Structured bank conditions require Human Review.",
                    blocking=True,
                )
        else:
            issue(issues, "ERROR", "INVALID_CONDITION_REVIEW", f"{condition_path}.review", "Condition review must be an object.")
        _validate_rule_references(
            condition.get("ruleReferences"),
            rule_package,
            issues,
            path=f"{condition_path}.ruleReferences",
        )
        _require_rule_reference(
            condition.get("ruleReferences"),
            "STD.CONSTRAINT.BANK_CONDITION",
            rule_package,
            issues,
            path=f"{condition_path}.ruleReferences",
        )

        source_condition = (
            schema_conditions[source_index]
            if isinstance(source_index, int) and source_index < len(schema_conditions)
            else None
        )
        controlling_field = field_ids.get(controlling_ref) if isinstance(controlling_ref, str) else None
        target_field = field_ids.get(target_ref) if isinstance(target_ref, str) else None
        if not isinstance(source_condition, dict) or not isinstance(controlling_field, dict) or not isinstance(target_field, dict):
            issue(
                issues,
                "ERROR",
                "SCHEMAIR_CONDITION_MISMATCH",
                condition_path,
                "Standard condition must resolve to an equivalent SchemaIR condition.",
            )
        elif any(
            (
                source_condition.get("controllingFieldPath") != controlling_field.get("schemaIrFieldPath"),
                source_condition.get("targetFieldPath") != target_field.get("schemaIrFieldPath"),
                source_condition.get("operator") != operator,
                source_condition.get("literal") != literal,
                source_condition.get("effect") != effect,
            )
        ):
            issue(
                issues,
                "ERROR",
                "SCHEMAIR_CONDITION_MISMATCH",
                condition_path,
                "Standard condition must preserve the SchemaIR condition semantics.",
            )
        elif (
            source_condition.get("sourceText") != condition.get("sourceText")
            or source_condition.get("evidence") != condition.get("evidence")
        ):
            issue(
                issues,
                "ERROR",
                "SCHEMAIR_CONDITION_SOURCE_MISMATCH",
                condition_path,
                "Standard condition must preserve the SchemaIR source text and evidence exactly.",
            )
    return seen_indexes


def _validate_differences(
    field: dict[str, Any],
    rule_package: RulePackage,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    value = field.get("differences")
    if not isinstance(value, list):
        return
    seen_properties: set[str] = set()
    for index, difference in enumerate(value):
        difference_path = f"{path}.differences[{index}]"
        if not isinstance(difference, dict):
            issue(issues, "ERROR", "INVALID_DIFFERENCE", difference_path, "Difference must be an object.")
            continue
        _object_contract(
            difference,
            DIFFERENCE_PROPERTIES_SET,
            DIFFERENCE_PROPERTIES_SET,
            issues,
            path=difference_path,
            missing_code="MISSING_DIFFERENCE_PROPERTY",
            unknown_code="UNKNOWN_DIFFERENCE_PROPERTY",
        )
        property_name = difference.get("property")
        _enum(
            property_name,
            DIFFERENCE_PROPERTIES,
            issues,
            "INVALID_DIFFERENCE_PROPERTY",
            f"{difference_path}.property",
        )
        if isinstance(property_name, str):
            if property_name in seen_properties:
                issue(
                    issues,
                    "ERROR",
                    "DUPLICATE_DIFFERENCE_PROPERTY",
                    f"{difference_path}.property",
                    "Each Standard property may have at most one difference record.",
                )
            seen_properties.add(property_name)
            if difference.get("standardValue") != field.get(property_name):
                issue(
                    issues,
                    "ERROR",
                    "DIFFERENCE_STANDARD_VALUE_MISMATCH",
                    f"{difference_path}.standardValue",
                    "Difference standardValue must equal the field property.",
                )
        _required_string(difference.get("reason"), issues, "INVALID_DIFFERENCE_REASON", f"{difference_path}.reason")
        _validate_rule_references(
            difference.get("ruleReferences"),
            rule_package,
            issues,
            path=f"{difference_path}.ruleReferences",
        )
        _require_rule_reference(
            difference.get("ruleReferences"),
            "STD.DIFFERENCE.PRESERVE",
            rule_package,
            issues,
            path=f"{difference_path}.ruleReferences",
        )
        review = difference.get("review")
        if isinstance(review, dict):
            _validate_review(review, issues, path=f"{difference_path}.review")
            if review.get("status") != "APPROVED":
                issue(
                    issues,
                    "WARNING",
                    "DIFFERENCE_REVIEW_NOT_APPROVED",
                    f"{difference_path}.review.status",
                    "SchemaIR-to-Standard differences require Human Review.",
                    blocking=True,
                )
        else:
            issue(issues, "ERROR", "INVALID_DIFFERENCE_REVIEW", f"{difference_path}.review", "Difference review must be an object.")


def _validate_length(value: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_LENGTH_CONSTRAINT", path, "lengthLimit must be an object.")
        return
    _object_contract(
        value,
        LENGTH_PROPERTIES,
        LENGTH_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_LENGTH_PROPERTY",
        unknown_code="UNKNOWN_LENGTH_PROPERTY",
    )
    state = _enum(value.get("state"), CONSTRAINT_STATES, issues, "INVALID_CONSTRAINT_STATE", f"{path}.state")
    numbers: dict[str, int | None] = {}
    for name in ("min", "max", "precision", "scale"):
        item = value.get(name)
        if item is not None and (isinstance(item, bool) or not isinstance(item, int) or item < 0):
            issue(
                issues,
                "ERROR",
                "INVALID_LENGTH_VALUE",
                f"{path}.{name}",
                "Length values must be non-negative integers or null.",
            )
            numbers[name] = None
        else:
            numbers[name] = item
    has_range = numbers["min"] is not None or numbers["max"] is not None
    has_decimal = numbers["precision"] is not None or numbers["scale"] is not None
    if state == "VALUE":
        if has_range == has_decimal:
            issue(
                issues,
                "ERROR",
                "INVALID_LENGTH_VALUE",
                path,
                "VALUE lengthLimit must use either min/max or precision/scale.",
            )
        if numbers["min"] is not None and numbers["max"] is not None and numbers["min"] > numbers["max"]:
            issue(issues, "ERROR", "INVALID_LENGTH_RANGE", path, "lengthLimit min must not exceed max.")
        if has_decimal and (
            numbers["precision"] is None
            or numbers["precision"] < 1
            or numbers["scale"] is None
            or numbers["scale"] > numbers["precision"]
        ):
            issue(
                issues,
                "ERROR",
                "INVALID_DECIMAL_LENGTH",
                path,
                "Decimal lengthLimit requires precision >= 1 and 0 <= scale <= precision.",
            )
    elif state in {"NO_CONSTRAINT", "UNKNOWN"} and (has_range or has_decimal):
        issue(
            issues,
            "ERROR",
            "CONSTRAINT_STATE_VALUE_CONFLICT",
            path,
            "NO_CONSTRAINT and UNKNOWN lengthLimit values must be null.",
        )
    if state == "UNKNOWN":
        issue(
            issues,
            "WARNING",
            "UNKNOWN_CONSTRAINT",
            path,
            "UNKNOWN constraints cannot enter a Final Standard.",
            blocking=True,
        )


def _validate_text_constraint(value: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_TEXT_CONSTRAINT", path, "Constraint must be an object.")
        return
    _object_contract(
        value,
        TEXT_CONSTRAINT_PROPERTIES,
        TEXT_CONSTRAINT_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_CONSTRAINT_PROPERTY",
        unknown_code="UNKNOWN_CONSTRAINT_PROPERTY",
    )
    state = _enum(value.get("state"), CONSTRAINT_STATES, issues, "INVALID_CONSTRAINT_STATE", f"{path}.state")
    constraint_value = value.get("value")
    if state == "VALUE":
        _required_string(constraint_value, issues, "INVALID_CONSTRAINT_VALUE", f"{path}.value")
    elif state in {"NO_CONSTRAINT", "UNKNOWN"} and constraint_value is not None:
        issue(
            issues,
            "ERROR",
            "CONSTRAINT_STATE_VALUE_CONFLICT",
            f"{path}.value",
            "NO_CONSTRAINT and UNKNOWN values must be null.",
        )
    if state == "UNKNOWN":
        issue(
            issues,
            "WARNING",
            "UNKNOWN_CONSTRAINT",
            path,
            "UNKNOWN constraints cannot enter a Final Standard.",
            blocking=True,
        )


def _validate_sequences(fields: list[dict[str, Any]], issues: list[ValidationIssue]) -> None:
    groups: dict[str, list[int]] = defaultdict(list)
    for field in fields:
        parent = field.get("parentPath")
        sequence = field.get("sequence")
        if isinstance(parent, str) and isinstance(sequence, int) and not isinstance(sequence, bool) and sequence >= 1:
            groups[parent].append(sequence)
    for parent, sequences in groups.items():
        counts = Counter(sequences)
        if any(count > 1 for count in counts.values()):
            issue(
                issues,
                "ERROR",
                "DUPLICATE_FIELD_SEQUENCE",
                parent,
                "Sibling field sequences must be unique.",
            )
        if sorted(sequences) != list(range(1, len(sequences) + 1)):
            issue(
                issues,
                "ERROR",
                "NON_CONTIGUOUS_FIELD_SEQUENCE",
                parent,
                "Sibling field sequences must be contiguous from 1.",
            )


def _validate_rule_references(
    value: Any,
    rule_package: RulePackage,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    if not isinstance(value, list):
        issue(issues, "ERROR", "INVALID_RULE_REFERENCES", path, "ruleReferences must be an array.")
        return
    if not value:
        issue(issues, "ERROR", "EMPTY_RULE_REFERENCES", path, "ruleReferences must not be empty.")
    seen: set[str] = set()
    for index, rule_id in enumerate(value):
        item_path = f"{path}[{index}]"
        _required_string(rule_id, issues, "INVALID_RULE_REFERENCE", item_path)
        if not isinstance(rule_id, str):
            continue
        if rule_id in seen:
            issue(issues, "ERROR", "DUPLICATE_RULE_REFERENCE", item_path, "Rule references must be unique.")
        seen.add(rule_id)
        rule = rule_package.rules_by_id.get(rule_id) if isinstance(rule_package, RulePackage) else None
        if rule is None:
            issue(issues, "ERROR", "UNKNOWN_RULE_REFERENCE", item_path, "Rule reference must resolve in the loaded package.")
        elif rule.get("domain") != "STANDARD":
            issue(
                issues,
                "ERROR",
                "INVALID_RULE_REFERENCE_DOMAIN",
                item_path,
                "InterfaceStandardIR may reference only STANDARD rules.",
            )


def _require_rule_reference(
    value: Any,
    required_rule: str,
    rule_package: RulePackage,
    issues: list[ValidationIssue],
    *,
    path: str,
) -> None:
    if isinstance(value, list) and required_rule not in value:
        issue(
            issues,
            "ERROR",
            "MISSING_REQUIRED_RULE_REFERENCE",
            path,
            "The Standard feature is missing its governing Rule ID.",
        )
    if isinstance(rule_package, RulePackage) and required_rule not in rule_package.rules_by_id:
        issue(
            issues,
            "ERROR",
            "UNKNOWN_RULE_REFERENCE",
            path,
            "The governing Rule ID is unavailable in the loaded package.",
        )


def _validate_evidence(value: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(value, list):
        issue(issues, "ERROR", "INVALID_EVIDENCE", path, "evidence must be an array.")
        return
    if not value:
        issue(issues, "ERROR", "EMPTY_EVIDENCE", path, "evidence must not be empty.")
    for index, item in enumerate(value):
        _validate_single_evidence(item, issues, path=f"{path}[{index}]")


def _validate_single_evidence(value: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_EVIDENCE", path, "evidence must be an object.")
        return
    _object_contract(
        value,
        EVIDENCE_PROPERTIES,
        EVIDENCE_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_EVIDENCE_PROPERTY",
        unknown_code="UNKNOWN_EVIDENCE_PROPERTY",
    )
    _enum(value.get("kind"), EVIDENCE_KINDS, issues, "INVALID_EVIDENCE_KIND", f"{path}.kind")
    _required_string(value.get("sourceRef"), issues, "INVALID_EVIDENCE_SOURCE", f"{path}.sourceRef")
    _required_string(value.get("note"), issues, "INVALID_EVIDENCE_NOTE", f"{path}.note")


def _validate_condition_evidence(value: Any, issues: list[ValidationIssue], *, path: str) -> None:
    if not isinstance(value, dict):
        issue(issues, "ERROR", "INVALID_EVIDENCE", path, "condition evidence must be an object.")
        return
    _object_contract(
        value,
        SCHEMA_EVIDENCE_PROPERTIES,
        SCHEMA_EVIDENCE_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_EVIDENCE_PROPERTY",
        unknown_code="UNKNOWN_EVIDENCE_PROPERTY",
    )
    _enum(value.get("kind"), SCHEMA_EVIDENCE_KINDS, issues, "INVALID_EVIDENCE_KIND", f"{path}.kind")
    _required_string(value.get("note"), issues, "INVALID_EVIDENCE_NOTE", f"{path}.note")


def _validate_review(review: dict[str, Any], issues: list[ValidationIssue], *, path: str) -> None:
    _object_contract(
        review,
        REVIEW_PROPERTIES,
        REVIEW_PROPERTIES,
        issues,
        path=path,
        missing_code="MISSING_REVIEW_PROPERTY",
        unknown_code="UNKNOWN_REVIEW_PROPERTY",
    )
    status = review.get("status")
    _enum(status, REVIEW_STATUSES, issues, "INVALID_REVIEW_STATUS", f"{path}.status")
    reviewer = review.get("reviewer")
    reviewed_at = review.get("reviewedAt")
    _nullable_string(review.get("note"), issues, "INVALID_REVIEW_NOTE", f"{path}.note")
    if status == "PENDING":
        if reviewer is not None or reviewed_at is not None:
            issue(
                issues,
                "ERROR",
                "PENDING_REVIEW_HAS_APPROVAL",
                path,
                "Pending review cannot carry reviewer or reviewedAt values.",
            )
    elif status == "APPROVED":
        _required_string(reviewer, issues, "INVALID_REVIEWER", f"{path}.reviewer")
        if not isinstance(reviewed_at, str) or not _is_offset_datetime(reviewed_at):
            issue(
                issues,
                "ERROR",
                "INVALID_REVIEWED_AT",
                f"{path}.reviewedAt",
                "reviewedAt must be an RFC 3339 timestamp with a timezone offset.",
            )


def _schema_data_type(field: dict[str, Any]) -> str | None:
    if field.get("hasChildren") is True or field.get("dataType") == "object":
        return "Node" if field.get("multiple") is True or _occurs_is_repeated(field.get("occurs")) else "Object"
    return {
        "string": "String",
        "boolean": "Boolean",
        "date": "Date",
        "datetime": "Date",
        "integer": "Number",
        "decimal": "Number",
    }.get(field.get("dataType"))


def _schema_length_constraint(field: dict[str, Any]) -> dict[str, Any]:
    format_value = field.get("format")
    decimal_match = DECIMAL_FORMAT_PATTERN.fullmatch(format_value) if isinstance(format_value, str) else None
    if decimal_match:
        return {
            "state": "VALUE",
            "min": None,
            "max": None,
            "precision": int(decimal_match.group(1)),
            "scale": int(decimal_match.group(2)),
        }
    length = field.get("length")
    minimum = length.get("min") if isinstance(length, dict) else None
    maximum = length.get("max") if isinstance(length, dict) else None
    if isinstance(minimum, int) and not isinstance(minimum, bool) or isinstance(maximum, int) and not isinstance(maximum, bool):
        return {
            "state": "VALUE",
            "min": minimum,
            "max": maximum,
            "precision": None,
            "scale": None,
        }
    return {"state": "NO_CONSTRAINT", "min": None, "max": None, "precision": None, "scale": None}


def _occurs_is_repeated(value: Any) -> bool:
    if not isinstance(value, str) or ".." not in value:
        return False
    maximum = value.split("..", 1)[1]
    return maximum == "n" or maximum.isdigit() and int(maximum) > 1


def _unique_index(
    fields: list[dict[str, Any]],
    key: str,
    duplicate_code: str,
    issues: list[ValidationIssue],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, field in enumerate(fields):
        value = field.get(key)
        if isinstance(value, str) and value:
            if value in result:
                issue(issues, "ERROR", duplicate_code, f"fields[{index}].{key}", f"{key} must be unique.")
            else:
                result[value] = field
    return result


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
    for key in sorted(required):
        if key not in value:
            issue(issues, "ERROR", missing_code, _path(path, key), "Required property is missing.")
    for key in value:
        if key not in allowed:
            issue(issues, "ERROR", unknown_code, _path(path, key), "Property is not supported by this contract.")


def _required_string(value: Any, issues: list[ValidationIssue], code: str, path: str) -> str | None:
    if not isinstance(value, str) or not value:
        issue(issues, "ERROR", code, path, "Property must be a non-empty string.")
        return None
    return value


def _nullable_string(value: Any, issues: list[ValidationIssue], code: str, path: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, issues, code, path)


def _boolean(value: Any, issues: list[ValidationIssue], code: str, path: str) -> bool | None:
    if not isinstance(value, bool):
        issue(issues, "ERROR", code, path, "Property must be boolean.")
        return None
    return value


def _enum(value: Any, allowed: set[str], issues: list[ValidationIssue], code: str, path: str) -> str | None:
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


def _is_offset_datetime(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _path(parent: str | None, child: str) -> str:
    return f"{parent}.{child}" if parent else child


def _result(standard: object, fields: list[Any], issues: list[ValidationIssue]) -> dict[str, Any]:
    field_objects = [field for field in fields if isinstance(field, dict)]
    return build_validation_result(
        standard,
        result_contract_version=RESULT_CONTRACT_VERSION,
        artifact_kind="InterfaceStandardIR",
        artifact_id_field="standardId",
        artifact_version_field="standardVersion",
        issues=issues,
        summary={
            "standardId": standard.get("standardId") if isinstance(standard, Mapping) else None,
            "interfaceCode": standard.get("interfaceCode") if isinstance(standard, Mapping) else None,
            "direction": standard.get("direction") if isinstance(standard, Mapping) else None,
            "rulePackageVersion": standard.get("rulePackageVersion") if isinstance(standard, Mapping) else None,
            "fieldCount": len(field_objects),
        },
        coverage={
            "scalarFieldCount": sum(1 for field in field_objects if field.get("dataType") in {"String", "Boolean", "Date", "Number"}),
            "containerFieldCount": sum(1 for field in field_objects if field.get("dataType") in {"Node", "Object"}),
            "xmlKeyCount": sum(len(field.get("xmlKeys", [])) for field in field_objects if isinstance(field.get("xmlKeys"), list)),
            "conditionalConstraintCount": sum(
                len(field.get("conditionalConstraints", []))
                for field in field_objects
                if isinstance(field.get("conditionalConstraints"), list)
            ),
            "differenceCount": sum(
                len(field.get("differences", []))
                for field in field_objects
                if isinstance(field.get("differences"), list)
            ),
            "uncertainFieldCount": sum(1 for field in field_objects if field.get("uncertain") is True),
        },
    )


def _log_result(result: dict[str, Any]) -> None:
    summary = result["summary"]
    outcome = "succeeded" if result["status"] != "failed" else "failed"
    log = LOGGER.info if outcome == "succeeded" else LOGGER.warning
    log(
        "InterfaceStandardIR validation completed",
        extra={
            "component": "interface_standard_validator",
            "artifact_id": summary.get("standardId"),
            "direction": summary.get("direction"),
            "outcome": outcome,
            "field_count": summary.get("fieldCount"),
            "error_count": summary.get("errorCount"),
            "warning_count": summary.get("warningCount"),
            "blocking_count": summary.get("blockingCount"),
        },
    )
