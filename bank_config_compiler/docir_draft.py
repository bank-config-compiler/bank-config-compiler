from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any


DOCIR_EXTRACTION_CONTRACT = "docir-extraction/v2"
DOCIR_SEMANTIC_CANDIDATE_CONTRACT = "docir-semantic-candidate/v2"
DOCIR_MATERIALIZER_CONTRACT = "docir-semantic-materializer/v4"
DOCIR_VALIDATION_RESULT_CONTRACT = "docir-validation-result/v1"
INTERFACE_ENVELOPE_SEGMENT_CONTRACT = "docir-interface-envelope-segment/v2"
MESSAGES_OUTLINE_SEGMENT_CONTRACT = "docir-messages-outline-segment/v1"
FIELD_DETAILS_SEGMENT_CONTRACT = "docir-field-details-segment/v2"
SEMANTIC_INTERFACE_ENVELOPE_SEGMENT_CONTRACT = "docir-interface-envelope-tree-segment/v2"
SEMANTIC_MESSAGES_TREE_SEGMENT_CONTRACT = "docir-messages-tree-segment/v1"
SEMANTIC_FIELD_DETAILS_SEGMENT_CONTRACT = "docir-field-semantics-segment/v2"
METADATA_HEADER = "| Key | Value | Review Note |"
FIELDS_HEADER = "| Index | Or | Message Item | Mult. | Type | Required | 说明 | 校验点 | Review |"
LEGACY_FIELDS_HEADER = (
    "| Index | Or | Message Item | Mult. | Type | Required | 说明 | "
    "前置机校验点/格式 | 接口平台校验点 | Review |"
)
UNKNOWN_REVIEW_MARKER = "原文未说明，待人工确认"
REQUIRED_UNKNOWN_REVIEW_MARKER = "Required 原文未说明，待人工确认"
REJECTED_MULTIPLICITY_REVIEW_MARKER = "候选 Mult. 不符合规范，已留空，待人工确认"
NORMALIZED_TYPE_REVIEW_MARKER = "候选 Type 与结构规范不一致，已按规范物化，待人工复核"
NO_EXPLICIT_CONDITIONS = "原文未提供可确认条件。"
_FIXED_REVIEW_CHECKLIST = (
    "核对 Interface、Envelope、ASSEMBLY、PARSE 的字段和父子层级是否完整忠实于 raw-doc。",
    "核对 Source Context 的适用范围，确认通用 XML 示例或其他交易代码未污染目标交易字段。",
    "核对所有冲突、空值和“原文未说明”项均已显式保留，未被模型静默推断。",
    "核对 ASSEMBLY 与 PARSE Conditions 是否完整且仅包含 raw-doc 明确表达的条件分支。",
)

_TOP_PROPERTIES = {
    "contractVersion",
    "interface",
    "sourceContext",
    "envelope",
    "assembly",
    "parse",
}
_METADATA_PROPERTIES = {"key", "value", "reviewNote"}
_FIELD_PROPERTIES = {
    "index",
    "or",
    "item",
    "multiplicity",
    "type",
    "required",
    "description",
    "validation",
    "review",
}
_SEMANTIC_NODE_PROPERTIES = _FIELD_PROPERTIES - {"index", "item"}
_SEMANTIC_NODE_KINDS = {"XML_ELEMENT", "XML_ATTRIBUTE"}
_METADATA_KEYS = {
    "interface": (
        "Interface Code",
        "Interface Name",
        "Message Format",
        "Version",
        "Source Document",
    ),
    "envelope": ("Envelope Name", "Root Path", "Applies To", "Evidence Scope"),
    "assembly": ("Message Name", "Function Type", "Root Path", "Description"),
    "parse": ("Message Name", "Function Type", "Root Path", "Description"),
}
_SECTION_PROPERTIES = {
    "interface": {"metadata"},
    "envelope": {"metadata", "fields"},
    "assembly": {"metadata", "fields", "conditions"},
    "parse": {"metadata", "fields", "conditions"},
}
_FIELD_TYPES = {"", "String", "Boolean", "Date", "Decimal", "Object"}
_REQUIRED_VALUES = {"", "Y", "N", "C"}
_ITEM_PATTERN = re.compile(r"^@?[^\s<>`|]+$")
_INDEX_SUFFIX_PATTERN = re.compile(r"^[1-9]\d*$")
_MULTIPLICITY_PATTERN = re.compile(r"^\[(0|[1-9]\d*)\.\.(0|[1-9]\d*|\*)\]$")
_OPTIONAL_EVIDENCE = re.compile(
    r"可空(?:字符串|字符)?|可选|\boptional\b|\bnullable\b", re.IGNORECASE
)
_DIRECT_REQUIRED_EVIDENCE = re.compile(
    r"非空(?:字符串|字符)?|(?:本字段|此项|该项)(?:为|是|需|需要|必须)?(?:必填|必输)"
    r"|^\s*(?:必填|必输|mandatory|non-empty)\s*$",
    re.IGNORECASE,
)
_CONDITIONAL_REQUIRED_EVIDENCE = re.compile(
    r"(?:当|若|如果)[^。；]*(?:此项|该项|本字段)[^。；]*(?:必填|必输|必须上送|不能为空|非空)"
    r"|(?<!非空)(?<!不为空)时[^。；]*(?:必填|必输|不能为空|且非空)",
    re.IGNORECASE,
)
_POSSIBLE_CROSS_FIELD_REQUIREMENT = re.compile(
    r"必须上送|需要上送|应上送|\brequired\b|\bmust\b", re.IGNORECASE
)
# 这里只做保守的表达形式门禁，避免普通字段校验污染 Conditions；
# 是否忠实来自 raw-doc 仍必须由 Human Review，代码不能据此创造或改写业务条件。
_EXPLICIT_CONDITION_BRANCH = re.compile(
    r"^(?:(?:如果|若|当|(?<!例)如|在)[^。；]{1,160}?(?:则|时|情况下|，)[^。；]+"
    r"|[^，。；]{1,60}(?:为空|非空|不为空|为[^，。；]{1,40}|=[^，。；]{1,40})"
    r"(?:时|则|表示)[^。；]+"
    r"|\bif\b[^.;]{1,160}(?:\bthen\b|,)[^.;]+)(?:[。；.;]|$)",
    re.IGNORECASE,
)


class DocIRDraftError(ValueError):
    """Raised when structured DocIR extraction or its rendered wire is invalid."""


def materialize_docir_semantic_candidate(
    value: Any, *, interface_code: str | None = None
) -> dict[str, Any]:
    """Project one structurally unambiguous ordered semantic tree to DocIR wire fields."""

    candidate = _require_object(value, label="DocIR semantic candidate")
    _require_exact_properties(candidate, _TOP_PROPERTIES, label="DocIR semantic candidate")
    if candidate.get("contractVersion") != DOCIR_SEMANTIC_CANDIDATE_CONTRACT:
        raise DocIRDraftError(
            "DocIR semantic candidate contractVersion must be "
            f"{DOCIR_SEMANTIC_CANDIDATE_CONTRACT}"
        )

    interface = _require_object(
        candidate.get("interface"), label="DocIR semantic candidate interface"
    )
    _require_exact_properties(
        interface, {"metadata"}, label="DocIR semantic candidate interface"
    )
    extraction: dict[str, Any] = {
        "contractVersion": DOCIR_EXTRACTION_CONTRACT,
        "interface": {
            "metadata": _validated_metadata(
                interface.get("metadata"), section_name="interface"
            )
        },
        "sourceContext": _require_string_array(
            candidate.get("sourceContext"),
            label="DocIR semantic candidate sourceContext",
        ),
    }
    if interface_code is not None:
        _lock_interface_code(extraction["interface"]["metadata"], interface_code)
    for section_name, root_index in (
        ("envelope", "1"),
        ("assembly", "2"),
        ("parse", "3"),
    ):
        extraction[section_name] = _materialized_semantic_section(
            candidate,
            section_name=section_name,
            root_index=root_index,
        )
    return _validated_extraction(extraction)


def _lock_interface_code(metadata: list[dict[str, str]], interface_code: str) -> None:
    if not isinstance(interface_code, str) or not interface_code:
        raise DocIRDraftError("locked Interface Code must be a non-empty string")
    for row in metadata:
        if row["key"] == "Interface Code":
            # Interface Code 属于 task identity；候选值及其不确定性不能覆盖可信请求身份。
            row["value"] = interface_code
            row["reviewNote"] = ""
            return
    raise DocIRDraftError("DocIR interface metadata is missing Interface Code")


