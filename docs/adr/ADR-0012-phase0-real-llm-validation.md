# ADR-0012: Phase0-PoC 必须验证真实 LLM Draft 链路

## Status

Accepted. Amends ADR-0003's P0-T4 fixture-only provider boundary.

## Date

2026-08-10

## Context

P0-T4 已证明 provider-neutral 编排、Validator、Human Review 边界和双方向 Workbook 可以通过 deterministic fixture 闭合，但 fixture 不会调用 LLM，不能证明真实模型输出是否能穿过同一 Draft trust boundary。

Phase0 需要验证真实 LLM 到双方向 Workbook 的完整链路。用户确认测试可使用能够处理该敏感输入的 provider，并要求使用 OpenAI-compatible Chat API；实际模型可以是 DeepSeek、Qwen 或其他兼容服务。

## Decision

- Phase0 新增 P0-T5：一个运行时显式选择的真实 provider 必须通过 OpenAI-compatible Chat API 依次生成 DocIR、SchemaIR、ASSEMBLY/PARSE Standard 和 ASSEMBLY/PARSE Template Draft。
- 真实 provider 只实现现有 `DraftProvider` 边界，并将外部响应转换为 `draft-provider-response/v1`；不得把厂商 API、密钥或模型特性泄漏为 IR 或 Final trusted-chain 契约。
- 每个 Draft 只能以 `DRAFT/PENDING` 发布。DocIR、SchemaIR、两个 Standard 和两个 Template 必须分别由 Human 对准确内容 hash 确认；JSON Final candidate 必须重新通过对应 Validator，才可进入下游。
- 最终必须用由真实 Draft 经上述 Review 形成的 Final trusted chain，通过两次 `check --profile phase0` 并生成 ASSEMBLY/PARSE 两份 Configuration Workbook。
- fixture regression 保留为确定性回归基线，不能替代真实调用。真实输入和输出是否可提交版本库须单独按数据保留授权决定；API 可处理输入不等于允许将其写入仓库。

## Alternatives Considered

### 保持 fixture-only Phase0

Pros:

- 回归稳定且不依赖网络、模型或凭证。

Cons:

- 不能证明真实模型输出、外部调用和人工修订后仍能形成完整 trusted chain。

Why not chosen:

- 不满足 Phase0 对真实 LLM Draft 的明确验证目标。

### 将厂商 SDK 或 Chat API 逻辑写入核心生成器

Pros:

- 初始接入代码较少。

Cons:

- 会将 provider 选择、认证和响应细节耦合到 Validator/IR 编排层。

Why not chosen:

- 现有 `DraftProvider` 已定义足够的外部边界；复用该边界可保留 Validator、Human Review 和 Workbook 的独立可信性。

## Consequences

- Phase0 从 Done 变为 In Progress，直至 P0-T5 产生可审计的真实调用和双方向 Workbook 证据。
- 实现必须新增真实 provider、显式运行时配置、脱敏日志、失败上下文与不接入真实 API 的自动化测试；真实调用不应成为 CI 前提。
- 人工确认必须按依赖层逐一进行，不能以最终一次确认替代上游 Final gate。
