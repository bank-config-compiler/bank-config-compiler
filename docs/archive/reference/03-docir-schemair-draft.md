# DocIR / SchemaIR 参考草案

## Status

Archived. Not accepted schema. Replaced by the current IR design under `docs/design/`.

## Date

2026-05-27

## Context

本文从 `tmp/docs/docir.md` 和 `tmp/docs/schemair.md` 整理候选中间表示。当前正式结构以 `docs/design/02-intermediate-representations.md` 为准；本文只保留为低优先级参考，不作为实现契约。

## DocIR 候选定义

DocIR 是银行接口文档的标准化 Markdown 版本。

它不是最终业务语义模型，而是：

```text
适合 LLM 和 Human Review 的强结构化工程文档。
```

候选职责：

- 保留原始文档中的字段表。
- 保留章节结构。
- 保留 XML/JSON 示例。
- 保留条件说明。
- 清洗格式噪声。
- 统一为稳定 Markdown。

候选非职责：

- 不直接判断最终字段类型是否为 string / node / list。
- 不生成 Schema Workbook。
- 不表达系统最终配置逻辑。
- 不执行字段映射规则。

## DocIR 候选模板

````md
# Message

Message Name:
Message Type:
Format:
Version:

---

# Section: <section name>

## Description

<section description>

## Fields

| Field Name | XML Path | Type | Length | Occurs | Required | Description |
|---|---|---|---|---|---|---|
| MsgId | GrpHdr.MsgId | String | 35 | 1..1 | M | Message Identification |

## Conditions

- <condition text>

## XML Example

```xml
<GrpHdr>
  <MsgId>ABC123</MsgId>
</GrpHdr>
```
````

## DocIR 候选 Review 要点

Human Review 可重点检查：

- 字段表是否完整。
- 列是否错位。
- 字段是否遗漏。
- XML/JSON Path 是否明显错误。
- Section 是否合并或拆分正确。
- 条件说明是否保留。
- XML/JSON 示例是否保留。

## DocIR 候选质量标准

候选标准：

- 所有字段定义表可读。
- 字段行不出现明显错列。
- 必输、长度、类型、Occurs 不丢失。
- 重要条件说明不丢失。
- 能被后续 SchemaIR Extractor 稳定读取。

待讨论点：

- DocIR 是纯规范化原文，还是允许包含推导信息。
- XML/JSON Path 可推导时是否直接填入，还是标记为推导。
- `REVIEW` 标记具体触发条件。
- 是否需要字段级 sourceText。

## SchemaIR 候选定义

SchemaIR 是银行接口和报文结构的语义中间表示，使用 JSON 格式。

候选用途：

- 机器校验。
- Human Review。
- Workbook Generator 输入。
- 后续扩展到 DTO、Mock、Diff、Mapping 等能力。

## SchemaIR 候选顶层结构

```json
{
  "interfaceCode": "b2e0061",
  "interfaceName": "公对私转账汇款",
  "messageFormat": "XML",
  "version": "120",
  "sourceDocument": "docs/reference/samples/b2eboc/b2e0061.md",
  "messages": []
}
```

## SchemaIR 候选 message 结构

```json
{
  "functionType": "ASSEMBLY",
  "messageName": "b2e0061-rq",
  "rootPath": "Root.bocb2e.trans.trn-b2e0061-rq",
  "description": "组装请求报文",
  "fields": []
}
```

## SchemaIR 候选字段结构

```json
{
  "path": "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.acttyp",
  "fieldName": "acttyp",
  "displayName": "收款账户类型",
  "parentPath": "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn",
  "level": 5,
  "nodeKind": "XML_ELEMENT",
  "dataType": "string",
  "format": null,
  "length": {
    "max": 3,
    "min": 0,
    "raw": "0-3"
  },
  "required": false,
  "multiple": false,
  "hasChildren": false,
  "occurs": "0..1",
  "description": "收款账户类型",
  "conditionText": null,
  "sourceText": "| <acttyp> | 收款账户类型 | 数码 长度0-3 | ... |",
  "confidence": 0.95,
  "uncertain": false,
  "uncertainReason": null,
  "reviewNote": null,
  "configGuidance": null
}
```

## nodeKind 候选枚举

- `XML_ELEMENT`
- `XML_ATTRIBUTE`
- `JSON_OBJECT`
- `JSON_ARRAY`
- `SCALAR`

## dataType 候选枚举

- `string`
- `integer`
- `decimal`
- `boolean`
- `date`
- `datetime`
- `object`
- `array`

## required 候选规则

| 原文 | SchemaIR |
|---|---|
| M / Mandatory / Required / 必输 | `true` |
| O / Optional / 可选 | `false` |
| C / Conditional / 条件必输 | `false`，并保留条件说明 |

## multiple 候选规则

| 原文 | SchemaIR |
|---|---|
| `1..n` | `true` |
| `0..n` | `true` |
| List / Array / Repeating | `true` |
| `1..1` / 空 | `false` |

## sourceText 候选要求

每个字段必须有 `sourceText`。

没有 `sourceText` 的字段必须标记为不确定：

```json
{
  "uncertain": true,
  "uncertainReason": "缺少原文证据"
}
```

## Validator 候选规则

- `interfaceCode` 非空。
- `messageFormat` 属于允许枚举。
- `messages` 至少包含一个 message。
- `functionType` 属于允许枚举。
- `path` 非空。
- `fieldName` 非空。
- `nodeKind` 属于允许枚举。
- `dataType` 属于允许枚举。
- `required` 是 boolean。
- `multiple` 是 boolean。
- `hasChildren` 是 boolean。
- `confidence` 在 0 到 1 之间。
- `sourceText` 非空。
- 同一 message 内 `path` 不重复。
- `parentPath` 存在或可推导。
- `hasChildren`、`multiple`、`dataType`、`nodeKind` 不冲突。

## SchemaIR 候选 Review 边界

Human 可修改：

- `path`
- `fieldName`
- `dataType`
- `required`
- `multiple`
- `hasChildren`
- `description`
- `uncertain`

Human 不建议修改：

- `confidence`
- `sourceText`

待讨论点：

- 字段覆盖率如何验收。
- sourceText 粒度。
- 推导字段是否需要单独来源标记。
- `confidence` 是否保留，还是只保留 `uncertain`。
