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
- 不生成 Schema Workbook。
- 不表达目标系统配置页面细节。
- 不执行字段映射规则。

### 最小模板

````md
# Interface

Interface Code:
Interface Name:
Message Format: XML
Version:

---

# Message: ASSEMBLY

Message Name:
Root Path:

## Description

<section description>

## Fields

| Field Name | Path | Type | Length | Occurs | Required | Description |
|---|---|---|---|---|---|---|
| acttyp | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.acttyp | String | 0-3 | 0..1 | N | 收款账户类型 |

## Conditions

- <condition text>

## Example

```xml
<acttyp>119</acttyp>
```
````

### Review 要点

- 字段表是否完整。
- 列是否错位。
- 字段是否遗漏。
- Path 是否明显错误。
- Section 是否合并或拆分正确。
- 条件说明是否保留。
- XML/JSON 示例是否保留。
- 请求组装和响应处理是否被正确区分为 `ASSEMBLY` / `PARSE`。

## 2. SchemaIR

SchemaIR 是银行接口和报文结构的语义中间表示，使用 JSON 格式。

`Final SchemaIR` 是系统内部事实源。Schema Workbook 必须由 `Final SchemaIR` 确定性生成。

### 职责

- 支持机器校验。
- 支持 Human Review。
- 作为 Workbook Generator 输入。
- 为后续 DTO、Mock、Diff、Mapping 等能力保留扩展基础。

### 顶层结构

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

### message 结构

```json
{
  "functionType": "ASSEMBLY",
  "messageName": "b2e0061-rq",
  "rootPath": "Root.bocb2e.trans.trn-b2e0061-rq",
  "description": "组装请求报文",
  "fields": []
}
```

`functionType` 候选枚举：

- `ASSEMBLY`：组装请求报文。
- `PARSE`：处理响应报文。

`messageFormat` 候选枚举：

- `XML`
- `JSON`

### 字段结构

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

### nodeKind 候选枚举

- `XML_ELEMENT`
- `XML_ATTRIBUTE`
- `JSON_OBJECT`
- `JSON_ARRAY`
- `SCALAR`

XML attribute 应作为字段建模，例如：

```json
{
  "path": "Root.bocb2e.@locale",
  "fieldName": "locale",
  "nodeKind": "XML_ATTRIBUTE"
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
| M / Mandatory / Required / 必输 / 非空 | `true` |
| O / Optional / 可选 / 可空 | `false` |
| C / Conditional / 条件必输 | `false`，并保留 `conditionText` |

### multiple 候选规则

| 原文 | SchemaIR |
|---|---|
| `1..n` | `true` |
| `0..n` | `true` |
| List / Array / Repeating / 多笔 | `true` |
| `1..1` / `0..1` / 空 | `false` |

### sourceText 要求

每个字段必须有 `sourceText`。没有 `sourceText` 的字段必须标记为不确定：

```json
{
  "uncertain": true,
  "uncertainReason": "缺少原文证据"
}
```

## 3. Validator 候选规则

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
- 父子路径关系可解释。
- `hasChildren`、`multiple`、`dataType`、`nodeKind` 不存在明显冲突。

Validator 失败时必须返回字段级错误列表，不能只返回通用失败信息。

## 4. Workbook Generator 输入边界

Workbook Generator 只能读取：

- `Final SchemaIR`
- `schemair-validation-result.json`
- 任务上下文，例如生成时间和源文件名

Workbook Generator 不允许：

- 反向解析 Excel 作为事实源。
- 根据目标系统导入模板补业务字段。
- 静默丢弃 `uncertain=true` 字段。
- 把条件必填字段强行改成普通必填字段。

## 5. 待确认点

- DocIR 是纯规范化原文，还是允许包含推导信息。
- Path 可推导时是否直接填入，还是标记为推导。
- `REVIEW` 标记具体触发条件。
- SchemaIR 字段覆盖率如何验收。
- `sourceText` 粒度。
- 推导字段是否需要单独来源标记。
- `confidence` 是否保留，还是只保留 `uncertain`。
- `configGuidance` 是人工维护，还是由规则生成。
