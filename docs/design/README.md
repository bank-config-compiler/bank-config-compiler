# Design 文档索引

## Status

Active.

## Purpose

`docs/design/` 记录系统设计、模块边界、四层中间表示、Configuration Workbook 生成边界和验证资产策略。

本目录不记录历史讨论流水账，也不替代需求文档。需求范围以 `docs/01-requirements.md` 和 `docs/phases/` 为准；关键技术决策以 `docs/adr/` 为准。

## Documents

- `01-system-overview.md`：总体链路、模块职责、可信边界和候选 workspace 结构。
- `02-intermediate-representations.md`：DocIR / SchemaIR / InterfaceStandardIR / InterfaceTemplateIR 的职责边界和衔接。
- `03-ir-field-reference.md`：DocIR / SchemaIR 字段含义、方向级 XML encoding、Review 规则和 confidence 阈值。
- `04-system-configuration-model.md`：Interface Standard / Template 生命周期、Standard 镜像、结构绑定、银行条件、取值表达式、omission 和 Validator 边界。
- `05-configuration-workbook.md`：Configuration Workbook 的 sheet、双端列来源矩阵、状态流转和结构化回归策略。
- `06-golden-sample.md`：golden sample 的作用、最低覆盖内容、P0-T2 审查前基线与当前 P0-T3 执行边界。

已 superseded 的历史设计统一存放在 `docs/archive/`，不再列入当前 design 文档。

## Maintenance Rules

- Design 文档可以处于 Draft，但必须显式标记哪些内容已确认，哪些仍是候选。
- 不把 reference 草案中的具体 API、字段或技术栈直接提升为长期承诺。
- 当某个设计选择会约束后续实现时，应补充或更新 ADR。
