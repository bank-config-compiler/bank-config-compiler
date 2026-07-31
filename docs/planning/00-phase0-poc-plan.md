# Phase0-PoC 执行计划

## Status

Active. P0-T3 is blocked by the unavailable target-system catalog.

## 1. 目标与边界

Phase0-PoC 证明一条无 UI、可重复运行、可回归的可信链路：

```text
Raw Docs
→ Final DocIR
→ SchemaIR Draft / Validator / Final SchemaIR
→ ConfigIR Draft / Validator / Final ConfigIR
→ Configuration Workbook
→ golden regression
```

LLM 只生成 Draft。Workbook Generator 只消费双 Final 模型、两份通过校验结果和指定规则版本。

Phase0a 不再作为独立 active phase。已完成 CLI、`ingest`、workspace artifact 协议和 `check` 统一记录为 Phase0 bootstrap。

## 2. 当前状态

| TASK | 状态 | 依赖 | 阻塞点 | 完成标志 |
|---|---|---|---|---|
| P0-T0：Bootstrap | Done | 无 | 无 | CLI 可导入 raw doc，workspace artifact 协议和 `check --profile raw\|phase0a` 可用。 |
| P0-T1：`b2e0061` IR candidate / Review | Done | P0-T0 | 无 | Candidate DocIR / SchemaIR 经 Human Review 更新，正式 IR 设计和 reference 边界清晰。 |
| P0-T2：Review Golden sample boundary | Done | P0-T1 | 无 | Expected DocIR、expected SchemaIR 和 expected review notes 已冻结。 |
| P0-T3：Trusted chain | Blocked | P0-T2、真实 catalog | 目标系统 fields/functions/mappings catalog 尚未提供，不能形成 `configuration-rules/v1`、Final ConfigIR 或工作簿断言 | 保留已完成 SchemaIR Validator；完成规则包 v1、ConfigIR contract/fixture/Validator、Configuration Workbook 和结构化 golden regression。 |
| P0-T4：Draft generators | Blocked | P0-T3 | trusted chain 未完成 | DocIR、SchemaIR、ConfigIR 的 stub 与 LLM Draft generators 可运行，且 LLM 不进入可信边界。 |

状态定义：

- `Done`：完成标志与验证均已满足。
- `In Progress`：已有可验证子产物，但完整完成标志未满足。
- `Next`：依赖已满足，应优先执行。
- `Blocked`：存在明确前置条件，不能开始或继续关键工作。

## 3. 已完成证据

- `samples/golden/b2eboc-b2e0061/docir.expected.md`：expected DocIR。
- `samples/golden/b2eboc-b2e0061/schemair.expected.json`：expected SchemaIR。
- `samples/golden/b2eboc-b2e0061/review-notes.expected.md`：expected Review output；未确认业务问题是样例的一部分。
- `samples/golden/b2eboc-b2e0061/schemair-validation.expected.json`：expected SchemaIR Validator result。
- SchemaIR Validator v1 已实现并已有自动化测试；当前仍接受早期 `JSON` / JSON node kind 枚举，后续需按 XML-only 产品契约收紧。

这些证据只证明 DocIR / SchemaIR Review boundary 和 SchemaIR Validator，不证明 ConfigIR、规则包、Configuration Workbook 或完整可信链路已实现。

SchemaIR Validator 的现有 legacy JSON 枚举只是实现差距，不是 JSON 银行报文支持证据。

## 4. P0-T3：Trusted chain

### 4.1 当前 blocker

需要用户后续整理并提供目标系统资料：

- 字段原始标识和显示名称；
- function 原始标识、显示名称、参数和适用规则；
- mapping 原始标识、显示名称和业务含义；
- 六种取值方式的选择规则；
- required、empty、overlength、length、row limit、中文字符、非法字符和替换规则。

在资料提供并经业务 Review 前：

- 不创建带占位内容的 `configuration-rules/v1`；
- 不从 `docs/reference/` 历史导出 JSON 提取 catalog；
- 不让 LLM 或实现者猜测相近字段、function、mapping 或 Rule ID；
- ConfigIR schema、fixture、Validator 和 Workbook Generator 保持 Blocked。

