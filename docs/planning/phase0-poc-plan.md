# Phase0-PoC 执行计划

## Status

Active.

## 1. 目标与边界

Phase0-PoC 的目标是证明一条无 UI、可重复运行、可回归的配置辅助链路可行：

```text
Raw Docs
→ Final SchemaIR
→ SchemaIR Validator
→ Schema Workbook
→ golden regression
```

Phase0a 不再作为独立 active phase。已完成的 CLI、`ingest`、workspace artifact 协议和 `check` 统一记录为 Phase0 bootstrap 工作。

## 2. 当前状态

| TASK | 状态 | 依赖 | 阻塞点 | 完成标志 |
|---|---|---|---|---|
| P0-T0：Bootstrap | Done | 无 | 无 | CLI 可导入 raw doc，workspace artifact 协议和 `check --profile raw|phase0a` 已可用。 |
| P0-T1：`b2e0061` IR candidate / review | Done | P0-T0 | 无 | 已产出并按 human review 更新 candidate DocIR / SchemaIR，正式 IR 设计已沉淀，review-only 边界清晰。 |
| P0-T2：Golden sample boundary | Next | P0-T1 | expected IR 和 workbook assertions 待确认 | 形成 expected DocIR、expected SchemaIR、validator expected result 和 workbook assertions。 |
| P0-T3：Trusted chain | Blocked | P0-T2 | golden sample 未确认 | 实现 SchemaIR Validator、Workbook Generator 和 golden regression。 |
| P0-T4：Draft generators | Blocked | P0-T3 | trusted chain 未完成 | 接入 stub / OpenAI-compatible draft generator，LLM 只生成 draft。 |

状态说明：

- `Done`：完成标志和验证均已满足。
- `Next`：下一步应优先执行。
- `Blocked`：存在明确前置条件，不能直接实施。

## 3. 当前阻塞点

当前不能直接实现正式 trusted chain，因为 formal IR 设计和 updated candidate IR 已产出，但 expected/golden artifacts 尚未确认：

- `DocIR` candidate 已按 metadata table 结构更新，但 expected DocIR 尚未冻结。
- `SchemaIR` candidate 已包含 `envelope`、`evidence`、confidence 阈值和 `ASSEMBLY` / `PARSE` 消息，但 expected SchemaIR 尚未冻结。
- `b2e0061.md` 对应的 expected DocIR / expected SchemaIR 尚未形成。
- workbook assertions 依赖 confirmed SchemaIR，尚未确认。

在这些内容确认前，不应实现正式 SchemaIR Validator、Workbook Generator 或 golden regression，避免把候选 IR 固化为 runtime contract。

## 4. 下一步任务

### P0-T1：`b2e0061` IR candidate / review

目标：基于 `docs/reference/samples/b2eboc/b2e0061.md` 产出用于人工 review 的 candidate IR。当前 P0-T1 产物已落地到 `samples/candidates/b2eboc-b2e0061/`。

已产出：

```text
samples/candidates/b2eboc-b2e0061/
├── raw-doc.md
├── docir.candidate.md
├── schemair.candidate.json
└── review-notes.md
```

完成标志：

- `docir.candidate.md` 可用于确认 DocIR 最小格式和质量标准。
- `schemair.candidate.json` 可用于确认 SchemaIR 字段集合、枚举和来源规则。
- `review-notes.md` 明确列出未确认字段、推导点和人工确认问题。

注意：candidate 不是 golden，不作为 runtime contract。

### P0-T2：Golden sample boundary

目标：review P0-T1 candidate IR，经人工确认后形成正式 golden sample 输入。

P0-T2 应以 formal IR 设计和 `samples/candidates/b2eboc-b2e0061/` 下的 updated candidate 为输入；历史导出 JSON 只能作为人工对照，不作为字段来源、expected SchemaIR 来源或回归输入。

正式 golden sample 至少应包含：

- `raw-doc.md`
- `docir.expected.md`
- `schemair.expected.json`
- `schemair-validation.expected.json`
- `workbook-assertions.expected.json`

完成标志：

- expected DocIR / SchemaIR 已经人工确认。
- workbook assertions 的最小检查范围已确认。
- 后续 Validator 和 Workbook Generator 可以基于 confirmed artifacts 实施。

### P0-T3：Trusted chain

目标：在 IR 和 golden sample 确认后，实现不依赖 LLM 的可信链路。

涉及范围：

- SchemaIR Validator。
- Workbook Generator。
- 结构化 workbook assertions。
- golden regression。

完成标志：

- 可从 confirmed `schemair-final.json` 或 expected SchemaIR 跑到 validation result。
- 可由通过校验的 Final SchemaIR 确定性生成 Schema Workbook。
- golden regression 可重复运行并产出可比较结果。

### P0-T4：Draft generators

目标：trusted chain 建立后，再接入 DocIR / SchemaIR draft 生成能力。

涉及范围：

- stub generator。
- OpenAI-compatible adapter。
- 缺配置错误处理。
- 敏感日志约束。

完成标志：

- LLM 只生成 draft，不进入可信边界。
- stub 输出稳定，可用于测试。
- 日志不输出完整银行原文。

## 5. 验证要求

文档更新阶段：

- `git diff --check`
- 手工确认 `README.md`、`docs/phases/phase0-poc.md` 和本文档状态一致。

后续实现阶段：

- `uv run --group dev pytest`
- Validator 字段级错误测试。
- Workbook 结构化 assertions 测试。
- docs-sync 检查。

只要用户可见命令、artifact、配置、验证方式或阶段状态发生变化，必须检查 `README.md`。
