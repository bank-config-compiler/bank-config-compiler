# ADR-0001: Human Review 与确定性生成器作为可信边界

## Status

Accepted. Partially superseded by `ADR-0004-schemair-and-workbook-artifacts.md`; the current target-configuration extension is defined by ADR-0007 and amended by `ADR-0008-directional-template-bindings-and-bank-conditions.md`.

## Context

银行接口文档字段层级、必输规则、重复节点、条件说明和报文示例经常分散在不同章节。LLM 可以辅助整理和抽取，但输出质量可能受文档格式、表格错位、Prompt、模型版本和上下文长度影响。

如果让 LLM 直接生成最终 Import JSON，系统会缺少可信边界、来源追溯、人工确认点和稳定回归路径。

## Decision

系统采用 Human Review 与确定性生成器作为可信边界：

- LLM 只生成 DocIR、SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR Draft。
- Draft 先经过 Validator 形成可审查的机器结果；Human 修改并完成完整 Final candidate 后，必须再次运行 Validator，不能把 Draft 结果复用为 Final 结果。
- Human Review metadata 属于 Final artifact 内容。三类 JSON IR 的 validation result 使用 canonical JSON SHA-256 绑定包括 Review 在内的完整语义内容；任一语义修改都会使旧结果失效。
- 最终交付物只能由确定性生成器基于三份顺序关联的 Final IR、三份 identity/version/contract/hash 匹配且 `finalEligible=true` 的结果、精确规则版本和显式 Standard Action 生成。
- Validator 拦截结构、引用和确定性 invariant，但不能伪造 Human Review 或自动提升 lifecycle 状态。

注：本 ADR 原先将 Import JSON Draft 作为确定性最终产物。该部分已由 ADR-0004 supersede；ADR-0006、ADR-0007 又依次调整目标配置模型和 Workbook 边界。Human Review 与确定性生成器作为可信边界的决定仍然有效。

## Alternatives Considered

### LLM 直接生成 Import JSON

Pros:

- 初期实现更短。
- Demo 效果更直接。

Cons:

- 输出不可稳定回归。
- 字段来源和推导过程难以审计。
- 容易把错误包装成可信配置。
- 难以定位 Rule、Prompt、文档理解分别造成的问题。

Why not chosen:

- 不满足银企直连实施场景对可追溯、可校验和可人工确认的要求。

### 人工完全整理配置

Pros:

- 可信边界清晰。
- 不引入 LLM 输出不稳定风险。

Cons:

- 无法降低从零阅读和整理字段的起步成本。
- 不能沉淀可复用的 DocIR、SchemaIR 和确定性生成链路。

Why not chosen:

- 无法达成项目“半自动化、可审计化”的核心价值。

## Consequences

- 系统必须保留 Raw Docs、DocIR、SchemaIR、Validator 结果和确定性生成的最终交付物等关键中间产物。
- SchemaIR 字段必须尽量保留 `sourceText` 和不确定信息。
- 最终交付物生成器需要保持简单、确定、可测试。
- UI 或无 UI 流程都必须表达人工确认边界。
- Draft validation 与 Final revalidation 是两个不同证据点；只有后者可以进入 Workbook trusted chain。
