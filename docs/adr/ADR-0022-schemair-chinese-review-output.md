# ADR-0022: SchemaIR 中文审查输出合同

## Status

Accepted。本 ADR 将 SchemaIR Prompt 从 `draft-prompt/v11` 升级为 `draft-prompt/v12`，并替换 ADR-0020/ADR-0021 中 SchemaIR Review Notes 的具体呈现方式；两者关于 selector、分段执行、归一化、Validator、原子发布和 Human Gate 的其余约束继续有效。

## Context

`schemair-008` 已形成结构完整且可由公开 Validator 校验的 Draft，但其 Review Notes 仍包含共享英文页眉、平铺的逐条 issue，以及大量重复的字段不确定性提示。28 条 `CONDITIONAL_FIELD` INFO 与 blocking 问题混排，同一字段的 `UNCERTAIN_FIELD`、`LOW_CONFIDENCE` 和 `NON_DIRECT_EVIDENCE` 也被拆成多个条目，Human 难以按优先级完成审查。

此外，SchemaIR v11 Prompt 没有约束人类可读语义的语言。`description`、`conditionText`、`uncertainReason`、`reviewNote` 和 `evidence.note` 等字段因此可能混用英文。已有 v11 响应是不可改写的历史 evidence，不能在确定性渲染阶段伪装为模型已经输出中文；但新的 attempt 可以通过 Prompt 明确语言约束。

## Decision

### Prompt v12 与语言边界

- SchemaIR Prompt 升级为 `draft-prompt/v12`。metadata 与 field segment 均要求人类可读语义使用简体中文；标识符、field name、path、枚举和 XML/协议技术字面量保持原样。
- 语言要求只由 Prompt 约束。本阶段不增加中文字符门禁、语言检测或因语言不符触发的 segment retry，避免用不可靠的启发式规则拒绝本可审查的 Draft。
- Prompt contract 是 `SegmentFingerprint` 的组成部分。v11 的 `schemair-007`、`schemair-008` evidence 不能用于 v12 resume；新的完整中文 Draft 必须使用全新 attempt。

### SchemaIR Review Notes

- generation 与 `validate-draft schemair` 共用一个确定性 renderer，直接输出 `# SchemaIR Draft 校验审查说明`，不再叠加共享的英文 `Generated Draft Review Context`。
- Notes 首先记录准确内容 hash、Validation 状态，以及 ERROR、WARNING、INFO、BLOCKING 计数。
- `问题清单` 分为必须处理、非阻塞提醒和按方向汇总的信息项。同一字段的 `UNCERTAIN_FIELD`、`LOW_CONFIDENCE`、`NON_DIRECT_EVIDENCE` 合并为一个条目，但保留全部 issue code、path、结构化值和建议动作。
- Blocking 项按 Envelope、ASSEMBLY、PARSE、生命周期排序；无法绑定字段的问题按 path 与 code 稳定排序。
- `CONDITIONAL_FIELD` INFO 按方向汇总字段名和数量，完整逐条路径仍以 `schemair-validation-result.json` 为准。
- `确定性归一化记录` 使用中文动作说明，不复制被删除的原始属性值。`显式 Review 证据` 只展示未在问题清单中重复呈现的 review/evidence。
- Validator JSON、issue code、path、计数和公开 SchemaIR contract 不变。renderer 为已知 code 提供中文解释；未知 code 使用中文兜底并指向原始 Validation Result，不直接把未知英文 message 当作中文说明。

### `validate-draft` 的 evidence 信任边界

- `validate-draft schemair` 只从与当前 generation lineage 匹配的 `draft-provider-call-result/v3` 读取结构化 `normalizationDiagnostics`。
- task、artifact、source、attempt 或 contract 任一不匹配时，不信任该 evidence。缺失或不可信 evidence 不改变 Validator 结果，只在 Notes 中明确说明未取得可信归一化记录。
- `validate-draft` 不读取原始模型响应来重建语义，不修改 Draft，并继续原子替换 Review Notes 与 Validation Result。

## Alternatives Considered

### 在 renderer 中翻译已有模型原文

这会把确定性代码生成的新文本伪装为 LLM 原始 evidence，并可能改变语义。拒绝；v11 英文原文按历史 evidence 原样保留。

### 增加中文代码门禁和语言失败重试

语言识别存在中英混合技术文本的误判风险，并会扩大调用成本。当前目标是提升审查可读性，不是建立自然语言质量分类器，因此本轮不采用。

### 继续使用通用 Validation Notes

通用 renderer 无法理解 SchemaIR 方向、字段 issue 合并、归一化 lineage 和 Human Gate 优先级，不能解决当前审查问题。拒绝。

## Consequences

- 新的 SchemaIR attempt 会要求中文人类可读语义，但不会因语言偏差自动重试或 hard fail；语义准确性仍由 Validator 与 Human Gate 控制。
- `schemair-008` Draft 和 Validation Result contract 不变，可离线重建更清晰的 Notes；其中既有英文模型说明仍被明确标为历史原始证据。
- v12 fingerprint 与 v11 不兼容，后续 `schemair-009` 必须使用默认 batch 16 的全新 attempt，并在执行真实调用前再次取得明确授权。
- 本 ADR 不授权真实 LLM 调用、不修改或批准任何 SchemaIR Draft，也不改变 Standard、Template 或 Workbook。
