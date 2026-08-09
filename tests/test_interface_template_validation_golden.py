from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from bank_config_compiler.configuration_rules import load_rule_package
from bank_config_compiler.interface_template_validator import (
    apply_mapping,
    apply_replacement,
    validate_interface_template,
)


FIXTURE_DIR = Path("samples/trusted-chain/b2eboc-b2e0061")
TEMPLATES_DIR = FIXTURE_DIR / "templates"
RULE_PACKAGE_DIR = Path("configuration-rules/v2")
CONTRACT_FIXTURE = Path("tests/fixtures/interface-template-v1/mapping-replacement.json")
EXPECTED = {
    "assembly": {
        "status": "passed_with_warnings",
        "hash": "sha256:b9966a449ddc29e08fa29c6cf7838273ce3cab91e00dbb38092767d21af2f561",
        "fieldConfigCount": 26,
        "warningCount": 4,
        "blockingCount": 0,
        "coverage": {
            "valueBindingCount": 25,
            "structureBindingCount": 1,
            "collectionBindingCount": 0,
            "fieldValueExpressionCount": 25,
            "xmlKeyExpressionCount": 3,
            "omissionCount": 4,
            "approvedOmissionCount": 4,
            "uncertainFieldConfigCount": 0,
            "functionInvocationCount": 4,
            "mappingExpressionCount": 0,
            "replacementCount": 0,
        },
    },
    "parse": {
        "status": "passed",
        "hash": "sha256:16eb305b6ac3944f28cb1060b943fdfc2d471f69e6bf8ea52ce059c797fb22f9",
        "fieldConfigCount": 8,
        "warningCount": 0,
        "blockingCount": 0,
        "coverage": {
            "valueBindingCount": 7,
            "structureBindingCount": 0,
            "collectionBindingCount": 1,
            "fieldValueExpressionCount": 7,
            "xmlKeyExpressionCount": 0,
            "omissionCount": 0,
            "approvedOmissionCount": 0,
            "uncertainFieldConfigCount": 0,
            "functionInvocationCount": 1,
            "mappingExpressionCount": 0,
            "replacementCount": 0,
        },
    },
}


def load_final(direction: str) -> dict[str, Any]:
    return json.loads(
        (TEMPLATES_DIR / direction / "v1/template-final.json").read_text(encoding="utf-8")
    )


def load_standard(direction: str) -> dict[str, Any]:
    return json.loads(
        (
            FIXTURE_DIR / "standards" / direction / "v1/standard-final.json"
        ).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("direction", ["assembly", "parse"])
def test_final_template_matches_committed_validation_result(direction: str) -> None:
    candidate = load_final(direction)
    standard = load_standard(direction)
    expected_result = json.loads(
        (TEMPLATES_DIR / direction / "v1/template-validation-result.json").read_text(
            encoding="utf-8"
        )
    )

    actual = validate_interface_template(
        candidate,
        standard=standard,
        rule_package=load_rule_package(RULE_PACKAGE_DIR),
    )
    expected = EXPECTED[direction]

    assert actual == expected_result
    assert actual["validatedArtifact"]["contentHash"] == expected["hash"]
    assert actual["status"] == expected["status"]
    assert actual["finalEligible"] is True
    assert actual["summary"]["fieldConfigCount"] == expected["fieldConfigCount"]
    assert actual["summary"]["errorCount"] == 0
    assert actual["summary"]["warningCount"] == expected["warningCount"]
    assert actual["summary"]["blockingCount"] == expected["blockingCount"]
    assert actual["coverage"] == expected["coverage"]


def test_final_templates_preserve_reviewed_boundaries() -> None:
    assembly = load_final("assembly")
    parse = load_final("parse")
    assembly_standard = load_standard("assembly")
    assembly_paths = {
        field["fieldId"]: field["fullPath"] for field in assembly_standard["fields"]
    }

    assert assembly["status"] == parse["status"] == "FINAL"
    assert assembly["review"]["status"] == parse["review"]["status"] == "APPROVED"
    assert assembly["review"]["reviewer"] == parse["review"]["reviewer"] == "deng"
    assert "<REDACTED>" not in json.dumps((assembly, parse), ensure_ascii=False)
    assert '"condition"' not in json.dumps((assembly, parse), ensure_ascii=False)

    root = next(
        config
        for config in assembly["fieldConfigs"]
        if config["standardTarget"]["standardFieldRef"] == "b2e0061-assembly-bocb2e"
    )
    assert root["bindingKind"] == "STRUCTURE_ONLY"
    assert set(root["xmlKeyExpressions"]) == {"@version", "@security", "@locale"}
    assert all("xmlKeyExpressions" not in config for config in parse["fieldConfigs"])

    omitted_paths = {
        assembly_paths[item["standardFieldRef"]] for item in assembly["omissions"]
    }
    assert omitted_paths == {
        "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn.actnam",
        "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.toname",
        "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.tobknm",
        "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.bocflag",
    }
    assert all(item["reviewDisposition"] == "ACCEPTED" for item in assembly["omissions"])
    assert all(item["reviewer"] == "deng" for item in assembly["omissions"])

    parse_targets = {
        config["parseTarget"]["parseFieldRef"] for config in parse["fieldConfigs"]
    }
    assert {"queryStatus", "paymentStatus", "lineBankReturnMessage"}.isdisjoint(parse_targets)
    collection = next(
        config for config in parse["fieldConfigs"] if config["bindingKind"] == "COLLECTION_ITEM"
    )
    assert collection["standardSource"]["standardFieldRef"].endswith("-b2e0061-rs")
    assert collection["parseTarget"]["parseFieldRef"] == "paymentLineList"
    assert collection["parseTarget"]["dataType"] == "LIST"
    assert collection["valueExpression"] is None


def test_controlled_mapping_and_replacement_fixture_is_not_a_bank_fact() -> None:
    candidate = load_final("assembly")
    standard = load_standard("assembly")
    contract_fixture = json.loads(CONTRACT_FIXTURE.read_text(encoding="utf-8"))
    controlled = deepcopy(candidate)
    target = next(
        config
        for config in controlled["fieldConfigs"]
        if config["standardTarget"]["standardFieldRef"].endswith("-trncur")
    )
    target["valueExpression"] = contract_fixture["mappingExpression"]
    target["processingPolicies"]["replacementRuleName"] = contract_fixture[
        "replacementRuleName"
    ]
    target["ruleReferences"].append("TPL.PROCESS.REPLACEMENT")
    rules = load_rule_package(RULE_PACKAGE_DIR)

    result = validate_interface_template(controlled, standard=standard, rule_package=rules)

    assert result["summary"]["errorCount"] == 0
    assert result["coverage"]["mappingExpressionCount"] == 1
    assert result["coverage"]["replacementCount"] == 1
    assert apply_mapping("DEBT", "BDC-ChargeBearer-List", rule_package=rules) == "OUR"
    assert (
        apply_replacement(
            "ABC#(123)",
            "Swift_illegalCharacter_List_For_ING_Turkey",
            rule_package=rules,
        )
        == "ABC123"
    )
