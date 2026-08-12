from __future__ import annotations

import re
from typing import Any


DOCIR_EXTRACTION_CONTRACT = "docir-extraction/v1"
INTERFACE_ENVELOPE_SEGMENT_CONTRACT = "docir-interface-envelope-segment/v1"
MESSAGES_OUTLINE_SEGMENT_CONTRACT = "docir-messages-outline-segment/v1"
FIELD_DETAILS_SEGMENT_CONTRACT = "docir-field-details-segment/v1"
METADATA_HEADER = "| Key | Value | Review Note |"
FIELDS_HEADER = (
    "| Index | Or | Message Item | Mult. | Type | Required | 说明 | "
    "前置机校验点/格式 | 接口平台校验点 | Review |"
)
UNKNOWN_REVIEW_MARKER = "原文未说明，待人工确认"
_FIXED_REVIEW_CHECKLIST = (
    "核对 Interface、Envelope、ASSEMBLY、PARSE 的字段和父子层级是否完整忠实于 raw-doc。",
    "核对 Source Context 的适用范围，确认通用 XML 示例或其他交易代码未污染目标交易字段。",
    "核对所有冲突、空值和“原文未说明”项均已显式保留，未被模型静默推断。",
    "核对 ASSEMBLY 与 PARSE Conditions 是否完整且仅包含 raw-doc 支持的条件。",
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
    "preValidation",
    "platformValidation",
    "review",
}
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


class DocIRDraftError(ValueError):
    """Raised when structured DocIR extraction or its rendered wire is invalid."""


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
            if len(cells) != 10:
                raise DocIRDraftError(f"DocIR {heading} Fields row must have ten cells")
            rows.append(cells)
        _validate_rendered_field_rows(rows, root_index=root_index, label=heading)


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
    if (
        not field["multiplicity"] or not field["type"] or not field["required"]
    ) and UNKNOWN_REVIEW_MARKER not in field["review"]:
        raise DocIRDraftError(
            f"{label}.review must contain {UNKNOWN_REVIEW_MARKER} when a wire value is empty"
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


def _render_metadata(rows: list[dict[str, str]]) -> str:
    lines = [METADATA_HEADER, "|---|---|---|"]
    lines.extend(
        f"| {_table_cell(row['key'])} | {_table_cell(row['value'])} | "
        f"{_table_cell(row['reviewNote'])} |"
        for row in rows
    )
    return "\n".join(lines)


def _render_fields(rows: list[dict[str, str]]) -> str:
    lines = [FIELDS_HEADER, "|---|---|---|---|---|---|---|---|---|---|"]
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
            row["preValidation"],
            row["platformValidation"],
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
