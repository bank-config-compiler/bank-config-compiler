from __future__ import annotations

from copy import deepcopy

from bank_config_compiler.docir_draft import (
    materialize_docir_semantic_candidate,
    render_docir_extraction,
    validate_docir_markdown,
)


def _metadata(key: str, value: str) -> dict[str, str]:
    return {"key": key, "value": value, "reviewNote": ""}


def _node(
    selector: str,
    item: str,
    *,
    children: list[dict] | None = None,
    required: str = "Y",
    description: str = "非空字符串",
    validation: str = "长度1-35",
) -> dict:
    return {
        "selector": selector,
        "item": item,
        "nodeKind": "XML_ATTRIBUTE" if item.startswith("@") else "XML_ELEMENT",
        "children": children or [],
        "or": "",
        "multiplicity": "",
        "type": "",
        "required": required,
        "description": description,
        "validation": validation,
        "review": "",
    }


def _candidate() -> dict:
    return {
        "contractVersion": "docir-semantic-candidate/v2",
        "interface": {
            "metadata": [
                _metadata("Interface Code", "b2e9999"),
                _metadata("Interface Name", "测试接口"),
                _metadata("Message Format", "XML"),
                _metadata("Version", "120"),
                _metadata("Source Document", "raw-doc.md"),
            ]
        },
        "sourceContext": ["仅使用本次 attempt 的结构化结果。"],
        "envelope": {
            "metadata": [
                _metadata("Envelope Name", "root"),
                _metadata("Root Path", "/root"),
                _metadata("Applies To", "Request, Response"),
                _metadata("Evidence Scope", "共享信封"),
            ],
            "nodes": [
                _node(
                    "envelope:1",
                    "root",
                    children=[
                        _node(
                            "envelope:1.1",
                            "@version",
                            required="N",
                            description="可空字符串",
                        )
                    ],
                )
            ],
        },
        "assembly": {
            "metadata": [
                _metadata("Message Name", "test-rq"),
                _metadata("Function Type", "ASSEMBLY"),
                _metadata("Root Path", "trn-test-rq"),
                _metadata("Description", "请求报文"),
            ],
            "conditions": ["原文未提供可确认条件。"],
            "nodes": [
                _node(
                    "assembly:1",
                    "trn-test-rq",
                    children=[_node("assembly:1.1", "account")],
                )
            ],
        },
        "parse": {
            "metadata": [
                _metadata("Message Name", "test-rs"),
                _metadata("Function Type", "PARSE"),
                _metadata("Root Path", "trn-test-rs"),
                _metadata("Description", "响应报文"),
            ],
            "conditions": ["原文未提供可确认条件。"],
            "nodes": [
                _node(
                    "parse:1",
                    "trn-test-rs",
                    children=[_node("parse:1.1", "status")],
                )
            ],
        },
    }


def test_v2_candidate_renders_only_the_nine_column_docir_wire() -> None:
    markdown = render_docir_extraction(
        materialize_docir_semantic_candidate(_candidate())
    )

    assert (
        "| Index | Or | Message Item | Mult. | Type | Required | 说明 | 校验点 | Review |"
        in markdown
    )
    assert "前置机校验点/格式" not in markdown
    assert "接口平台校验点" not in markdown
    assert "| account description" not in markdown
    assert "| 非空字符串 | 长度1-35 |  |" in markdown


def test_materializer_projects_locked_interface_code_over_candidate() -> None:
    candidate = _candidate()
    candidate["interface"]["metadata"][0] = {
        "key": "Interface Code",
        "value": "",
        "reviewNote": "原文未说明，待人工确认",
    }

    extraction = materialize_docir_semantic_candidate(
        candidate, interface_code="b2e0061"
    )

    assert extraction["interface"]["metadata"][0] == {
        "key": "Interface Code",
        "value": "b2e0061",
        "reviewNote": "",
    }


def test_ten_column_docir_wire_fails_closed() -> None:
    legacy = ("# Interface\n\n## Metadata\n\n| Key | Value | Review Note |\n"
              "|---|---|---|\n| Interface Code | b2e9999 |  |\n\n"
              "# Source Context / 来源上下文\n\n- 来源。\n\n"
              "# Envelope\n\n## Metadata\n\n| Key | Value | Review Note |\n"
              "|---|---|---|\n| Envelope Name | root |  |\n\n## Fields\n\n"
              "| Index | Or | Message Item | Mult. | Type | Required | 说明 | "
              "前置机校验点/格式 | 接口平台校验点 | Review |\n"
              "|---|---|---|---|---|---|---|---|---|---|\n"
              "| 1 |  | `root` |  | Object | Y | 根 |  |  |  |\n")

    result = validate_docir_markdown(legacy)

    assert "DOCIR_FIELDS_TABLE_CONTRACT" in {
        issue["code"] for issue in result["issues"]
    }


