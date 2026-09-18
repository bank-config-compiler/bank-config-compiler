# ADR-0021: SchemaIR 可恢复分段与分层验证

## Status

Accepted。局部 supersede ADR-0020 中默认 batch 8、禁止 retry/resume，以及所有 segment shape 偏差均 hard fail 的决定。ADR-0020 的 Final DocIR selector、联合 metadata、确定性 merge、原子发布和 Human Gate 约束继续有效。

## Context

`schemair-003` 已证明单次完整生成无法稳定覆盖全部 SchemaIR 字段。ADR-0020 随后把 SchemaIR 拆为联合 metadata 与按方向分批的字段段，但固定 batch 8 会让当前 12/27/10 字段产生 9 次调用，并且任一后段失败都会废弃全部成功前缀。

真实验证进一步暴露了这个成本边界：`schemair-004` 完成 9 次调用并使用 77,742 tokens，最终得到 16 ERROR、4 WARNING 的 Invalid Draft；`schemair-007` 已完成 7 个有效段，第 8 段也返回完整 JSON，却因 PARSE scalar 回显 `required:null` 被旧的严格 segment validator 拒绝，第 9 段没有执行，累计使用 109,896 tokens、耗时 28 分 59 秒。`required` 是否存在是 Final DocIR 已知的结构事实，scalar 上的该属性可以由代码安全删除；为此丢弃全部成功段既没有提高事实准确性，也放大了成本和时延。

同时，SchemaIR 将来可能服务于更多相似配置系统。通用执行机制不应硬编码银行 XML 语义，但当前上游仍明确限定为银行接口文档和 XML Schema 事实，因此本阶段使用内置 Profile 隔离领域规则，不开放外部代码加载。

## Decision

### 可恢复的原子分段执行

- 默认 `--schemair-field-batch-size` 从 8 调整为 16。当前 12/27/10 字段形成 1 个 metadata 段和 4 个字段段，共 5 个逻辑段；显式 batch 8 仍保持 9 个逻辑段。
- 每个逻辑段最多重试 `--segment-max-retries` 次，默认 1，允许 0。只重试当前段，不重放已接受的成功段。
- timeout、连接失败、HTTP 408/429/可恢复 5xx、stream 或 JSON 不完整，以及 selector binding 偏差属于可重试失败。HTTP 401/403、模型不存在、其他确定性 4xx、可物化的语义 Invalid Draft 和内部 materializer bug 不重试。
- `Retry-After` 不超过 30 秒时遵循；其他可恢复 HTTP 失败默认等待 2 秒。每次等待和调用都受 attempt deadline 约束。
- `--attempt-deadline-seconds` 默认 3600；`--attempt-token-budget` 默认 150000。每次物理调用结束后累计本 attempt usage，在下一次调用或重试前 fail closed。单个物理调用期限取 `--chat-timeout-seconds` 与 attempt 剩余时间的较小值。
- `--resume-from-attempt` 只接受显式指定的单个前序 attempt，不自动扫描或选择历史 evidence。只有 source/request、prompt 与 segment contract、model、endpoint、generation parameters 和 segment payload 组成的完整 fingerprint，以及原始 response hash 都可重建且匹配时，才复用对应成功段。
- 复用只改变执行来源，不改变原子发布语义。任何不可恢复失败都不得在 workspace 根目录发布部分 candidate 或 Draft。

### 通用 Kernel 与内置 Profile