def validate_docir_interface_envelope_tree_segment(value: Any) -> dict[str, Any]:
    segment = _require_object(value, label="DocIR interface-envelope tree segment")
    _require_exact_properties(
        segment,
        {"contractVersion", "interface", "sourceContext", "envelope"},
        label="DocIR interface-envelope tree segment",
    )
    if segment.get("contractVersion") != SEMANTIC_INTERFACE_ENVELOPE_SEGMENT_CONTRACT:
        raise DocIRDraftError(
            "DocIR interface-envelope tree segment contractVersion must be "
            f"{SEMANTIC_INTERFACE_ENVELOPE_SEGMENT_CONTRACT}"
        )
    interface = _require_object(
        segment.get("interface"), label="DocIR interface-envelope tree segment interface"
    )
    _require_exact_properties(
        interface,
        {"metadata"},
        label="DocIR interface-envelope tree segment interface",
    )
    envelope = _require_object(
        segment.get("envelope"), label="DocIR interface-envelope tree segment envelope"
    )
    _require_exact_properties(
        envelope,
        {"metadata", "nodes"},
        label="DocIR interface-envelope tree segment envelope",
    )
    return {
        "contractVersion": SEMANTIC_INTERFACE_ENVELOPE_SEGMENT_CONTRACT,
        "interface": {
            "metadata": _validated_metadata(
                interface.get("metadata"), section_name="interface"
            )
        },
        "sourceContext": _require_string_array(
            segment.get("sourceContext"),
            label="DocIR interface-envelope tree segment sourceContext",
        ),
        "envelope": {
            "metadata": _validated_metadata(
                envelope.get("metadata"), section_name="envelope"
            ),
            "nodes": _normalize_external_semantic_tree(
                envelope.get("nodes"), section_name="envelope", include_semantics=True
            ),
        },
    }


def validate_docir_messages_tree_segment(value: Any) -> dict[str, Any]:
    segment = _require_object(value, label="DocIR messages tree segment")
    _require_exact_properties(
        segment,
        {"contractVersion", "assembly", "parse"},
        label="DocIR messages tree segment",
    )
    if segment.get("contractVersion") != SEMANTIC_MESSAGES_TREE_SEGMENT_CONTRACT:
        raise DocIRDraftError(
            "DocIR messages tree segment contractVersion must be "
            f"{SEMANTIC_MESSAGES_TREE_SEGMENT_CONTRACT}"
        )
    result: dict[str, Any] = {"contractVersion": SEMANTIC_MESSAGES_TREE_SEGMENT_CONTRACT}
    for section_name in ("assembly", "parse"):
        label = f"DocIR messages tree segment {section_name}"
        section = _require_object(segment.get(section_name), label=label)
        _require_exact_properties(
            section, {"metadata", "conditions", "nodes"}, label=label
        )
        result[section_name] = {
            "metadata": _validated_metadata(
                section.get("metadata"), section_name=section_name
            ),
            "conditions": _require_string_array(
                section.get("conditions"), label=f"{label}.conditions"
            ),
            "nodes": _normalize_external_semantic_tree(
                section.get("nodes"), section_name=section_name, include_semantics=False
            ),
        }
    return result


def build_docir_semantic_field_batches(
    nodes: Any,
    *,
    batch_size: int,
) -> list[list[dict[str, str]]]:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise DocIRDraftError("DocIR field batch size must be a positive integer")
    outline: list[dict[str, str]] = []

    def visit(node: dict[str, Any]) -> None:
        outline.append(
            {
                "selector": node["selector"],
                "item": node["item"],
                "nodeKind": node["nodeKind"],
            }
        )
        for child in node["children"]:
            visit(child)

    if not isinstance(nodes, list) or len(nodes) != 1:
        raise DocIRDraftError("DocIR semantic nodes must contain exactly one root")
    visit(nodes[0])
    return [outline[index : index + batch_size] for index in range(0, len(outline), batch_size)]


def validate_docir_semantic_field_details_segment(
    value: Any,
    *,
    direction: str,
    batch_index: int,
    expected_outline: list[dict[str, str]],
) -> dict[str, Any]:
    segment = _require_object(value, label="DocIR field-semantics segment")
    _require_exact_properties(
        segment,
        {"contractVersion", "direction", "batchIndex", "fields"},
        label="DocIR field-semantics segment",
    )
    if segment.get("contractVersion") != SEMANTIC_FIELD_DETAILS_SEGMENT_CONTRACT:
        raise DocIRDraftError(
            "DocIR field-semantics segment contractVersion must be "
            f"{SEMANTIC_FIELD_DETAILS_SEGMENT_CONTRACT}"
        )
    if direction not in {"ASSEMBLY", "PARSE"} or segment.get("direction") != direction:
        raise DocIRDraftError("DocIR field-semantics direction does not match the request")
    if isinstance(batch_index, bool) or not isinstance(batch_index, int) or batch_index <= 0:
        raise DocIRDraftError("DocIR field-semantics batch index must be a positive integer")
    if segment.get("batchIndex") != batch_index:
        raise DocIRDraftError("DocIR field-semantics batch index does not match the request")
    fields_value = segment.get("fields")
    if not isinstance(fields_value, list) or not fields_value:
        raise DocIRDraftError("DocIR field-semantics fields must be a non-empty array")
    if len(fields_value) != len(expected_outline):
        raise DocIRDraftError("DocIR field-semantics fields do not exactly cover target selectors")

    fields: list[dict[str, str]] = []
    for position, (row_value, expected) in enumerate(
        zip(fields_value, expected_outline, strict=True)
    ):
        label = f"DocIR field-semantics fields[{position}]"
        row = _require_object(row_value, label=label)
        allowed = {"selector"} | _SEMANTIC_NODE_PROPERTIES
        missing = {"selector"} - set(row)
        unknown = set(row) - allowed
        if missing or unknown:
            detail: list[str] = []
            if missing:
                detail.append("missing properties: selector")
            if unknown:
                detail.append("unknown properties: " + ", ".join(sorted(unknown)))
            raise DocIRDraftError(f"{label} has invalid properties ({'; '.join(detail)})")
        selector = _require_string(
            row.get("selector"), label=f"{label}.selector", allow_empty=False
        )
        if selector != expected["selector"]:
            raise DocIRDraftError(
                "DocIR field-semantics fields do not exactly cover target selectors"
            )
        fields.append({"selector": selector, **_semantic_strings(row, label=label)})
    return {
        "contractVersion": SEMANTIC_FIELD_DETAILS_SEGMENT_CONTRACT,
        "direction": direction,
        "batchIndex": batch_index,
        "fields": fields,
    }


def merge_docir_semantic_segments(
    *,
    interface_envelope: Any,
    messages_tree: Any,
    assembly_details: list[Any],
    parse_details: list[Any],
    batch_size: int = 16,
) -> dict[str, Any]:
    envelope_segment = validate_docir_interface_envelope_tree_segment(interface_envelope)
    messages_segment = validate_docir_messages_tree_segment(messages_tree)
    detail_values = {"ASSEMBLY": assembly_details, "PARSE": parse_details}
    completed_nodes: dict[str, list[dict[str, Any]]] = {}

    for direction, section_name in (("ASSEMBLY", "assembly"), ("PARSE", "parse")):
        expected_batches = build_docir_semantic_field_batches(
            messages_segment[section_name]["nodes"], batch_size=batch_size
        )
        supplied_batches = detail_values[direction]
        if len(supplied_batches) != len(expected_batches):
            raise DocIRDraftError(
                f"DocIR {direction} detail batches do not exactly cover the semantic tree"
            )
        semantics_by_selector: dict[str, dict[str, str]] = {}
        for batch_index, (supplied, expected) in enumerate(
            zip(supplied_batches, expected_batches, strict=True), start=1
        ):
            validated = validate_docir_semantic_field_details_segment(
                supplied,
                direction=direction,
                batch_index=batch_index,
                expected_outline=expected,
            )
            for row in validated["fields"]:
                semantics_by_selector[row["selector"]] = {
                    key: row[key] for key in _SEMANTIC_NODE_PROPERTIES
                }
        completed_nodes[section_name] = _attach_semantics(
            messages_segment[section_name]["nodes"], semantics_by_selector
        )

    return {
        "contractVersion": DOCIR_SEMANTIC_CANDIDATE_CONTRACT,
        "interface": envelope_segment["interface"],
        "sourceContext": envelope_segment["sourceContext"],
        "envelope": envelope_segment["envelope"],
        "assembly": {
            "metadata": messages_segment["assembly"]["metadata"],
            "conditions": messages_segment["assembly"]["conditions"],
            "nodes": completed_nodes["assembly"],
        },
        "parse": {
            "metadata": messages_segment["parse"]["metadata"],
            "conditions": messages_segment["parse"]["conditions"],
            "nodes": completed_nodes["parse"],
        },
    }


