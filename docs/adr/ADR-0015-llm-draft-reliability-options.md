# ADR-0015: 可选模型下的 LLM Draft 可靠性与校验反馈修正

## Status

Proposed. 本 ADR 记录待确认的设计方向，不修改 ADR-0014 当前 Accepted 的 fail-fast、无自动 retry/resume 与失败 attempt 全量重跑语义。

## Date

2026-08-12

## Context

本系统面向不同银行文档与目标系统配置，不是 `b2e0061` 专用转换器。银行字段与目标系统字段之间的语义映射不能由代码硬编码，也不能依赖系统对某个样例或某家银行的预置常识；这部分必须来自输入事实、LLM 候选和 Human Review。

真实 DocIR attempts 并非都产生完全不可用的内容。`docir-012` 至 `docir-016` 多次生成了基本可读或大体完整的结构，但被局部 shape、分段职责、固定 Review 表述或 index 格式错误阻断。`docir-017`/`018` 分别是 ReadTimeout 和连接失败。`docir-019` 的 Interface/Envelope 与联合 outline 均通过，首个 16-field detail 也完整返回，最终只因 4 行缺少固定 Review 标记而失败。

这些 evidence 表明当前问题至少包含两类，不应混为一个“模型不可用”问题：

- transport/incomplete failure：没有可供修正的完整候选，例如 connection failure、deadline、流中断、refusal 或不完整响应；
- complete-but-invalid candidate：模型给出完整候选，但违反局部机械合同或存在待 Human Review 的语义问题。

目标不是要求 LLM 一次直接写出六个完全可信的严格 IR，而是让系统在 LLM 协助下可靠地产生可校验、可人工审查并最终可信的 IR。Final 可信边界仍由严格 Validator、独立 Human Review、准确内容 hash 与匹配 validation result 共同构成。

运行时模型与 OpenAI-compatible provider 可以显式选择。Structured Outputs 能力不能作为所有候选模型或 provider 的共同前提；早期验证可以选择具有该能力的组合，但系统仍需在能力缺失或未验证时 fail closed，不能把 provider 声明替代本地校验。

## Constraints And Decision Drivers

- 保持通用产品边界，不为 `b2e0061` 或单一银行/目标系统硬编码字段映射。
- LLM 负责从来源中提出语义候选；代码可以执行确定性机械工作，但不能创造未由来源、规则或 Human Review 提供的映射事实。
- 任何修正路径都不能降低 Final publication 的严格 Validator 与 Human Review 门禁，也不能自动 promotion。
- 模型/provider 可替换；Structured Outputs 只能是可探测、可选择的能力，不能成为正确性唯一基础。
- transport/incomplete failure 与 complete-but-invalid candidate 必须保持不同的处理和 evidence 分类。
- P0-T5 的六个真实 Draft、逐层 Final gate、双方向 `check --profile phase0` 与 Workbook 验证完成标志不变。

## Options Discussed

### 继续收紧 Prompt 或减小 field batch

这条路径改动最小，也可能继续提高单次成功率。`docir-012` 至 `docir-017` 已证明针对实证错误收紧 Prompt 能逐步消除部分问题；减小 batch 也能降低单个 detail 响应的输出压力。

它的限制是概率性的：已经明确写入 v12 的逐行固定标记仍在 `docir-019` 随机漏执行。更小 batch 会增加调用数、重复输入 token、成本与 transport 暴露面，不能保证消除同类局部 invariant 失败。该方向可作为调参手段，但目前没有证据支持把它单独作为可靠性闭环；`docir-020` 因此不直接按 batch 8 启动。

### 将 Structured Outputs 作为可选 provider capability

当模型、endpoint 和 SDK 路径经实际 capability probe 证明支持目标 schema 时，Structured Outputs 可以减少缺字段、类型错误、额外属性和 JSON shape 漂移。早期受控验证可以显式选择这种 provider/model 组合。

它不能解决来源理解、字段遗漏、银行到目标系统的语义映射或 Review 判断，也不能保证所有 OpenAI-compatible provider 都具有等价能力。即使 provider 接受 schema，本地仍必须校验完整响应、refusal/incomplete 状态、业务 invariant 和跨 artifact 引用。该方向适合作为可选优化或前期 provider 选择条件，不适合作为跨 provider 的正确性基础。

### 让代码承担更多确定性生成

代码可以从已经明确的来源事实或 LLM 候选中确定性生成机械内容，例如 canonical index、固定 Review 标记、hash、lifecycle metadata、稳定排序和 Markdown/JSON 渲染。当前 renderer 与 Validator 已经体现这一边界。

