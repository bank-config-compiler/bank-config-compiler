from __future__ import annotations

import json
from pathlib import Path

from bank_config_compiler.schemair_validator import validate_schemair


GOLDEN_DIR = Path("samples/golden/b2eboc-b2e0061")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_b2e0061_schemair_validation_matches_expected_result() -> None:
    schemair = read_json(GOLDEN_DIR / "schemair.expected.json")
    expected_result = read_json(GOLDEN_DIR / "schemair-validation.expected.json")

    assert validate_schemair(schemair) == expected_result


def test_b2e0061_schemair_validation_coverage_is_stable() -> None:
    schemair = read_json(GOLDEN_DIR / "schemair.expected.json")

    result = validate_schemair(schemair)

    assert result["status"] == "passed_with_warnings"
    assert result["summary"]["errorCount"] == 0
    assert result["summary"]["fieldCount"] == 50
    assert result["coverage"] == {
        "envelopeFieldCount": 13,
        "messageFieldCount": 37,
        "fieldsByFunctionType": {
            "ASSEMBLY": 27,
            "PARSE": 10,
        },
    }
