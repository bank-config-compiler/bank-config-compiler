from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, TypedDict

import yaml


LOGGER = logging.getLogger(__name__)
RULE_DOCUMENT_NAMES = ("rules.yaml", "fields.yaml", "functions.yaml", "mappings.yaml")
UTF8_BOM = b"\xef\xbb\xbf"
PACKAGE_STATUSES = {"DRAFT", "RELEASED", "SUPERSEDED"}
RULE_DOMAINS = {"STANDARD", "TEMPLATE"}
XML_STANDARD_DATA_TYPES = {"String", "Boolean", "Date", "Number", "Node", "Object"}
PARSE_FIELD_DATA_TYPES = {"STRING", "BOOLEAN", "DATE", "NUMBER", "LIST"}
CONSTRAINT_STATES = {"VALUE", "NO_CONSTRAINT", "UNKNOWN"}
TEMPLATE_BINDING_KINDS = {"VALUE", "STRUCTURE_ONLY", "COLLECTION_ITEM"}
VALUE_MODES = {"FIXED_VALUE", "EMPTY", "FIELD", "FUNCTION", "MAPPING", "CONCATENATE"}
FUNCTION_ARGUMENT_KINDS = {"FIELD_REF", "LITERAL"}
FIXED_VALUE_PAYLOAD_KINDS = {"LITERAL", "SECURE_INPUT_REF"}
# v1 的 function catalog 只接受正式导出中实际观察到的条目，不能用 bkl.md 补齐。
FUNCTION_SOURCES = {"TARGET_SYSTEM_FORMAL_EXPORT"}
FUNCTION_CONTRACT_STATUSES = {"OBSERVED"}
REDACTED_VALUE = "<REDACTED>"

FIELDS_VALIDATION_CONTRACT = {
    "requireDirection": True,
    "requireDescriptionByDirection": {"ASSEMBLY": True, "PARSE": False},
    "preserveMissingDescription": True,
    "requireUniqueCodeWithinDirection": True,
    "assemblyReferenceForm": "FLAT_CODE",
    "parseReferenceForm": "CODE_WITH_PARENT_PATH_AND_DATA_TYPE",
    "parseCatalogRequiresTemplateCoverage": False,
    "inferCodePopulatedFields": False,
}
FUNCTIONS_VALIDATION_CONTRACT = {
    "requireUniqueCode": True,
    "requireContiguousParameterPositions": True,
    "rejectUnknownArgumentKind": True,
    "rejectRecursiveFunctionArgument": True,
    "semanticDataTypeValidation": "STRICT_STRING",
    "aliasInferenceAllowed": False,
}
MAPPINGS_VALIDATION_CONTRACT = {
    "requireUniqueRuleName": True,
    "requireUniqueSourceWithinRule": True,
    "requireStringSource": True,
    "requireStringTarget": True,
    "allowEmptyTarget": True,
    "rejectRedactedRuleInFinal": True,
}


class RulePackageIssue(TypedDict):
    code: str
    file: str | None
    path: str | None
    message: str


@dataclass(slots=True)
class RulePackage:
    version: str
    status: str
    documents: dict[str, dict[str, Any]]
    rules_by_id: dict[str, dict[str, Any]]
    fields_by_direction: dict[str, dict[str, dict[str, Any]]]
    functions_by_code: dict[str, dict[str, Any]]
    mappings_by_name: dict[str, dict[str, Any]]


