# ADR-0013: DocIR 使用结构化提取与确定性 Markdown 渲染

## Status

Accepted. Amends ADR-0012's direct model-to-Markdown DocIR generation mechanism. Its single-response extraction mechanism is amended by ADR-0014.

## Date

2026-08-11

## Context

ADR-0012 要求真实 LLM provider 仍通过 `draft-provider-response/v1` 返回 DocIR Markdown Draft，并由 Human Review 决定是否冻结。早期实现让模型直接生成完整 Markdown wire：

- `draft-prompt/v3` 的 `docir-005` 已证明流式长请求可以成功，但模型未遵守冻结的 `Mult./Type/Required` 值域、跨章节 Index 和 U+3000 缩进。
- `draft-prompt/v4` 已明确上述格式与未知值规则；`docir-006` 改善了值域和 Index，仍忽略 U+3000，并继续出现无证据推断、来源术语误写、Review 自相矛盾和 Conditions 遗漏。

Human Review 能阻止不合格 Draft 进入下游，但不能让概率模型可靠承担确定性的 Markdown 表格布局。继续加入更多格式指令会增加 prompt 与付费重试成本，仍不能提供机械 wire 保证。

同时，DocIR 仍是面向人的 Review artifact，不能为了内部实现方便新增一个需要持久化、版本化或进入 trusted chain 的公开 IR。

## Decision

- `openai-chat` 的 DocIR 模型响应改为内部 `docir-extraction/v1` JSON object；它不是公开 IR，不写入 workspace，不成为下游输入。
- extraction 使用严格 schema：固定顶层属性、Metadata key set、Field 属性、1/2/3 根 Index、父节点先于子节点、XML item name、`Mult./Type/Required` 值域与 Conditions。未知 wire 值必须留空，并在对应 metadata `reviewNote` 或 field `review` 包含“原文未说明，待人工确认”。
- 代码在信任边界内校验 extraction，再确定性生成五个一级章节、四个 Metadata 表、三个 Fields 表、两个 Conditions 段、固定列顺序、U+3000 层级缩进与 Markdown escaping。
- DocIR Human Review Notes 不再由模型单独生成；代码按固定 checklist、Metadata 顺序和 Field Index 顺序聚合 extraction 中非空的 `reviewNote`/`review`，并保留稳定字段位置。
- renderer 产物必须再次通过机械 wire 校验，才可转换为既有 `draft-provider-response/v1`；外部 `artifactContent` 仍是 DocIR Markdown，CLI、workspace 路径、hash、Human Review 和 Final gate 不变。
- 模型只负责语义提取与候选证据表达；确定性 renderer 不能补充业务事实、修正无证据推断或替代 Human Review。
- prompt 和 extraction schema 不读取 Golden、Final、workspace 或厂商专属事实，也不得硬编码某个银行交易样例。
- 不新增 Golden evaluator。Golden 只保留为开发 fixture、历史批准样例和确定性 trusted-chain regression；真实 DocIR 候选的语义完整性与来源忠实性仍由 Human Review 判断。
- SchemaIR、Standard、Template 的模型响应与现有 Validator 路径不变。

## Alternatives Considered

### 继续仅强化 Markdown prompt

Pros:

- 实现改动最小。

Cons:

- `docir-005/006` 已证明明确格式指令仍可能被忽略。
- 每次发现机械差异都需要修改 prompt 并再次付费调用。
- 格式错误与语义错误混在同一个 Human Review 中，诊断边界不清晰。

Why not chosen:

- 冻结 wire 属于确定性职责，不应继续依赖概率输出。

### 将 extraction 发布为新的长期 IR

Pros:

- 可保存原始结构化模型输出，便于离线分析。

Cons:

- 会新增公开 contract、版本治理、workspace artifact、迁移和下游兼容成本。
- extraction 仍是未经 Human Review 的模型候选，不应成为新的事实源。

Why not chosen:

- Phase0 只需要内部信任边界，不需要第五种持久化 IR。

### 解析并修补模型生成的 Markdown

Pros:

- 可以保留原 prompt 输出形态。

Cons:

- 需要容忍和猜测任意 Markdown 变体。
- 表格列错位、路径缩写和层级错误很难在不改变语义的情况下安全修复。

Why not chosen:

- 先生成不稳定文本再反向解析，比直接校验结构化数据更脆弱。

### 使用 Golden evaluator 自动判定真实候选语义

Pros:

- 对已有受控接口可以自动发现字段或层级回归。

Cons:

- 新接口没有 Golden，无法提供同等判定；已有 Golden 也可能因 raw-doc 修订而过期。
- 当前只有 b2e0061 基线，容易把单一样例结构误包装成通用银行语义规则。
- evaluator 不能替代绑定准确 hash 的 Human Review，仍会增加维护和特殊状态成本。

Why not chosen:

- Phase0 保留通用机械门禁，把真实候选语义统一交给 Human Review；反复出现的接口无关错误应提升为确定性规则，而不是 Golden 特例。

## Consequences

- DocIR 真实调用的 Prompt contract 升级为 `draft-prompt/v7`，模型必须直接返回 `docir-extraction/v1` 根对象，不再返回 `{artifact, reviewNotes}`。
- 固定 Markdown wire、escaping 和层级缩进由代码覆盖并可离线回归；语义完整性、来源忠实度、冲突和不确定性仍由 Human Review rubric 判断。
- extraction schema 或 renderer 失败时整次调用 fail closed，不发布 Markdown、review notes 或成功调用摘要；开发验证默认保存失败摘要和已收到的完整/部分模型响应，CLI 输出具体原因与证据路径，操作者修订后只能使用新的 attempt ID 明确重试。
- `DraftProvider`、`draft-provider-response/v1`、fixture regression、Final DocIR hash gate 与下游 trusted chain 无兼容性变化。

### Implementation amendment (2026-08-11)

- `docir-008` 的完整流通过 transport 后，模型响应在本地边界被判定为同时缺少顶层 `artifact` 与 `reviewNotes`；失败未发布任何部分 Draft。
- v5 一方面要求完整外层 envelope，另一方面只展示裸 `docir-extraction/v1` structural shape，形成互相竞争的输出示例。`draft-prompt/v6` 将示例改为唯一完整 `{artifact, reviewNotes}` 外层结构，并明确 extraction 六个属性只能位于 `artifact` 内。
- `docir-010` 的完整流返回了 `artifact`，但缺少顶层 `reviewNotes`；继续要求模型重复表达 extraction 内已有的 Review 信息只增加失败面。
- `draft-prompt/v7` 删除 DocIR 专属外层 envelope，直接校验 extraction 根对象，并由代码确定性生成 Review Notes；公开 `draft-provider-response/v1` 不变。
- `docir-011` 验证了直接 extraction 根消除了 envelope 歧义，但模型在 `finish_reason=stop` 下只返回到不完整的 `assembly` 并缺少 `parse`。通用机械门禁按设计拒绝该响应并保存完整诊断；该结果不授权增加 Golden evaluator，也不自动触发下一次付费调用。
- ADR-0014 基于该结果采用完整 Interface/Envelope、联合 messages outline 与有界字段详情分段；`docir-extraction/v1`、确定性 renderer、公开 response 和 Human Review 语义保持不变。
