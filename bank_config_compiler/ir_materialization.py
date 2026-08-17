from __future__ import annotations

import re
from collections import defaultdict
from copy import deepcopy
from typing import Any

from .artifact_validation import content_hash
from .configuration_rules import RulePackage
from .docir_draft import FIELDS_HEADER, METADATA_HEADER
from .draft_generation import DraftGenerationError


SCHEMAIR_MATERIALIZER_CONTRACT = "schemair-materializer/v2"
STANDARD_MATERIALIZER_CONTRACT = "interface-standard-materializer/v1"
TEMPLATE_MATERIALIZER_CONTRACT = "interface-template-materializer/v1"

_SCHEMA_DATA_TYPES = {
    "String": "string",
    "Boolean": "boolean",
    "Date": "date",
    "Decimal": "decimal",
    "Object": "object",
}

_SCHEMAIR_CANDIDATE_TOP_LEVEL_PROPERTIES = {"envelope", "messages"}
_SCHEMAIR_CANDIDATE_ENVELOPE_PROPERTIES = {"description", "fields"}
_SCHEMAIR_CANDIDATE_MESSAGE_PROPERTIES = {
    "functionType",
    "xmlEncoding",
    "xmlEncodingEvidence",
    "description",
    "fields",
    "conditionalConstraints",
}
_SCHEMAIR_CANDIDATE_FIELD_PROPERTY_ORDER = (
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
_SCHEMAIR_CANDIDATE_FIELD_PROPERTIES = set(_SCHEMAIR_CANDIDATE_FIELD_PROPERTY_ORDER)
_SCHEMAIR_CANDIDATE_CONDITION_PROPERTY_ORDER = (
    "controllingFieldPath",
    "operator",
    "literal",
    "targetFieldPath",
    "effect",
    "sourceText",
    "evidence",
)
_SCHEMAIR_CANDIDATE_CONDITION_PROPERTIES = set(
    _SCHEMAIR_CANDIDATE_CONDITION_PROPERTY_ORDER
)
_SCHEMAIR_CANDIDATE_LENGTH_PROPERTIES = {"min", "max", "raw"}
_SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES = {"kind", "note"}
_SCHEMAIR_CANDIDATE_ENCODING_EVIDENCE_PROPERTIES = {
    "sourceKind",
    "sourceRef",
    "observedValue",
    "disposition",
    "reviewNote",
}


def materialize_schemair_candidate(
    candidate: Any,
    *,
    docir_final: str,
    schema_id: str,
    schema_version: str,
    interface_code: str,
) -> dict[str, Any]:
    candidate_object = _require_candidate_object(
        candidate,
        label="SchemaIR candidate",
        allowed=_SCHEMAIR_CANDIDATE_TOP_LEVEL_PROPERTIES,
        required=_SCHEMAIR_CANDIDATE_TOP_LEVEL_PROPERTIES,
    )
    structure = parse_final_docir_structure(docir_final)
    interface = structure["interface"]
    if interface.get("Interface Code") != interface_code:
        raise DraftGenerationError(
            "Final DocIR Interface Code does not match the locked task identity"
        )

    artifact = {
        "contractVersion": "schemair/v2",
        "schemaId": schema_id,
        "schemaVersion": schema_version,
        "status": "DRAFT",
        "review": _pending_review(),
        "interfaceCode": interface_code,
        "interfaceName": interface.get("Interface Name", ""),
        "messageFormat": "XML",
        "protocolVersion": interface.get("Version", ""),
        "sourceDocument": "raw-doc.md",
    }
    candidate_envelope = _require_candidate_object(
        candidate_object.get("envelope"),
        label="SchemaIR candidate envelope",
        allowed=_SCHEMAIR_CANDIDATE_ENVELOPE_PROPERTIES,
        required=_SCHEMAIR_CANDIDATE_ENVELOPE_PROPERTIES,
    )
    envelope_structure = structure["envelope"]
    envelope = {
        "rootPath": envelope_structure["rootPath"],
        "description": deepcopy(candidate_envelope["description"]),
        "fields": _materialize_schema_fields(
            candidate_envelope["fields"],
            envelope_structure["fields"],
            label="envelope.fields",
        ),
    }
    artifact["envelope"] = envelope

    messages = candidate_object.get("messages")
    if not isinstance(messages, list):
        raise DraftGenerationError("SchemaIR candidate messages must be an array")
    by_direction: dict[str, dict[str, Any]] = {}
    for index, message in enumerate(messages):
        message_object = _require_candidate_object(
            message,
            label=f"SchemaIR candidate messages[{index}]",
            allowed=_SCHEMAIR_CANDIDATE_MESSAGE_PROPERTIES,
            required=_SCHEMAIR_CANDIDATE_MESSAGE_PROPERTIES,
        )
        direction = message_object.get("functionType")
        if direction not in {"ASSEMBLY", "PARSE"} or direction in by_direction:
            raise DraftGenerationError(
                "SchemaIR candidate must contain one unambiguous ASSEMBLY and PARSE message"
            )
        by_direction[direction] = message_object
    if set(by_direction) != {"ASSEMBLY", "PARSE"}:
        raise DraftGenerationError(
            "SchemaIR candidate must contain exactly ASSEMBLY and PARSE messages"
        )
    materialized_messages: list[dict[str, Any]] = []
    for direction in ("ASSEMBLY", "PARSE"):
        candidate_message = by_direction[direction]
        message_structure = structure[direction.lower()]
        message = {
            "functionType": direction,
            "messageName": message_structure["messageName"],
            "rootPath": message_structure["rootPath"],
            "xmlEncoding": deepcopy(candidate_message["xmlEncoding"]),
            "xmlEncodingEvidence": _materialize_schema_encoding_evidence(
                candidate_message["xmlEncodingEvidence"],
                label=f"messages[{direction}].xmlEncodingEvidence",
            ),
            "description": deepcopy(candidate_message["description"]),
            "fields": _materialize_schema_fields(
                candidate_message["fields"],
                message_structure["fields"],
                label=f"messages[{direction}].fields",
            ),
            "conditionalConstraints": _materialize_schema_conditions(
                candidate_message["conditionalConstraints"],
                label=f"messages[{direction}].conditionalConstraints",
            ),
        }
        materialized_messages.append(message)
    artifact["messages"] = materialized_messages
    inherited_message_parents = {
        field["parentPath"]
        for message in materialized_messages
        for field in message["fields"]
    }
    for field in envelope["fields"]:
        if field["path"] in inherited_message_parents:
            field["hasChildren"] = True
    return artifact


def materialize_standard_candidate(
    candidate: Any,
    *,
    schemair_final: dict[str, Any],
    rule_package: RulePackage,
    direction: str,
    standard_id: str,
    standard_version: str,
) -> dict[str, Any]:
    artifact = _object_copy(candidate, label="InterfaceStandardIR candidate")
    message = _schema_message(schemair_final, direction)
    source_fields = [
        field
        for section in (schemair_final["envelope"]["fields"], message["fields"])
        for field in section
        if field.get("nodeKind") != "XML_ATTRIBUTE"
    ]
    attributes = {
        field["path"]: field
        for section in (schemair_final["envelope"]["fields"], message["fields"])
        for field in section
        if field.get("nodeKind") == "XML_ATTRIBUTE"
    }
    supplied = artifact.get("fields")
    if not isinstance(supplied, list):
        raise DraftGenerationError("InterfaceStandardIR candidate fields must be an array")
    by_source = _unique_by(
        supplied,
        key="schemaIrFieldPath",
        label="InterfaceStandardIR candidate fields",
    )
    expected_paths = {field["path"] for field in source_fields}
    if set(by_source) != expected_paths:
        raise DraftGenerationError(
            "InterfaceStandardIR candidate field coverage must exactly match Final SchemaIR XML elements"
        )

    sibling_sequence: defaultdict[str, int] = defaultdict(int)
    materialized_fields: list[dict[str, Any]] = []
    for source in source_fields:
        path = source["path"]
        field = deepcopy(by_source[path])
        parent = source["parentPath"]
        sibling_sequence[parent] += 1
        xml_keys = [
            {
                "name": attribute["fieldName"],
                "schemaIrFieldPath": attribute_path,
            }
            for attribute_path, attribute in attributes.items()
            if attribute.get("parentPath") == path
        ]
        field.update(
            {
                "fieldId": _field_id(
                    schemair_final["interfaceCode"], direction, path
                ),
                "sequence": sibling_sequence[parent],
                "fieldName": source["fieldName"],
                "parentPath": parent,
                "fullPath": path,
                "xmlKeys": xml_keys,
                "schemaIrFieldPath": path,
            }
        )
        materialized_fields.append(field)
    artifact.update(
        {
            "contractVersion": "interface-standard/v1",
            "standardId": standard_id,
            "standardVersion": standard_version,
            "status": "DRAFT",
            "review": _pending_review(),
            "interfaceCode": schemair_final["interfaceCode"],
            "direction": direction,
            "schemaIrRef": {
                "schemaId": schemair_final["schemaId"],
                "schemaVersion": schemair_final["schemaVersion"],
                "contractVersion": schemair_final["contractVersion"],
                "contentHash": content_hash(schemair_final),
            },
            "rulePackageVersion": rule_package.version,
            "xmlEncodingRef": {
                "functionType": direction,
                "value": message["xmlEncoding"],
            },
            "fields": materialized_fields,
        }
    )
    return artifact


def materialize_template_candidate(
    candidate: Any,
    *,
    standard_final: dict[str, Any],
    rule_package: RulePackage,
    direction: str,
    template_id: str,
    template_version: str,
) -> dict[str, Any]:
    artifact = _object_copy(candidate, label="InterfaceTemplateIR candidate")
    supplied = artifact.get("fieldConfigs")
    if not isinstance(supplied, list):
        raise DraftGenerationError("InterfaceTemplateIR candidate fieldConfigs must be an array")
    standard_fields = standard_final.get("fields")
    if not isinstance(standard_fields, list):
        raise DraftGenerationError("Final InterfaceStandardIR fields must be an array")
    expected_ids = {field["fieldId"] for field in standard_fields}
    configs: list[dict[str, Any]] = []
    if direction == "ASSEMBLY":
        by_standard = _unique_by_nested(
            supplied,
            container="standardTarget",
            key="standardFieldRef",
            label="InterfaceTemplateIR candidate fieldConfigs",
        )
        if not by_standard or not set(by_standard).issubset(expected_ids):
            raise DraftGenerationError(
                "InterfaceTemplateIR candidate configs must uniquely reference Final Standard fields"
            )
        for standard_field in standard_fields:
            field_id = standard_field["fieldId"]
            if field_id not in by_standard:
                continue
            config = deepcopy(by_standard[field_id])
            config["standardTarget"] = {
                "standardFieldRef": field_id,
                "standardProjection": {
                    "required": standard_field["required"],
                    "length": deepcopy(standard_field["lengthLimit"]),
                    "dataType": standard_field["dataType"],
                },
            }
            configs.append(config)
    else:
        # PARSE 的 parseTarget 是目标系统语义，不能从 Standard 反推；只锁定依赖身份并保留 Human 候选顺序。
        configs = deepcopy(supplied)
    artifact.update(
        {
            "contractVersion": "interface-template/v1",
            "templateId": template_id,
            "templateVersion": template_version,
            "status": "DRAFT",
            "interfaceCode": standard_final["interfaceCode"],
            "direction": direction,
            "standardRef": {
                "standardId": standard_final["standardId"],
                "standardVersion": standard_final["standardVersion"],
                "contentHash": content_hash(standard_final),
            },
            "rulePackageVersion": rule_package.version,
            "fieldConfigs": configs,
            "review": _pending_review(),
        }
    )
    return artifact


def parse_final_docir_structure(content: str) -> dict[str, Any]:
    if not isinstance(content, str) or not content:
        raise DraftGenerationError("Final DocIR must be non-empty text")
    headings = {
        "interface": "# Interface",
        "envelope": "# Envelope",
        "assembly": "# Message: ASSEMBLY",
        "parse": "# Message: PARSE",
    }
    result: dict[str, Any] = {}
    for name, heading in headings.items():
        section = _markdown_section(content, heading)
        result[name] = {"metadata": _metadata_table(section)}
        if name != "interface":
            root_index = {"envelope": "1", "assembly": "2", "parse": "3"}[name]
            root_path = _canonical_root_path(
                result[name]["metadata"].get("Root Path", "")
            )
            result[name].update(
                {
                    "rootPath": root_path,
                    "messageName": result[name]["metadata"].get("Message Name", ""),
                    "fields": _docir_field_structure(
                        section, root_index=root_index, root_path=root_path
                    ),
                }
            )
    result["interface"] = result["interface"]["metadata"]
    return result


def _materialize_schema_fields(
    supplied_value: Any,
    structure: list[dict[str, Any]],
    *,
    label: str,
) -> list[dict[str, Any]]:
    if not isinstance(supplied_value, list) or len(supplied_value) != len(structure):
        raise DraftGenerationError(
            f"{label} must exactly cover the Final DocIR semantic tree"
        )
    result: list[dict[str, Any]] = []
    for position, (supplied_value_item, derived) in enumerate(
        zip(supplied_value, structure, strict=True)
    ):
        supplied = _require_object(
            supplied_value_item, label=f"{label}[{position}]"
        )
        required_properties = set(_SCHEMAIR_CANDIDATE_FIELD_PROPERTIES)
        if derived["dataType"] == "object":
            required_properties.add("required")
        _require_candidate_properties(
            supplied,
            label=f"{label}[{position}]",
            allowed=required_properties,
            required=required_properties,
        )
        if supplied.get("fieldName") != derived["fieldName"]:
            raise DraftGenerationError(
                f"{label}[{position}] fieldName does not match Final DocIR preorder"
            )
        materialized = {
            name: deepcopy(supplied[name])
            for name in _SCHEMAIR_CANDIDATE_FIELD_PROPERTY_ORDER
        }
        derived = dict(derived)
        maximum = derived.pop("_maximumOccurs")
        if derived["dataType"] == "object":
            # DocIR 的 Object.Required 是 N/A；容器出现性属于 SchemaIR 的独立语义，
            # 不能从内部必填叶子反推，但 maximum 仍必须受 Final DocIR Mult. 约束。
            required = supplied.get("required")
            if not isinstance(required, bool):
                raise DraftGenerationError(
                    f"{label}[{position}] Object required must be proposed as a boolean"
                )
            materialized.update(derived)
            materialized["required"] = required
            materialized["occurs"] = _schema_occurs(1 if required else 0, maximum)
        else:
            materialized.update(derived)
        _require_candidate_object(
            materialized["length"],
            label=f"{label}[{position}].length",
            allowed=_SCHEMAIR_CANDIDATE_LENGTH_PROPERTIES,
            required=_SCHEMAIR_CANDIDATE_LENGTH_PROPERTIES,
        )
        _require_candidate_object(
            materialized["evidence"],
            label=f"{label}[{position}].evidence",
            allowed=_SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
            required=_SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
        )
        result.append(materialized)
    return result


def _materialize_schema_encoding_evidence(value: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DraftGenerationError(f"{label} must be an array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        evidence = _require_candidate_object(
            item,
            label=f"{label}[{index}]",
            allowed=_SCHEMAIR_CANDIDATE_ENCODING_EVIDENCE_PROPERTIES,
            required=_SCHEMAIR_CANDIDATE_ENCODING_EVIDENCE_PROPERTIES,
        )
        result.append(deepcopy(evidence))
    return result


def _materialize_schema_conditions(value: Any, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise DraftGenerationError(f"{label} must be an array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        condition = _require_candidate_object(
            item,
            label=f"{label}[{index}]",
            allowed=_SCHEMAIR_CANDIDATE_CONDITION_PROPERTIES,
            required=_SCHEMAIR_CANDIDATE_CONDITION_PROPERTIES,
        )
        _require_candidate_object(
            condition["evidence"],
            label=f"{label}[{index}].evidence",
            allowed=_SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
            required=_SCHEMAIR_CANDIDATE_EVIDENCE_PROPERTIES,
        )
        materialized = {
            name: deepcopy(condition[name])
            for name in _SCHEMAIR_CANDIDATE_CONDITION_PROPERTY_ORDER
        }
        materialized["review"] = _pending_review()
        result.append(materialized)
    return result


def _require_candidate_object(
    value: Any,
    *,
    label: str,
    allowed: set[str],
    required: set[str],
) -> dict[str, Any]:
    result = _require_object(value, label=label)
    _require_candidate_properties(
        result,
        label=label,
        allowed=allowed,
        required=required,
    )
    return result


def _require_candidate_properties(
    value: dict[str, Any],
    *,
    label: str,
    allowed: set[str],
    required: set[str],
) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - allowed)
    if not missing and not unknown:
        return
    details: list[str] = []
    if missing:
        details.append(f"missing properties: {', '.join(missing)}")
    if unknown:
        details.append(f"unknown properties: {', '.join(unknown)}")
    raise DraftGenerationError(f"{label} has invalid properties ({'; '.join(details)})")


def _docir_field_structure(
    section: str,
    *,
    root_index: str,
    root_path: str,
) -> list[dict[str, Any]]:
    lines = section.splitlines()
    try:
        start = lines.index(FIELDS_HEADER)
    except ValueError as exc:
        raise DraftGenerationError("Final DocIR section is missing its Fields table") from exc
    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = _split_row(line)
        if len(cells) != 9:
            raise DraftGenerationError("Final DocIR field row must contain nine cells")
        rows.append(cells)
    paths: dict[str, str] = {}
    fields: list[dict[str, Any]] = []
    child_counts: defaultdict[str, int] = defaultdict(int)
    for cells in rows:
        index = cells[0]
        item = cells[2].lstrip("\u3000").strip("`")
        if index == root_index:
            path = root_path
            parent_path = root_path.rsplit(".", 1)[0]
        else:
            parent_index = index.rsplit(".", 1)[0]
            parent_path = paths.get(parent_index)
            if parent_path is None:
                raise DraftGenerationError(
                    f"Final DocIR field {index} has no materialized parent"
                )
            path = f"{parent_path}.{item}"
        paths[index] = path
        child_counts[parent_path] += 1
        multiplicity = cells[3]
        _, maximum = _occurs(multiplicity)
        maximum = 1 if maximum is None else maximum
        data_type = _SCHEMA_DATA_TYPES.get(cells[4], "string")
        required_value = cells[5]
        if data_type == "object":
            if required_value:
                raise DraftGenerationError(
                    f"Final DocIR Object field {index} Required must be empty"
                )
        elif required_value not in {"Y", "N", "C"}:
            raise DraftGenerationError(
                f"Final DocIR scalar field {index} Required must be Y, N or C"
            )
        multiple = maximum == "n" or (
            isinstance(maximum, int) and maximum > 1
        )
        field = {
                "path": path,
                "fieldName": item,
                "parentPath": parent_path,
                "level": path.count("."),
                "nodeKind": (
                    "XML_ATTRIBUTE" if item.startswith("@") else "XML_ELEMENT"
                ),
                "dataType": data_type,
                "multiple": multiple,
                "hasChildren": False,
                "_maximumOccurs": maximum,
            }
        if data_type != "object":
            required = required_value == "Y"
            field["required"] = required
            field["occurs"] = _schema_occurs(1 if required else 0, maximum)
        fields.append(field)
    paths_with_children = {field["parentPath"] for field in fields}
    for field in fields:
        field["hasChildren"] = field["path"] in paths_with_children
    return fields


def _markdown_section(content: str, heading: str) -> str:
    lines = content.splitlines()
    if heading not in lines:
        raise DraftGenerationError(f"Final DocIR is missing section {heading}")
    start = lines.index(heading)
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("# ")),
        len(lines),
    )
    return "\n".join(lines[start:end])


