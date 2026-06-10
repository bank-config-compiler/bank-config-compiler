# DocIR / SchemaIR 设计

## Status

Draft.

## 1. DocIR

DocIR 是银行接口文档的标准化 Markdown 版本。

DocIR 不是最终业务语义模型，而是适合 LLM 和 Human Review 的强结构化工程文档。

### 职责

- 保留原始文档中的字段表。
- 保留章节结构。
- 保留 XML/JSON 示例。
- 保留条件说明。
- 清洗格式噪声。
- 统一为稳定 Markdown。
- 标记无法确认的信息和需要人工检查的位置。

### 非职责

- 不直接判断最终字段类型是否为 string / node / list。
- 不生成 Import JSON。
- 不表达系统最终配置逻辑。
- 不执行字段映射规则。

### 最小模板

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

### Review 要点

- 字段表是否完整。
- 列是否错位。
- 字段是否遗漏。
- XML/JSON Path 是否明显错误。
- Section 是否合并或拆分正确。
- 条件说明是否保留。
- XML/JSON 示例是否保留。

## 2. SchemaIR

SchemaIR 是银行报文结构的语义中间表示，使用 JSON 格式。

### 职责

- 支持机器校验。
- 支持 Human Review。
- 作为 Rule Engine 输入。
- 为后续 DTO、Mock、Diff、Mapping 等能力保留扩展基础。

### 顶层结构

```json
{
  "messageName": "pain.001",
  "messageType": "payment",
  "format": "ISO20022",
  "version": "001.001.03",
  "fields": []
}
```

### 字段结构

```json
{
  "path": "GrpHdr.MsgId",
  "fieldName": "MsgId",
  "displayName": "Message Identification",
  "parentPath": "GrpHdr",
  "level": 2,
  "dataType": "string",
  "format": null,
  "length": {
    "max": 35,
    "min": null,
    "raw": "35"
  },
  "required": true,
  "multiple": false,
  "hasChildren": false,
  "occurs": "1..1",
  "description": "Message Identification",
  "sourceText": "MsgId | GrpHdr.MsgId | String | 35 | 1..1 | M | Message Identification",
  "confidence": 0.95,
  "uncertain": false,
  "uncertainReason": null
}
```

### dataType 候选枚举

- `string`
- `integer`
- `decimal`
- `boolean`
- `date`
- `datetime`
- `object`
- `array`

### required 候选规则

| 原文 | SchemaIR |
|---|---|
| M / Mandatory / Required / 必输 | `true` |
| O / Optional / 可选 | `false` |
| C / Conditional / 条件必输 | `false`，并保留条件说明 |

### multiple 候选规则

| 原文 | SchemaIR |
|---|---|
| `1..n` | `true` |
| `0..n` | `true` |
| List / Array / Repeating | `true` |
| `1..1` / 空 | `false` |

### sourceText 要求

每个字段必须有 `sourceText`。没有 `sourceText` 的字段必须标记为不确定：

```json
{
  "uncertain": true,
  "uncertainReason": "缺少原文证据"
}
```

## 3. Validator 候选规则

- `path` 非空。
- `fieldName` 非空。
- `dataType` 属于允许枚举。
- `required` 是 boolean。
- `multiple` 是 boolean。
- `confidence` 在 0 到 1 之间。
- `sourceText` 非空。
- `path` 不重复。
- `parentPath` 存在或可推导。
- `hasChildren`、`multiple`、`dataType` 不冲突。

## 4. 待确认点

- DocIR 是纯规范化原文，还是允许包含推导信息。
- XML/JSON Path 可推导时是否直接填入，还是标记为推导。
- `REVIEW` 标记具体触发条件。
- 是否需要字段级 `sourceText`。
- SchemaIR 字段覆盖率如何验收。
- `sourceText` 粒度。
- 推导字段是否需要单独来源标记。
- `confidence` 是否保留，还是只保留 `uncertain`。
