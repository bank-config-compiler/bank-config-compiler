from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bank_config_compiler.configuration_rules import load_rule_package
from bank_config_compiler.draft_generation import DraftGenerationError
from bank_config_compiler.interface_standard_validator import validate_interface_standard
from bank_config_compiler.interface_template_validator import validate_interface_template
from bank_config_compiler.ir_materialization import (
    materialize_schemair_candidate,
    materialize_standard_candidate,
    materialize_template_candidate,
    parse_final_docir_structure,
)
from bank_config_compiler.schemair_validator import validate_schemair


ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "samples/trusted-chain/b2eboc-b2e0061"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _draft(value: dict) -> dict:
    candidate = deepcopy(value)
    candidate["status"] = "DRAFT"
    candidate["review"] = {
        "status": "PENDING",
        "reviewer": None,
        "reviewedAt": None,
        "note": None,
    }
    return candidate


def _schema_candidate_with_docir_lang() -> dict:
    final = _json(CHAIN / "schemair-final.json")

    def semantic_field(field: dict) -> dict:
        names = (
            "fieldName",
            "displayName",
            "format",
            "length",
            "description",
            "conditionText",
            "sourceText",
            "evidence",
            "confidence",
            "uncertain",
            "uncertainReason",
            "reviewNote",
        )
        result = {name: deepcopy(field[name]) for name in names}
        if field["dataType"] == "object":
            result["required"] = field["required"]
        return result

    def semantic_message(message: dict) -> dict:
        return {
            "functionType": message["functionType"],
            "xmlEncoding": message["xmlEncoding"],
            "xmlEncodingEvidence": deepcopy(message["xmlEncodingEvidence"]),
            "description": message["description"],
            "fields": [semantic_field(field) for field in message["fields"]],
            "conditionalConstraints": [
                {key: deepcopy(value) for key, value in condition.items() if key != "review"}
                for condition in message["conditionalConstraints"]
            ],
        }

    candidate = {
        "envelope": {
            "description": final["envelope"]["description"],
            "fields": [semantic_field(field) for field in final["envelope"]["fields"]],
        },
        "messages": [semantic_message(message) for message in final["messages"]],
    }
    locale = semantic_field(final["envelope"]["fields"][3])
    locale.update(
        fieldName="@lang",
        displayName="历史语言属性",
        description="历史报文示例中的语言属性。",
    )
    candidate["envelope"]["fields"].insert(4, locale)
    return candidate


def test_schemair_materializer_rebuilds_locked_identity_and_all_structure() -> None:
    candidate = _schema_candidate_with_docir_lang()
    docir = (
        ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md"
    ).read_text(encoding="utf-8")

    materialized = materialize_schemair_candidate(
        candidate,
        docir_final=docir,
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
        interface_code="b2e0061",
    )
    result = validate_schemair(materialized)

    assert materialized["schemaId"] == "b2eboc-b2e0061-schema"
    assert materialized["schemaVersion"] == "v1"
    assert materialized["interfaceCode"] == "b2e0061"
    assert materialized["envelope"]["fields"][0]["path"] == "Root.bocb2e"
    assert materialized["envelope"]["fields"][0]["parentPath"] == "Root"
    assert materialized["envelope"]["fields"][0]["level"] == 1
    assert materialized["envelope"]["fields"][0]["hasChildren"] is True
    conditions = [
        condition
        for message in materialized["messages"]
        for condition in message["conditionalConstraints"]
    ]
    assert conditions
    assert all(
        condition["review"]["status"] == "PENDING"
        for condition in conditions
    )
    assert result["summary"]["errorCount"] == 0


def test_schemair_materializer_rejects_missing_docir_tree_coverage() -> None:
    final = _schema_candidate_with_docir_lang()
    final["messages"][0]["fields"].pop()
    docir = (
        ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md"
    ).read_text(encoding="utf-8")

    with pytest.raises(DraftGenerationError, match="exactly cover"):
        materialize_schemair_candidate(
            final,
            docir_final=docir,
            schema_id="b2eboc-b2e0061-schema",
            schema_version="v1",
            interface_code="b2e0061",
        )