def _normalize_external_semantic_tree(
    value: Any,
    *,
    section_name: str,
    include_semantics: bool,
) -> list[dict[str, Any]]:
    label = f"DocIR {section_name} semantic nodes"
    if not isinstance(value, list) or len(value) != 1:
        raise DocIRDraftError(f"{label} must contain exactly one root")
    visited: set[int] = set()

    def normalize(node_value: Any, *, suffix: str, node_label: str) -> dict[str, Any]:
        node = _require_object(node_value, label=node_label)
        object_id = id(node)
        if object_id in visited:
            raise DocIRDraftError(
                f"{node_label} is reused by multiple parents or forms a cycle"
            )
        visited.add(object_id)
        required = {"item", "nodeKind", "children"}
        allowed = required | (_SEMANTIC_NODE_PROPERTIES if include_semantics else set())
        _require_exact_or_optional_properties(node, required, allowed, label=node_label)
        item = _require_string(
            node.get("item"), label=f"{node_label}.item", allow_empty=False
        )
        if not _ITEM_PATTERN.fullmatch(item):
            raise DocIRDraftError(f"{node_label}.item must be a plain XML item name")
        node_kind = _require_string(
            node.get("nodeKind"), label=f"{node_label}.nodeKind", allow_empty=False
        )
        if node_kind not in _SEMANTIC_NODE_KINDS:
            raise DocIRDraftError(
                f"{node_label}.nodeKind must be XML_ELEMENT or XML_ATTRIBUTE"
            )
        if (node_kind == "XML_ATTRIBUTE") != item.startswith("@"):
            raise DocIRDraftError(
                f"{node_label}.item and nodeKind must describe the same XML node kind"
            )
        children = node.get("children")
        if not isinstance(children, list):
            raise DocIRDraftError(f"{node_label}.children must be an ordered array")
        if node_kind == "XML_ATTRIBUTE" and children:
            raise DocIRDraftError(f"{node_label} attribute nodes cannot have children")
        sibling_names: set[str] = set()
        normalized_children: list[dict[str, Any]] = []
        for position, child_value in enumerate(children, start=1):
            child = _require_object(
                child_value, label=f"{node_label}.children[{position - 1}]"
            )
            child_name = _require_string(
                child.get("item"),
                label=f"{node_label}.children[{position - 1}].item",
                allow_empty=False,
            )
            if child_name in sibling_names:
                raise DocIRDraftError(
                    f"{node_label} has duplicate sibling item {child_name}"
                )
            sibling_names.add(child_name)
            normalized_children.append(
                normalize(
                    child,
                    suffix=f"{suffix}.{position}",
                    node_label=f"{node_label}.children[{position - 1}]",
                )
            )
        normalized: dict[str, Any] = {
            "selector": f"{section_name}:{suffix}",
            "item": item,
            "nodeKind": node_kind,
            "children": normalized_children,
        }
        if include_semantics:
            normalized.update(
                _normalized_semantics(
                    node,
                    label=node_label,
                    item=item,
                    node_kind=node_kind,
                    has_children=bool(normalized_children),
                )
            )
        return normalized

    root = normalize(value[0], suffix="1", node_label=f"{label}[0]")
    if root["nodeKind"] != "XML_ELEMENT":
        raise DocIRDraftError(f"{label}[0] root must be an XML_ELEMENT")
    return [root]


def _semantic_strings(value: dict[str, Any], *, label: str) -> dict[str, str]:
    return {
        name: _require_string(value.get(name, ""), label=f"{label}.{name}")
        for name in _SEMANTIC_NODE_PROPERTIES
    }


def _normalized_semantics(
    value: dict[str, Any],
    *,
    label: str,
    item: str,
    node_kind: str,
    has_children: bool,
) -> dict[str, str]:
    semantics = _semantic_strings(value, label=label)
    candidate_type = semantics["type"]
    canonical_type = _canonical_docir_type(
        candidate_type,
        item=item,
        node_kind=node_kind,
        has_children=has_children,
    )
    if candidate_type and candidate_type != canonical_type:
        semantics["review"] = _append_review_marker(
            semantics["review"], NORMALIZED_TYPE_REVIEW_MARKER
        )
    semantics["type"] = canonical_type

    # Mult. 只承载重复 Object；非重复范围被规范化为空。非法值保留专用 marker，
    # 使 Validator 能区分“无需填写”和“模型给出了不可接受的候选”。
    multiplicity = semantics["multiplicity"]
    try:
        _validate_multiplicity(multiplicity, label=f"{label}.multiplicity")
    except DocIRDraftError:
        semantics["multiplicity"] = ""
        semantics["review"] = _append_review_marker(
            semantics["review"], REJECTED_MULTIPLICITY_REVIEW_MARKER
        )
    else:
        maximum = _multiplicity_bounds(multiplicity)[1]
        repeated = maximum == "*" or isinstance(maximum, int) and maximum > 1
        if repeated and canonical_type != "Object":
            semantics["multiplicity"] = ""
            semantics["review"] = _append_review_marker(
                semantics["review"], REJECTED_MULTIPLICITY_REVIEW_MARKER
            )
        elif not repeated:
            semantics["multiplicity"] = ""

    if canonical_type == "Object":
        # Object 只是结构容器，没有独立字段值；其出现性在 SchemaIR 阶段单独审查，
        # 不能从子叶子的 Required 反推，也不能在 DocIR 中伪装成字段必填性。
        semantics["required"] = ""
    elif semantics["required"] not in _REQUIRED_VALUES:
        semantics["required"] = ""
    if canonical_type != "Object" and not semantics["required"]:
        semantics["review"] = _append_review_marker(
            semantics["review"], REQUIRED_UNKNOWN_REVIEW_MARKER
        )
    return semantics


def _canonical_docir_type(
    candidate_type: str,
    *,
    item: str,
    node_kind: str,
    has_children: bool,
) -> str:
    if has_children or item == "trans":
        return "Object"
    if node_kind in _SEMANTIC_NODE_KINDS and candidate_type in {
        "Boolean",
        "Date",
        "Decimal",
    }:
        return candidate_type
    return "String"


def _append_review_marker(review: str, marker: str) -> str:
    if marker in review:
        return review
    return f"{review}；{marker}" if review else marker


