# IR 字段参考

## Status

Draft. P0-T2 expected DocIR / SchemaIR remains a historical Review baseline; the SchemaIR v2 fields below describe the implemented P0-T3 machine contract.

## 1. 目的

本文解释 DocIR 和 SchemaIR 字段含义，避免后续 agent 或实现者把候选字段误解为目标系统导入格式。InterfaceStandardIR / InterfaceTemplateIR 的字段、版本绑定与取值表达式见 `docs/design/04-system-configuration-model.md`。

正式字段结构以 `docs/design/02-intermediate-representations.md` 为准；本文用于解释 review 规则和字段使用方式。

## 2. DocIR 字段

### Metadata 表格

`Interface`、`Envelope` 和 `Message` 必须包含 `## Metadata` 表格。

`# Source Context / 来源上下文` 必须明确区分目标接口字段表、共享 envelope 说明和其他交易代码的通用 XML 示例。通用示例可保留为 evidence 摘要，但不能把示例专属交易字段投影到目标接口 Message。

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
| `Mult.` | 只描述重复 `Object`，例如 `[0..1000]`；新生成的非重复字段留空，历史 `[0..1]/[1..1]` 继续兼容。 |
| `Type` | DocIR 类型只允许 `Object/String/Boolean/Date/Decimal`；容器由代码派生 `Object`，普通 leaf/attribute 默认 `String`。 |
| `Required` | `Y`、`N` 或 `C`。`C` 表示条件必填。 |
| `说明` | 字段业务说明，保留 raw doc 中的中文含义。 |
| `前置机校验点/格式` | raw doc 中前置机侧的格式或校验说明。 |
| `接口平台校验点` | raw doc 中接口平台侧的校验说明。 |
| `Review` | 不确定、冲突、推导说明和人工 review 提醒。 |

DocIR 主表不展示完整 `Path`，避免人工 review 时被长路径淹没。完整 path 由 SchemaIR 表达；DocIR 必须通过 `Index`、`Message Item` 缩进和 review 信息保留足够层级线索。`Index` 不是展示行号，不能用连续行号跨越层级；例如 `2.3.4` 的子节点应编号为 `2.3.4.1`，而不是后续行号 `2.17`。DocIR 不负责把复杂条件转换为 DSL。

真实 provider 的模型响应不直接承载本表 Markdown。内部 `docir-semantic-candidate/v1` 保存有序 XML element/attribute 树和语义属性，不保存由模型选择的 index/path/level；代码按固定 section root 与当前父子/兄弟顺序分配 Index，并从树规范化 Type、非重复 Mult.、U+3000、代码标记和固定列。candidate 只存在于临时 attempt evidence，不改变本页定义的公开 DocIR wire，也不能作为 SchemaIR 输入。

有 children 的节点和固定 `trans` 交接容器为 `Object`；普通 leaf/attribute 为 `String`，原文明示时可覆盖为 `Boolean/Date/Decimal`。只有重复 Object 填写 `Mult.`；空 Mult. 规范表示 maximum `1`，而不是 `0..n`。DocIR 不包含 Standard `Node` 或 Parse target `List`。

Draft 无法从原文直接确认 `Required` 时，该单元格留空，并在 `Review` 标记“原文未说明，待人工确认”。空 Required 表示待 Review，不能默认 `Y/N`。SchemaIR 的 `required` 与 occurs minimum 由 `Y/N/C` 确定，occurs maximum 由 `Mult.` 确定；显式 lower bound 与 Required 冲突时产生 Review WARNING，但投影以 Required 为准。

## 3. SchemaIR 顶层字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `contractVersion` | string | 固定为 `schemair/v2`。 |
| `schemaId` | string | 仓库内唯一、不可变的 kebab-case stable ID。 |
| `schemaVersion` | string | 不可变 artifact version，格式为 `v<正整数>`。 |
| `status` | string | `DRAFT | FINAL`。 |
| `review` | object | `status`、具名 reviewer、带时区 `reviewedAt` 和可空 note；Pending 不携带审批身份。 |
| `interfaceCode` | string | 接口编码，例如 `b2e0061`。 |
| `interfaceName` | string | 接口名称。 |
| `messageFormat` | string | 银行报文格式，当前只允许 `XML`。JSON 序列化不表示支持 JSON 银行报文。 |
| `protocolVersion` | string | 银行协议候选版本；它不是 artifact version，不确定性由 `envelope.fields` 中的 attribute 字段承载。 |
| `sourceDocument` | string | SchemaIR 来源文档路径。 |
| `envelope` | object | 可复用 BOCB2E envelope/head/trans 模型。 |
| `messages` | array | 交易消息集合，当前按 `ASSEMBLY` / `PARSE` 区分。 |