def test_schemair_materializer_rejects_unknown_candidate_properties() -> None:
    candidate = _schema_candidate_with_docir_lang()
    candidate["sourceHash"] = "sha256:" + "1" * 64
    docir = (
        ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md"
    ).read_text(encoding="utf-8")

    with pytest.raises(DraftGenerationError, match="unknown properties: sourceHash"):
        materialize_schemair_candidate(
            candidate,
            docir_final=docir,
            schema_id="b2eboc-b2e0061-schema",
            schema_version="v1",
            interface_code="b2e0061",
        )


@pytest.mark.parametrize(
    ("target", "property_name", "value"),
    [
        ("top", "contractVersion", "schemair/v2"),
        ("envelope", "rootPath", "Root"),
        ("message", "messageName", "request"),
        ("field", "path", "Root.bocb2e"),
        ("scalar", "required", True),
        ("condition", "review", {"status": "APPROVED"}),
    ],
)
def test_schemair_materializer_rejects_public_derived_candidate_properties(
    target: str,
    property_name: str,
    value: object,
) -> None:
    candidate = _schema_candidate_with_docir_lang()
    targets = {
        "top": candidate,
        "envelope": candidate["envelope"],
        "message": candidate["messages"][0],
        "field": candidate["envelope"]["fields"][0],
        "scalar": candidate["envelope"]["fields"][1],
        "condition": candidate["messages"][0]["conditionalConstraints"][0],
    }
    targets[target][property_name] = value
    docir = (
        ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md"
    ).read_text(encoding="utf-8")

    with pytest.raises(
        DraftGenerationError,
        match=rf"unknown properties: {property_name}",
    ):
        materialize_schemair_candidate(
            candidate,
            docir_final=docir,
            schema_id="b2eboc-b2e0061-schema",
            schema_version="v1",
            interface_code="b2e0061",
        )


def test_schemair_materializer_rejects_missing_candidate_field_semantics() -> None:
    candidate = _schema_candidate_with_docir_lang()
    field = candidate["envelope"]["fields"][0]
    field.pop("displayName")
    field["scalarType"] = "object"
    docir = (
        ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md"
    ).read_text(encoding="utf-8")

    with pytest.raises(
        DraftGenerationError,
        match=r"missing properties: displayName; unknown properties: scalarType",
    ):
        materialize_schemair_candidate(
            candidate,
            docir_final=docir,
            schema_id="b2eboc-b2e0061-schema",
            schema_version="v1",
            interface_code="b2e0061",
        )


def test_docir_required_and_blank_multiplicity_determine_schema_occurs() -> None:
    docir = (
        ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md"
    ).read_text(encoding="utf-8")
    docir = docir.replace(
        "| 1.1 |  | 　`@version` | [0..1] | String | N |",
        "| 1.1 |  | 　`@version` |  | String | N |",
    ).replace(
        "| 2 |  | `trn-b2e0061-rq` | [1..1] | Object |  |",
        "| 2 |  | `trn-b2e0061-rq` | [0..1000] | Object |  |",
    )

    structure = parse_final_docir_structure(docir)
    envelope_version = next(
        field for field in structure["envelope"]["fields"] if field["fieldName"] == "@version"
    )
    assembly_root = structure["assembly"]["fields"][0]

    assert envelope_version["required"] is False
    assert envelope_version["multiple"] is False
    assert envelope_version["occurs"] == "0..1"
    assert "required" not in assembly_root
    assert assembly_root["multiple"] is True
    assert "occurs" not in assembly_root


