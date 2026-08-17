# ADR-0016: 收敛 DocIR Type、Multiplicity 与 Required 语义

## Status

Accepted. 本 ADR 局部 supersede ADR-0015 将 DocIR `type`、`multiplicity` 全部归为 LLM/Human 业务语义的决定；ADR-0015 的统一 materialization、Invalid Draft 与 Human Gate 继续有效。

## Date

2026-08-12

## Context

`docir-021` 成功发布了 49 fields 的真实 Invalid Draft，但旧 Validator 报出 75 个 ERROR：42 个来自空 `Mult.`、18 个来自空 `Type`，只有 15 个来自空 `Required`。raw-doc 并未为大多数普通 XML 字段声明出现次数或类型；继续要求模型填满三列，会把 XML 树已经能够确定的事实误报为业务缺失。

DocIR 只描述银行 XML 文档，不具有 Standard 的 `Node` 或 Parse target 的 `List`。代码已经掌握有序 XML element/attribute 树，因此可以规范化容器、叶子和非重复出现次数；但是代码仍不能从字段出现、表格行或 XML 示例证明银行是否要求该字段。

## Decision

### DocIR Type

- DocIR wire 继续只允许 `Object | String | Boolean | Date | Decimal`。
- 有 children 的节点和固定 `trans` 交接容器由代码物化为 `Object`。
- 普通 leaf 与 attribute 默认物化为 `String`。
- 只有来源明确支持时，模型可以提出 `Boolean | Date | Decimal`；数字编码、账号和枚举码仍是 `String`。
- 缺失 Type 不产生 ERROR。候选 Type 不受支持或与树结构冲突时，materializer 使用规范值，写入专用 Review marker，Validator 产生非阻塞 `DOCIR_TYPE_NORMALIZED` WARNING。

`Node` 只在 InterfaceStandardIR 中表示重复 Object；`List` 只属于 PARSE 的目标对象。二者都不得进入 DocIR 或 XML Standard 的 DocIR 类型集合。

### DocIR Multiplicity

- `Mult.` 只描述重复 Object。新生成的标量和非重复 Object 留空。
- 重复 Object 使用 `[min..max]`，例如 `[0..1000]`。
- 为保持已冻结 DocIR 兼容，Validator 继续接受历史非重复范围 `[0..1]` 与 `[1..1]`。
- 非法格式或重复标量候选被降为空值并写入专用 Review marker；Validator 产生 blocking `DOCIR_MULTIPLICITY_REJECTED` ERROR，不能与规范空值混淆。
- `Required` 与显式范围 lower bound 不一致时，Validator 产生非阻塞 `DOCIR_REQUIRED_MULTIPLICITY_CONFLICT` WARNING。

### DocIR Required 与 SchemaIR 投影

- 只有来源明确表达必输/非空、可选/可空或条件必填时，候选才分别使用 `Y`、`N`、`C`。
- 不从字段表、XML 示例或模型常识推断 Required。无可靠证据时留空、写入固定 Review marker，并产生 `DOCIR_SEMANTIC_VALUE_MISSING` ERROR。
- SchemaIR `required` 和 occurs minimum 由 DocIR Required 决定：`Y → true/1`，`N | C → false/0`。
- 空 `Mult.` 的 occurs maximum 固定为 `1`；显式范围只提供 maximum 和 `multiple`。因此 Required 与历史 lower bound 冲突时，SchemaIR 投影以 Required 为准。
- `C` 的条件文本和 evidence 仍由 SchemaIR candidate/Human 补充，不能由结构投影创造。

### Contract 版本与兼容性

- DocIR prompt 升级为 `draft-prompt/v14`。
- materializer 升级为 `docir-semantic-materializer/v2`。
- `docir-semantic-candidate/v1` shape、DocIR Markdown 列结构和 `docir-validation-result/v1` shape 不变。
- 已冻结历史 Final DocIR 及其 hash 不迁移、不改写；新语义只影响新 attempt 的 materialization 和当前内容的重新校验。

## Alternatives Considered

### 继续要求模型填满三列

这会制造大量与 raw-doc 无关的 ERROR，并让概率输出重复表达代码已经掌握的 XML 树事实，因此不采用。

### Type、Multiplicity、Required 全部使用默认值

Type 和非重复次数可以从结构规范化，但 Required 是银行业务约束。默认 `Y` 或 `N` 会掩盖真实不确定性，因此 Required 继续保留 Human Gate。

### 在 DocIR 引入 Node 或 List

这会混合银行 XML、目标系统 Standard 与 PARSE 输出对象三层模型。DocIR 保持 XML 类型集合，重复容器到 Standard `Node` 的映射留在下游；`List` 不进入 XML Standard。

## Consequences

- 新 DocIR Draft 的错误数更接近真实业务缺口，而不是空列数量。
- materializer 和 Validator 必须分别证明新生成规范与历史 wire 兼容性。
- Human 仍需逐项确认 Required、真实重复范围、来源冲突和字段完整性。
- `docir-021` 保持 immutable；v2 只读离线重放用于回归，不构成新的 generation lineage 或 Human approval。