def test_required_evidence_conflict_preserves_candidate_evidence() -> None:
    candidate = _candidate()
    field = candidate["assembly"]["nodes"][0]["children"][0]
    field.update(
        required="N",
        description="付款账号。非空字符串1-35位",
        validation="账户已维护",
    )
    markdown = render_docir_extraction(
        materialize_docir_semantic_candidate(candidate)
    )

    result = validate_docir_markdown(markdown)

    issue = next(
        item
        for item in result["issues"]
        if item["code"] == "DOCIR_REQUIRED_EVIDENCE_CONFLICT"
    )
    assert "account" in issue["message"]
    assert "Required=N" in issue["message"]
    assert "付款账号。非空字符串1-35位" in issue["message"]


def test_missing_required_preserves_conditional_evidence() -> None:
    candidate = deepcopy(_candidate())
    field = candidate["assembly"]["nodes"][0]["children"][0]
    field.update(
        required="",
        description="收款人开户行名称。可空字符串0-70位",
        validation="当收款行联行号为空时，此项为必填",
    )
    markdown = render_docir_extraction(
        materialize_docir_semantic_candidate(candidate)
    )

    result = validate_docir_markdown(markdown)

    issue = next(
        item
        for item in result["issues"]
        if item["code"] == "DOCIR_SEMANTIC_VALUE_MISSING"
    )
    assert "account" in issue["message"]
    assert "Required=<empty>" in issue["message"]
    assert "当收款行联行号为空时，此项为必填" in issue["message"]


def test_invalid_required_issue_preserves_item_and_current_value() -> None:
    markdown = render_docir_extraction(
        materialize_docir_semantic_candidate(_candidate())
    ).replace(
        "| 2.1 |  | \u3000`account` |  | String | Y |",
        "| 2.1 |  | \u3000`account` |  | String | 不需要 |",
    )

    result = validate_docir_markdown(markdown)

    issue = next(
        item for item in result["issues"] if item["code"] == "DOCIR_REQUIRED"
    )
    assert "item=account" in issue["message"]
    assert "Required=不需要" in issue["message"]


def test_required_evidence_examples_do_not_create_false_conflicts() -> None:
    cases = [
        ("C", "可空字符串0-70位", "当收款行联行号为空时，此项为必填"),
        ("C", "可空，若不为空只为数字", "交易类型为2时上送有效，且非空"),
        ("N", "收款人电子邮件地址", "可空；非空时包含@，3-80位"),
        ("N", "可空字符串0-35位", "如果不为空则字符1-20位"),
    ]
    for required, description, validation in cases:
        candidate = _candidate()
        candidate["assembly"]["nodes"][0]["children"][0].update(
            required=required,
            description=description,
            validation=validation,
        )
        result = validate_docir_markdown(
            render_docir_extraction(materialize_docir_semantic_candidate(candidate))
        )
        assert "DOCIR_REQUIRED_EVIDENCE_CONFLICT" not in {
            issue["code"] for issue in result["issues"]
        }


def test_cross_field_requirement_is_reviewed_without_changing_current_required() -> None:
    candidate = _candidate()
    candidate["assembly"]["nodes"][0]["children"][0].update(
        required="Y",
        description="收款账号。非空字符串1-35位",
        validation="中行账户且长度18位时必须上送收款行联行号",
    )
    result = validate_docir_markdown(
        render_docir_extraction(materialize_docir_semantic_candidate(candidate))
    )

    codes = {issue["code"] for issue in result["issues"]}
    assert "DOCIR_REQUIRED_EVIDENCE_CONFLICT" not in codes
    assert "DOCIR_REQUIRED_EVIDENCE_AMBIGUOUS" in codes


def test_conditions_reject_field_constraints_without_an_explicit_branch() -> None:
    candidate = _candidate()
    candidate["assembly"]["conditions"] = [
        "b2e0061-rq 不超过1000笔",
        "insid 非空字符串，长度1-32，客户号下不能重复",
        "actacn 非空字符串1-35位，如果是中行账户且长度18位，则必须上送toibkn",
    ]

    result = validate_docir_markdown(
        render_docir_extraction(materialize_docir_semantic_candidate(candidate))
    )

    issues = [
        issue
        for issue in result["issues"]
        if issue["code"] == "DOCIR_CONDITION_NOT_EXPLICIT_BRANCH"
    ]
    assert [issue["path"] for issue in issues] == [
        "ASSEMBLY.Conditions[1]",
        "ASSEMBLY.Conditions[2]",
        "ASSEMBLY.Conditions[3]",
    ]


def test_conditions_accept_explicit_branches_and_no_condition_marker() -> None:
    candidate = _candidate()
    candidate["assembly"]["conditions"] = [
        "当 transtype=2 时，obssid 必须非空。",
        "comacn 为空时使用付款账户，否则使用 comacn。",
        "transtype 为空时表示普通转账；非空时只能为1或2。",
        "if transtype=2, then obssid must be non-empty.",
    ]
    candidate["parse"]["conditions"] = ["原文未提供可确认条件。"]

    result = validate_docir_markdown(
        render_docir_extraction(materialize_docir_semantic_candidate(candidate))
    )

    assert "DOCIR_CONDITION_NOT_EXPLICIT_BRANCH" not in {
        issue["code"] for issue in result["issues"]
    }