def _metadata_table(section: str) -> dict[str, str]:
    lines = section.splitlines()
    if METADATA_HEADER not in lines:
        raise DraftGenerationError("Final DocIR section is missing Metadata table")
    start = lines.index(METADATA_HEADER)
    metadata: dict[str, str] = {}
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            if metadata:
                break
            continue
        cells = _split_row(line)
        if len(cells) != 3:
            break
        metadata[cells[0]] = cells[1]
    return metadata


def _split_row(line: str) -> list[str]:
    cells = re.split(r"(?<!\\)\|", line[1:-1])
    return [cell.strip(" ").replace("\\|", "|") for cell in cells]


def _canonical_root_path(value: str) -> str:
    value = value.strip()
    if not value:
        raise DraftGenerationError("Final DocIR Root Path must be non-empty")
    if value == "Root" or value.startswith("Root."):
        return value
    return f"Root.{value.replace('/', '.')}"


def _occurs(value: str) -> tuple[int | None, int | str | None]:
    match = re.fullmatch(r"\[(\d+)\.\.(\d+|\*)\]", value)
    if match is None:
        return None, None
    maximum: int | str = "n" if match.group(2) == "*" else int(match.group(2))
    return int(match.group(1)), maximum


def _schema_occurs(minimum: int, maximum: int | str) -> str:
    return f"{minimum}..{maximum}"


