from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bank_config_compiler.schemair_validator import validate_schemair


GOLDEN_DIR = Path("samples/golden/b2eboc-b2e0061")
TRUSTED_CHAIN_DIR = Path("samples/trusted-chain/b2eboc-b2e0061")
P0_T2_HASHES = {
    "docir.expected.md": "6e155c590aa09633106bac5193b9823ace66070d17a20c179f75eb6b8fbfe9a0",
    "schemair.expected.json": "ad9477a2c3abd3baab2ca03c5f018b02cc3e4fd827e8721df080fd612e44bfc4",
    "schemair-validation.expected.json": "0d716a1c026c8cb6648a64a0d480a1e443befadb63fed6bf97626d895002896a",
    "review-notes.expected.md": "e94856b0ea55148c4955fdbf602f369284429eecffc466dc30c6d35aa7f7835b",
}


def test_p0_t2_review_golden_files_remain_byte_identical() -> None:
    actual = {
        name: hashlib.sha256((GOLDEN_DIR / name).read_bytes()).hexdigest()
        for name in P0_T2_HASHES
    }

    assert actual == P0_T2_HASHES


def test_legacy_schemair_is_not_accepted_by_v2_validator() -> None:
    schemair = json.loads((GOLDEN_DIR / "schemair.expected.json").read_text(encoding="utf-8"))

    result = validate_schemair(schemair)

    assert result["status"] == "failed"
    assert result["finalEligible"] is False
    assert "MISSING_TOP_LEVEL_PROPERTY" in {item["code"] for item in result["issues"]}
    assert "UNKNOWN_TOP_LEVEL_PROPERTY" in {item["code"] for item in result["issues"]}


def test_schemair_v2_final_matches_committed_validation_result() -> None:
    schemair = json.loads((TRUSTED_CHAIN_DIR / "schemair-final.json").read_text(encoding="utf-8"))
    expected = json.loads(
        (TRUSTED_CHAIN_DIR / "schemair-validation-result.json").read_text(encoding="utf-8")
    )

    actual = validate_schemair(schemair)

    assert actual == expected
    assert actual["validatedArtifact"]["contentHash"] == (
        "sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162"
    )
    assert actual["status"] == "passed"
    assert actual["finalEligible"] is True
    assert actual["summary"]["errorCount"] == 0
    assert actual["summary"]["warningCount"] == 0
    assert actual["summary"]["blockingCount"] == 0
    assert actual["coverage"] == {
        "envelopeFieldCount": 12,
        "messageFieldCount": 37,
        "fieldsByFunctionType": {"ASSEMBLY": 27, "PARSE": 10},
    }
