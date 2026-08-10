# ADR-0003: 分阶段工具链交付形态

## Status

Accepted. Delivery model retained; target configuration IR and Configuration Workbook boundaries are updated by ADR-0006 and ADR-0007. The Phase0 real LLM validation boundary is defined by ADR-0012.

## Context

本项目需要把银行接口文档转换为可人工 Review、可校验、可追溯、可回归的配置草稿。讨论中出现了几种可能交付形态：

- Skill：封装给 Codex 或其他开发助手使用的流程能力。
- Agent：面向文档理解和草稿生成的智能组件。
- Dify workflow 或类似 workflow：编排 LLM、Prompt 和结构化输出。
- 独立系统：承载任务状态、产物管理、Review、Validator、Workbook Generator、预览下载和回归验证。

如果一开始建设完整系统，容易过重；如果只选择 Skill、Agent 或 workflow，又无法完整证明控制、校验、人工确认和回归边界。

## Decision

项目采用分阶段工具链交付形态：

- Phase0-PoC：交付可重复运行的链路验证工具，例如 CLI、script 或 lightweight workflow runner，加文件 workspace、golden sample fixtures、Validator、Workbook Generator 和 golden sample regression。
- Phase1-MVP：交付轻量 Review Tool，支持实施人员 Review、校验、确认、Schema Workbook 预览和下载。
- Phase2-Pilot：交付受控内部试点工具或小型内部系统，用真实或准真实项目验证提效、稳定性和运维边界。
- Phase3-Production：暂不定义。

Skill、Agent 和 Dify workflow 可以作为组件或辅助方式：

- Skill 可用于开发、验证或局部流程封装，但不是完整业务交付物。
- Agent 可用于 DocIR Draft 和 SchemaIR Draft 生成，但不是可信边界。
- Dify workflow 可用于 Phase0 的 LLM 编排实验，但不替代 Validator、Workbook Generator、Human Review 边界和 golden sample regression。

### P0-T4 Amendment: provider-neutral Draft boundary

Phase0 的四类 Draft generator 使用 provider-neutral interface，不把 OpenAI-specific API、网络、认证、重试或模型配置写入核心运行时。PoC 只提供由调用者显式选择的 deterministic fixture provider，用精确上游内容 hash、方向、artifact version 和规则版本匹配受控 `b2e0061` case。

Provider 只返回 UTF-8 Draft response envelope；编排层在 workspace 写入前校验 envelope、Draft lifecycle、依赖、规则版本和对应 Validator 结果。Provider、Agent 或 workflow 均不得写入 Final、构造 Human Review 结论或调用 Workbook Generator 绕过 trusted chain。真实 provider 由后续阶段在相同边界下增加，不改变 Human Review、Validator 和 canonical hash 门禁。

## Alternatives Considered

### 只交付 Skill

Pros:

- 实现成本低。
- 适合个人开发和验证流程复用。

Cons:

- 面向使用 agent 的人，不直接面向实施人员。
- 不天然承载任务状态、产物治理和人工确认边界。
- 难以作为团队可验收交付物。

Why not chosen:

- 无法完整覆盖 Phase0 要证明的控制、校验、Review 和回归边界。

### 只交付 Agent

Pros:

- 适合文档理解和草稿生成。
- 能快速验证 LLM 生成 DocIR / SchemaIR 的可行性。

Cons:

- 输出不稳定。
- 不能作为最终可信边界。
- 不应直接生成最终 Schema Workbook 或绕过 Validator。

Why not chosen:

- 项目核心不只是生成草稿，而是生成、确认、校验、确定性转换和回归。

### 只使用 Dify workflow 或类似 workflow

Pros:

- 适合快速 PoC。
- 便于 Prompt、模型和节点编排实验。

Cons:

- 更像编排层，不天然提供项目所需的持久化产物、Review 记录、字段级 Validator、Workbook Generator 测试和 golden sample regression。
- 容易把 LLM 编排误当成可信配置流程。

Why not chosen:

- 可作为 Phase0 的实验工具，但不应成为完整交付形态。

### 一开始建设完整系统

Pros:

- 更接近长期生产形态。
- 可以从一开始规划权限、审计、部署和运维。

Cons:

- 对 Phase0/Phase1 过重。
- 容易在尚未证明业务价值前投入复杂系统能力。

Why not chosen:

- 当前更需要先证明链路价值，再按试点结果决定是否系统化。

## Consequences

- Phase0 文档和计划不能把 Skill、纯 Agent 或单纯 workflow 写成完整交付物。
- Phase1 应控制为轻量 Review Tool，不提前引入生产权限、审批流、多用户协同或复杂部署。
- Phase2 才根据真实试点证据判断是否向内部系统演进。
- Agent、Skill、Dify workflow 相关能力应在设计文档中标记为组件或辅助工具，而不是可信边界。
- 新 provider 只能实现 Draft generation contract；provider-specific 配置、错误和外部响应必须在边界处转换，不能泄漏为 Final artifact 或长期业务契约。
