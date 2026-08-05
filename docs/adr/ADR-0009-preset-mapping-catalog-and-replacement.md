# ADR-0009: 预设 Mapping Catalog 与 Replacement 执行语义

## Status

Accepted. Amends ADR-0007 and ADR-0008 for MAPPING and Replacement.

## Date

2026-08-04

## Context

早期资料将 MAPPING 描述成模板内联 source-target entries，并且没有 Replacement 实例，因此 ADR-0008 与后续设计把两项能力排除出 P0。

补充的 `mapping.txt`、`others.json` 和业务确认表明，目标系统实际维护预设 Mapping catalog：模板配置 MAPPING 或 Replacement 时只选择一个全局唯一 `mappingRuleName`。正式导出会嵌入所选规则的 snapshot，但配置动作和稳定引用仍然是规则名称。

MAPPING 与 Replacement 共享同一套 String source-target entries，但执行对象不同。如果把两者都解释成完整值查表，特殊字符删除规则将无法处理包含普通文本的字符串；如果把 MAPPING 解释成片段替换，又会掩盖完整业务值未配置的错误。

## Decision

### Catalog ownership

- 版本化规则包使用 `mappings.yaml` 保存预设 Mapping catalog。
- `mappingRuleName` 在 catalog 内全局唯一，是 Template IR 和 Workbook 的稳定引用。
- source、target 和所有 Function 输入、参数、返回值的数据类型均为 String。
- Template IR 不内联 entries；导出中的 snapshot 只用于来源对照。
- 当前 `mappings.yaml` 是已提供资料的样例子集，不声称覆盖目标系统全量 catalog。

### MAPPING Value Expression

- 输入只能是一个 String `FIELD_REF`。
- expression 只能选择一个 `mappingRuleName`。
- 对完整输入 String 做 source 精确匹配并返回 target。
- 未匹配必须报错；不得透传、返回空值或使用隐式默认。

### Replacement processing policy

- 每个 field config 最多选择一个 `mappingRuleName`。
- Replacement 在 Value Expression 完成后处理结果 String。
- 命中片段替换为 target；空 target 删除命中片段。
- 未命中的内容原样保留。

MAPPING 与 Replacement 共享 catalog reference，但 Validator 必须按各自执行语义校验，不能合并成同一种 expression。

### P0 scope

MAPPING 与 Replacement 纳入 P0 InterfaceTemplateIR、Validator、Configuration Workbook 和专项 golden regression。b2e0061 正式模板没有实际 MAPPING/Replacement 行时，不得伪造银行 fixture；使用补充样例验证 contract 和 Workbook 表达。

## Alternatives Considered

### 在 Template IR 内联 mapping entries

Pros:

- 单个 IR 自包含全部 source-target 数据。

Cons:

- 与真实“选择预设 `mappingRuleName`”的配置动作不一致。
- 同一规则被复制到多个模板，无法稳定治理、复用和审计版本。
- 导出 snapshot 容易被误认为模板拥有的配置事实。

Why not chosen:

- 预设 catalog 已由真实资料和业务确认建立。

### MAPPING 与 Replacement 使用相同执行算法

Pros:

- 实现结构更少。

Cons:

- 完整值查表无法正确表达字符串内特殊字符删除。
- 片段替换无法对未知完整业务值 fail closed。

Why not chosen:

- 两者只共享规则引用，不共享匹配边界与 unmatched 行为。

### 继续排除出 P0

Pros:

- P0 实现范围更小。

Cons:

- 已确认的核心 Value Mode 和 processing policy 仍无法进入可信链路。
- Workbook 无法表达真实目标系统配置。

Why not chosen:

- 当前资料已足以形成确定性契约和校验。

## Consequences

- `configuration-rules/v1` 新增 `mappings.yaml`，并将 MAPPING/Replacement 从 documented-only 改为 P0 能力。
- InterfaceTemplateIR 需要分别定义 MAPPING expression 和单一 Replacement rule reference。
- Validator 必须校验 catalog 引用、String 类型、单规则基数和各自 unmatched 行为。
- Workbook 展示 `mappingRuleName`，不复制 source-target entries。
- `others.json` 中的公司名称 target 必须脱敏，且占位值不得进入 Final fixture 或生成输入。
- `redacted: true` 的 Mapping rule 只能用于结构验证；Validator 必须拒绝 Final Template 引用。
