from __future__ import annotations

import json
from pathlib import Path

import pytest

from bank_config_compiler.configuration_rules import load_rule_package
from bank_config_compiler.interface_standard_validator import validate_interface_standard


FIXTURE_DIR = Path("samples/trusted-chain/b2eboc-b2e0061")
STANDARDS_DIR = FIXTURE_DIR / "standards"
RULE_PACKAGE_DIR = Path("configuration-rules/v1")
EXPECTED = {
    "assembly": {
        "hash": "sha256:34691505230a063e7b0c92798f6bd81b7fc41c5a988b0476195fcc23ec778af4",
        "fieldCount": 36,
        "warningCount": 4,
        "blockingCount": 4,
        "coverage": {
            "scalarFieldCount": 29,
            "containerFieldCount": 7,
            "xmlKeyCount": 3,
            "conditionalConstraintCount": 1,
            "differenceCount": 0,
            "uncertainFieldCount": 1,
        },
    },
    "parse": {
        "hash": "sha256:28dfde20c7190d5eccc93558d0726e7675656c4e6029b77f3018e76807fcacb2",
        "fieldCount": 19,
        "warningCount": 6,
        "blockingCount": 6,
        "coverage": {
            "scalarFieldCount": 12,
            "containerFieldCount": 7,
            "xmlKeyCount": 3,
            "conditionalConstraintCount": 0,
            "differenceCount": 4,
            "uncertainFieldCount": 0,
        },
    },
}


@pytest.mark.parametrize("direction", ["assembly", "parse"])
def test_standard_draft_matches_committed_validation_result(direction: str) -> None:
    schemair = json.loads((FIXTURE_DIR / "schemair-final.json").read_text(encoding="utf-8"))
    standard_dir = STANDARDS_DIR / direction / "v1"
    standard = json.loads((standard_dir / "standard-draft.json").read_text(encoding="utf-8"))
    expected_result = json.loads(
        (standard_dir / "standard-validation-result.json").read_text(encoding="utf-8")
    )

    actual = validate_interface_standard(
        standard,
        schemair=schemair,
        rule_package=load_rule_package(RULE_PACKAGE_DIR),
    )
    expected = EXPECTED[direction]

    assert actual == expected_result
    assert actual["validatedArtifact"]["contentHash"] == expected["hash"]
    assert actual["status"] == "passed_with_warnings"
    assert actual["finalEligible"] is False
    assert actual["summary"]["fieldCount"] == expected["fieldCount"]
    assert actual["summary"]["errorCount"] == 0
    assert actual["summary"]["warningCount"] == expected["warningCount"]
    assert actual["summary"]["blockingCount"] == expected["blockingCount"]
    assert actual["coverage"] == expected["coverage"]


def test_standard_drafts_preserve_reviewed_projection_boundaries() -> None:
    assembly = json.loads(
        (STANDARDS_DIR / "assembly/v1/standard-draft.json").read_text(encoding="utf-8")
    )
    parse = json.loads(
        (STANDARDS_DIR / "parse/v1/standard-draft.json").read_text(encoding="utf-8")
    )

    for standard in (assembly, parse):
        assert standard["status"] == "DRAFT"
        assert standard["review"]["status"] == "PENDING"
        root = next(field for field in standard["fields"] if field["fullPath"] == "Root.bocb2e")
        assert [key["name"] for key in root["xmlKeys"]] == ["@version", "@security", "@locale"]
        assert all(field["fieldName"] not in {"@lang", "vamflag"} for field in standard["fields"])

    request_node = next(field for field in assembly["fields"] if field["fieldName"] == "b2e0061-rq")
    response_node = next(field for field in parse["fields"] if field["fieldName"] == "b2e0061-rs")
    assert (request_node["dataType"], request_node["required"]) == ("Node", True)
    assert (response_node["dataType"], response_node["required"]) == ("Node", False)

    obssid = next(
        field
        for field in assembly["fields"]
        if field["fullPath"].endswith("b2e0061-rq.obssid")
    )
    assert obssid["required"] is False
    assert obssid["conditionalConstraints"][0]["operator"] == "EQUALS"
    assert obssid["conditionalConstraints"][0]["literal"] == "2"
    assert obssid["conditionalConstraints"][0]["effect"] == "REQUIRED"

    response_status_fields = [
        field for field in parse["fields"] if field["fieldName"] in {"rspcod", "rspmsg"}
    ]
    assert len(response_status_fields) == 4
    assert {
        field["fieldName"]: field["lengthLimit"]["max"] for field in response_status_fields
    } == {"rspcod": 50, "rspmsg": 500}
    assert all(field["differences"][0]["review"]["status"] == "PENDING" for field in response_status_fields)

    email = next(field for field in assembly["fields"] if field["fieldName"] == "email")
    assert email["regex"] == {"state": "UNKNOWN", "value": None}
    assert email["uncertain"] is True
