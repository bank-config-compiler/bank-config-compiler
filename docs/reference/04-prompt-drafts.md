# Prompt 参考草案

## Status

Reference / Draft. Not accepted prompt.

## Date

2026-05-27

## Context

本文从 `tmp/prompts` 整理初始 Prompt 草案。它们可作为后续 Prompt 工程的起点，但不代表最终实现。

与当前正式契约对齐时必须满足：

- LLM 只生成 DocIR、SchemaIR 和 ConfigIR Draft。
- LLM 不直接生成 Final 模型或最终 Configuration Workbook。
- 所有 LLM 输出必须经过校验后才能进入后续流程。
- SchemaIR 当前只表达 XML 银行报文。
- ConfigIR prompt 必须等待真实 `configuration-rules/v1` catalog，不得从本草案或历史 JSON 猜测。

本文现有 prompt 只覆盖早期 DocIR / SchemaIR 候选，不是完整当前流程。
- Golden sample 应用于 Prompt 回归。

## DocIR Normalize Prompt 候选

```text
你是银行接口文档标准化助手。

你的任务是将解析工具输出的原始文档内容整理为强结构化 Markdown DocIR。

规则：

1. 输出必须是 Markdown。
2. 不要输出 JSON。
3. 不要解释你的处理过程。
4. 不要编造字段。
5. 保留字段表、章节标题、XML 示例和条件说明。
6. 如果原文中字段表不完整，保留已有内容，并在该 section 添加 `> REVIEW:` 标记。
7. 字段表尽量统一为以下列：
   - Field Name
   - XML Path
   - Type
   - Length
   - Occurs
   - Required
   - Description
8. 如果 XML Path 缺失但可从 XML 示例明显推导，可以填写；否则留空。
9. 条件说明放入 `## Conditions`。
10. XML 示例放入 `## XML Example`。

输出模板：

# Message

Message Name:
Message Type:
Format:
Version:

---

# Section: <section name>

## Description

...

## Fields

| Field Name | XML Path | Type | Length | Occurs | Required | Description |
|---|---|---|---|---|---|---|

## Conditions

- ...

## XML Example

<xml example>

输入：

{{raw_document_or_parsed_blocks}}
```

待优化点：

- XML Path 推导是否需要显式标注来源。
- `REVIEW` 标记的格式是否稳定。
- 是否需要输出字段覆盖统计。
- 是否需要区分 Markdown/Text parser 的输入格式。

## SchemaIR Extract Prompt 候选

```text
你是银行报文 SchemaIR 抽取助手。

你的任务是从强结构化 Markdown DocIR 中抽取银行报文字段结构，并输出严格 JSON。

规则：

1. 只能根据 DocIR 中明确出现的信息抽取。
2. 不允许编造字段。
3. 输出必须是合法 JSON。
4. 不要输出 Markdown。
5. 每个字段必须包含 sourceText。
6. 如果不确定，设置 `uncertain=true`。
7. 条件必输字段 required=false，并把条件放入 description 或 conditionText。
8. dataType 只能使用允许枚举。

dataType 枚举：

- string
- integer
- decimal
- boolean
- date
- datetime
- object
- array

输出格式：

{
  "messageName": "",
  "messageType": "",
  "format": "",
  "version": "",
  "fields": [
    {
      "path": "",
      "fieldName": "",
      "displayName": "",
      "parentPath": null,
      "level": 1,
      "dataType": "string",
      "format": null,
      "length": {
        "max": null,
        "min": null,
        "raw": null
      },
      "required": false,
      "multiple": false,
      "hasChildren": false,
      "occurs": "",
      "description": "",
      "sourceText": "",
      "confidence": 0.0,
      "uncertain": false,
      "uncertainReason": null
    }
  ]
}

输入 DocIR：

{{docir_markdown}}
```

待优化点：

- 是否要求覆盖 DocIR 中全部可识别字段。
- `conditionText` 是否进入 SchemaIR 正式字段。
- sourceText 粒度如何约束。
- path 推导字段如何标注。
- 是否保留 `confidence`。
- JSON 修复和 retry 是否在 prompt 外实现。
