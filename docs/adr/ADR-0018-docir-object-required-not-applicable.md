# ADR-0018: DocIR Object Required 不适用

## Status

Accepted. 本 ADR supersede ADR-0016、ADR-0017 中“所有 DocIR 节点 Required 缺证据均阻塞”的决定；标量 Required 证据门禁和九列格式继续有效。

## Date

2026-08-13

## Context

DocIR 的 `Object` 表示 XML 结构容器，不承载独立字段值。旧规则要求每个 Object 同样填写 `Y/N/C`，导致 Human 必须为 `bocb2e`、`head`、`trans` 和消息包装节点填写没有直接字段语义的 Required，并产生大量无效 Review。

“容器包含必填叶子”也不能证明容器本身无条件出现：可选容器一旦出现时，其内部叶子仍可能必填。因此既不能要求 DocIR Object Required，也不能从后代叶子自动推导容器出现性。

## Decision

- DocIR `Object.Required` 固定留空，语义为 N/A；填写 `Y/N/C` 属于 contract error。
- Object 不产生 Required 缺失 issue，也不注入 Required Review marker。
- 标量 `String/Boolean/Date/Decimal` 仍只接受 `Y/N/C`；缺失时注入明确的 `Required 原文未说明，待人工确认` 并阻塞。
- 代码不从任意后代叶子的 Required 推导 Object 是否出现。
- DocIR `Mult.` 继续只锁定重复 Object 的最大出现次数；Object 在 SchemaIR 中的 `required` 由 SchemaIR candidate 提议并经 Human Review，materializer 据此规范化 occurs minimum，同时从 Final DocIR 锁定 maximum。
- SchemaIR 标量 `required/occurs` 仍从 Final DocIR 的 `Y/N/C` 和 `Mult.` 确定性投影。

Contract 版本升级为 `draft-prompt/v16`、`docir-semantic-materializer/v4`、JSON IR `draft-prompt/v9` 和 `schemair-materializer/v2`。DocIR candidate/extraction JSON shape、九列 Markdown wire 和 Validation Result JSON shape 不变。

## Alternatives Considered

### 从必填叶子向上推导 Object 必填

这会混淆“容器是否出现”与“容器出现后内部字段是否必填”，可能把可选结构错误升级为必填，因此不采用。

### 在 DocIR 为 Object 增加独立 occurs-required 列

会扩大当前九列 contract，并在 DocIR 阶段提前承担 SchemaIR 的结构出现性审查；Phase 0 没有必要增加第二套容器必填模型。

### 将 Object 空 Required 默认为 N

空值代表不适用，不代表容器可选。默认 `N` 会静默创造银行事实，因此不采用。

## Consequences

- DocIR Human Gate 只要求对有值的标量确认 Required，Review 项更准确。
- SchemaIR generation 必须为每个 Object 提出明确 boolean `required`，并由 Human 独立确认；该值不是从叶子自动产生。
- 历史有效 DocIR fixture 需要清空 Object Required 并重建 hash；历史 provider attempt evidence 保持 immutable。
