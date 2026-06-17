# IR 字段参考

## Status

Draft. Applies to P0-T2 expected DocIR / SchemaIR work.

## 1. 目的

本文解释 DocIR 和 SchemaIR 字段含义，避免后续 agent 或实现者把候选字段误解为目标系统导入格式。

正式字段结构以 `docs/design/intermediate-representations.md` 为准；本文用于解释 review 规则和字段使用方式。

## 2. DocIR 字段

### Metadata 表格

`Interface`、`Envelope` 和 `Message` 必须包含 `## Metadata` 表格。

| 列 | 含义 |
|---|---|
| `Key` | 元数据名称，例如 `Interface Code`、`Function Type`、`Root Path`。 |
| `Value` | 从 raw doc 直接得到或人工确认后的值。 |
| `Review Note` | 不确定、推导或需要人工确认的说明。 |

### Fields 表格

| 列 | 含义 |
|---|---|
| `Field Name` | XML tag、attribute 或 JSON 字段名，不含父路径。 |
| `Path` | 规范化完整路径，用于区分重复 tag。 |
| `Type` | 面向人阅读的候选类型，例如 `String`、`Object`、`Decimal`。 |
| `Length` | raw doc 中的长度或格式说明，不强行规范成唯一数字。 |
| `Occurs` | 出现次数，例如 `1..1`、`0..1`、`0..1000`。 |
| `Required` | `Y`、`N` 或 `C`。`C` 表示条件必填。 |
| `Description` | 字段业务说明。 |
| `Condition / Review` | 条件、枚举、冲突、推导说明和人工 review 提醒。 |

DocIR 中的 `Path` 可以由表格层级推导，但必须在 review 信息中保留不确定点。DocIR 不负责把复杂条件转换为 DSL。

## 3. SchemaIR 顶层字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `interfaceCode` | string | 接口编码，例如 `b2e0061`。 |
| `interfaceName` | string | 接口名称。 |
| `messageFormat` | string | 报文格式，当前候选为 `XML` 或 `JSON`。 |
| `version` | string/null | 便于展示的候选协议版本。不确定性由 `envelope.fields` 中的 attribute 字段承载。 |
| `sourceDocument` | string | SchemaIR 来源文档路径。 |
| `envelope` | object | 可复用 BOCB2E envelope/head/trans 模型。 |
| `messages` | array | 交易消息集合，当前按 `ASSEMBLY` / `PARSE` 区分。 |

## 4. SchemaIR 字段对象

| 字段 | 类型 | 含义 |
|---|---|---|
| `path` | string | 唯一完整路径。重复 tag 通过 path 区分。 |
| `fieldName` | string | 当前节点名称。XML attribute 不带 `@`。 |
| `displayName` | string/null | 面向配置人员的中文名称或说明。 |
| `parentPath` | string/null | 父节点路径。root 字段可为 `null`。 |
| `level` | number | 路径层级，用于 workbook 缩进和排序。 |
| `nodeKind` | string | `XML_ELEMENT`、`XML_ATTRIBUTE`、`JSON_OBJECT`、`JSON_ARRAY` 或 `SCALAR`。 |
| `dataType` | string | 标准化类型，例如 `string`、`decimal`、`date`、`object`。 |
| `format` | string/null | 格式提示，例如 `YYYYMMDD`、`HHMMSS`、`email`。 |
| `length` | object | `min`、`max`、`raw`。冲突或非数值格式可只保留 `raw`。 |
| `required` | boolean | 普通必填。条件必填字段用 `false`，条件进入 `conditionText`。 |
| `multiple` | boolean | 是否为重复节点或多笔记录。 |
| `hasChildren` | boolean | 是否存在子字段。 |
| `occurs` | string/null | 原文或推导的出现次数。 |
| `description` | string/null | 字段说明。 |
| `conditionText` | string/null | 条件必填、枚举、平台校验和约束说明。 |
| `sourceText` | string | 字段行级来源证据。 |
| `evidence` | object | 来源类型和推导说明。 |
| `confidence` | number | 0 到 1 的候选置信度。 |
| `uncertain` | boolean | 是否需要人工确认。 |
| `uncertainReason` | string/null | 不确定原因。 |
| `reviewNote` | string/null | 面向 human reviewer 的补充说明。 |
| `configGuidance` | string/null | 面向配置人员的指导，不作为 raw doc 事实。 |

## 5. evidence.kind

| 值 | 含义 | Review 要求 |
|---|---|---|
| `DIRECT` | 字段事实直接来自 raw doc 字段行或明确上下文。 | 常规 review。 |
| `DERIVED` | 由表格层级、路径规则或上下文推导。 | 至少进入注意级 review。 |
| `ASSUMED` | 为保持结构完整而临时假设。 | 必须设置 `uncertain=true` 并进入重点 review。 |

## 6. confidence 阈值

| 范围 | 级别 | 处理 |
|---|---|---|
| `>= 0.9` | 常规 | 可抽查。 |
| `0.7 - 0.89` | 注意 | 进入 `review-notes.md` 的建议关注区。 |
| `< 0.7` | 重点 | 进入 `review-notes.md` 的必须确认区。 |

只要 `uncertain=true`，无论 confidence 分值多少，都必须进入 review notes 和 workbook warnings。

## 7. 类型策略

- XML 文本默认是 `string`。
- 金额字段使用 `decimal`。
- 日期字段使用 `date`，并在 `format` 中保留 `YYYYMMDD` 等格式。
- 时间字段如果 raw doc 只给出文本格式，保留 `string`，在 `format` 中写 `HHMMSS`。
- 账号、联行号、币种、交易代码、流水号和枚举代码保留 `string`，避免丢失前导零或编码语义。

## 8. review-notes.md 结构

每次 DocIR / SchemaIR draft 都应生成 `review-notes.md`，并按以下顺序组织：

1. `必须确认`：影响字段是否存在、path、required、occurs、类型、版本和配置正确性的事项。
2. `建议关注`：推导字段、长度冲突、平台/前置机约束差异。
3. `低风险说明`：已保留但暂不影响 expected IR 的背景说明。
4. `历史导出 JSON 对照`：仅记录差异或对照结论，不把导出 JSON 作为字段来源。