### 4.2 规则包 v1

输入条件：真实资料已提供。

涉及文件：

```text
configuration-rules/v1/
├── README.md
├── rules.md
├── fields.md
├── functions.md
└── mappings.md
```

完成标志：

- 规则包由业务负责人确认。
- 每条可引用规则具有稳定且唯一的 Rule ID。
- catalog 只包含真实原始标识和显示名称。
- v1 发布后不可原地覆盖。

### 4.3 SchemaIR Validator XML-only 对齐

本次文档批次不修改代码。后续实现批次必须：

- 将 `messageFormat` 的可接受产品值收紧为 `XML`；
- 移除当前产品路径中的 `JSON_OBJECT`、`JSON_ARRAY`；
- 增加拒绝 legacy JSON 枚举的测试；
- 保持现有 XML golden validation 通过。

### 4.4 ConfigIR contract 与 fixture

输入条件：`configuration-rules/v1` 已确认。

涉及范围：

- 冻结可机器校验的 ConfigIR JSON contract。
- 为 b2e0061 形成经人工确认的 `configir.expected.json`。
- 同一表达模型覆盖 ASSEMBLY 与 PARSE。
- 至少覆盖 `FIELD`、`FIXED_VALUE`、`EMPTY`、`FUNCTION`、`MAPPING` 和递归 `CONCATENATE`。
- 覆盖 SchemaIR 与 ConfigIR required/length 差异、原因、Rule ID 和人工结论。

完成标志：

- 所有业务标识和 Rule ID 均可追溯到 v1。
- 缺少引用、未映射、规则冲突和未确认差异保持显式，不被猜测补齐。
- fixture 由业务负责人确认。

### 4.5 ConfigIR Validator

涉及范围：

- JSON 结构与枚举；
- SchemaIR path 引用；
- 递归 Value Expression；
- Rule ID 与 catalog 引用；
- 字段处理策略；
- 差异原因和人工 Review 结论；
- Final 条件。

完成标志：

- 返回可定位到 direction、path、expression 和 Rule ID 的错误。
- 只校验结构、引用和确定性 invariant。
- 不以程序判断代替 function/mapping 业务语义 Review。

### 4.6 Configuration Workbook 与 regression

涉及范围：

- 七个固定 sheet；
- ASSEMBLY / PARSE 完整列；
- 递归 Value Expressions 展开；
- Warnings 与 Rule References；
- 执行/验证状态；
- `workbook-assertions.expected.json`；
- 完整 trusted-chain golden regression。

完成标志：

- 相同双 Final 模型、两份校验结果和规则版本可重复生成相同结构化内容。
- 六种 Value Mode 和递归 `CONCATENATE` 均有断言。
- 未映射、规则冲突、差异和 Validator warning 均有断言。

## 5. P0-T4：Draft generators

P0-T3 完成后接入三个 Draft generator：

- Raw Docs → DocIR Draft；
- Final DocIR → SchemaIR Draft；
- Final SchemaIR + 指定规则版本 → ConfigIR Draft。

涉及范围：

- 确定性 stub；
- OpenAI-compatible adapter；
- 输出结构校验和缺配置错误；
- 敏感日志约束。

完成标志：

- LLM 只生成 Draft，不能直接写 Final。
- stub 输出稳定，可用于测试。
- 缺 catalog 时 ConfigIR Draft 生成 fail closed。
- 日志不输出完整银行原文、规则敏感内容或 secret。

## 6. 验证要求

当前文档批次：

- `git diff --check`
- UTF-8 no BOM 检查
- 旧路径和旧产品术语搜索
- Markdown 本地路径存在性检查
- Mermaid 人工渲染
- docs-sync

后续实现批次：

- `uv run --group dev pytest`
- SchemaIR / ConfigIR Validator 字段级错误测试
- Workbook 结构化 assertions
- 完整 golden regression
- docs-sync

只要用户可见命令、artifact、配置、验证方式或阶段状态变化，必须检查 `README.md`。