class RulePackageValidationError(Exception):
    def __init__(self, issues: list[RulePackageIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__(f"rule package validation failed with {len(issues)} issue(s)")


def load_rule_package(package_dir: Path, *, require_released: bool = True) -> RulePackage:
    package_dir = package_dir.resolve()
    LOGGER.debug(
        "Loading configuration rule package",
        extra={"component": "configuration_rules", "package_path": str(package_dir), "outcome": "started"},
    )

    issues: list[RulePackageIssue] = []
    documents = _load_documents(package_dir, issues)
    if len(documents) != len(RULE_DOCUMENT_NAMES):
        _raise_validation_error(issues)

    rules_document = documents["rules.yaml"]
    fields_document = documents["fields.yaml"]
    functions_document = documents["functions.yaml"]
    mappings_document = documents["mappings.yaml"]

    _validate_rules_document(rules_document, package_dir, issues)
    _validate_fields_document(fields_document, issues)
    _validate_functions_document(functions_document, issues)
    _validate_mappings_document(mappings_document, issues)
    _validate_cross_document_contract(documents, issues)

    package = rules_document.get("package")
    version = package.get("version") if isinstance(package, dict) and isinstance(package.get("version"), str) else None
    status = package.get("status") if isinstance(package, dict) and isinstance(package.get("status"), str) else None
    if require_released and status in PACKAGE_STATUSES and status != "RELEASED":
        _issue(
            issues,
            "RULE_PACKAGE_NOT_RELEASED",
            "rules.yaml",
            "package.status",
            "Rule package status must be RELEASED.",
        )

    if issues:
        _raise_validation_error(issues, version=version, status=status)

    rules_by_id = {rule["id"]: rule for rule in rules_document["rules"]}
    fields_by_direction = {
        direction: {entry["code"]: entry for entry in catalog["entries"]}
        for direction, catalog in fields_document["catalogs"].items()
    }
    functions_by_code = {function["code"]: function for function in functions_document["functions"]}
    mappings_by_name = {
        mapping["mappingRuleName"]: mapping for mapping in mappings_document["catalog"]["rules"]
    }

    LOGGER.info(
        "Configuration rule package loaded",
        extra={
            "component": "configuration_rules",
            "package_version": version,
            "package_status": status,
            "outcome": "succeeded",
            "rule_count": len(rules_by_id),
            "field_count": sum(len(fields) for fields in fields_by_direction.values()),
            "function_count": len(functions_by_code),
            "mapping_count": len(mappings_by_name),
        },
    )
    return RulePackage(
        version=version,
        status=status,
        documents=documents,
        rules_by_id=rules_by_id,
        fields_by_direction=fields_by_direction,
        functions_by_code=functions_by_code,
        mappings_by_name=mappings_by_name,
    )


def _load_documents(package_dir: Path, issues: list[RulePackageIssue]) -> dict[str, dict[str, Any]]:
    if not package_dir.is_dir():
        _issue(
            issues,
            "RULE_PACKAGE_DIRECTORY_INVALID",
            None,
            None,
            "Rule package path must be an existing directory.",
        )
        return {}

    documents: dict[str, dict[str, Any]] = {}
    for name in RULE_DOCUMENT_NAMES:
        path = package_dir / name
        if not path.exists():
            _issue(issues, "MISSING_RULE_DOCUMENT", name, None, "Required rule document is missing.")
            continue
        if not path.is_file():
            _issue(issues, "RULE_DOCUMENT_NOT_FILE", name, None, "Rule document path must be a file.")
            continue
        try:
            data = path.read_bytes()
        except OSError:
            _issue(issues, "RULE_DOCUMENT_READ_ERROR", name, None, "Rule document could not be read.")
            continue
        if data.startswith(UTF8_BOM):
            _issue(issues, "RULE_DOCUMENT_HAS_BOM", name, None, "Rule document must be UTF-8 without BOM.")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            _issue(issues, "RULE_DOCUMENT_INVALID_UTF8", name, None, "Rule document must contain valid UTF-8.")
            continue
        try:
            document = yaml.safe_load(text)
        except yaml.YAMLError:
            # 不回显 parser 原始异常，避免把规则内容带入日志或上层错误。
            _issue(issues, "RULE_DOCUMENT_INVALID_YAML", name, None, "Rule document must contain safe valid YAML.")
            continue
        if not isinstance(document, dict):
            _issue(issues, "RULE_DOCUMENT_NOT_OBJECT", name, None, "Rule document root must be an object.")
            continue
        documents[name] = document
    return documents


def _validate_rules_document(
    document: dict[str, Any], package_dir: Path, issues: list[RulePackageIssue]
) -> None:
    file = "rules.yaml"
    _check_keys(
        document,
        file,
        None,
        required={
            "package",
            "ruleReference",
            "dataTypes",
            "constraintStates",
            "sourceAuthority",
            "templateBindingKinds",
            "rules",
            "valueExpressions",
            "processingPolicies",
            "bankDocumentConditions",
            "mapping",
        },
        issues=issues,
    )
    package = _object(
        document.get("package"),
        file,
        "package",
        required={"name", "version", "status", "maintainer", "businessReviewer", "confirmationDate", "scope"},
        issues=issues,
    )
    if package is not None:
        _literal_string(package.get("name"), "configuration-rules", file, "package.name", issues)
        version = _string(package.get("version"), file, "package.version", issues)
        status = _enum(package.get("status"), PACKAGE_STATUSES, file, "package.status", issues)
        _string(package.get("maintainer"), file, "package.maintainer", issues)
        _string(package.get("businessReviewer"), file, "package.businessReviewer", issues)
        _literal_string(
            package.get("scope"),
            "BKL_CONFIGURATION_RULES_SUBSET",
            file,
            "package.scope",
            issues,
        )
        confirmation_date = package.get("confirmationDate")
        if status == "DRAFT" and confirmation_date is not None:
            _issue(
                issues,
                "DRAFT_PACKAGE_HAS_CONFIRMATION_DATE",
                file,
                "package.confirmationDate",
                "DRAFT package confirmationDate must be null.",
            )
        elif status in {"RELEASED", "SUPERSEDED"} and not _is_iso_date_string(confirmation_date):
            _issue(
                issues,
                "RELEASED_PACKAGE_MISSING_CONFIRMATION_DATE",
                file,
                "package.confirmationDate",
                "Released package confirmationDate must be an ISO date string.",
            )
        if version is not None and package_dir.name != version:
            _issue(
                issues,
                "RULE_PACKAGE_VERSION_MISMATCH",
                file,
                "package.version",
                "Rule package directory name must match package.version.",
            )

    rule_reference = _object(
        document.get("ruleReference"),
        file,
        "ruleReference",
        required={"requiredFields", "versionValue"},
        issues=issues,
    )
    if rule_reference is not None:
        _string_set(
            rule_reference.get("requiredFields"),
            {"rulePackageVersion", "ruleId"},
            file,
            "ruleReference.requiredFields",
            issues,
        )
        version_value = _string(rule_reference.get("versionValue"), file, "ruleReference.versionValue", issues)
        if package is not None and version_value is not None and version_value != package.get("version"):
            _issue(
                issues,
                "RULE_PACKAGE_VERSION_MISMATCH",
                file,
                "ruleReference.versionValue",
                "Rule reference version must match package.version.",
            )

    data_types = _object(
        document.get("dataTypes"),
        file,
        "dataTypes",
        required={"xmlInterfaceStandard", "parseFieldCatalog", "notes"},
        issues=issues,
    )
    if data_types is not None:
        _string_set(
            data_types.get("xmlInterfaceStandard"),
            XML_STANDARD_DATA_TYPES,
            file,
            "dataTypes.xmlInterfaceStandard",
            issues,
        )
        _string_set(
            data_types.get("parseFieldCatalog"),
            PARSE_FIELD_DATA_TYPES,
            file,
            "dataTypes.parseFieldCatalog",
            issues,
        )
        notes = _object(
            data_types.get("notes"),
            file,
            "dataTypes.notes",
            required={"Node", "Object", "List"},
            issues=issues,
        )
        if notes is not None:
            for key in ("Node", "Object", "List"):
                _string(notes.get(key), file, f"dataTypes.notes.{key}", issues)

    _string_set(document.get("constraintStates"), CONSTRAINT_STATES, file, "constraintStates", issues)
    source_authority = _object(
        document.get("sourceAuthority"),
        file,
        "sourceAuthority",
        required={
            "bankFacts",
            "targetSystemExports",
            "reviewedAbsenceInBankDocument",
            "ambiguousOrConflictingEvidence",
            "differencesMustBePreserved",
        },
        issues=issues,
    )
    if source_authority is not None:
        expected = {
            "bankFacts": "FINAL_SCHEMA_IR",
            "targetSystemExports": "REPRESENTATION_AND_OBSERVED_CONFIGURATION_EVIDENCE",
            "reviewedAbsenceInBankDocument": "NO_CONSTRAINT",
            "ambiguousOrConflictingEvidence": "UNKNOWN",
        }
        for key, value in expected.items():
            _literal_string(source_authority.get(key), value, file, f"sourceAuthority.{key}", issues)
        _literal_bool(
            source_authority.get("differencesMustBePreserved"),
            True,
            file,
            "sourceAuthority.differencesMustBePreserved",
            issues,
        )

    _string_set(
        document.get("templateBindingKinds"),
        TEMPLATE_BINDING_KINDS,
        file,
        "templateBindingKinds",
        issues,
    )
    _validate_rule_entries(document.get("rules"), issues)
    _validate_value_expressions(document.get("valueExpressions"), issues)
    _validate_processing_policies(document.get("processingPolicies"), issues)
    _validate_bank_document_conditions(document.get("bankDocumentConditions"), issues)
    _validate_mapping_contract(document.get("mapping"), issues)


def _validate_rule_entries(value: Any, issues: list[RulePackageIssue]) -> None:
    file = "rules.yaml"
    entries = _array(value, file, "rules", issues, require_non_empty=True)
    if entries is None:
        return
    seen: set[str] = set()
    for index, value in enumerate(entries):
        path = f"rules[{index}]"
        entry = _object(value, file, path, required={"id", "domain", "summary"}, optional={"implementationStatus"}, issues=issues)
        if entry is None:
            continue
        rule_id = _string(entry.get("id"), file, f"{path}.id", issues)
        _enum(entry.get("domain"), RULE_DOMAINS, file, f"{path}.domain", issues)
        _string(entry.get("summary"), file, f"{path}.summary", issues)
        if "implementationStatus" in entry:
            _literal_string(
                entry.get("implementationStatus"),
                "DOCUMENTED_ONLY",
                file,
                f"{path}.implementationStatus",
                issues,
            )
        if rule_id is not None:
            if rule_id in seen:
                _issue(issues, "DUPLICATE_RULE_ID", file, f"{path}.id", "Rule ID must be unique.")
            seen.add(rule_id)


def _validate_value_expressions(value: Any, issues: list[RulePackageIssue]) -> None:
    file = "rules.yaml"
    path = "valueExpressions"
    expressions = _object(
        value,
        file,
        path,
        required={"modes", "functionArgumentKinds", "fixedValuePayloadKinds", "recursiveMode", "documentedOnlyModes"},
        issues=issues,
    )
    if expressions is None:
        return
    _string_set(expressions.get("modes"), VALUE_MODES, file, f"{path}.modes", issues)
    _string_set(
        expressions.get("functionArgumentKinds"),
        FUNCTION_ARGUMENT_KINDS,
        file,
        f"{path}.functionArgumentKinds",
        issues,
    )
    _string_set(
        expressions.get("fixedValuePayloadKinds"),
        FIXED_VALUE_PAYLOAD_KINDS,
        file,
        f"{path}.fixedValuePayloadKinds",
        issues,
    )
    _literal_string(expressions.get("recursiveMode"), "CONCATENATE", file, f"{path}.recursiveMode", issues)
    documented_only = _array(expressions.get("documentedOnlyModes"), file, f"{path}.documentedOnlyModes", issues)
    if documented_only is not None and documented_only:
        _issue(
            issues,
            "INVALID_CONTRACT_VALUE",
            file,
            f"{path}.documentedOnlyModes",
            "documentedOnlyModes must be empty for the Phase0 contract.",
        )


def _validate_processing_policies(value: Any, issues: list[RulePackageIssue]) -> None:
    file = "rules.yaml"
    path = "processingPolicies"
    policies = _object(
        value,
        file,
        path,
        required={"emptyHandling", "overlengthHandling", "rowLimit", "chineseCharacterLength", "replacement"},
        issues=issues,
    )
    if policies is None:
        return
    _validate_code_policy(
        policies.get("emptyHandling"),
        f"{path}.emptyHandling",
        {"BLANK", "DELETE"},
        issues,
    )
    _validate_code_policy(
        policies.get("overlengthHandling"),
        f"{path}.overlengthHandling",
        {"INTERCEPT", "TRUNCATE_FRONT", "OVERLONG_LINE_BREAK", "TRUNCATE_BACK"},
        issues,
    )

    row_limit_path = f"{path}.rowLimit"
    row_limit = _object(
        policies.get("rowLimit"),
        file,
        row_limit_path,
        required={"valueType", "meaning", "minimum", "observedValues", "default"},
        issues=issues,
    )
    if row_limit is not None:
        _literal_string(row_limit.get("valueType"), "POSITIVE_INTEGER", file, f"{row_limit_path}.valueType", issues)
        _string(row_limit.get("meaning"), file, f"{row_limit_path}.meaning", issues)
        minimum = _integer(row_limit.get("minimum"), file, f"{row_limit_path}.minimum", issues, minimum=1)
        observed = _array(row_limit.get("observedValues"), file, f"{row_limit_path}.observedValues", issues)
        if observed is not None:
            for index, item in enumerate(observed):
                _integer(item, file, f"{row_limit_path}.observedValues[{index}]", issues, minimum=minimum or 1)
        _literal_string(row_limit.get("default"), "UNKNOWN", file, f"{row_limit_path}.default", issues)

    length_path = f"{path}.chineseCharacterLength"
    character_length = _object(
        policies.get("chineseCharacterLength"),
        file,
        length_path,
        required={"valueType", "allowedValues", "meanings", "default"},
        issues=issues,
    )
    length_modes = {f"STANDARD_{number}" for number in range(1, 7)}
    if character_length is not None:
        _literal_string(character_length.get("valueType"), "CODE", file, f"{length_path}.valueType", issues)
        _string_set(character_length.get("allowedValues"), length_modes, file, f"{length_path}.allowedValues", issues)
        meanings = _object(
            character_length.get("meanings"),
            file,
            f"{length_path}.meanings",
            required=length_modes,
            issues=issues,
        )
        if meanings is not None:
            weighted_keys = {"alphabetNumberHalfWidthPunctuation", "fullWidthPunctuation", "otherCharacters"}
            for mode in sorted(length_modes):
                required = {"allCharacters"} if mode == "STANDARD_4" else weighted_keys
                weights = _object(
                    meanings.get(mode),
                    file,
                    f"{length_path}.meanings.{mode}",
                    required=required,
                    issues=issues,
                )
                if weights is not None:
                    for key in required:
                        _integer(weights.get(key), file, f"{length_path}.meanings.{mode}.{key}", issues, minimum=1)
        # 该默认值来自业务确认；继续接受 UNKNOWN 会让调用方绕过已确认的 BKL 行为。
        _literal_string(character_length.get("default"), "STANDARD_1", file, f"{length_path}.default", issues)

    replacement_path = f"{path}.replacement"
    replacement = _object(
        policies.get("replacement"),
        file,
        replacement_path,
        required={
            "valueType",
            "catalogFile",
            "cardinality",
            "applicationStage",
            "matchedBehavior",
            "emptyTargetBehavior",
            "unmatchedBehavior",
            "default",
        },
        issues=issues,
    )
    if replacement is not None:
        expected = {
            "valueType": "MAPPING_RULE_NAME",
            "catalogFile": "mappings.yaml",
            "cardinality": "ONE",
            "applicationStage": "AFTER_VALUE_EXPRESSION",
            "matchedBehavior": "REPLACE_WITH_TARGET",
            "emptyTargetBehavior": "DELETE_MATCHED_FRAGMENT",
            "unmatchedBehavior": "KEEP_UNMATCHED_TEXT",
            "default": "UNKNOWN",
        }
        for key, expected_value in expected.items():
            code = "INVALID_CATALOG_REFERENCE" if key == "catalogFile" else "INVALID_CONTRACT_VALUE"
            _literal_string(replacement.get(key), expected_value, file, f"{replacement_path}.{key}", issues, code=code)


def _validate_code_policy(value: Any, path: str, allowed_values: set[str], issues: list[RulePackageIssue]) -> None:
    file = "rules.yaml"
    policy = _object(
        value,
        file,
        path,
        required={"valueType", "allowedValues", "meanings", "default"},
        issues=issues,
    )
    if policy is None:
        return
    _literal_string(policy.get("valueType"), "CODE", file, f"{path}.valueType", issues)
    _string_set(policy.get("allowedValues"), allowed_values, file, f"{path}.allowedValues", issues)
    meanings = _object(policy.get("meanings"), file, f"{path}.meanings", required=allowed_values, issues=issues)
    if meanings is not None:
        for name in allowed_values:
            _string(meanings.get(name), file, f"{path}.meanings.{name}", issues)
    _literal_string(policy.get("default"), "UNKNOWN", file, f"{path}.default", issues)


def _validate_bank_document_conditions(value: Any, issues: list[RulePackageIssue]) -> None:
    file = "rules.yaml"
    path = "bankDocumentConditions"
    conditions = _object(
        value,
        file,
        path,
        required={"source", "supportedOperators", "supportedEffects", "requirements"},
        issues=issues,
    )
    if conditions is None:
        return
    _literal_string(conditions.get("source"), "BANK_DOCUMENT", file, f"{path}.source", issues)
    _string_set(conditions.get("supportedOperators"), {"EQUALS", "IS_EMPTY"}, file, f"{path}.supportedOperators", issues)
    _string_set(conditions.get("supportedEffects"), {"REQUIRED"}, file, f"{path}.supportedEffects", issues)
    _string_array(conditions.get("requirements"), file, f"{path}.requirements", issues, require_non_empty=True)


def _validate_mapping_contract(value: Any, issues: list[RulePackageIssue]) -> None:
    file = "rules.yaml"
    path = "mapping"
    contract = _object(
        value,
        file,
        path,
        required={
            "storage",
            "catalogFile",
            "presetCatalog",
            "ruleNameField",
            "ruleNameScope",
            "sourceExpressionKind",
            "sourceDataType",
            "targetDataType",
            "ruleCardinality",
            "matchMode",
            "duplicateSourceAllowed",
            "unmatchedBehavior",
            "embeddedEntriesAllowedInIR",
        },
        issues=issues,
    )
    if contract is None:
        return
    expected_strings = {
        "storage": "CATALOG_REFERENCE",
        "catalogFile": "mappings.yaml",
        "ruleNameField": "mappingRuleName",
        "ruleNameScope": "GLOBAL_UNIQUE",
        "sourceExpressionKind": "FIELD_REF",
        "sourceDataType": "String",
        "targetDataType": "String",
        "ruleCardinality": "ONE",
        "matchMode": "WHOLE_VALUE_EXACT",
        "unmatchedBehavior": "ERROR",
    }
    for key, expected in expected_strings.items():
        code = "INVALID_CATALOG_REFERENCE" if key == "catalogFile" else "INVALID_CONTRACT_VALUE"
        _literal_string(contract.get(key), expected, file, f"{path}.{key}", issues, code=code)
    _literal_bool(contract.get("presetCatalog"), True, file, f"{path}.presetCatalog", issues)
    _literal_bool(contract.get("duplicateSourceAllowed"), False, file, f"{path}.duplicateSourceAllowed", issues)
    _literal_bool(contract.get("embeddedEntriesAllowedInIR"), False, file, f"{path}.embeddedEntriesAllowedInIR", issues)


def _validate_fields_document(document: dict[str, Any], issues: list[RulePackageIssue]) -> None:
    file = "fields.yaml"
    _check_keys(document, file, None, required={"packageVersion", "status", "catalogs", "validation"}, issues=issues)
    _string(document.get("packageVersion"), file, "packageVersion", issues)
    _enum(document.get("status"), PACKAGE_STATUSES, file, "status", issues)
    catalogs = _object(document.get("catalogs"), file, "catalogs", required={"ASSEMBLY", "PARSE"}, issues=issues)
    if catalogs is not None:
        _validate_field_catalog("ASSEMBLY", catalogs.get("ASSEMBLY"), issues)
        _validate_field_catalog("PARSE", catalogs.get("PARSE"), issues)
    if document.get("validation") != FIELDS_VALIDATION_CONTRACT:
        _issue(
            issues,
            "INVALID_VALIDATION_CONTRACT",
            file,
            "validation",
            "Field validation contract must match the enforced runtime invariant.",
        )


def _validate_field_catalog(direction: str, value: Any, issues: list[RulePackageIssue]) -> None:
    file = "fields.yaml"
    path = f"catalogs.{direction}"
    direction_key = "valueRuleId" if direction == "ASSEMBLY" else "coverageRuleId"
    catalog = _object(
        value,
        file,
        path,
        required={"catalogId", "bindingRuleId", direction_key, "source", "scope", "entries"},
        issues=issues,
    )
    if catalog is None:
        return
    _string(catalog.get("catalogId"), file, f"{path}.catalogId", issues)
    _string(catalog.get("bindingRuleId"), file, f"{path}.bindingRuleId", issues)
    _string(catalog.get(direction_key), file, f"{path}.{direction_key}", issues)
    _string(catalog.get("source"), file, f"{path}.source", issues)
    expected_scope = "DIRECTION_GLOBAL_FLAT_NAMES" if direction == "ASSEMBLY" else "FIXED_OUTPUT_OBJECT"
    _literal_string(catalog.get("scope"), expected_scope, file, f"{path}.scope", issues)
    entries = _array(catalog.get("entries"), file, f"{path}.entries", issues, require_non_empty=True)
    if entries is None:
        return
    seen: set[str] = set()
    for index, value in enumerate(entries):
        entry_path = f"{path}.entries[{index}]"
        required = {"code", "description"}
        if direction == "PARSE":
            required |= {"dataType", "parentPath", "fullPath"}
        entry = _object(value, file, entry_path, required=required, issues=issues)
        if entry is None:
            continue
        code = _string(entry.get("code"), file, f"{entry_path}.code", issues)
        if direction == "ASSEMBLY":
            _string(entry.get("description"), file, f"{entry_path}.description", issues)
        else:
            _nullable_string(entry.get("description"), file, f"{entry_path}.description", issues)
            _enum(entry.get("dataType"), PARSE_FIELD_DATA_TYPES, file, f"{entry_path}.dataType", issues)
            parent_path = _string(entry.get("parentPath"), file, f"{entry_path}.parentPath", issues)
            full_path = _string(entry.get("fullPath"), file, f"{entry_path}.fullPath", issues)
            if code is not None and parent_path is not None and full_path is not None:
                if full_path != f"{parent_path}.{code}":
                    _issue(
                        issues,
                        "INVALID_FULL_PATH",
                        file,
                        f"{entry_path}.fullPath",
                        "Parse field fullPath must equal parentPath plus code.",
                    )
        if code is not None:
            if code in seen:
                _issue(issues, "DUPLICATE_FIELD_CODE", file, f"{entry_path}.code", "FIELD code must be unique per direction.")
            seen.add(code)


def _validate_functions_document(document: dict[str, Any], issues: list[RulePackageIssue]) -> None:
    file = "functions.yaml"
    _check_keys(
        document,
        file,
        None,
        required={"packageVersion", "status", "evidenceSources", "dataTypeContract", "invocationRuleId", "argumentKinds", "functions", "validation"},
        issues=issues,
    )
    _string(document.get("packageVersion"), file, "packageVersion", issues)
    _enum(document.get("status"), PACKAGE_STATUSES, file, "status", issues)
    evidence_sources = _array(document.get("evidenceSources"), file, "evidenceSources", issues, require_non_empty=True)
    if evidence_sources is not None:
        seen_sources: set[str] = set()
        for index, value in enumerate(evidence_sources):
            path = f"evidenceSources[{index}]"
            source = _object(value, file, path, required={"source", "paths"}, issues=issues)
            if source is None:
                continue
            source_name = _enum(source.get("source"), FUNCTION_SOURCES, file, f"{path}.source", issues)
            _string_array(source.get("paths"), file, f"{path}.paths", issues, require_non_empty=True)
            if source_name is not None:
                if source_name in seen_sources:
                    _issue(issues, "DUPLICATE_EVIDENCE_SOURCE", file, f"{path}.source", "Evidence source must be unique.")
                seen_sources.add(source_name)

    data_type_contract = _object(
        document.get("dataTypeContract"),
        file,
        "dataTypeContract",
        required={"source", "fieldReferenceInput", "literalInput", "parameter", "result"},
        issues=issues,
    )
    if data_type_contract is not None:
        # 正式导出不携带参数/返回值类型，String 契约必须明确归因于业务确认。
        _literal_string(
            data_type_contract.get("source"),
            "BUSINESS_CONFIRMATION",
            file,
            "dataTypeContract.source",
            issues,
        )
        for key in ("fieldReferenceInput", "literalInput", "parameter", "result"):
            _literal_string(data_type_contract.get(key), "String", file, f"dataTypeContract.{key}", issues)
    _string(document.get("invocationRuleId"), file, "invocationRuleId", issues)
    _string_set(document.get("argumentKinds"), FUNCTION_ARGUMENT_KINDS, file, "argumentKinds", issues)
    _validate_function_entries(document.get("functions"), issues)
    if document.get("validation") != FUNCTIONS_VALIDATION_CONTRACT:
        _issue(
            issues,
            "INVALID_VALIDATION_CONTRACT",
            file,
            "validation",
            "Function validation contract must match the enforced runtime invariant.",
        )


def _validate_function_entries(value: Any, issues: list[RulePackageIssue]) -> None:
    file = "functions.yaml"
    functions = _array(value, file, "functions", issues, require_non_empty=True)
    if functions is None:
        return
    seen: set[str] = set()
    for function_index, value in enumerate(functions):
        path = f"functions[{function_index}]"
        function = _object(
            value,
            file,
            path,
            required={"code", "name", "source", "contractStatus", "parameters", "resultDataType"},
            optional={"description"},
            issues=issues,
        )
        if function is None:
            continue
        code = _string(function.get("code"), file, f"{path}.code", issues)
        _string(function.get("name"), file, f"{path}.name", issues)
        _enum(function.get("source"), FUNCTION_SOURCES, file, f"{path}.source", issues)
        _enum(
            function.get("contractStatus"),
            FUNCTION_CONTRACT_STATUSES,
            file,
            f"{path}.contractStatus",
            issues,
        )
        if "description" in function:
            _string(function.get("description"), file, f"{path}.description", issues)
        _literal_string(function.get("resultDataType"), "String", file, f"{path}.resultDataType", issues)
        parameters = _array(function.get("parameters"), file, f"{path}.parameters", issues)
        positions: list[int] = []
        if parameters is not None:
            for parameter_index, value in enumerate(parameters):
                parameter_path = f"{path}.parameters[{parameter_index}]"
                parameter = _object(
                    value,
                    file,
                    parameter_path,
                    required={"position", "name", "required", "allowedArgumentKinds", "dataType"},
                    optional={"default"},
                    issues=issues,
                )
                if parameter is None:
                    continue
                position = _integer(parameter.get("position"), file, f"{parameter_path}.position", issues, minimum=1)
                if position is not None:
                    positions.append(position)
                _string(parameter.get("name"), file, f"{parameter_path}.name", issues)
                _boolean(parameter.get("required"), file, f"{parameter_path}.required", issues)
                argument_kinds = _array(
                    parameter.get("allowedArgumentKinds"),
                    file,
                    f"{parameter_path}.allowedArgumentKinds",
                    issues,
                    require_non_empty=True,
                )
                if argument_kinds is not None:
                    for argument_index, argument_kind in enumerate(argument_kinds):
                        _enum(
                            argument_kind,
                            FUNCTION_ARGUMENT_KINDS,
                            file,
                            f"{parameter_path}.allowedArgumentKinds[{argument_index}]",
                            issues,
                        )
                _literal_string(parameter.get("dataType"), "String", file, f"{parameter_path}.dataType", issues)
                if "default" in parameter:
                    _string(parameter.get("default"), file, f"{parameter_path}.default", issues)
            if positions != list(range(1, len(parameters) + 1)):
                _issue(
                    issues,
                    "NON_CONTIGUOUS_PARAMETER_POSITIONS",
                    file,
                    f"{path}.parameters",
                    "Function parameter positions must be contiguous and ordered from 1.",
                )
        if code is not None:
            if code in seen:
                _issue(issues, "DUPLICATE_FUNCTION_CODE", file, f"{path}.code", "Function code must be unique.")
            seen.add(code)


def _validate_mappings_document(document: dict[str, Any], issues: list[RulePackageIssue]) -> None:
    file = "mappings.yaml"
    _check_keys(document, file, None, required={"packageVersion", "status", "catalog", "validation"}, issues=issues)
    _string(document.get("packageVersion"), file, "packageVersion", issues)
    _enum(document.get("status"), PACKAGE_STATUSES, file, "status", issues)
    catalog = _object(
        document.get("catalog"),
        file,
        "catalog",
        required={"catalogId", "sampleSubset", "ruleNameScope", "sourceDataType", "targetDataType", "sourceFiles", "rules"},
        issues=issues,
    )
    if catalog is not None:
        _string(catalog.get("catalogId"), file, "catalog.catalogId", issues)
        _literal_bool(catalog.get("sampleSubset"), True, file, "catalog.sampleSubset", issues)
        _literal_string(catalog.get("ruleNameScope"), "GLOBAL_UNIQUE", file, "catalog.ruleNameScope", issues)
        _literal_string(catalog.get("sourceDataType"), "String", file, "catalog.sourceDataType", issues)
        _literal_string(catalog.get("targetDataType"), "String", file, "catalog.targetDataType", issues)
        source_files = _string_array(catalog.get("sourceFiles"), file, "catalog.sourceFiles", issues, require_non_empty=True)
        _validate_mapping_entries(catalog.get("rules"), set(source_files or []), issues)
    if document.get("validation") != MAPPINGS_VALIDATION_CONTRACT:
        _issue(
            issues,
            "INVALID_VALIDATION_CONTRACT",
            file,
            "validation",
            "Mapping validation contract must match the enforced runtime invariant.",
        )


def _validate_mapping_entries(value: Any, source_files: set[str], issues: list[RulePackageIssue]) -> None:
    file = "mappings.yaml"
    mappings = _array(value, file, "catalog.rules", issues, require_non_empty=True)
    if mappings is None:
        return
    seen_names: set[str] = set()
    for mapping_index, value in enumerate(mappings):
        path = f"catalog.rules[{mapping_index}]"
        mapping = _object(
            value,
            file,
            path,
            required={"mappingRuleName", "description", "sourceFile", "entries"},
            optional={"redacted"},
            issues=issues,
        )
        if mapping is None:
            continue
        name = _string(mapping.get("mappingRuleName"), file, f"{path}.mappingRuleName", issues)
        _nullable_string(mapping.get("description"), file, f"{path}.description", issues)
        source_file = _string(mapping.get("sourceFile"), file, f"{path}.sourceFile", issues)
        if source_file is not None and source_file not in source_files:
            _issue(issues, "INVALID_SOURCE_REFERENCE", file, f"{path}.sourceFile", "Mapping sourceFile must be declared in catalog.sourceFiles.")
        redacted = False
        if "redacted" in mapping:
            parsed_redacted = _boolean(mapping.get("redacted"), file, f"{path}.redacted", issues)
            redacted = parsed_redacted is True
        entries = _array(mapping.get("entries"), file, f"{path}.entries", issues, require_non_empty=True)
        seen_sources: set[str] = set()
        if entries is not None:
            for entry_index, value in enumerate(entries):
                entry_path = f"{path}.entries[{entry_index}]"
                entry = _object(
                    value,
                    file,
                    entry_path,
                    required={"source", "target"},
                    optional={"sourceDescription"},
                    issues=issues,
                )
                if entry is None:
                    continue
                source = _string(entry.get("source"), file, f"{entry_path}.source", issues)
                target = _string(entry.get("target"), file, f"{entry_path}.target", issues, allow_empty=True)
                if "sourceDescription" in entry:
                    _string(entry.get("sourceDescription"), file, f"{entry_path}.sourceDescription", issues)
                if source is not None:
                    if source in seen_sources:
                        _issue(issues, "DUPLICATE_MAPPING_SOURCE", file, f"{entry_path}.source", "Mapping source must be unique within a rule.")
                    seen_sources.add(source)
                if target is not None and ((redacted and target != REDACTED_VALUE) or (not redacted and target == REDACTED_VALUE)):
                    _issue(
                        issues,
                        "INVALID_REDACTED_MAPPING",
                        file,
                        f"{entry_path}.target",
                        "Mapping target does not match its redaction declaration.",
                    )
        if name is not None:
            if name in seen_names:
                _issue(issues, "DUPLICATE_MAPPING_RULE_NAME", file, f"{path}.mappingRuleName", "Mapping rule name must be globally unique.")
            seen_names.add(name)


def _validate_cross_document_contract(
    documents: dict[str, dict[str, Any]], issues: list[RulePackageIssue]
) -> None:
    rules_document = documents["rules.yaml"]
    package = rules_document.get("package")
    if not isinstance(package, dict):
        return
    version = package.get("version")
    status = package.get("status")
    for name in ("fields.yaml", "functions.yaml", "mappings.yaml"):
        document = documents[name]
        if isinstance(version, str) and isinstance(document.get("packageVersion"), str):
            if document["packageVersion"] != version:
                _issue(issues, "RULE_DOCUMENT_VERSION_MISMATCH", name, "packageVersion", "Rule document version must match rules.yaml.")
        if isinstance(status, str) and isinstance(document.get("status"), str):
            if document["status"] != status:
                _issue(issues, "RULE_DOCUMENT_STATUS_MISMATCH", name, "status", "Rule document status must match rules.yaml.")

    rule_domains: dict[str, str] = {}
    rules = rules_document.get("rules")
    if isinstance(rules, list):
        for rule in rules:
            if isinstance(rule, dict) and isinstance(rule.get("id"), str) and isinstance(rule.get("domain"), str):
                rule_domains.setdefault(rule["id"], rule["domain"])

    references: list[tuple[str, str, Any]] = []
    catalogs = documents["fields.yaml"].get("catalogs")
    if isinstance(catalogs, dict):
        for direction, catalog in catalogs.items():
            if not isinstance(catalog, dict):
                continue
            for key, value in catalog.items():
                if isinstance(key, str) and key.endswith("RuleId"):
                    references.append(("fields.yaml", f"catalogs.{direction}.{key}", value))
    references.append(("functions.yaml", "invocationRuleId", documents["functions.yaml"].get("invocationRuleId")))
    for file, path, value in references:
        if not isinstance(value, str):
            continue
        domain = rule_domains.get(value)
        if domain is None:
            _issue(issues, "UNKNOWN_RULE_REFERENCE", file, path, "Rule reference must resolve inside rules.yaml.")
        elif domain != "TEMPLATE":
            _issue(issues, "INVALID_RULE_REFERENCE_DOMAIN", file, path, "Catalog rule reference must resolve to a TEMPLATE rule.")


def _check_keys(
    value: dict[Any, Any],
    file: str,
    path: str | None,
    *,
    required: set[str],
    optional: set[str] | None = None,
    issues: list[RulePackageIssue],
) -> None:
    allowed = required | (optional or set())
    for key in sorted(required):
        if key not in value:
            _issue(issues, "MISSING_PROPERTY", file, _path(path, key), "Required property is missing.")
    for key in value:
        if key not in allowed:
            _issue(issues, "UNKNOWN_PROPERTY", file, _path(path, str(key)), "Property is not supported by this contract.")


def _object(
    value: Any,
    file: str,
    path: str,
    *,
    required: set[str],
    optional: set[str] | None = None,
    issues: list[RulePackageIssue],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        _issue(issues, "INVALID_OBJECT", file, path, "Property must be an object.")
        return None
    _check_keys(value, file, path, required=required, optional=optional, issues=issues)
    return value


def _array(
    value: Any,
    file: str,
    path: str,
    issues: list[RulePackageIssue],
    *,
    require_non_empty: bool = False,
) -> list[Any] | None:
    if not isinstance(value, list):
        _issue(issues, "INVALID_ARRAY", file, path, "Property must be an array.")
        return None
    if require_non_empty and not value:
        _issue(issues, "EMPTY_ARRAY", file, path, "Property must contain at least one item.")
    return value


def _string(
    value: Any,
    file: str,
    path: str,
    issues: list[RulePackageIssue],
    *,
    allow_empty: bool = False,
) -> str | None:
    if not isinstance(value, str) or (not allow_empty and not value):
        _issue(issues, "INVALID_STRING", file, path, "Property must be a string with the required cardinality.")
        return None
    return value


def _nullable_string(value: Any, file: str, path: str, issues: list[RulePackageIssue]) -> str | None:
    if value is None:
        return None
    return _string(value, file, path, issues)


def _boolean(value: Any, file: str, path: str, issues: list[RulePackageIssue]) -> bool | None:
    if not isinstance(value, bool):
        _issue(issues, "INVALID_BOOLEAN", file, path, "Property must be boolean.")
        return None
    return value


def _integer(
    value: Any,
    file: str,
    path: str,
    issues: list[RulePackageIssue],
    *,
    minimum: int | None = None,
) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        _issue(issues, "INVALID_INTEGER", file, path, "Property must be an integer.")
        return None
    if minimum is not None and value < minimum:
        _issue(issues, "INVALID_INTEGER", file, path, "Integer property is below its minimum.")
        return None
    return value


def _enum(value: Any, allowed: set[str], file: str, path: str, issues: list[RulePackageIssue]) -> str | None:
    parsed = _string(value, file, path, issues)
    if parsed is not None and parsed not in allowed:
        _issue(issues, "INVALID_ENUM_VALUE", file, path, "Property is outside the supported value set.")
        return None
    return parsed


def _string_array(
    value: Any,
    file: str,
    path: str,
    issues: list[RulePackageIssue],
    *,
    require_non_empty: bool = False,
) -> list[str] | None:
    items = _array(value, file, path, issues, require_non_empty=require_non_empty)
    if items is None:
        return None
    parsed: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        string = _string(item, file, f"{path}[{index}]", issues)
        if string is not None:
            parsed.append(string)
            if string in seen:
                _issue(issues, "DUPLICATE_VALUE", file, f"{path}[{index}]", "Array values must be unique.")
            seen.add(string)
    return parsed


def _string_set(value: Any, expected: set[str], file: str, path: str, issues: list[RulePackageIssue]) -> None:
    parsed = _string_array(value, file, path, issues)
    if parsed is not None and set(parsed) != expected:
        _issue(issues, "INVALID_ENUM_SET", file, path, "Property must contain the exact supported value set.")


def _literal_string(
    value: Any,
    expected: str,
    file: str,
    path: str,
    issues: list[RulePackageIssue],
    *,
    code: str = "INVALID_CONTRACT_VALUE",
) -> None:
    parsed = _string(value, file, path, issues)
    if parsed is not None and parsed != expected:
        _issue(issues, code, file, path, "Property does not match the fixed contract value.")


def _literal_bool(
    value: Any,
    expected: bool,
    file: str,
    path: str,
    issues: list[RulePackageIssue],
) -> None:
    parsed = _boolean(value, file, path, issues)
    if parsed is not None and parsed is not expected:
        _issue(issues, "INVALID_CONTRACT_VALUE", file, path, "Property does not match the fixed contract value.")


def _is_iso_date_string(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _path(parent: str | None, child: str) -> str:
    return f"{parent}.{child}" if parent else child


def _issue(
    issues: list[RulePackageIssue],
    code: str,
    file: str | None,
    path: str | None,
    message: str,
) -> None:
    issues.append({"code": code, "file": file, "path": path, "message": message})


def _raise_validation_error(
    issues: list[RulePackageIssue],
    *,
    version: str | None = None,
    status: str | None = None,
) -> None:
    LOGGER.warning(
        "Configuration rule package validation failed",
        extra={
            "component": "configuration_rules",
            "package_version": version,
            "package_status": status,
            "outcome": "failed",
            "issue_count": len(issues),
        },
    )
    raise RulePackageValidationError(issues)
