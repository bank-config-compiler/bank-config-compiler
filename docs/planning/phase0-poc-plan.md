# Phase0-PoC 当前执行计划

## Status

Draft.

## 1. Phase0 目标

Phase0-PoC 的目标不变：证明一条无 UI、可重复运行、可回归的配置辅助链路可行。

完整 Phase0 链路包括：

```text
Raw Docs
→ Final SchemaIR
→ SchemaIR Validator
→ Schema Workbook
→ golden regression
```

其中 `Final SchemaIR` 是系统内部事实源，Schema Workbook 是面向配置人员的人工配置交付物。Phase0 通过条件不能被 Phase0a 的 bootstrap 范围缩小。

## 2. 当前状态

Phase0a 已完成 bootstrap 子阶段：

- Python CLI 骨架。
- `ingest`：将 `.md` / `.txt` 原始输入保存为 workspace 内的 `raw-doc.md`。
- workspace artifact 协议。
- `check --profile raw|phase0a`：校验固定 artifact 名称、UTF-8 without BOM 和 JSON 可解析性。

Phase0a 不继续承载完整 Phase0 的后续实现。旧 Phase0a TASK 3-8 不再按原顺序直接执行。

## 3. 当前阻塞点

当前不能直接实现正式 trusted chain，因为核心 IR 尚未确认：

- `DocIR` 最小格式和质量标准尚未确认。
- `SchemaIR` 字段集合、枚举、`sourceText` 粒度和 `uncertain` 规则尚未确认。
- `b2e0061.md` 对应的 expected DocIR / expected SchemaIR 尚未确认。
- workbook assertions 依赖 confirmed SchemaIR，尚未确认。

在这些内容确认前，不应实现正式 SchemaIR Validator、Workbook Generator 或 golden regression，避免把候选 IR 固化为 runtime contract。

## 4. 下一步任务

### TASK P0-1：确认 Phase0 / Phase0a 文档边界

目标：让后续执行者清楚区分完整 Phase0、已完成 Phase0a bootstrap、当前 IR blocker 和下一步样例确认任务。

涉及范围：

- `docs/planning/phase0-poc-plan.md`
- `docs/planning/phase0a-poc-tasks.md`
- `docs/phases/phase0-poc.md`
- `README.md`

完成标志：

- README 当前状态与 planning 一致。
- Phase0 目标仍包含 Schema Workbook 和 golden regression。
- Phase0a 文档不再暗示旧 TASK 3-8 可直接继续实施。

### TASK P0-2：产出 `b2e0061` IR candidate

目标：基于 `docs/reference/samples/b2eboc/b2e0061.md` 产出用于人工 review 的 candidate IR。

输出候选：

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

### TASK P0-3：确认 golden sample 边界

目标：在 candidate IR 经人工确认后，形成正式 golden sample 输入。

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

### TASK P0-4：实现 trusted chain

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

### TASK P0-5：接入 draft generator

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

本文档更新阶段：

- `git diff --check`
- 手工确认 README、Phase0 phase 文档和 planning 文档状态一致。

后续实现阶段：

- `uv run --group dev pytest`
- Validator 字段级错误测试。
- Workbook 结构化 assertions 测试。
- docs-sync 检查。

只要用户可见命令、artifact、配置、验证方式或阶段状态发生变化，必须检查 `README.md`。
