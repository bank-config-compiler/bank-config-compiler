from __future__ import annotations

import logging
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from bank_config_compiler.configuration_rules import RulePackageValidationError, load_rule_package


RULE_PACKAGE_DIR = Path(__file__).parents[1] / "configuration-rules" / "v1"


def copy_rule_package(tmp_path: Path, *, version: str = "v1") -> Path:
    package_dir = tmp_path / version
    shutil.copytree(RULE_PACKAGE_DIR, package_dir)
    return package_dir


def read_yaml(package_dir: Path, name: str) -> dict[str, Any]:
    return yaml.safe_load((package_dir / name).read_text(encoding="utf-8"))


def write_yaml(package_dir: Path, name: str, document: dict[str, Any]) -> None:
    (package_dir / name).write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
        newline="",
    )


def set_package_status(package_dir: Path, status: str, confirmation_date: str | None) -> None:
    rules = read_yaml(package_dir, "rules.yaml")
    rules["package"]["status"] = status
    rules["package"]["confirmationDate"] = confirmation_date
    write_yaml(package_dir, "rules.yaml", rules)
    for name in ("fields.yaml", "functions.yaml", "mappings.yaml"):
        document = read_yaml(package_dir, name)
        document["status"] = status
        write_yaml(package_dir, name, document)


def validation_codes(error: RulePackageValidationError) -> set[str]:
    return {issue["code"] for issue in error.issues}


def test_loads_current_draft_rule_package_and_builds_indexes() -> None:
    package = load_rule_package(RULE_PACKAGE_DIR, require_released=False)

    assert package.version == "v1"
    assert package.status == "DRAFT"
    assert len(package.rules_by_id) == 27
    assert {direction: len(fields) for direction, fields in package.fields_by_direction.items()} == {
        "ASSEMBLY": 207,
        "PARSE": 14,
    }
    assert set(package.functions_by_code) == {
        "DateFormat",
        "SeqNoGenerate",
        "SinglePaymentGetPaymentNo",
        "SystemDateFormat",
        "TotalAmountWithDecimalPlace",
    }
    assert len(package.mappings_by_name) == 6
    rules_document = package.documents["rules.yaml"]
    functions_document = package.documents["functions.yaml"]
    assert rules_document["package"]["scope"] == "BKL_CONFIGURATION_RULES_SUBSET"
    assert rules_document["processingPolicies"]["chineseCharacterLength"]["default"] == "STANDARD_1"
    assert "b2e0061Examples" not in rules_document["bankDocumentConditions"]
    assert functions_document["dataTypeContract"]["source"] == "BUSINESS_CONFIRMATION"
    assert {source["source"] for source in functions_document["evidenceSources"]} == {
        "TARGET_SYSTEM_FORMAL_EXPORT"
    }
    assert package.rules_by_id["TPL.VALUE.FUNCTION"]["domain"] == "TEMPLATE"
    assert package.fields_by_direction["PARSE"]["paymentLineList"]["dataType"] == "LIST"
    assert package.functions_by_code["DateFormat"]["resultDataType"] == "String"
    assert package.mappings_by_name["Swift-Uppercase-List"]["entries"][0] == {
        "source": "z",
        "target": "Z",
    }


