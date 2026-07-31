# ADR-0004: SchemaIR 作为事实源，Schema Workbook 作为人工配置交付物

## Status

Accepted. Partially superseded by `ADR-0006-configir-and-configuration-workbook.md`.

## Date

2026-06-16

## Context

本项目早期目标曾包含由确定性 Rule Engine 基于 `Final SchemaIR` 生成目标系统 Import JSON Draft。接入 `b2eboc` 样例后，目标导出 JSON 暴露出较高适配成本：同一接口存在 `ASSEMBLY` / `PARSE` 两个方向，导出 JSON 中包含历史 ID、父子引用、目标系统状态字段和导入模板字段。

这些字段不完全来自银行 raw doc。若继续以 Import JSON 为最终目标，项目会需要维护目标系统导入适配器、例外清单和兼容性校验，复杂度会超过当前“辅助配置人员人工配置”的核心目标。

同时，配置人员真正需要的是一份可审计、可筛选、可核对、可指导人工配置的字段清单。Excel workbook 更适合承载人工配置工作流，但不适合作为系统内部事实源。

## Decision

项目采用以下产物边界：

- `Final SchemaIR` 是系统内部事实源。
- `schemair-validation-result.json` 是 `Final SchemaIR` 是否可用于生成交付物的机器校验证据。
- Schema Workbook 是面向配置人员的人工配置交付物。
- Schema Workbook 必须由 `Final SchemaIR` 确定性生成。
- 系统不再追求直接或间接生成目标系统 Import JSON。

本 ADR supersedes ADR-0001 中“Import JSON Draft 作为确定性最终产物”的部分。ADR-0001 中 Human Review、Validator 和 deterministic generation 作为可信边界的决策仍然有效。

状态说明：ADR-0006 将“Final SchemaIR 单一事实源”和“Workbook 只读取 Final SchemaIR”调整为 Final SchemaIR / Final ConfigIR 双事实源及双模型输入，并将 Schema Workbook 调整为 Configuration Workbook。本 ADR 中“不生成 Import JSON”“Excel 不是事实源”“确定性生成”的决定继续有效。

## Alternatives Considered

### 继续生成 Import JSON

Pros:

- 更接近自动化导入。
- 如果目标系统导入格式稳定，后续可以减少人工配置步骤。

Cons:

- 需要维护目标系统导入适配规则和例外清单。
- 导出 JSON 中的历史 ID、父子引用和状态字段不是 raw doc 的自然产物。
- 适配成本会掩盖文档解析、SchemaIR 校验和人工 Review 的核心价值。

Why not chosen:

- 当前项目目标是降低人工整理和核对成本，不是建设目标系统导入适配器。

### 直接以 Excel 作为事实源

Pros:

- 配置人员最容易直接阅读和编辑。
- 交付物与人工工作流一致。

Cons:

- Excel 二进制 diff 和回归验证成本高。
- 样式、筛选和手工编辑会污染事实源。
- 后续重新生成、比对和自动化测试困难。

Why not chosen:

- 不满足可回归、可机器校验和可追溯的工程要求。

### 同时维护 Import JSON 和 Schema Workbook

Pros:

- 兼顾人工配置和未来自动导入。

Cons:

- 双产物会显著增加设计、验证和维护成本。
- 两个产物之间容易产生一致性问题。

Why not chosen:

- 当前阶段应先证明 SchemaIR 和人工配置工作簿的价值，不提前承担导入自动化成本。

## Consequences

- 所有实现应优先保证 `Final SchemaIR` 的完整性、可校验性和可回归性。
- Workbook Generator 不得补业务字段，不得静默丢弃不确定字段。
- Workbook 回归应读取 xlsx 做结构化断言，不比较整个二进制文件。
- 与当前 raw doc 样例绑定的历史导出 JSON 可保留为 reference，但不得作为目标产物、Workbook Generator 输入或阶段成功条件；过期 toy 样例应清除。
- 如果未来重新启动 Import JSON 支持，必须通过新的 ADR 明确范围、兼容策略和维护成本。