def _schema_message(schemair: dict[str, Any], direction: str) -> dict[str, Any]:
    messages = schemair.get("messages")
    if not isinstance(messages, list):
        raise DraftGenerationError("Final SchemaIR messages must be an array")
    matches = [message for message in messages if message.get("functionType") == direction]
    if len(matches) != 1:
        raise DraftGenerationError(
            "Final SchemaIR must contain exactly one selected direction"
        )
    return matches[0]


def _unique_by(values: list[Any], *, key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for position, value in enumerate(values):
        item = _require_object(value, label=f"{label}[{position}]")
        identity = item.get(key)
        if not isinstance(identity, str) or not identity or identity in result:
            raise DraftGenerationError(f"{label} has invalid or duplicate {key}")
        result[identity] = item
    return result


def _unique_by_nested(
    values: list[Any],
    *,
    container: str,
    key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for position, value in enumerate(values):
        item = _require_object(value, label=f"{label}[{position}]")
        nested = _require_object(item.get(container), label=f"{label}[{position}].{container}")
        identity = nested.get(key)
        if not isinstance(identity, str) or not identity or identity in result:
            raise DraftGenerationError(f"{label} has invalid or duplicate {container}.{key}")
        result[identity] = item
    return result


def _object_copy(value: Any, *, label: str) -> dict[str, Any]:
    return deepcopy(_require_object(value, label=label))


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DraftGenerationError(f"{label} must be an object")
    return value


def _pending_review() -> dict[str, Any]:
    return {"status": "PENDING", "reviewer": None, "reviewedAt": None, "note": None}


def _field_id(interface_code: str, direction: str, path: str) -> str:
    relative_path = path.removeprefix("Root.")
    suffix = re.sub(r"[^a-z0-9]+", "-", relative_path.lower()).strip("-")
    return f"{interface_code}-{direction.lower()}-{suffix}"
