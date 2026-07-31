# ADR 索引

## Status

Active.

## Purpose

`docs/adr/` 记录会约束后续实现的关键技术决策。

ADR 只记录已经形成工程约束或需要被反复解释的选择。尚未确认的技术栈、API 形态或产品范围应留在 requirements、phase 或 design 文档中。

## Records

- `ADR-0001-human-review-and-rule-engine.md`：采用 Human Review 与确定性生成器作为可信边界。
- `ADR-0002-phase0-input-scope.md`：Phase0-PoC 仅支持文本、Markdown 和粘贴输入，暂不支持富文档解析。
- `ADR-0003-delivery-model.md`：采用分阶段工具链交付形态，而不是 Skill、纯 Agent 或一开始建设完整系统。
- `ADR-0004-schemair-and-workbook-artifacts.md`：历史上采用 `Final SchemaIR` 单一事实源和 Schema Workbook；该输入边界已被 ADR-0006 部分 supersede，不生成 Import JSON 的决定仍有效。
- `ADR-0005-schemair-envelope-and-evidence.md`：SchemaIR 使用 `envelope` 表达可复用 BOCB2E 结构，并用字段级 `evidence` 解释来源。
- `ADR-0006-configir-and-configuration-workbook.md`：采用独立 ConfigIR、版本化自然语言规则包、双事实源和 Configuration Workbook。
