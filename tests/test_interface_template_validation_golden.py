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
        "hash": "sha256:356b83c1aff90d83d82fa3bbc14f7fe8277c34605a3d5edb4cb99abd71c49957",
        "fieldConfigCount": 26,
        "warningCount": 10,
        "blockingCount": 10,
        "coverage": {
            "valueBindingCount": 25,
            "structureBindingCount": 1,
            "collectionBindingCount": 0,
            "fieldValueExpressionCount": 25,
            "xmlKeyExpressionCount": 3,
            "omissionCount": 4,
            "approvedOmissionCount": 0,
            "uncertainFieldConfigCount": 0,
            "functionInvocationCount": 4,
            "mappingExpressionCount": 0,
            "replacementCount": 0,
        },
    },
    "parse": {
        "hash": "sha256:33cd4f7ae02701d6ab19cf46628398354590dba3d612f91e43b06f78d1356621",
        "fieldConfigCount": 8,
        "warningCount": 2,
        "blockingCount": 2,
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


def load_candidate(direction: str) -> dict[str, Any]:
    return json.loads(
        (TEMPLATES_DIR / direction / "v1/template-draft.json").read_text(encoding="utf-8")
    )


def load_standard(direction: str) -> dict[str, Any]:
    return json.loads(
        (
            FIXTURE_DIR / "standards" / direction / "v1/standard-final.json"
        ).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("direction", ["assembly", "parse"])
def test_draft_template_matches_committed_validation_result(direction: str) -> None:
    candidate = load_candidate(direction)
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
    assert actual["status"] == "passed_with_warnings"
    assert actual["finalEligible"] is False
    assert actual["summary"]["fieldConfigCount"] == expected["fieldConfigCount"]
    assert actual["summary"]["errorCount"] == 0
    assert actual["summary"]["warningCount"] == expected["warningCount"]
    assert actual["summary"]["blockingCount"] == expected["blockingCount"]
    assert actual["coverage"] == expected["coverage"]


def test_draft_candidates_preserve_review_boundaries() -> None:
    assembly = load_candidate("assembly")
    parse = load_candidate("parse")
    assembly_standard = load_standard("assembly")
    assembly_paths = {
        field["fieldId"]: field["fullPath"] for field in assembly_standard["fields"]
    }

    assert assembly["status"] == parse["status"] == "DRAFT"
    assert assembly["review"]["status"] == parse["review"]["status"] == "PENDING"
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
    assert all(item["reviewDisposition"] == "PENDING" for item in assembly["omissions"])

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
    candidate = load_candidate("assembly")
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
