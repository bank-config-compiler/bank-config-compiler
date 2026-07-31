# ADR-0005: SchemaIR envelope 与 evidence 模型

## Status

Accepted. Envelope/evidence decisions remain; Workbook terminology and input boundary are updated by `ADR-0006-configir-and-configuration-workbook.md`.

## Date

2026-06-17

## Context

P0-T1 的 `b2e0061` candidate review 暴露出几个问题：

- 仅覆盖交易消息字段不足以指导完整配置，BOCB2E `head`、`trans` 和 `bocb2e` 属性也需要进入可 review 的 IR。
- `version`、容器必填性、path、长度和条件约束中有不少内容来自推导或存在冲突，单靠 `confidence` 和 `uncertain` 不足以解释来源。
- Schema Workbook 面向配置人员，需要在单个方向中看到完整报文结构，而不是在多个 sheet 之间拼接理解。
- 历史导出 JSON 可以帮助理解目标系统形态，但它包含历史 ID、状态字段和导入模板噪声，不能作为 SchemaIR 字段来源。

## Decision

- SchemaIR 顶层新增 `envelope` 字段，专门表达可复用的 BOCB2E envelope/head/trans。
- `messages` 只表达接口交易消息，例如 `ASSEMBLY` 的 `b2e0061-rq` 和 `PARSE` 的 `b2e0061-rs`。
- 所有 SchemaIR 字段新增 `evidence`，其中 `kind` 为 `DIRECT`、`DERIVED` 或 `ASSUMED`，`note` 说明来源或推导原因。
- 顶层 `version` 可以保留候选便捷值；真实来源和不确定性由 `envelope.fields` 中的 `Root.bocb2e.@version` 表达。
- Schema Workbook 不新增独立 `ENVELOPE` sheet；`ASSEMBLY` 和 `PARSE` sheet 都并入 envelope/head 字段，再接当前方向交易字段。
- 历史导出 JSON 仅作为人工 review 对照，不作为字段来源、不进入 expected SchemaIR、不作为 golden regression 输入。

## Alternatives Considered

### 把 envelope/head 作为特殊 message

- Pros:
  - 顶层结构更少。
  - 所有字段都在 `messages` 下，处理路径统一。
- Cons:
  - `messages` 同时包含可复用协议结构和交易消息，语义混杂。
  - Workbook 需要特殊过滤或新增方向，配置人员理解成本更高。
- Why not chosen:
  - envelope/head 是跨接口复用结构，不应伪装成某个交易方向。

### 在 ASSEMBLY / PARSE 中重复完整 envelope 字段

- Pros:
  - 每个方向天然完整。
  - Workbook 生成逻辑直观。
- Cons:
  - SchemaIR 事实源重复同一组通用字段。
  - 后续多接口复用和 validator 去重更困难。
- Why not chosen:
  - 重复适合 workbook 展示，不适合作为事实源结构。

### 只用 confidence / uncertain 表达来源

- Pros:
  - 字段结构更短。
  - 与 P0-T1 candidate 改动较小。
- Cons:
  - 无法区分直接证据、路径推导和临时假设。
  - Validator 和 human review 难以判断应重点关注什么。
- Why not chosen:
  - P0-T2 需要把候选 IR 提升为 expected IR，来源解释必须机器可见。

### 用历史导出 JSON 补字段

- Pros:
  - 更接近已有目标系统配置形态。
  - 可能发现 raw doc 中缺失的配置字段。
- Cons:
  - 会引入历史 ID、parent ID、状态字段、导入模板字段等噪声。
  - 会把当前项目重新拉回 Import JSON 适配方向，背离 ADR-0004。
- Why not chosen:
  - 当前可信来源是 raw doc / DocIR / human review，历史导出 JSON 只能做对照。

## Consequences

- Validator 需要校验 `envelope` 和字段级 `evidence.kind`。
- Workbook Generator 需要在 `ASSEMBLY` 和 `PARSE` sheet 中重复展示 envelope/head 字段。
- Review notes 可以按 `uncertain`、`confidence` 和 `evidence.kind` 稳定生成。
- SchemaIR 比 P0-T1 candidate 更长，但来源解释和复用边界更清楚。
- 后续 expected SchemaIR 不应从历史导出 JSON 补字段；如发现 raw doc 不足，应通过 human review 明确补充来源和不确定性。