def _attach_semantics(
    nodes: list[dict[str, Any]], semantics_by_selector: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    def attach(node: dict[str, Any]) -> dict[str, Any]:
        selector = node["selector"]
        if selector not in semantics_by_selector:
            raise DocIRDraftError(
                f"DocIR semantic detail coverage is missing selector {selector}"
            )
        return {
            "selector": selector,
            "item": node["item"],
            "nodeKind": node["nodeKind"],
            "children": [attach(child) for child in node["children"]],
            **semantics_by_selector[selector],
        }

    return [attach(node) for node in nodes]


def _require_exact_or_optional_properties(
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
    *,
    label: str,
) -> None:
    missing = required - set(value)
    unknown = set(value) - allowed
    if missing or unknown:
        detail: list[str] = []
        if missing:
            detail.append("missing properties: " + ", ".join(sorted(missing)))
        if unknown:
            detail.append("unknown properties: " + ", ".join(sorted(unknown)))
        raise DocIRDraftError(f"{label} has invalid properties ({'; '.join(detail)})")


def _materialized_semantic_section(
    candidate: dict[str, Any],
    *,
    section_name: str,
    root_index: str,
) -> dict[str, Any]:
    label = f"DocIR semantic candidate {section_name}"
    section = _require_object(candidate.get(section_name), label=label)
    expected_properties = {"metadata", "nodes"}
    if section_name in {"assembly", "parse"}:
        expected_properties.add("conditions")
    _require_exact_properties(section, expected_properties, label=label)
    nodes = section.get("nodes")
    if not isinstance(nodes, list) or len(nodes) != 1:
        raise DocIRDraftError(f"{label}.nodes must contain exactly one root")

    fields: list[dict[str, str]] = []
    visited: set[int] = set()
    _materialize_semantic_node(
        nodes[0],
        section_name=section_name,
        selector_suffix="1",
        index=root_index,
        label=f"{label}.nodes[0]",
        fields=fields,
        visited=visited,
        is_root=True,
    )
    result: dict[str, Any] = {
        "metadata": _validated_metadata(
            section.get("metadata"), section_name=section_name
        ),
        "fields": fields,
    }
    if section_name in {"assembly", "parse"}:
        result["conditions"] = _require_string_array(
            section.get("conditions"), label=f"{label}.conditions"
        )
    return result


def _materialize_semantic_node(
    value: Any,
    *,
    section_name: str,
    selector_suffix: str,
    index: str,
    label: str,
    fields: list[dict[str, str]],
    visited: set[int],
    is_root: bool,
) -> None:
    node = _require_object(value, label=label)
    object_id = id(node)
    if object_id in visited:
        raise DocIRDraftError(f"{label} is reused by multiple parents or forms a cycle")
    visited.add(object_id)

    required = {"selector", "item", "nodeKind", "children"}
    unknown = set(node) - required - _SEMANTIC_NODE_PROPERTIES
    missing = required - set(node)
    if missing or unknown:
        detail: list[str] = []
        if missing:
            detail.append("missing properties: " + ", ".join(sorted(missing)))
        if unknown:
            detail.append("unknown properties: " + ", ".join(sorted(unknown)))
        raise DocIRDraftError(f"{label} has invalid properties ({'; '.join(detail)})")

    expected_selector = f"{section_name}:{selector_suffix}"
    selector = _require_string(
        node.get("selector"), label=f"{label}.selector", allow_empty=False
    )
    if selector != expected_selector:
        raise DocIRDraftError(
            f"{label}.selector must be the canonical selector {expected_selector}"
        )
    item = _require_string(node.get("item"), label=f"{label}.item", allow_empty=False)
    if not _ITEM_PATTERN.fullmatch(item):
        raise DocIRDraftError(f"{label}.item must be a plain XML item name")
    node_kind = _require_string(
        node.get("nodeKind"), label=f"{label}.nodeKind", allow_empty=False
    )
    if node_kind not in _SEMANTIC_NODE_KINDS:
        raise DocIRDraftError(f"{label}.nodeKind must be XML_ELEMENT or XML_ATTRIBUTE")
    if (node_kind == "XML_ATTRIBUTE") != item.startswith("@"):
        raise DocIRDraftError(f"{label}.item and nodeKind must describe the same XML node kind")
    if is_root and node_kind != "XML_ELEMENT":
        raise DocIRDraftError(f"{label} root must be an XML_ELEMENT")

    children = node.get("children")
    if not isinstance(children, list):
        raise DocIRDraftError(f"{label}.children must be an ordered array")
    if node_kind == "XML_ATTRIBUTE" and children:
        raise DocIRDraftError(f"{label} attribute nodes cannot have children")

    semantics = _normalized_semantics(
        node,
        label=label,
        item=item,
        node_kind=node_kind,
        has_children=bool(children),
    )
    field = {"index": index, "item": item, **semantics}
    fields.append(_validated_field(field, root_index=index.split(".", 1)[0], label=label))

    sibling_names: set[str] = set()
    for position, child in enumerate(children, start=1):
        child_object = _require_object(child, label=f"{label}.children[{position - 1}]")
        child_name = _require_string(
            child_object.get("item"),
            label=f"{label}.children[{position - 1}].item",
            allow_empty=False,
        )
        if child_name in sibling_names:
            raise DocIRDraftError(f"{label} has duplicate sibling item {child_name}")
        sibling_names.add(child_name)
        _materialize_semantic_node(
            child_object,
            section_name=section_name,
            selector_suffix=f"{selector_suffix}.{position}",
            index=f"{index}.{position}",
            label=f"{label}.children[{position - 1}]",
            fields=fields,
            visited=visited,
            is_root=False,
        )


def validate_docir_interface_envelope_segment(value: Any) -> dict[str, Any]:
    segment = _require_object(value, label="DocIR interface-envelope segment")
    _require_exact_properties(
        segment,
        {"contractVersion", "interface", "sourceContext", "envelope"},
        label="DocIR interface-envelope segment",
    )
    if segment.get("contractVersion") != INTERFACE_ENVELOPE_SEGMENT_CONTRACT:
        raise DocIRDraftError(
            "DocIR interface-envelope segment contractVersion must be "
            f"{INTERFACE_ENVELOPE_SEGMENT_CONTRACT}"
        )
    return {
        "contractVersion": INTERFACE_ENVELOPE_SEGMENT_CONTRACT,
        "interface": _validated_section(segment, "interface"),
        "sourceContext": _require_string_array(
            segment.get("sourceContext"),
            label="DocIR interface-envelope segment sourceContext",
        ),
        "envelope": _validated_section(segment, "envelope", root_index="1"),
    }


def validate_docir_messages_outline_segment(value: Any) -> dict[str, Any]:
    segment = _require_object(value, label="DocIR messages-outline segment")
    _require_exact_properties(
        segment,
        {"contractVersion", "assembly", "parse"},
        label="DocIR messages-outline segment",
    )
    if segment.get("contractVersion") != MESSAGES_OUTLINE_SEGMENT_CONTRACT:
        raise DocIRDraftError(
            "DocIR messages-outline segment contractVersion must be "
            f"{MESSAGES_OUTLINE_SEGMENT_CONTRACT}"
        )
    return {
        "contractVersion": MESSAGES_OUTLINE_SEGMENT_CONTRACT,
        "assembly": _validated_outline_section(segment, "assembly", root_index="2"),
        "parse": _validated_outline_section(segment, "parse", root_index="3"),
    }


def build_docir_field_batches(
    outline: Any,
    *,
    batch_size: int,
) -> list[list[dict[str, str]]]:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise DocIRDraftError("DocIR field batch size must be a positive integer")
    if not isinstance(outline, list) or not outline:
        raise DocIRDraftError("DocIR field outline must be a non-empty array")
    return [outline[index : index + batch_size] for index in range(0, len(outline), batch_size)]


def validate_docir_field_details_segment(
    value: Any,
    *,
    direction: str,
    batch_index: int,
    expected_outline: list[dict[str, str]],
) -> dict[str, Any]:
    segment = _require_object(value, label="DocIR field-details segment")
    _require_exact_properties(
        segment,
        {"contractVersion", "direction", "batchIndex", "fields"},
        label="DocIR field-details segment",
    )
    if segment.get("contractVersion") != FIELD_DETAILS_SEGMENT_CONTRACT:
        raise DocIRDraftError(
            "DocIR field-details segment contractVersion must be "
            f"{FIELD_DETAILS_SEGMENT_CONTRACT}"
        )
    if direction not in {"ASSEMBLY", "PARSE"}:
        raise DocIRDraftError("DocIR field-details direction must be ASSEMBLY or PARSE")
    if segment.get("direction") != direction:
        raise DocIRDraftError("DocIR field-details direction does not match the request")
    if isinstance(batch_index, bool) or not isinstance(batch_index, int) or batch_index <= 0:
        raise DocIRDraftError("DocIR field-details batch index must be a positive integer")
    if segment.get("batchIndex") != batch_index:
        raise DocIRDraftError("DocIR field-details batch index does not match the request")
    fields_value = segment.get("fields")
    if not isinstance(fields_value, list) or not fields_value:
        raise DocIRDraftError("DocIR field-details fields must be a non-empty array")
    root_index = "2" if direction == "ASSEMBLY" else "3"
    fields = [
        _validated_field(
            item,
            root_index=root_index,
            label=f"DocIR field-details fields[{position}]",
        )
        for position, item in enumerate(fields_value)
    ]
    actual_outline = [
        {"index": field["index"], "item": field["item"]}
        for field in fields
    ]
    if actual_outline != expected_outline:
        raise DocIRDraftError("DocIR field-details fields do not match the target outline")
    return {
        "contractVersion": FIELD_DETAILS_SEGMENT_CONTRACT,
        "direction": direction,
        "batchIndex": batch_index,
        "fields": fields,
    }


def merge_docir_extraction_segments(
    *,
    interface_envelope: Any,
    messages_outline: Any,
    assembly_details: list[Any],
    parse_details: list[Any],
    batch_size: int = 16,
) -> dict[str, Any]:
    interface_envelope_segment = validate_docir_interface_envelope_segment(
        interface_envelope
    )
    outline_segment = validate_docir_messages_outline_segment(messages_outline)
    details_by_direction = {
        "ASSEMBLY": assembly_details,
        "PARSE": parse_details,
    }
    merged_fields: dict[str, list[dict[str, str]]] = {}
    for direction, section_name in (("ASSEMBLY", "assembly"), ("PARSE", "parse")):
        expected_batches = build_docir_field_batches(
            outline_segment[section_name]["fields"],
            batch_size=batch_size,
        )
        detail_segments = details_by_direction[direction]
        if len(detail_segments) != len(expected_batches):
            raise DocIRDraftError(
                f"DocIR {direction} detail batches do not exactly cover the outline"
            )
        validated_batches = [
            validate_docir_field_details_segment(
                detail_segment,
                direction=direction,
                batch_index=index,
                expected_outline=expected_outline,
            )["fields"]
            for index, (detail_segment, expected_outline) in enumerate(
                zip(detail_segments, expected_batches, strict=True),
                start=1,
            )
        ]
        merged_fields[section_name] = [
            field for batch in validated_batches for field in batch
        ]

    merged = {
        "contractVersion": DOCIR_EXTRACTION_CONTRACT,
        "interface": interface_envelope_segment["interface"],
        "sourceContext": interface_envelope_segment["sourceContext"],
        "envelope": interface_envelope_segment["envelope"],
        "assembly": {
            "metadata": outline_segment["assembly"]["metadata"],
            "fields": merged_fields["assembly"],
            "conditions": outline_segment["assembly"]["conditions"],
        },
        "parse": {
            "metadata": outline_segment["parse"]["metadata"],
            "fields": merged_fields["parse"],
            "conditions": outline_segment["parse"]["conditions"],
        },
    }
    return _validated_extraction(merged)


def render_docir_extraction(value: Any) -> str:
    extraction = _validated_extraction(value)
    interface = extraction["interface"]
    envelope = extraction["envelope"]
    assembly = extraction["assembly"]
    parse = extraction["parse"]
    source_context = extraction["sourceContext"]

    parts = [
        "# Interface",
        "",
        "## Metadata",
        "",
        _render_metadata(interface["metadata"]),
        "",
        "# Source Context / 来源上下文",
        "",
        _render_bullets(source_context),
        "",
        "# Envelope",
        "",
        "## Metadata",
        "",
        _render_metadata(envelope["metadata"]),
        "",
        "## Fields",
        "",
        _render_fields(envelope["fields"]),
        "",
        "# Message: ASSEMBLY",
        "",
        "## Metadata",
        "",
        _render_metadata(assembly["metadata"]),
        "",
        "## Fields",
        "",
        _render_fields(assembly["fields"]),
        "",
        "## Conditions",
        "",
        _render_bullets(assembly["conditions"]),
        "",
        "# Message: PARSE",
        "",
        "## Metadata",
        "",
        _render_metadata(parse["metadata"]),
        "",
        "## Fields",
        "",
        _render_fields(parse["fields"]),
        "",
        "## Conditions",
        "",
        _render_bullets(parse["conditions"]),
    ]
    rendered = "\n".join(parts) + "\n"
    validate_docir_markdown_wire(rendered)
    return rendered


def _validated_extraction(value: Any) -> dict[str, Any]:
    extraction = _require_object(value, label="DocIR extraction")
    _require_exact_properties(extraction, _TOP_PROPERTIES, label="DocIR extraction")
    if extraction.get("contractVersion") != DOCIR_EXTRACTION_CONTRACT:
        raise DocIRDraftError(
            f"DocIR extraction contractVersion must be {DOCIR_EXTRACTION_CONTRACT}"
        )

    interface = _validated_section(extraction, "interface")
    envelope = _validated_section(extraction, "envelope", root_index="1")
    assembly = _validated_section(extraction, "assembly", root_index="2")
    parse = _validated_section(extraction, "parse", root_index="3")
    source_context = _require_string_array(
        extraction.get("sourceContext"),
        label="DocIR extraction sourceContext",
    )

    return {
        "contractVersion": DOCIR_EXTRACTION_CONTRACT,
        "interface": interface,
        "sourceContext": source_context,
        "envelope": envelope,
        "assembly": assembly,
        "parse": parse,
    }


def render_docir_review_notes(value: Any) -> str:
    extraction = _validated_extraction(value)
    review_items: list[str] = []
    for section_label, section_name in (
        ("Interface", "interface"),
        ("Envelope", "envelope"),
        ("ASSEMBLY", "assembly"),
        ("PARSE", "parse"),
    ):
        section = extraction[section_name]
        for row in section["metadata"]:
            if row["reviewNote"]:
                review_items.append(
                    f"{section_label}.Metadata[{row['key']}]: {row['reviewNote']}"
                )
    for section_label, section_name in (
        ("Envelope", "envelope"),
        ("ASSEMBLY", "assembly"),
        ("PARSE", "parse"),
    ):
        for row in extraction[section_name]["fields"]:
            if row["review"]:
                review_items.append(
                    f"{section_label}[{row['index']} {row['item']}]: {row['review']}"
                )

    parts = [
        "# 待人工确认",
        "",
        "## 固定检查清单",
        "",
        _render_bullets(list(_FIXED_REVIEW_CHECKLIST)),
    ]
    if review_items:
        parts.extend(["", "## 提取项", "", _render_bullets(review_items)])
    return "\n".join(parts) + "\n"


def render_docir_validation_review_notes(
    content: str, result: dict[str, Any]
) -> str:
    """Render hash-bound notes by copying only facts already present in this Draft/result."""

    if not isinstance(content, str):
        raise DocIRDraftError("DocIR Review Notes source must be text")
    validated = result.get("validatedArtifact")
    summary = result.get("summary")
    issues = result.get("issues")
    if not isinstance(validated, dict) or not isinstance(summary, dict):
        raise DocIRDraftError("DocIR Review Notes require one Validation Result")
    if not isinstance(issues, list):
        raise DocIRDraftError("DocIR Review Notes issues must be an array")

    parts = [
        "# Draft Validation Review Notes",
        "",
        f"Content hash: `{validated.get('contentHash', '')}`",
        "",
        f"Status: `{result.get('status', '')}`",
        "",
        (
            "Summary: "
            f"ERROR={summary.get('errorCount', 0)}, "
            f"WARNING={summary.get('warningCount', 0)}, "
            f"INFO={summary.get('infoCount', 0)}"
        ),
        "",
    ]
    if issues:
        parts.extend(["## Issues", ""])
        for issue in issues:
            location = f" `{issue.get('path')}`" if issue.get("path") else ""
            parts.append(
                f"- [{issue.get('severity')}] `{issue.get('code')}`{location}: "
                f"{issue.get('message')}"
            )
    else:
        parts.append("Validator 未发现 ERROR 或 WARNING。Human 仍需对照 raw-doc 审查语义完整性。")

    explicit_reviews = _markdown_review_evidence(content)
    if explicit_reviews:
        parts.extend(["", "## 显式 Review 证据", ""])
        parts.extend(f"- {item}" for item in explicit_reviews)
    return "\n".join(parts) + "\n"


def _markdown_review_evidence(content: str) -> list[str]:
    evidence: list[str] = []
    section = ""
    table = ""
    for line in content.splitlines():
        if line.startswith("# "):
            section = line[2:]
            table = ""
            continue
        if line == METADATA_HEADER:
            table = "metadata"
            continue
        if line == FIELDS_HEADER:
            table = "fields"
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        try:
            cells = _split_markdown_row(line)
        except DocIRDraftError:
            continue
        if table == "metadata" and len(cells) == 3 and cells[2]:
            evidence.append(f"{section}.Metadata[{cells[0]}]: {cells[2]}")
        elif table == "fields" and len(cells) == 9 and cells[8]:
            item = cells[2].lstrip("\u3000").strip("`")
            evidence.append(f"{section}[{cells[0]} {item}]: {cells[8]}")
    return evidence


def validate_docir_markdown_wire(content: Any) -> None:
    if not isinstance(content, str) or not content:
        raise DocIRDraftError("DocIR Markdown wire must be non-empty text")
    if content.startswith("\ufeff"):
        raise DocIRDraftError("DocIR Markdown wire must be UTF-8 without BOM")

    lines = content.splitlines()
    headings = [line for line in lines if line.startswith("# ")]
    expected_headings = [
        "# Interface",
        "# Source Context / 来源上下文",
        "# Envelope",
        "# Message: ASSEMBLY",
        "# Message: PARSE",
    ]
    if headings != expected_headings:
        raise DocIRDraftError("DocIR Markdown wire has invalid top-level heading order")
    if LEGACY_FIELDS_HEADER in content:
        raise DocIRDraftError(
            "DocIR Markdown wire uses the unsupported legacy ten-column Fields contract"
        )
    if content.count(METADATA_HEADER) != 4:
        raise DocIRDraftError("DocIR Markdown wire must contain four fixed Metadata headers")
    if content.count(FIELDS_HEADER) != 3:
        raise DocIRDraftError("DocIR Markdown wire must contain three fixed Fields headers")
    if content.count("## Conditions") != 2:
        raise DocIRDraftError("DocIR Markdown wire must contain two Conditions sections")
    if "| Path |" in content or "| Tag |" in content or "…/" in content:
        raise DocIRDraftError("DocIR Markdown wire contains a forbidden path or tag form")

    for heading, root_index in (
        ("# Envelope", "1"),
        ("# Message: ASSEMBLY", "2"),
        ("# Message: PARSE", "3"),
    ):
        start = lines.index(heading)
        end = next(
            (index for index in range(start + 1, len(lines)) if lines[index].startswith("# ")),
            len(lines),
        )
        section_lines = lines[start:end]
        try:
            header_index = section_lines.index(FIELDS_HEADER)
        except ValueError as exc:
            raise DocIRDraftError(f"DocIR {heading} is missing its Fields table") from exc
        rows: list[list[str]] = []
        for line in section_lines[header_index + 2 :]:
            if not line.startswith("|"):
                if rows:
                    break
                continue
            cells = _split_markdown_row(line)
            if len(cells) != 9:
                raise DocIRDraftError(f"DocIR {heading} Fields row must have nine cells")
            rows.append(cells)
        _validate_rendered_field_rows(rows, root_index=root_index, label=heading)


def validate_docir_markdown(content: Any) -> dict[str, Any]:
    """Return all independently discoverable DocIR Draft issues for the exact bytes."""

    if not isinstance(content, str):
        raise DocIRDraftError("DocIR Markdown wire must be text")
    content_hash = f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
    issues: list[dict[str, Any]] = []
    lines = content.splitlines()

    def add(
        code: str,
        path: str | None,
        message: str,
        *,
        severity: str = "ERROR",
        blocking: bool | None = None,
    ) -> None:
        issues.append(
            {
                "severity": severity,
                "blocking": severity == "ERROR" if blocking is None else blocking,
                "code": code,
                "path": path,
                "message": message,
            }
        )

    if not content:
        add("DOCIR_EMPTY", None, "DocIR Markdown wire must be non-empty text")
    if content.startswith("\ufeff"):
        add("DOCIR_UTF8_BOM", None, "DocIR Markdown wire must be UTF-8 without BOM")
    if LEGACY_FIELDS_HEADER in content:
        add(
            "DOCIR_FIELDS_TABLE_CONTRACT",
            None,
            "DocIR Markdown wire uses the unsupported legacy ten-column Fields contract",
        )

    headings = [line for line in lines if line.startswith("# ")]
    expected_headings = [
        "# Interface",
        "# Source Context / 来源上下文",
        "# Envelope",
        "# Message: ASSEMBLY",
        "# Message: PARSE",
    ]
    if headings != expected_headings:
        add(
            "DOCIR_HEADING_ORDER",
            None,
            "DocIR Markdown wire has invalid top-level heading order",
        )
    if content.count(METADATA_HEADER) != 4:
        add(
            "DOCIR_METADATA_TABLE_COUNT",
            None,
            "DocIR Markdown wire must contain four fixed Metadata headers",
        )
    if content.count(FIELDS_HEADER) != 3:
        add(
            "DOCIR_FIELDS_TABLE_COUNT",
            None,
            "DocIR Markdown wire must contain three fixed Fields headers",
        )
    if content.count("## Conditions") != 2:
        add(
            "DOCIR_CONDITIONS_COUNT",
            None,
            "DocIR Markdown wire must contain two Conditions sections",
        )
    if "| Path |" in content or "| Tag |" in content or "…/" in content:
        add(
            "DOCIR_FORBIDDEN_WIRE_FORM",
            None,
            "DocIR Markdown wire contains a forbidden path or tag form",
        )

    field_count = 0
    covered_sections = 0
    for heading, section_label, root_index in (
        ("# Envelope", "Envelope", "1"),
        ("# Message: ASSEMBLY", "ASSEMBLY", "2"),
        ("# Message: PARSE", "PARSE", "3"),
    ):
        if heading not in lines:
            add(
                "DOCIR_SECTION_MISSING",
                section_label,
                f"DocIR is missing the {section_label} section",
            )
            continue
        start = lines.index(heading)
        end = next(
            (
                position
                for position in range(start + 1, len(lines))
                if lines[position].startswith("# ")
            ),
            len(lines),
        )
        section_lines = lines[start:end]
        if FIELDS_HEADER not in section_lines:
            add(
                "DOCIR_FIELDS_TABLE_MISSING",
                f"{section_label}.Fields",
                f"DocIR {section_label} is missing its Fields table",
            )
            continue
        covered_sections += 1
        header_index = section_lines.index(FIELDS_HEADER)
        rows: list[list[str]] = []
        for line in section_lines[header_index + 2 :]:
            if not line.startswith("|"):
                if rows:
                    break
                continue
            try:
                cells = _split_markdown_row(line)
            except DocIRDraftError as exc:
                add("DOCIR_FIELD_ROW_FORMAT", f"{section_label}.Fields", str(exc))
                continue
            if len(cells) != 9:
                add(
                    "DOCIR_FIELD_CELL_COUNT",
                    f"{section_label}.Fields",
                    f"DocIR {section_label} Fields row must have nine cells",
                )
                continue
            rows.append(cells)
        field_count += len(rows)
        _collect_rendered_field_issues(
            rows,
            root_index=root_index,
            section_label=section_label,
            add=add,
        )
        _collect_condition_evidence_issues(
            section_lines,
            section_label=section_label,
            add=add,
        )

    ordered = sorted(
        issues,
        key=lambda item: (item["path"] or "", item["code"], item["message"]),
    )
    counts = Counter(item["severity"] for item in ordered)
    error_count = counts["ERROR"]
    return {
        "contractVersion": DOCIR_VALIDATION_RESULT_CONTRACT,
        "validatedArtifact": {
            "kind": "docir",
            "contentHash": content_hash,
        },
        "status": "failed" if error_count else "passed",
        "finalEligible": False,
        "summary": {
            "fieldCount": field_count,
            "errorCount": error_count,
            "warningCount": counts["WARNING"],
            "infoCount": counts["INFO"],
            "blockingCount": sum(1 for item in ordered if item["blocking"]),
        },
        "coverage": {
            "expectedSections": 3,
            "validatedSections": covered_sections,
        },
        "issues": ordered,
    }


def _collect_rendered_field_issues(
    rows: list[list[str]],
    *,
    root_index: str,
    section_label: str,
    add: Any,
) -> None:
    if not rows:
        add(
            "DOCIR_ROOT_MISSING",
            f"{section_label}.Fields",
            f"DocIR {section_label} Fields must contain a root",
        )
        return
    if rows[0][0] != root_index:
        add(
            "DOCIR_ROOT_INDEX",
            f"{section_label}.Fields[{rows[0][0]}]",
            f"DocIR {section_label} root index must be {root_index}",
        )

    seen_indexes: set[str] = set()
    previous_index_key: tuple[int, ...] | None = None
    for position, row in enumerate(rows):
        index = row[0]
        path = f"{section_label}.Fields[{index or position}]"
        try:
            _validate_index(index, root_index=root_index, label=f"DocIR {section_label} index")
        except DocIRDraftError as exc:
            add("DOCIR_INDEX", path, str(exc))
            continue
        index_key = _index_key(index)
        if previous_index_key is not None and index_key <= previous_index_key:
            add(
                "DOCIR_INDEX_ORDER",
                path,
                f"DocIR {section_label} index order is invalid: {index}",
            )
        previous_index_key = index_key
        if index in seen_indexes:
            add(
                "DOCIR_INDEX_DUPLICATE",
                path,
                f"DocIR {section_label} index is duplicated: {index}",
            )
        if index != root_index:
            parent = index.rsplit(".", 1)[0]
            if parent not in seen_indexes:
                add(
                    "DOCIR_PARENT_MISSING",
                    path,
                    f"DocIR {section_label} parent index is missing for {index}",
                )
        seen_indexes.add(index)

        depth = index.count(".")
        expected_prefix = "\u3000" * depth
        item_cell = row[2]
        item_valid = item_cell.startswith(expected_prefix + "`") and item_cell.endswith("`")
        if not item_valid:
            add(
                "DOCIR_ITEM_INDENTATION",
                path,
                f"DocIR {section_label} Message Item indentation is invalid for {index}",
            )
        else:
            item = item_cell[len(expected_prefix) + 1 : -1]
            if not _ITEM_PATTERN.fullmatch(item):
                add(
                    "DOCIR_ITEM",
                    path,
                    f"DocIR {section_label} Message Item is invalid for {index}",
                )

        item = item_cell[len(expected_prefix) + 1 : -1] if item_valid else ""

        multiplicity_bounds: tuple[int | None, int | str | None] = (None, None)
        try:
            _validate_multiplicity(row[3], label=f"DocIR {section_label} multiplicity")
            multiplicity_bounds = _multiplicity_bounds(row[3])
        except DocIRDraftError as exc:
            add("DOCIR_MULTIPLICITY", path, str(exc))
        if row[4] not in _FIELD_TYPES:
            add(
                "DOCIR_TYPE",
                path,
                f"DocIR {section_label} Type wire value is invalid",
            )
        if row[5] not in _REQUIRED_VALUES:
            add(
                "DOCIR_REQUIRED",
                path,
                f"DocIR {section_label} {index} Required wire value is invalid; "
                f"item={item or '<invalid>'}; Required={row[5] or '<empty>'}",
            )

        has_children = any(
            other[0].startswith(f"{index}.") for other in rows if other is not row
        )
        if row[4] in _FIELD_TYPES:
            if (has_children or item == "trans") and row[4] != "Object":
                add(
                    "DOCIR_TYPE_STRUCTURE",
                    path,
                    f"DocIR {section_label} {index} container Type must be Object",
                )
            elif not has_children and item != "trans" and row[4] not in {
                "String",
                "Boolean",
                "Date",
                "Decimal",
            }:
                add(
                    "DOCIR_TYPE_STRUCTURE",
                    path,
                    f"DocIR {section_label} {index} leaf Type must be a scalar DocIR type",
                )

        minimum, maximum = multiplicity_bounds
        repeated = maximum == "*" or isinstance(maximum, int) and maximum > 1
        if repeated and row[4] != "Object":
            add(
                "DOCIR_MULTIPLICITY_TYPE",
                path,
                f"DocIR {section_label} {index} repeated Mult. requires Object Type",
            )
        if minimum is not None and row[5] in {"Y", "N", "C"}:
            required_minimum = 1 if row[5] == "Y" else 0
            if minimum != required_minimum:
                add(
                    "DOCIR_REQUIRED_MULTIPLICITY_CONFLICT",
                    path,
                    f"DocIR {section_label} {index} Required conflicts with Mult. lower bound",
                    severity="WARNING",
                    blocking=False,
                )

        is_object = row[4] == "Object"
        evidence = _required_evidence(row[6], row[7])
        if is_object and row[5]:
            add(
                "DOCIR_OBJECT_REQUIRED_NOT_APPLICABLE",
                path,
                f"DocIR {section_label} {index} Object Required must be empty",
            )
        elif not is_object and not row[5]:
            add(
                "DOCIR_SEMANTIC_VALUE_MISSING",
                path,
                _required_issue_message(
                    item=item,
                    required="",
                    evidence=evidence[2],
                    prefix="Required 值未确定，需要 Human 根据当前字段证据确认 Y/N/C。",
                ),
            )
        elif not is_object and evidence[0] is not None and row[5] != evidence[0]:
            add(
                "DOCIR_REQUIRED_EVIDENCE_CONFLICT",
                path,
                _required_issue_message(
                    item=item,
                    required=row[5],
                    evidence=evidence[2],
                    prefix=f"Required 与当前字段明确证据冲突；证据支持 {evidence[0]}。",
                ),
            )
        if not is_object and evidence[1]:
            add(
                "DOCIR_REQUIRED_EVIDENCE_AMBIGUOUS",
                path,
                _required_issue_message(
                    item=item,
                    required=row[5],
                    evidence=evidence[2],
                    prefix="Required 证据可能涉及其他字段，必须由 Human 确认约束对象。",
                ),
                severity="WARNING",
                blocking=False,
            )
        if (
            not is_object
            and not row[5]
            and REQUIRED_UNKNOWN_REVIEW_MARKER not in row[8]
        ):
            add(
                "DOCIR_REVIEW_MARKER_MISSING",
                path,
                f"DocIR {section_label} {index} missing Required requires the explicit Review marker",
            )
        if REJECTED_MULTIPLICITY_REVIEW_MARKER in row[8]:
            add(
                "DOCIR_MULTIPLICITY_REJECTED",
                path,
                f"DocIR {section_label} {index} has a rejected multiplicity candidate",
            )
        if NORMALIZED_TYPE_REVIEW_MARKER in row[8]:
            add(
                "DOCIR_TYPE_NORMALIZED",
                path,
                f"DocIR {section_label} {index} Type was normalized and requires Human review",
                severity="WARNING",
                blocking=False,
            )


def _required_evidence(description: str, validation: str) -> tuple[str | None, bool, str]:
    evidence_parts = []
    if description:
        evidence_parts.append(f"说明={description}")
    if validation:
        evidence_parts.append(f"校验点={validation}")
    evidence = "；".join(evidence_parts) or "<none>"
    text = "；".join(part for part in (description, validation) if part)
    optional = bool(_OPTIONAL_EVIDENCE.search(text))
    conditional = bool(_CONDITIONAL_REQUIRED_EVIDENCE.search(text))
    direct_required = bool(_DIRECT_REQUIRED_EVIDENCE.search(text))
    cross_field = bool(_POSSIBLE_CROSS_FIELD_REQUIREMENT.search(text))

    # 关键词只用于发现候选结果与同一字段证据的明显矛盾。涉及条件或其他字段时，
    # 代码保留原文并交给 Human，绝不把自然语言解析结果写回 Required。
    if conditional:
        expected = "C"
    elif optional and direct_required:
        expected = None
    elif optional:
        expected = "N"
    elif direct_required:
        expected = "Y"
    else:
        expected = None
    return expected, cross_field, evidence


def _required_issue_message(
    *, item: str, required: str, evidence: str, prefix: str
) -> str:
    value = required or "<empty>"
    return f"{prefix} item={item}; Required={value}; evidence: {evidence}"


def _collect_condition_evidence_issues(
    section_lines: list[str], *, section_label: str, add: Any
) -> None:
    if "## Conditions" not in section_lines:
        return
    start = section_lines.index("## Conditions") + 1
    position = 0
    for line in section_lines[start:]:
        if not line.startswith("- "):
            continue
        position += 1
        evidence = line[2:]
        if (
            evidence != NO_EXPLICIT_CONDITIONS
            and not _EXPLICIT_CONDITION_BRANCH.search(evidence)
        ):
            add(
                "DOCIR_CONDITION_NOT_EXPLICIT_BRANCH",
                f"{section_label}.Conditions[{position}]",
                "Conditions 只允许 raw-doc 明确表达的条件分支；格式、长度、枚举、"
                f"唯一性、最大笔数和普通业务校验必须保留在字段说明或校验点。 evidence: {evidence}",
            )
        if _POSSIBLE_CROSS_FIELD_REQUIREMENT.search(evidence):
            add(
                "DOCIR_REQUIRED_EVIDENCE_AMBIGUOUS",
                f"{section_label}.Conditions[{position}]",
                "Required 证据可能涉及其他字段，必须由 Human 确认约束对象。 "
                f"evidence: {evidence}",
                severity="WARNING",
                blocking=False,
            )


def _validated_section(
    extraction: dict[str, Any],
    section_name: str,
    *,
    root_index: str | None = None,
) -> dict[str, Any]:
    section = _require_object(
        extraction.get(section_name),
        label=f"DocIR extraction {section_name}",
    )
    _require_exact_properties(
        section,
        _SECTION_PROPERTIES[section_name],
        label=f"DocIR extraction {section_name}",
    )
    metadata = _validated_metadata(section.get("metadata"), section_name=section_name)
    result: dict[str, Any] = {"metadata": metadata}
    if root_index is not None:
        result["fields"] = _validated_fields(
            section.get("fields"),
            root_index=root_index,
            label=f"DocIR extraction {section_name}.fields",
        )
    if section_name in {"assembly", "parse"}:
        result["conditions"] = _require_string_array(
            section.get("conditions"),
            label=f"DocIR extraction {section_name}.conditions",
        )
    return result


def _validated_metadata(value: Any, *, section_name: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise DocIRDraftError(f"DocIR extraction {section_name}.metadata must be an array")
    indexed: dict[str, dict[str, str]] = {}
    for index, item in enumerate(value):
        label = f"DocIR extraction {section_name}.metadata[{index}]"
        row = _require_object(item, label=label)
        _require_exact_properties(row, _METADATA_PROPERTIES, label=label)
        key = _require_string(row.get("key"), label=f"{label}.key", allow_empty=False)
        if key in indexed:
            raise DocIRDraftError(f"{label}.key is duplicated: {key}")
        metadata_value = _require_string(row.get("value"), label=f"{label}.value")
        review_note = _require_string(row.get("reviewNote"), label=f"{label}.reviewNote")
        if not metadata_value and UNKNOWN_REVIEW_MARKER not in review_note:
            raise DocIRDraftError(
                f"{label}.reviewNote must contain {UNKNOWN_REVIEW_MARKER} when value is empty"
            )
        indexed[key] = {"key": key, "value": metadata_value, "reviewNote": review_note}

    expected_keys = _METADATA_KEYS[section_name]
    if set(indexed) != set(expected_keys):
        missing = set(expected_keys) - set(indexed)
        unknown = set(indexed) - set(expected_keys)
        detail = []
        if missing:
            detail.append("missing keys: " + ", ".join(sorted(missing)))
        if unknown:
            detail.append("unknown keys: " + ", ".join(sorted(unknown)))
        raise DocIRDraftError(
            f"DocIR extraction {section_name}.metadata has invalid keys ({'; '.join(detail)})"
        )
    ordered = [indexed[key] for key in expected_keys]
    values = {item["key"]: item["value"] for item in ordered}
    if section_name == "interface":
        if values["Message Format"] != "XML":
            raise DocIRDraftError("DocIR extraction Message Format must be XML")
        if values["Source Document"] != "raw-doc.md":
            raise DocIRDraftError("DocIR extraction Source Document must be raw-doc.md")
    elif section_name in {"assembly", "parse"}:
        expected_direction = section_name.upper()
        if values["Function Type"] != expected_direction:
            raise DocIRDraftError(
                f"DocIR extraction {section_name} Function Type must be {expected_direction}"
            )
    return ordered


def _validated_fields(
    value: Any,
    *,
    root_index: str,
    label: str,
) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise DocIRDraftError(f"{label} must be a non-empty array")
    fields: list[dict[str, str]] = []
    seen_indexes: set[str] = set()
    previous_index_key: tuple[int, ...] | None = None
    for position, item in enumerate(value):
        field_label = f"{label}[{position}]"
        field = _validated_field(item, root_index=root_index, label=field_label)
        index = field["index"]
        index_key = _index_key(index)
        if previous_index_key is not None and index_key <= previous_index_key:
            raise DocIRDraftError(f"{field_label}.index order is invalid: {index}")
        previous_index_key = index_key
        if index in seen_indexes:
            raise DocIRDraftError(f"{field_label}.index is duplicated: {index}")
        if position == 0 and index != root_index:
            raise DocIRDraftError(f"{label} root index must be {root_index}")
        if index != root_index:
            parent = index.rsplit(".", 1)[0]
            if parent not in seen_indexes:
                raise DocIRDraftError(f"{field_label} parent index must appear before {index}")
        seen_indexes.add(index)

        fields.append(field)
    return fields


def _validated_field(item: Any, *, root_index: str, label: str) -> dict[str, str]:
    row = _require_object(item, label=label)
    _require_exact_properties(row, _FIELD_PROPERTIES, label=label)
    field = {
        name: _require_string(row.get(name), label=f"{label}.{name}")
        for name in _FIELD_PROPERTIES
    }
    _validate_index(field["index"], root_index=root_index, label=f"{label}.index")
    if not _ITEM_PATTERN.fullmatch(field["item"]):
        raise DocIRDraftError(f"{label}.item must be a plain XML item name")
    _validate_multiplicity(field["multiplicity"], label=f"{label}.multiplicity")
    if field["type"] not in _FIELD_TYPES:
        raise DocIRDraftError(f"{label}.type uses an unsupported DocIR wire value")
    if field["required"] not in _REQUIRED_VALUES:
        raise DocIRDraftError(f"{label}.required uses an unsupported DocIR wire value")
    if field["type"] == "Object" and field["required"]:
        raise DocIRDraftError(f"{label}.required must be empty for Object")
    if (
        field["type"] != "Object"
        and not field["required"]
        and REQUIRED_UNKNOWN_REVIEW_MARKER not in field["review"]
    ):
        raise DocIRDraftError(
            f"{label}.review must contain {REQUIRED_UNKNOWN_REVIEW_MARKER} when Required is empty"
        )
    return field


def _validated_outline_section(
    segment: dict[str, Any],
    section_name: str,
    *,
    root_index: str,
) -> dict[str, Any]:
    section = _require_object(
        segment.get(section_name),
        label=f"DocIR messages-outline {section_name}",
    )
    _require_exact_properties(
        section,
        {"metadata", "fields", "conditions"},
        label=f"DocIR messages-outline {section_name}",
    )
    return {
        "metadata": _validated_metadata(section.get("metadata"), section_name=section_name),
        "conditions": _require_string_array(
            section.get("conditions"),
            label=f"DocIR messages-outline {section_name}.conditions",
        ),
        "fields": _validated_field_outline(
            section.get("fields"),
            root_index=root_index,
            label=f"DocIR messages-outline {section_name}.fields",
        ),
    }


def _validated_field_outline(
    value: Any,
    *,
    root_index: str,
    label: str,
) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise DocIRDraftError(f"{label} must be a non-empty array")
    outline: list[dict[str, str]] = []
    seen_indexes: set[str] = set()
    previous_index_key: tuple[int, ...] | None = None
    for position, item in enumerate(value):
        field_label = f"{label}[{position}]"
        row = _require_object(item, label=field_label)
        _require_exact_properties(row, {"index", "item"}, label=field_label)
        index = _require_string(row.get("index"), label=f"{field_label}.index")
        item_name = _require_string(
            row.get("item"), label=f"{field_label}.item", allow_empty=False
        )
        _validate_index(index, root_index=root_index, label=f"{field_label}.index")
        index_key = _index_key(index)
        if previous_index_key is not None and index_key <= previous_index_key:
            raise DocIRDraftError(f"{field_label}.index order is invalid: {index}")
        previous_index_key = index_key
        if index in seen_indexes:
            raise DocIRDraftError(f"{field_label}.index is duplicated: {index}")
        if position == 0 and index != root_index:
            raise DocIRDraftError(f"{label} root index must be {root_index}")
        if index != root_index:
            parent = index.rsplit(".", 1)[0]
            if parent not in seen_indexes:
                raise DocIRDraftError(f"{field_label} parent index must appear before {index}")
        if not _ITEM_PATTERN.fullmatch(item_name):
            raise DocIRDraftError(f"{field_label}.item must be a plain XML item name")
        seen_indexes.add(index)
        outline.append({"index": index, "item": item_name})
    return outline


def _validate_rendered_field_rows(
    rows: list[list[str]],
    *,
    root_index: str,
    label: str,
) -> None:
    if not rows or rows[0][0] != root_index:
        raise DocIRDraftError(f"DocIR {label} root index must be {root_index}")
    seen_indexes: set[str] = set()
    previous_index_key: tuple[int, ...] | None = None
    for row in rows:
        index = row[0]
        _validate_index(index, root_index=root_index, label=f"DocIR {label} index")
        index_key = _index_key(index)
        if previous_index_key is not None and index_key <= previous_index_key:
            raise DocIRDraftError(f"DocIR {label} index order is invalid: {index}")
        previous_index_key = index_key
        if index in seen_indexes:
            raise DocIRDraftError(f"DocIR {label} index is duplicated: {index}")
        if index != root_index:
            parent = index.rsplit(".", 1)[0]
            if parent not in seen_indexes:
                raise DocIRDraftError(f"DocIR {label} parent index is missing for {index}")
        seen_indexes.add(index)

        depth = index.count(".")
        expected_prefix = "\u3000" * depth
        item_cell = row[2]
        if not item_cell.startswith(expected_prefix + "`") or not item_cell.endswith("`"):
            raise DocIRDraftError(f"DocIR {label} Message Item indentation is invalid for {index}")
        item = item_cell[len(expected_prefix) + 1 : -1]
        if not _ITEM_PATTERN.fullmatch(item):
            raise DocIRDraftError(f"DocIR {label} Message Item is invalid for {index}")
        _validate_multiplicity(row[3], label=f"DocIR {label} multiplicity")
        if row[4] not in _FIELD_TYPES:
            raise DocIRDraftError(f"DocIR {label} Type wire value is invalid")
        if row[5] not in _REQUIRED_VALUES:
            raise DocIRDraftError(f"DocIR {label} Required wire value is invalid")


def _validate_index(value: str, *, root_index: str, label: str) -> None:
    parts = value.split(".")
    if not parts or parts[0] != root_index or any(
        not _INDEX_SUFFIX_PATTERN.fullmatch(part) for part in parts
    ):
        raise DocIRDraftError(f"{label} must be a hierarchical index rooted at {root_index}")


def _index_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def _validate_multiplicity(value: str, *, label: str) -> None:
    if not value:
        return
    match = _MULTIPLICITY_PATTERN.fullmatch(value)
    if match is None:
        raise DocIRDraftError(f"{label} must use a bracketed [min..max] value")
    minimum = int(match.group(1))
    maximum = match.group(2)
    if maximum != "*" and minimum > int(maximum):
        raise DocIRDraftError(f"{label} minimum must not exceed maximum")


def _multiplicity_bounds(value: str) -> tuple[int | None, int | str | None]:
    if not value:
        return None, None
    match = _MULTIPLICITY_PATTERN.fullmatch(value)
    if match is None:
        return None, None
    maximum: int | str = "*" if match.group(2) == "*" else int(match.group(2))
    return int(match.group(1)), maximum


def _render_metadata(rows: list[dict[str, str]]) -> str:
    lines = [METADATA_HEADER, "|---|---|---|"]
    lines.extend(
        f"| {_table_cell(row['key'])} | {_table_cell(row['value'])} | "
        f"{_table_cell(row['reviewNote'])} |"
        for row in rows
    )
    return "\n".join(lines)


def _render_fields(rows: list[dict[str, str]]) -> str:
    lines = [FIELDS_HEADER, "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        indentation = "\u3000" * row["index"].count(".")
        item = f"{indentation}`{row['item']}`"
        cells = (
            row["index"],
            row["or"],
            item,
            row["multiplicity"],
            row["type"],
            row["required"],
            row["description"],
            row["validation"],
            row["review"],
        )
        lines.append("| " + " | ".join(_table_cell(cell) for cell in cells) + " |")
    return "\n".join(lines)


def _render_bullets(items: list[str]) -> str:
    return "\n".join(f"- {_prose(item)}" for item in items)


def _table_cell(value: str) -> str:
    # U+3000 是冻结 wire 的层级标记，不能被 Unicode-aware strip() 当作普通空白删除。
    normalized = value.strip(" ").replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\\|", "|").replace("|", "\\|")
    return normalized.replace("\n", "<br>")


def _prose(value: str) -> str:
    return " ".join(value.replace("\r", "\n").splitlines()).strip()


def _split_markdown_row(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        raise DocIRDraftError("DocIR Markdown table row must start and end with a pipe")
    cells: list[str] = []
    current: list[str] = []
    backslashes = 0
    for character in line[1:-1]:
        if character == "|" and backslashes % 2 == 0:
            cells.append("".join(current).strip(" "))
            current = []
            backslashes = 0
            continue
        current.append(character)
        if character == "\\":
            backslashes += 1
        else:
            backslashes = 0
    cells.append("".join(current).strip(" "))
    return cells


def _require_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DocIRDraftError(f"{label} must be an object")
    return value


def _require_exact_properties(
    value: dict[str, Any],
    allowed: set[str],
    *,
    label: str,
) -> None:
    missing = allowed - set(value)
    unknown = set(value) - allowed
    if missing or unknown:
        detail: list[str] = []
        if missing:
            detail.append("missing properties: " + ", ".join(sorted(missing)))
        if unknown:
            detail.append("unknown properties: " + ", ".join(sorted(unknown)))
        raise DocIRDraftError(f"{label} has invalid properties ({'; '.join(detail)})")


def _require_string(value: Any, *, label: str, allow_empty: bool = True) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise DocIRDraftError(f"{label} must be {qualifier}")
    return value.strip()


def _require_string_array(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise DocIRDraftError(f"{label} must be a non-empty array")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_require_string(item, label=f"{label}[{index}]", allow_empty=False))
    return result
