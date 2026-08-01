# IR 字段参考

## Status

Draft. Applies to P0-T2 expected DocIR / SchemaIR work.

## 1. 目的

本文解释 DocIR 和 SchemaIR 字段含义，避免后续 agent 或实现者把候选字段误解为目标系统导入格式。InterfaceStandardIR / InterfaceTemplateIR 的字段、版本绑定与取值表达式见 `docs/design/04-system-configuration-model.md`。

正式字段结构以 `docs/design/02-intermediate-representations.md` 为准；本文用于解释 review 规则和字段使用方式。

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
| `Index` | 面向人工 review 的结构编号，例如 `2`、`2.1`、`2.1.1`；同级递增最后一段，子节点追加一段。 |
| `Or` | 表达原文中的互斥选择关系；无互斥关系时留空。 |
| `Message Item` | XML item name，不带尖括号；attribute 使用 `@version`。可用缩进表达父子层级。 |
| `Mult.` | 出现次数，例如 `[1..1]`、`[0..1]`、`[0..1000]`。 |
| `Type` | 面向人阅读的候选类型，例如 `String`、`Object`、`Decimal`。 |
| `Required` | `Y`、`N` 或 `C`。`C` 表示条件必填。 |
| `说明` | 字段业务说明，保留 raw doc 中的中文含义。 |
| `前置机校验点/格式` | raw doc 中前置机侧的格式或校验说明。 |
| `接口平台校验点` | raw doc 中接口平台侧的校验说明。 |
| `Review` | 不确定、冲突、推导说明和人工 review 提醒。 |

DocIR 主表不展示完整 `Path`，避免人工 review 时被长路径淹没。完整 path 由 SchemaIR 表达；DocIR 必须通过 `Index`、`Message Item` 缩进和 review 信息保留足够层级线索。`Index` 不是展示行号，不能用连续行号跨越层级；例如 `2.3.4` 的子节点应编号为 `2.3.4.1`，而不是后续行号 `2.17`。DocIR 不负责把复杂条件转换为 DSL。

## 3. SchemaIR 顶层字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `interfaceCode` | string | 接口编码，例如 `b2e0061`。 |
| `interfaceName` | string | 接口名称。 |
| `messageFormat` | string | 银行报文格式，当前只允许 `XML`。JSON 序列化不表示支持 JSON 银行报文。 |
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
| `level` | number | SchemaIR 路径层级，用于校验父子关系和辅助 Review；Configuration Workbook 的目标字段层级与顺序以 InterfaceStandardIR 的 parentPath/fullPath 和 sequence 为准。 |
| `nodeKind` | string | `XML_ELEMENT`、`XML_ATTRIBUTE` 或 `SCALAR`。 |
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

目标系统接口标准和模板配置不属于 SchemaIR 字段，分别由 InterfaceStandardIR 与 InterfaceTemplateIR 表达。

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

每次 IR Draft 都应生成 `review-notes.md`。DocIR / SchemaIR Review notes 按以下顺序组织：

1. `必须确认`：影响字段是否存在、path、required、occurs、类型、版本和配置正确性的事项。
2. `建议关注`：推导字段、长度冲突、平台/前置机约束差异。
3. `低风险说明`：已保留但暂不影响 expected IR 的背景说明。
4. `历史导出 JSON 对照`：仅记录差异或对照结论，不把导出 JSON 作为字段来源。