如果把该方向扩展为“由代码理解输出模板并完成银行字段到目标系统字段的映射”，则与通用系统目标冲突：模板结构只能说明允许的配置形状和约束，不能自行提供某份银行文档字段应映射到哪个目标字段的业务事实。更广泛的 observation/candidate IR 再由代码 materialize 严格 IR 可能是未来架构方向，但会新增中间 contract、来源引用和 Human Review 设计，不能从当前失败 evidence 直接推导为 P0-T5 的最小修复。

### Validator-guided 单次修正

用户提出：第一次 LLM 返回校验失败后，第二次调用同时携带第一次完整返回和校验结果，请模型生成修正后的 DocIR。该方向最贴近 `docir-019` 这类“整体基本可用、局部机械合同失败”的 evidence，并保留 LLM 对通用语义映射的职责。

“减弱校验”存在两种不同解释：

1. 放宽最终 Validator，使原本不合格的候选可以发布；这会削弱 trusted boundary，当前不建议采用。
2. 保持最终 Validator 不变，但把第一次完整候选的失败从 attempt 终点改为一次受限修正的诊断输入；这是本 ADR 继续评审的候选语义。

候选语义如下，但尚未 Accepted：

- 仅 complete-but-invalid candidate 可以进入修正；request/connection/deadline、流中断、refusal、usage/`finish_reason` 不完整等 transport failure 仍立即 fail closed。
- Validator 应先聚合本次候选的全部机械问题，并向修正调用提供稳定 path/code、期望约束和实际值摘要，避免只修复第一个错误。`docir-019` 实际有 4 行同类问题，而当前异常只暴露第一处，说明聚合是必要前提。
- 修正调用携带同一 raw-doc、同一 segment/DocIR contract、第一次完整返回和完整校验问题；这些内容是诊断上下文，不是新的业务事实来源。
- 一个原始候选最多允许一次修正调用；修正结果必须重新通过完全相同的严格 Validator。再次失败则整个 attempt 原子失败，不允许自动第三次调用。
- 成功前仍不发布任何部分 Draft；evidence 必须区分 original 与 correction，并保留各自 response hash、问题集合、usage、完成状态和最终结果。
- 即使采用失败 segment 修正，已通过 segment 也只能在同一 attempt 内存中继续使用，不能形成持久 checkpoint/resume；新的 attempt 仍必须从第一段开始。

## Open Questions

以下问题会实质改变实现与证据合同，不能在编码时默认选择：

1. 第二次调用应重生成完整 DocIR，还是只修正失败 segment？前者上下文完整但成本和回归面更大；后者更贴近局部失败，但需要定义 segment replacement 与最终 merge 语义。
2. 采用单次修正是否被接受为对 ADR-0014 “无自动重试”的明确修订？不能仅通过把它命名为 correction 来规避现有决定。
3. 聚合校验问题的最小稳定结构，以及 original/correction 是否要求 `draft-provider-*-result` evidence contract 升版，尚未确认。
4. 早期 P0-T5 是否将“通过 capability probe 的 Structured Outputs provider/model”设为验收选择条件，还是只保留为可选优化，尚未确认。

## Proposed Decision Gate

在本 ADR 变为 Accepted 前：

- 不实现 Validator-guided 修正，不修改 Prompt、Validator、provider/evidence 公开 contract；
- 不启动 `docir-020`；
- ADR-0014 的当前执行语义继续生效；
- P0-T5、Commit 8B、6.3 和 8.3 的完成门禁保持不变。

若用户确认采用该方向，应先回答上述关键问题，并在 Phase0 plan 中新增一个可独立回滚和验收的实现 commit：code、tests、已知 docs 同 commit，TDD 覆盖 eligible/ineligible failure、全问题聚合、最多一次修正、相同严格终验、原子失败和 evidence；完整离线验证通过后，再单独取得真实 provider attempt 授权。

## Consequences If Accepted

- 预期收益：避免因少量局部机械错误丢弃大体可用候选，降低全量重算次数，并把 Validator 的确定性诊断转化为一次有界反馈。
- 成本：每个 eligible failure 最多增加一次真实调用、token 与延迟；attempt/evidence 状态机更复杂，并需要明确区分修正与跨 attempt retry/resume。
- 风险：模型可能针对错误信息做局部修补时引入新的语义漂移，因此必须重跑完整严格校验并保留 Human Review，不能只验证原失败路径。
- 非目标：不由代码决定银行到目标系统字段映射，不承诺任意 provider 的 Structured Outputs，不新增 Golden evaluator，不自动生成 Final。
