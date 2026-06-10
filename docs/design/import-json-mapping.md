# Import JSON Mapping 设计

## Status

Draft.

## 1. 设计边界

Import JSON 是银企直连系统可导入或可预览的配置 JSON。

当前阶段 Import JSON 只生成 Draft，不直接落库。Import JSON 只能由 Rule Engine 基于 Final SchemaIR 生成，禁止由 LLM 直接生成。

Import JSON 应贴近真实银企直连导入格式。用户提供真实或接近真实的 Import JSON 样例后，必须重新确认目标字段模型、字段命名、层级关系和兼容性边界。

## 2. 候选示例

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

该示例是候选结构，不是长期兼容承诺。

## 3. 候选映射规则

### fieldCode

由 `path` 生成：

```text
GrpHdr.MsgId → GRP_HDR_MSG_ID
PmtInf.CdtTrfTxInf → PMT_INF_CDT_TRF_TX_INF
```

待确认：

- 是否符合真实系统字段编码规范。
- 缩写、大小写、重复字段冲突如何处理。
- `parentFieldCode` 是否使用同一规则生成。

### fieldType

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

### node / list

```text
hasChildren=true + multiple=false → NODE
hasChildren=true + multiple=true → LIST
hasChildren=false → 基础字段类型
```

待确认：

- `dataType=array` 与 `hasChildren=false` 是否允许。
- group 类型原文如何映射。
- list item 是否需要独立字段配置。

### controlType

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

- 真实系统是否使用这些 `controlType`。
- `controlType` 是否能完全从 SchemaIR 推导。
- 是否存在需要人工补充的 UI 控件配置。

### condition

当前阶段仅保留条件描述，不实现复杂 condition DSL。

如果 SchemaIR 中存在条件说明，可候选放入 `ext`：

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

## 4. 用户样例到位后必须确认

- 顶层字段模型。
- 字段配置数组名称。
- 字段编码规范。
- 父子关系表达方式。
- list / node 真实配置规则。
- 必填、长度、类型和控件字段的真实名称。
- draft/source/status 是否真实存在。
- 无法从文档推导的信息如何表达。