每个 `messages[]` 还保存方向级 `xmlEncoding` 与 `xmlEncodingEvidence[]`。evidence 记录 source kind/ref、observed value、`SUPPORTS | UNRESOLVED_CONFLICT | RESOLVED_CONFLICT` disposition 和 Review 说明；未处置冲突产生 blocking Warning。Final 值展示在 Workbook `Overview`，不投影成 Standard Field。b2e0061 的 ASSEMBLY、PARSE 两个方向已确认均为 canonical `UTF-8`。

## 4. SchemaIR 字段对象

| 字段 | 类型 | 含义 |
|---|---|---|
| `path` | string | 唯一完整路径。重复 tag 通过 path 区分。 |
| `fieldName` | string | 当前节点名称；XML attribute 保留 `@`，并与 path 最后一段完全一致。 |
| `displayName` | string | 面向配置人员的中文名称或说明。 |
| `parentPath` | string | 直接父节点路径；BOCB2E root 使用外部哨兵父路径 `Root`。 |
| `level` | number | SchemaIR 路径层级，用于校验父子关系和辅助 Review；Configuration Workbook 的目标字段层级与顺序以 InterfaceStandardIR 的 parentPath/fullPath 和 sequence 为准。 |
| `nodeKind` | string | `XML_ELEMENT`、`XML_ATTRIBUTE` 或 `SCALAR`。 |
| `dataType` | string | 标准化类型，例如 `string`、`decimal`、`date`、`object`。 |
| `format` | string/null | 格式提示，例如 `YYYYMMDD`、`HHMMSS`、`email`。 |
| `length` | object | `min`、`max`、`raw`。冲突或非数值格式可只保留 `raw`。 |
| `required` | boolean | 基础必填。条件必填字段使用 `false`，条件同时进入 `conditionText`；可结构化的银行条件另进入 `conditionalConstraints`。 |
| `multiple` | boolean | 是否为重复节点或多笔记录。 |
| `hasChildren` | boolean | 是否存在子字段。 |
| `occurs` | string | 原文或推导的 `min..max` 出现次数。 |
| `description` | string | 字段说明。 |
| `conditionText` | string/null | 银行原始条件必填、枚举、平台校验和约束说明；不因已结构化而删除。 |
| `sourceText` | string | 字段行级来源证据。 |
| `evidence` | object | 来源类型和推导说明。 |
| `confidence` | number | 0 到 1 的候选置信度。 |
| `uncertain` | boolean | 是否需要人工确认。 |
| `uncertainReason` | string/null | 不确定原因。 |
| `reviewNote` | string/null | 面向 human reviewer 的补充说明。 |

目标系统接口标准和模板配置不属于 SchemaIR 字段，分别由 InterfaceStandardIR 与 InterfaceTemplateIR 表达。

SchemaIR message 可以包含 `conditionalConstraints[]`，用于保存银行文档明确且落在当前最小规则集内的跨字段条件。每条约束至少具有 controlling field path、operator、target field path、effect、sourceText/evidence 和 Review 信息。P0 不把目的系统业务 Condition 写入这里，也不执行条件。

银行字段、路径、出现次数和约束以 raw-doc/Final SchemaIR 为准。正式导出中的 observed `@lang` 只保留在来源和 Review 证据中，不作为 Final SchemaIR 或 Standard 字段；b2e0061 Final Standard 已保留 raw-doc 的 `@security` 并排除 `vamflag`。这些投影决定不回写 P0-T2 审查前 Golden，而在 P0-T3 Final Standard 中落实。

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
4. `正式导出 JSON 对照`：记录差异或目标配置对照结论；导出不是 SchemaIR 字段来源，进入 Standard/Template 前仍需规则治理或人工确认。
