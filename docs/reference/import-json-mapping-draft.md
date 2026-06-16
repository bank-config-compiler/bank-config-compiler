# Import JSON Mapping 参考草案

## Status

Superseded reference. Current project target is Schema Workbook, not Import JSON.

## Date

2026-05-27

## Context

本文从 `tmp/docs/import-json.md` 整理候选 Import JSON 结构和基础映射规则。该方向已被 `docs/adr/ADR-0004-schemair-and-workbook-artifacts.md` supersede，本文仅作为历史参考保留。

当前正式文档已明确：项目不再以 Import JSON 作为目标产物，`Final SchemaIR` 是内部事实源，Schema Workbook 是面向配置人员的人工配置交付物。

## 候选定义

Import JSON 是银企直连系统可导入或可预览的配置 JSON。

MVP 中 Import JSON 只生成草稿，不直接落库。

Import JSON 只能由 Rule Engine 基于 Final SchemaIR 生成，禁止由 LLM 直接生成。

## 候选示例

```json
{
  "standardCode": "ISO20022",
  "messageCode": "pain.001",
  "messageName": "CustomerCreditTransferInitiation",
  "sceneCode": "BANK_PAYMENT_IMPORT",
  "fieldConfigs": [
    {
      "fieldCode": "GRP_HDR_MSG_ID",
      "fieldName": "MsgId",
      "fieldPath": "GrpHdr.MsgId",
      "fieldType": "STRING",
      "controlType": "INPUT",
      "required": true,
      "maxLength": 35,
      "parentFieldCode": "GRP_HDR",
      "level": 2,
      "repeated": false,
      "source": "AI_MVP",
      "status": "DRAFT"
    }
  ]
}
```

## fieldCode 候选规则

由 `path` 生成：

```text
GrpHdr.MsgId → GRP_HDR_MSG_ID
PmtInf.CdtTrfTxInf → PMT_INF_CDT_TRF_TX_INF
```

待确认：

- 是否符合真实系统字段编码规范。
- 缩写、大小写、重复字段冲突如何处理。
- parentFieldCode 是否使用同一规则生成。

## fieldType 候选映射

| SchemaIR | Import JSON |
|---|---|
| `string` | `STRING` |
| `integer` | `INTEGER` |
| `decimal` | `DECIMAL` |
| `boolean` | `BOOLEAN` |
| `date` | `DATE` |
| `datetime` | `DATETIME` |
| `object` | `NODE` |
| `array` | `LIST` |

## node/list 候选规则

```text
hasChildren=true + multiple=false → NODE
hasChildren=true + multiple=true → LIST
hasChildren=false → 基础字段类型
```

待确认：

- `dataType=array` 与 `hasChildren=false` 是否允许。
- group 类型原文如何映射。
- list item 是否需要独立字段配置。

## controlType 候选映射

| fieldType | controlType |
|---|---|
| `STRING` | `INPUT` |
| `INTEGER` | `NUMBER_INPUT` |
| `DECIMAL` | `NUMBER_INPUT` |
| `DATE` | `DATE_PICKER` |
| `DATETIME` | `DATETIME_PICKER` |
| `BOOLEAN` | `SWITCH` |
| `NODE` | `CONTAINER` |
| `LIST` | `TABLE` |

待确认：

- 真实系统是否使用这些 controlType。
- controlType 是否能完全从 SchemaIR 推导。
- 是否存在需要人工补充的 UI 控件配置。

## condition 候选规则

MVP 仅保留条件描述，不实现复杂 condition DSL。

如果 SchemaIR 中存在条件说明，可放入 `ext`：

```json
{
  "ext": {
    "conditionText": "Required when ..."
  }
}
```

待确认：

- 真实 Import JSON 是否支持 `ext`。
- condition 文本是否应进入字段配置、报文配置，还是独立规则配置。
- 后续是否需要 condition DSL。

## 等待用户样例后必须确认的事项

- 顶层字段模型。
- 字段配置数组名称。
- 字段编码规范。
- 父子关系表达方式。
- list / node 真实配置规则。
- 必填、长度、类型和控件字段的真实名称。
- draft/source/status 是否真实存在。
- 无法从文档推导的信息如何表达。