- 通用 segmented execution Kernel 使用 `SegmentSpec`、`SegmentFingerprint`、`SegmentDisposition`、`NormalizationDiagnostic` 和 `SegmentedArtifactProfile` 描述逻辑段、依赖、可信绑定、归一化、merge、materialize 与 Review Notes。
- 第一阶段只注册随代码发布的 `BankXmlSchemaIRProfile`。Kernel 不读取 workspace，也不包含银行字段业务语义；CLI/编排层负责读取显式 resume evidence 并将已验证候选传入 executor。
- `SegmentDisposition` 为 `ACCEPT`、`NORMALIZED`、`INVALID_DRAFT`、`RETRY_SEGMENT`、`HARD_FAIL`。Transport、binding、profile normalization 和公开 Validator 的职责必须分开。
- contract、section、batch、selector 数量/顺序/唯一性和 `fieldName` 回显无法确定性绑定时，先 `RETRY_SEGMENT`；重试或预算耗尽后 `HARD_FAIL`。实现不得覆盖或猜测 selector/fieldName。
- Profile 只能删除白名单内、可由代码拥有的属性：`path`、`parentPath`、`nodeKind`、`dataType`、identity/lifecycle，以及 scalar 上的 `required`。每次删除、补空或替换都产生不含敏感原值的 `NormalizationDiagnostic`，并进入 evidence 和 Review Notes。
- 缺失 nullable 属性补 `null`；缺失嵌套 wire slot 使用显式 null placeholder。白名单之外的未知属性不得静默吞掉，而是请求当前段重试。
- Object 的 `required` 缺失或无效时，不猜测 `false`：生成 `required:null`、`occurs:null` 的可物化 Invalid Draft，由公开 Validator 产生 blocking ERROR。description、evidence、length、condition 等可表达的缺失或非法语义也进入 Invalid Draft；只有无法与 selector 一一绑定或无法在不伪造事实的情况下表达时 hard fail。
- Final approval 仍要求 Object `required` 恢复为 boolean、`occurs` 合法一致并清除所有 blocking issues。Invalid Draft 不得进入 Standard、Template 或 Workbook。

### Evidence 与兼容恢复

- attempt evidence 升级为 v3。`calls` 记录本 attempt 的全部物理调用及 `segmentAttempt`；`segments` 对每个逻辑段记录 `LIVE`/`REUSED`、origin attempt/call/hash、fingerprint、disposition 和 normalization diagnostics。
- `attemptUsage` 只统计本次真实调用；`effectiveUsage` 统计最终 artifact 所引用的全部 live/reused 响应。原始响应文件名同时包含逻辑 segment 与物理 attempt 序号，重试不得覆盖前一响应。
- v1/v2 evidence 保持只读兼容，不原地修改。旧 attempt 只有在当前代码能完整重建 fingerprint 时才可复用。
- `schemair-007` 的离线兼容恢复必须显式使用 batch 8，重新校验完整响应，包括旧 evidence 中标为 segment failure 的完整第 8 段。无法证明 fingerprint 的旧段拒绝复用。离线验收只证明前 8 段可复用且仅缺 PARSE 第 2 批；真实 `schemair-008` 仍需单独授权。

## Alternatives Considered

### 恢复单次整体生成并整体重试

调用数较少，但任何 coverage 或语义失败仍需重付整个大响应成本，也无法以代码证明字段 coverage。拒绝。

### 保留 ADR-0020 的固定分段和整次重跑

实现简单，但 `schemair-007` 已证明尾段偏差会浪费大量成功前缀。拒绝。

### 方案 D：方向级大段生成后按缺口动态补齐

理论调用数更少，并可只修复缺口；但需要新的动态 repair contract、跨段语义一致性规则和更复杂 lineage。本轮不实现，只要求 segment plan/evidence 不写死固定段数，为后续演进保留兼容空间。

### 立即开放外部 Profile 插件

会引入签名、权限隔离、版本治理和不可信代码执行边界，当前没有非银行上游的现实需求支撑。仅记录为 future direction。

## Consequences

- 正常路径从 9 次降为 5 次调用，偶发传输或 binding 偏差只重试当前段；完整 fingerprint 防止把不同输入或模型结果错误拼接。
- 执行、evidence 和测试复杂度增加，但失败成本、恢复边界和 lineage 变得可证明。
- 更多可表达偏差会形成带完整诊断的 Invalid Draft，而不是 provider hard failure；Human Gate 和公开 Validator 仍保持 fail closed。
- `DraftProvider`、`draft-provider-response/v1`、SchemaIR v2、`schemair-materializer/v2` 和 Final approval 契约保持不变。
- 本 ADR 不授权真实 LLM 调用，不批准任何 SchemaIR，也不实现外部插件或方案 D。