def test_rejects_legacy_interface_specific_rule_contract(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    rules = read_yaml(package_dir, "rules.yaml")
    rules["package"]["scope"] = "B2E0061_PHASE0_MINIMUM"
    rules["processingPolicies"]["chineseCharacterLength"]["default"] = "UNKNOWN"
    rules["bankDocumentConditions"]["b2e0061Examples"] = []
    write_yaml(package_dir, "rules.yaml", rules)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {"INVALID_CONTRACT_VALUE", "UNKNOWN_PROPERTY"} <= validation_codes(captured.value)


def test_rejects_unapproved_function_sources(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    functions = read_yaml(package_dir, "functions.yaml")
    functions["evidenceSources"].append(
        {"source": "BKL_REFERENCE", "paths": ["docs/reference/samples/bkl.md"]}
    )
    functions["dataTypeContract"]["source"] = "TARGET_SYSTEM_FORMAL_EXPORT"
    functions["functions"][0]["source"] = "BKL_REFERENCE"
    functions["functions"][0]["contractStatus"] = "DECLARED_INCOMPLETE"
    write_yaml(package_dir, "functions.yaml", functions)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {"INVALID_ENUM_VALUE", "INVALID_CONTRACT_VALUE"} <= validation_codes(captured.value)


def test_rejects_draft_package_by_default() -> None:
    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(RULE_PACKAGE_DIR)

    assert validation_codes(captured.value) == {"RULE_PACKAGE_NOT_RELEASED"}
    assert captured.value.issues[0]["path"] == "package.status"


def test_accepts_well_formed_released_package_by_default(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    set_package_status(package_dir, "RELEASED", "2026-08-06")

    package = load_rule_package(package_dir)

    assert package.status == "RELEASED"


def test_rejects_superseded_package_by_default(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    set_package_status(package_dir, "SUPERSEDED", "2026-08-06")

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir)

    assert validation_codes(captured.value) == {"RULE_PACKAGE_NOT_RELEASED"}


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing", "MISSING_RULE_DOCUMENT"),
        ("directory", "RULE_DOCUMENT_NOT_FILE"),
        ("bom", "RULE_DOCUMENT_HAS_BOM"),
        ("invalid_utf8", "RULE_DOCUMENT_INVALID_UTF8"),
        ("invalid_yaml", "RULE_DOCUMENT_INVALID_YAML"),
        ("unsafe_tag", "RULE_DOCUMENT_INVALID_YAML"),
        ("non_object", "RULE_DOCUMENT_NOT_OBJECT"),
    ],
)
def test_rejects_invalid_rule_document_boundaries(tmp_path: Path, mutation: str, expected_code: str) -> None:
    package_dir = copy_rule_package(tmp_path)
    target = package_dir / "mappings.yaml"
    if mutation == "missing":
        target.unlink()
    elif mutation == "directory":
        target.unlink()
        target.mkdir()
    elif mutation == "bom":
        target.write_bytes(b"\xef\xbb\xbf" + target.read_bytes())
    elif mutation == "invalid_utf8":
        target.write_bytes(b"\xff\xfe")
    elif mutation == "invalid_yaml":
        target.write_text("catalog: [", encoding="utf-8")
    elif mutation == "unsafe_tag":
        target.write_text("!!python/object/apply:os.system ['echo unsafe']", encoding="utf-8")
    else:
        target.write_text("[]", encoding="utf-8")

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert expected_code in validation_codes(captured.value)
    assert all(issue["file"] == "mappings.yaml" for issue in captured.value.issues)


def test_rejects_missing_package_directory(tmp_path: Path) -> None:
    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(tmp_path / "missing", require_released=False)

    assert validation_codes(captured.value) == {"RULE_PACKAGE_DIRECTORY_INVALID"}


def test_rejects_version_status_and_confirmation_date_mismatches(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path, version="v2")
    rules = read_yaml(package_dir, "rules.yaml")
    rules["package"]["status"] = "RELEASED"
    write_yaml(package_dir, "rules.yaml", rules)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {
        "RULE_PACKAGE_VERSION_MISMATCH",
        "RULE_DOCUMENT_STATUS_MISMATCH",
        "RELEASED_PACKAGE_MISSING_CONFIRMATION_DATE",
    } <= validation_codes(captured.value)


def test_rejects_unknown_missing_and_wrongly_typed_properties(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    rules = read_yaml(package_dir, "rules.yaml")
    rules["unexpected"] = True
    del rules["sourceAuthority"]
    rules["processingPolicies"]["rowLimit"]["minimum"] = True
    write_yaml(package_dir, "rules.yaml", rules)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {"UNKNOWN_PROPERTY", "MISSING_PROPERTY", "INVALID_INTEGER"} <= validation_codes(captured.value)


def test_rejects_duplicate_identifiers_and_mapping_sources(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    rules = read_yaml(package_dir, "rules.yaml")
    rules["rules"].append(deepcopy(rules["rules"][0]))
    write_yaml(package_dir, "rules.yaml", rules)

    fields = read_yaml(package_dir, "fields.yaml")
    fields["catalogs"]["ASSEMBLY"]["entries"].append(
        deepcopy(fields["catalogs"]["ASSEMBLY"]["entries"][0])
    )
    write_yaml(package_dir, "fields.yaml", fields)

    functions = read_yaml(package_dir, "functions.yaml")
    functions["functions"].append(deepcopy(functions["functions"][0]))
    write_yaml(package_dir, "functions.yaml", functions)

    mappings = read_yaml(package_dir, "mappings.yaml")
    mappings["catalog"]["rules"].append(deepcopy(mappings["catalog"]["rules"][0]))
    mappings["catalog"]["rules"][1]["entries"].append(
        deepcopy(mappings["catalog"]["rules"][1]["entries"][0])
    )
    write_yaml(package_dir, "mappings.yaml", mappings)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {
        "DUPLICATE_RULE_ID",
        "DUPLICATE_FIELD_CODE",
        "DUPLICATE_FUNCTION_CODE",
        "DUPLICATE_MAPPING_RULE_NAME",
        "DUPLICATE_MAPPING_SOURCE",
    } <= validation_codes(captured.value)


def test_rejects_invalid_function_parameter_contract(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    functions = read_yaml(package_dir, "functions.yaml")
    date_format = next(item for item in functions["functions"] if item["code"] == "DateFormat")
    date_format["parameters"][0]["position"] = True
    date_format["parameters"][1]["position"] = 4
    date_format["parameters"][1]["allowedArgumentKinds"] = ["NESTED_EXPRESSION"]
    write_yaml(package_dir, "functions.yaml", functions)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {"INVALID_INTEGER", "NON_CONTIGUOUS_PARAMETER_POSITIONS", "INVALID_ENUM_VALUE"} <= validation_codes(
        captured.value
    )


def test_rejects_unknown_rule_and_catalog_references(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    fields = read_yaml(package_dir, "fields.yaml")
    fields["catalogs"]["ASSEMBLY"]["bindingRuleId"] = "TPL.UNKNOWN"
    write_yaml(package_dir, "fields.yaml", fields)

    functions = read_yaml(package_dir, "functions.yaml")
    functions["invocationRuleId"] = "TPL.UNKNOWN.FUNCTION"
    write_yaml(package_dir, "functions.yaml", functions)

    rules = read_yaml(package_dir, "rules.yaml")
    rules["processingPolicies"]["replacement"]["catalogFile"] = "other.yaml"
    write_yaml(package_dir, "rules.yaml", rules)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {"UNKNOWN_RULE_REFERENCE", "INVALID_CATALOG_REFERENCE"} <= validation_codes(captured.value)


def test_rejects_invalid_field_path_and_catalog_data_type(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    fields = read_yaml(package_dir, "fields.yaml")
    parse_field = fields["catalogs"]["PARSE"]["entries"][0]
    parse_field["dataType"] = "OBJECT"
    parse_field["fullPath"] = "Root.wrong"
    write_yaml(package_dir, "fields.yaml", fields)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {"INVALID_ENUM_VALUE", "INVALID_FULL_PATH"} <= validation_codes(captured.value)


def test_rejects_invalid_mapping_values_and_redaction_contract(tmp_path: Path) -> None:
    package_dir = copy_rule_package(tmp_path)
    mappings = read_yaml(package_dir, "mappings.yaml")
    first_mapping = mappings["catalog"]["rules"][0]
    first_mapping["entries"][0]["source"] = 1
    first_mapping["entries"][1]["target"] = False
    redacted_mapping = next(item for item in mappings["catalog"]["rules"] if item.get("redacted"))
    redacted_mapping["entries"][0]["target"] = ""
    mappings["validation"]["allowEmptyTarget"] = False
    write_yaml(package_dir, "mappings.yaml", mappings)

    with pytest.raises(RulePackageValidationError) as captured:
        load_rule_package(package_dir, require_released=False)

    assert {"INVALID_STRING", "INVALID_VALIDATION_CONTRACT", "INVALID_REDACTED_MAPPING"} <= validation_codes(
        captured.value
    )


def test_logs_only_diagnostic_metadata_without_rule_content(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    package_dir = copy_rule_package(tmp_path)
    mappings = read_yaml(package_dir, "mappings.yaml")
    redacted_mapping = next(item for item in mappings["catalog"]["rules"] if item.get("redacted"))
    redacted_mapping["entries"][0]["target"] = "secret-value"
    sensitive_description = "sensitive-description-that-must-not-be-logged"
    redacted_mapping["description"] = sensitive_description
    write_yaml(package_dir, "mappings.yaml", mappings)

    with caplog.at_level(logging.DEBUG, logger="bank_config_compiler.configuration_rules"):
        with pytest.raises(RulePackageValidationError) as captured:
            load_rule_package(package_dir, require_released=False)

    rendered_logs = "\n".join(record.getMessage() for record in caplog.records)
    rendered_issues = "\n".join(issue["message"] for issue in captured.value.issues)
    assert "secret-value" not in rendered_logs
    assert sensitive_description not in rendered_logs
    assert "secret-value" not in rendered_issues
    assert sensitive_description not in rendered_issues
    assert [record.outcome for record in caplog.records] == ["started", "failed"]