def test_schemair_object_occurrence_uses_candidate_not_required_leaf() -> None:
    candidate = _schema_candidate_with_docir_lang()
    candidate["envelope"]["fields"][0]["required"] = False
    docir = (
        ROOT / "samples/draft-generation/b2eboc-b2e0061/docir-final.md"
    ).read_text(encoding="utf-8")
    docir = docir.replace(
        "| 1 |  | `bocb2e` | [1..1] | Object | Y |",
        "| 1 |  | `bocb2e` | [1..1] | Object |  |",
    )

    materialized = materialize_schemair_candidate(
        candidate,
        docir_final=docir,
        schema_id="b2eboc-b2e0061-schema",
        schema_version="v1",
        interface_code="b2e0061",
    )

    root = materialized["envelope"]["fields"][0]
    required_child = next(
        field
        for field in materialized["envelope"]["fields"]
        if field["fieldName"] == "termid"
    )
    assert root["required"] is False
    assert root["occurs"] == "0..1"
    assert required_child["required"] is True


def test_standard_materializer_projects_paths_sequence_and_xml_keys() -> None:
    schema = _json(CHAIN / "schemair-final.json")
    final = _json(CHAIN / "standards/assembly/v1/standard-final.json")
    candidate = _draft(final)
    candidate.update(standardId="model-id", standardVersion="v9")
    candidate["fields"][0].update(
        fullPath="wrong", parentPath="wrong", sequence=99, xmlKeys=[]
    )
    rules = load_rule_package(ROOT / "configuration-rules/v1")

    materialized = materialize_standard_candidate(
        candidate,
        schemair_final=schema,
        rule_package=rules,
        direction="ASSEMBLY",
        standard_id="b2e0061-assembly-standard",
        standard_version="v1",
    )
    result = validate_interface_standard(
        materialized, schemair=schema, rule_package=rules
    )

    root = materialized["fields"][0]
    assert materialized["standardId"] == "b2e0061-assembly-standard"
    assert root["fullPath"] == "Root.bocb2e"
    assert root["parentPath"] == "Root"
    assert root["sequence"] == 1
    assert [key["name"] for key in root["xmlKeys"]] == [
        "@version",
        "@security",
        "@locale",
    ]
    assert result["summary"]["errorCount"] == 0


def test_standard_materializer_preserves_business_semantics_for_review() -> None:
    schema = _json(CHAIN / "schemair-final.json")
    final = _json(CHAIN / "standards/assembly/v1/standard-final.json")
    candidate = _draft(final)
    candidate["fields"][0].update(
        fieldDescription="Human candidate description",
        conditionText="Human candidate condition",
        required=False,
        dataType="String",
    )
    rules = load_rule_package(ROOT / "configuration-rules/v1")

    materialized = materialize_standard_candidate(
        candidate,
        schemair_final=schema,
        rule_package=rules,
        direction="ASSEMBLY",
        standard_id="b2e0061-assembly-standard",
        standard_version="v1",
    )

    root = materialized["fields"][0]
    assert root["fieldDescription"] == "Human candidate description"
    assert root["conditionText"] == "Human candidate condition"
    assert root["required"] is False
    assert root["dataType"] == "String"


def test_template_materializer_projects_standard_target_but_preserves_semantics() -> None:
    standard = _json(CHAIN / "standards/assembly/v1/standard-final.json")
    final = _json(CHAIN / "templates/assembly/v1/template-final.json")
    candidate = _draft(final)
    candidate.update(templateId="model-id", templateVersion="v9")
    candidate["fieldConfigs"][0]["standardTarget"]["standardProjection"].update(
        required=False, dataType="String"
    )
    original_expression = deepcopy(candidate["fieldConfigs"][0]["xmlKeyExpressions"])
    rules = load_rule_package(ROOT / "configuration-rules/v2")

    materialized = materialize_template_candidate(
        candidate,
        standard_final=standard,
        rule_package=rules,
        direction="ASSEMBLY",
        template_id="b2e0061-assembly-common",
        template_version="v1",
    )
    result = validate_interface_template(
        materialized, standard=standard, rule_package=rules
    )

    config = materialized["fieldConfigs"][0]
    assert config["standardTarget"]["standardProjection"]["required"] is True
    assert config["standardTarget"]["standardProjection"]["dataType"] == "Object"
    assert config["xmlKeyExpressions"] == original_expression
    assert result["summary"]["errorCount"] == 0
