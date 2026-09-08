# ADR-0020: SchemaIR 使用 Final DocIR selector 的原子有界分段提取

## Status

Accepted. 本 ADR 仅 supersede ADR-0014 中“非 DocIR artifact 仍记录一个 `complete-artifact` call”的 SchemaIR 部分；Standard 与 Template 继续使用单次 `complete-artifact` 调用。默认 batch、retry/resume、成功段复用和 segment hard-fail 边界已由 ADR-0021 局部 supersede。

## Date

2026-08-20

## Context

`schemair-003` 使用 `draft-prompt/v10` 完成了一次无自动重试的真实 SchemaIR 调用。Provider 正常返回 `finishReason=stop` 且 response complete，但 candidate 只覆盖 13/13 个 Envelope 字段和 16/27 个 ASSEMBLY 字段，缺少整个 10 字段 PARSE message、ASSEMBLY `conditionalConstraints`，最后一个字段还缺少六项必需语义属性。Strict materializer 在公开 Draft 发布前正确 fail closed。

该失败证明：单次响应同时承担 Envelope、双方向 metadata、conditions 和全部字段语义时，即使 transport 完整，也不能可靠证明 candidate coverage。继续只收紧完整响应 Prompt 或无条件重试，无法把 coverage 从概率边界移到确定性边界。

与 DocIR 不同，SchemaIR 不需要模型提出结构 outline。准确 Final DocIR 已经提供 Envelope、ASSEMBLY、PARSE 的字段 preorder、path、node kind 和 data type；代码可以据此构造有界 selector，而不创造银行业务事实。

## Decision

- 一个 SchemaIR attempt 固定按以下顺序原子执行：联合 `schemair-metadata` → Envelope 字段批次 → ASSEMBLY 字段批次 → PARSE 字段批次 → 确定性 merge → 既有 `schemair-materializer/v2` 与 SchemaIR Validator。
- `schemair-metadata` 使用 `schemair-metadata-segment/v1`，只返回 Envelope description，以及 ASSEMBLY/PARSE 的 `xmlEncoding`、encoding evidence、description 和 conditional constraints；不得返回字段。
- 字段批次使用 `schemair-field-semantics-segment/v1`，只返回当前 code-owned selector 的字段语义；不得返回 metadata、artifact identity、lifecycle、path、parent path、level、node kind、occurs、multiple 或 `hasChildren`。
- selector 由代码从准确 Final DocIR preorder 生成，携带稳定 selector、field name、path、node kind 和 data type。响应必须按原顺序准确回显 selector，不能 missing、extra、duplicate 或重排。
- 字段批次固定按 Envelope、ASSEMBLY、PARSE 顺序执行，默认每批最多 8 个字段。`generate-draft schemair --provider openai-chat` 可通过正整数 `--schemair-field-batch-size` 覆盖；fixture 和其他 artifact 不接受该参数。
- 默认物理调用数为 `1 + ceil(Envelope/8) + ceil(ASSEMBLY/8) + ceil(PARSE/8)`。当前 13/27/10 字段输入应执行 9 次调用。
- 每个 segment 在下一调用前严格校验 contract、section、batch index、selector 和最小可物化 shape。最终 merge 再次证明三个 section 的完整 coverage，并生成现有未版本化 SchemaIR semantic candidate shape。
- 任一 request、stream、JSON、segment 或 merge 失败立即停止；不自动 retry、resume 或复用成功前缀。失败后只能使用新的 attempt ID 从 `schemair-metadata` 重新开始。
- `draft-provider-response/v1`、SchemaIR candidate shape、`schemair-materializer/v2`、SchemaIR v2、Validator 和 Human Gate 保持不变。可物化但 Validator 含 ERROR 的 candidate 仍发布 Invalid Draft；结构或 coverage 不可物化时不发布 Draft。
- `draft-provider-call-result/v2` 与 `draft-provider-failure-result/v2` 增加可空的 `schemairFieldBatchSize`，并继续按 sequence 记录有序 subcall。旧 evidence 和 `docirFieldBatchSize` 保持有效。
- Review Notes 从 merged candidate 的 uncertainty、review note、非直接 evidence 和 Validator issues 确定性生成，不增加 LLM 调用。
- F-007 的离线实现、docs-sync 和独立 code review 全绿后，只能准备 `schemair-004` 的精确非 secret 外发摘要；真实调用仍需单独获得明确授权。

## Alternatives Considered

### 保持单次完整 SchemaIR candidate

调用和 evidence 最简单，但 `schemair-003` 已证明 response complete 不等于 coverage complete，不能满足 fail-closed trusted-chain 边界。

### Envelope、ASSEMBLY、PARSE 各返回一个完整 section

比单次完整 artifact 小，但 27 字段 ASSEMBLY 仍可能在正常结束时截断，无法消除已观察到的尾字段不完整风险。

### 让模型先生成 SchemaIR outline

可以复用 DocIR 的分段形态，但会让模型重复提出 Final DocIR 已确定的结构，并增加新的结构漂移和调用成本。SchemaIR 直接使用 code-owned Final DocIR selector。

### 从失败 batch 自动续跑或使用 LLM correction

可能减少重复调用，但会混合不同调用状态、扩大 checkpoint/evidence 协议，并违反 ADR-0015 的 Human-first、无 LLM correction 边界。

## Consequences

- SchemaIR Prompt 升级为 `draft-prompt/v11`，真实 attempt 的调用数、输入 token、延迟和失败暴露面增加。
- 每个字段 subcall 输出显著缩小，字段完整性和全量 coverage 可以在进入 materializer 前确定性证明。
- Provider 需要在 materialization 完成前暂存有序 subcall response，以便后置 hard failure 保存准确逐段 evidence，而不是伪造 `complete-artifact`。
- 中间 segment 仍不是 workspace artifact、公开 IR 或 trusted-chain 输入；成功只发布一个 merged candidate、一个 Draft 和一份有序 attempt 摘要。
- Standard 与 Template 的调用、candidate、materializer 和 Human Gate 不受影响。
