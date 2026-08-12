# ADR-0012: Phase0-PoC 必须验证真实 LLM Draft 链路

## Status

Accepted. Amends ADR-0003's P0-T4 fixture-only provider boundary. The direct DocIR Markdown generation mechanism is amended by ADR-0013; provider attempt evidence and DocIR call orchestration are further amended by ADR-0014.

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

### Implementation amendment (2026-08-10)

- `DraftProvider` 接收 request 与编排层显式构造的 `DraftGenerationContext`；上下文只包含当前上游内容、media type 和适用 RELEASED 规则包。provider 不获得 workspace path，不读取 Final/Golden，不扫描或选择版本。
- 真实 adapter 使用官方 OpenAI Python SDK 的流式 Chat Completions 与 JSON object response mode，并请求最终 usage 分块。provider 只在 `finish_reason=stop`、usage 和完整 JSON 均通过边界校验后返回结果；流中断或截断不得发布部分 Draft。SDK 自动重试固定为 0；timeout 为 1–3600 秒的显式运行时配置，失败后的重跑必须使用新的 attempt ID。
- API key、HTTPS base URL、精确 model ID 和 timeout 可来自启动目录中被 Git 忽略的 `.env` 或进程环境；只读取四个 `BANK_CONFIG_COMPILER_LLM_*` 白名单变量，进程环境优先，非敏感项可由 CLI 覆盖。API key 不提供 CLI 参数，attempt ID 始终按调用显式配置。artifact、日志、测试和版本库均不得保存 secret 或 endpoint 原文。
- `draft-provider-response/v1` 仍只承载 Draft 与 review notes。真实成功调用另存 `draft-provider-call-result/v1`，绑定 source/artifact hash，记录非敏感 provider/model/response/usage/time/Prompt contract 与 endpoint fingerprint；该摘要是调用证据，不是 Human Review 或 Final validation。
- 真实 DocIR 失败调用默认写入 `draft-provider-failure-result/v1`；若流已返回内容，另存完整或部分模型响应。失败证据由 workspace-aware 编排层写入，provider 仍不获得 workspace；这些文件是开发诊断，不是 Draft、Review、Final 或 trusted-chain artifact。
- DocIR prompt contract 必须投影冻结的 Markdown wire 与来源分区规则，但不得读取 Golden 或硬编码银行样例事实。`draft-prompt/v4` 要求 Source Context、固定 Metadata/Fields 表头与值域、跨章节 1/2/3 Index、U+3000 层级 Message Item、Conditions、未知值留空 Review，以及不同交易代码示例不得投影目标交易字段；DocIR 最小结构门禁仍不升级为第四个 trusted-chain Validator。
- ADR-0013 后续将上述“模型直接投影 Markdown”机制修订为内部 `docir-extraction/v1` 严格结构化提取与确定性 Markdown renderer；`draft-provider-response/v1` 和 Human Review gate 不变。
- 开发验证期间，由本项目 provider 自身产生的流、JSON、extraction 门禁错误保留具体校验原因并由 CLI 输出；SDK 或任意第三方异常仍只暴露异常类型。失败摘要不记录 API key、endpoint 原文或 raw-doc，响应文件允许保存实际模型输出以便复盘；该诊断不改变失败不发布部分 Draft 和显式新 attempt ID 重试的边界。
- ADR-0014 后续将单调用 evidence v1 升级为记录有序 subcall 的 attempt v2，并把 DocIR 单响应 extraction 修订为原子、顺序、fail-fast 的有界分段调用；本节保留的是实施历史。

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
