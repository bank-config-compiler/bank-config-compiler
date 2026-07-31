# Phase0-PoC 需求

## Status

Draft. Trusted-chain work is partially implemented; ConfigIR and Configuration Workbook work is blocked by the unavailable target-system catalog.

## 1. 阶段目标

Phase0-PoC 证明一条无 UI、可重复运行、可校验、可人工确认、可回归的配置辅助链路可行：

```text
Raw Docs
→ DocIR Draft / Final DocIR
→ SchemaIR Draft / Validator / Final SchemaIR
→ ConfigIR Draft / Validator / Final ConfigIR
→ deterministic Configuration Workbook
→ structured golden regression
```

本阶段不验证生产集成。成功标准是使用真实脱敏 XML 银行接口样例产出三层中间模型、两份校验结果和 Configuration Workbook，并以结构化 assertions 证明链路可重复。

Skill、Agent 或 workflow 可以生成 Draft，但不能替代 Validator、人工确认、确定性 Generator 和 golden regression。

## 2. 当前事实

已完成：

- Python CLI、`ingest`、workspace artifact bootstrap 和 `check`。
- `b2e0061` reference raw doc。
- 经人工 Review 的 expected DocIR、expected SchemaIR 和 expected review notes。
- SchemaIR Validator v1、字段级校验结果契约和 expected validation result。当前 Validator 仍接受早期 JSON 枚举，尚需按 XML-only 产品契约收紧。

尚未完成：

- DocIR、SchemaIR 和 ConfigIR Draft generator。
- SchemaIR Validator 的 XML-only 枚举对齐。
- `configuration-rules/v1`。
- ConfigIR machine wire contract、人工确认 fixture 和 ConfigIR Validator。
- Configuration Workbook Generator、expected workbook 和结构化 workbook assertions。
- 覆盖完整可信链路的 golden regression。

当前 catalog 尚未提供。具体字段、function、mapping 和 Rule ID 不得从历史导出 JSON、LLM 或相近概念推断，因而 ConfigIR 与 Configuration Workbook 实现保持 Blocked。详细任务状态见 `docs/planning/00-phase0-poc-plan.md`。

## 3. In Scope

- 使用一份真实脱敏 XML 银行接口文档作为验证样例。
- `.md`、`.txt` 和粘贴文本输入。
- Raw Docs 到 DocIR Draft，人工确认 Final DocIR fixture。
- Final DocIR 到 SchemaIR Draft，SchemaIR Validator，人工确认 Final SchemaIR fixture。
- 整理并由业务负责人确认不可变 `configuration-rules/v1`。
- Final SchemaIR 与指定规则版本到 ConfigIR Draft。
- 人工确认 ConfigIR fixture 和 ConfigIR Validator。
- Workbook Generator 基于双 Final 模型、两份通过校验结果和指定规则版本生成 Configuration Workbook。
- 保存关键中间产物和规则版本。
- 结构化 golden regression。
- ASSEMBLY 与 PARSE 使用同一 ConfigIR 表达模型。

## 4. Out of Scope

- UI。
- JSON 银行报文。
- `.docx`、PDF、OCR、bbox 和原文区域高亮。
- Import JSON、目标系统 API 写入、自动导入和生产库直连。
- Excel 反向导入或更新 ConfigIR。
- 连接、认证、证书、部署或全量系统配置。
- 多用户、权限和审批流。
- RAG、多 Agent、自动微调、自动规则学习。
- 复杂 condition DSL。
- 多银行和多报文标准泛化。

## 5. 功能需求

### 5.1 DocIR

系统基于 Raw Docs 生成 DocIR Draft，至少保留：

- 接口编码、接口名称、XML 报文格式和版本；
- `ASSEMBLY` 与 `PARSE`；
- 字段表、章节、XML 示例和条件；
- 字段层级、原始约束、来源证据、冲突与不确定项。

人工确认后形成 Final DocIR。

### 5.2 SchemaIR

系统基于 Final DocIR 生成 SchemaIR Draft。SchemaIR 保存银行 XML element、attribute、path、父子层级、类型、required、length、occurs、condition、evidence 和不确定性。

SchemaIR Validator 必须提供字段级错误，并拦截非法结构、枚举、路径和确定性 invariant。人工修改后必须重新校验，确认后形成 Final SchemaIR。

### 5.3 规则包

Phase0 必须使用业务负责人确认的不可变 `configuration-rules/v1`，其中包含：

- 六种取值方式和选择/处理规则；
- 稳定 Rule ID；
- 目标系统字段 catalog；
- function catalog；
- mapping catalog。

资料未提供前，本项保持 Blocked，不得制造占位业务标识。

### 5.4 ConfigIR

LLM 结合 Final SchemaIR 和 `configuration-rules/v1` 生成 ConfigIR Draft。ConfigIR 必须覆盖：

- `FIXED_VALUE`、`EMPTY`、`FIELD`、`FUNCTION`、`MAPPING`、递归 `CONCATENATE`；
- configured required、empty/overlength handling、configured length、row limit；
- 中文字符长度、非法字符和有序替换；
- Rule ID、confidence、不确定原因和人工 Review 结论；
- SchemaIR/ConfigIR 差异、原因与规则依据。

ConfigIR Validator 只校验结构、引用和确定性 invariant。人工确认业务语义后形成 Final ConfigIR。

### 5.5 Configuration Workbook

Generator 只读取 Final SchemaIR、Final ConfigIR、两份与 Final 内容匹配的通过校验结果和 `configuration-rules/v1`。

工作簿固定包含 `Overview`、`ASSEMBLY`、`PARSE`、`Value Expressions`、`Warnings`、`Rule References`、`Legend`。未映射、规则冲突、差异和 Validator issue 必须进入 Warnings。

工作簿是配置规格与执行清单，不直接导入目标系统，也不反向更新 ConfigIR。

## 6. Golden Regression

Phase0 golden regression 至少覆盖：

- ASSEMBLY 与 PARSE；
- `FIELD`；
- `FIXED_VALUE`；
- `EMPTY`；
- `FUNCTION`；
- `MAPPING`；
- 包含任意模式子表达式的递归 `CONCATENATE`；
- SchemaIR/ConfigIR required 或 length 差异；
- 未映射、规则冲突和 warning；
- 七个固定 workbook sheet 和状态列。

具体业务字段、function、mapping 和 Rule ID 只能来自已确认的 `v1` catalog。

## 7. 通过条件

- DocIR、SchemaIR、ConfigIR 逻辑契约与机器格式均已冻结。
- `configuration-rules/v1` 的内容可追溯且经业务负责人确认。
- 两个 Validator 都能返回可定位的错误。
- 三个 Draft 都能生成，且不会绕过人工确认形成 Final。
- 双 Final 模型可以稳定生成 Configuration Workbook。
- 结构化 regression 覆盖六种 Value Mode、递归表达式、差异和 warnings。
- 全链路可重复运行并通过测试。

catalog 未确认时，Phase0 不满足通过条件。
