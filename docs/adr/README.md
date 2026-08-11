# ADR 索引

## Status

Active.

## Purpose

`docs/adr/` 记录会约束后续实现的关键技术决策。

ADR 只记录已经形成工程约束或需要被反复解释的选择。尚未确认的技术栈、API 形态或产品范围应留在 requirements、phase 或 design 文档中。

## Records

- `ADR-0001-human-review-and-rule-engine.md`：采用 Human Review 与确定性生成器作为可信边界。
- `ADR-0002-phase0-input-scope.md`：原始 Phase0-PoC 文本输入边界；其中“粘贴文本”已由 ADR-0011 supersede，富文档解析仍不支持。
- `ADR-0003-delivery-model.md`：采用分阶段工具链交付形态，而不是 Skill、纯 Agent 或一开始建设完整系统。
- `ADR-0004-schemair-and-workbook-artifacts.md`：历史上采用 `Final SchemaIR` 单一事实源和 Schema Workbook；该输入边界后续由 ADR-0006、ADR-0007 supersede，不生成 Import JSON 的决定仍有效。
- `ADR-0005-schemair-envelope-and-evidence.md`：SchemaIR 使用 `envelope` 表达可复用 BOCB2E 结构，并用字段级 `evidence` 解释来源；方向级 encoding 与 observed-only 投影由 ADR-0008 扩展。
- `ADR-0006-configir-and-configuration-workbook.md`：历史上采用独立 ConfigIR 与双事实源；其单一配置模型和 Workbook 粒度已被 ADR-0007 supersede。
- `ADR-0007-interface-standard-and-template-irs.md`：采用独立 InterfaceStandardIR / InterfaceTemplateIR、标准版本复用和每方向模板一份 Workbook；银行事实投影、方向绑定与 Mapping 契约后续由 ADR-0008/0009 修订。
- `ADR-0008-directional-template-bindings-and-bank-conditions.md`：规定 raw-doc/SchemaIR 的银行事实优先级、Template Standard 镜像、容器 coverage、PARSE collection binding、方向级 encoding，并将银行文档明确条件归入 Standard 约束；PARSE projection 的保存位置后续由 ADR-0010 修订。
- `ADR-0009-preset-mapping-catalog-and-replacement.md`：采用全局唯一 `mappingRuleName` 的预设 catalog，区分 MAPPING 完整值查表与 Replacement 片段替换，并将两者纳入 P0。
- `ADR-0010-directional-standard-projection-resolution.md`：ASSEMBLY 显式保存 target projection；PARSE 在表达式/collection source 保存 `standardFieldRef` 并从精确绑定的 Final Standard 确定性解析 projection，不选择顶层主 source。
- `ADR-0011-phase0-file-input-only.md`：Phase0-PoC 的 raw-doc 仅接受 UTF-8 no BOM 的 `.md` / `.txt` 文件；不承诺粘贴、stdin 或 API 输入。
- `ADR-0012-phase0-real-llm-validation.md`：Phase0-PoC 必须通过 OpenAI-compatible Chat API 完成真实 LLM Draft、逐层 Human Review/Final validation 和双方向 Workbook 验证。
- `ADR-0013-structured-docir-extraction-and-rendering.md`：真实 provider 的 DocIR 改为内部严格结构化提取，再由代码确定性渲染现有 Markdown wire；不新增公开 IR 或 trusted-chain artifact。
