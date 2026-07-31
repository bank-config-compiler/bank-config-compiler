# Phase0-PoC 需求

## Status

Draft. Trusted-chain work is partially implemented; InterfaceStandardIR, InterfaceTemplateIR and Configuration Workbook work is blocked by the unavailable target-system catalog.

## 1. 阶段目标

Phase0-PoC 证明一条无 UI、可重复运行、可校验、可人工确认、可回归的配置辅助链路可行：

```text
Raw Docs
→ DocIR Draft / Final DocIR
→ SchemaIR Draft / Validator / Final SchemaIR
→ InterfaceStandardIR Draft / Validator / Final Standard
→ InterfaceTemplateIR Draft / Validator / Final Template
→ deterministic Configuration Workbook
→ structured golden regression
```

本阶段不验证生产集成。成功标准是使用真实脱敏 XML 银行接口样例产出四层 IR、三份校验结果和按方向模板生成的 Configuration Workbook，并以结构化 assertions 证明链路可重复。

LLM、Agent 或 workflow 可以生成 Draft，但不能替代 Validator、人工确认、确定性 Generator 和 golden regression。

## 2. 当前事实

已完成：

- Python CLI、`ingest`、workspace artifact bootstrap 和 `check`。
- `b2e0061` reference raw doc。
- 经人工 Review 的 expected DocIR、expected SchemaIR 和 expected review notes。
- SchemaIR Validator v1、字段级校验结果契约和 expected validation result。当前 Validator 仍接受早期 JSON 枚举，尚需按 XML-only 产品契约收紧。

尚未完成：

- 四类 IR Draft generator。
- SchemaIR Validator 的 XML-only 枚举对齐。
- `configuration-rules/v1`。
- InterfaceStandardIR / InterfaceTemplateIR machine wire contract、人工确认 fixture 和 Validator。
- Configuration Workbook Generator、expected workbook 和结构化 assertions。
- 覆盖完整可信链路的 golden regression。

当前 catalog 尚未提供。具体字段、function、mapping 和 Rule ID 不得从历史导出 JSON、LLM 或相近概念推断，因而两个目标配置 IR 与 Configuration Workbook 实现保持 Blocked。详细任务状态见 `docs/planning/00-phase0-poc-plan.md`。

## 3. In Scope

- 使用一份真实脱敏 XML 银行接口文档作为验证样例。
- `.md`、`.txt` 和粘贴文本输入。
- Raw Docs 到 DocIR Draft，人工确认 Final DocIR fixture。
- Final DocIR 到 SchemaIR Draft，SchemaIR Validator，人工确认 Final SchemaIR fixture。
- 整理并由业务负责人确认不可变 `configuration-rules/v1`。
- Final SchemaIR 到 InterfaceStandardIR Draft、Standard Validator 和人工确认 Final Standard。
- Final Standard 到 InterfaceTemplateIR Draft、Template Validator 和人工确认 Final Template。
- 一个标准关联多份同方向模板，模板精确绑定不可变标准版本。
- 模板字段子集、omission Warning 与人工 Review。
- 字段值和 XML Key 使用同一递归 Value Expression 模型。
- Workbook Generator 基于三份 Final 模型、三份校验结果、规则版本和 Standard Action 生成一份方向模板工作簿。
- 保存关键中间产物和结构化 golden regression。

## 4. Out of Scope

- UI。
- JSON 银行报文和目标系统 `List` 配置。
- `.docx`、PDF、OCR、bbox 和原文区域高亮。
- Import JSON、目标系统 API 写入、自动导入和生产库直连。
- Excel 反向导入或更新任一 IR。
- 连接、认证、证书、部署或全量系统配置。
- 同一标准字段多条模板行和 condition 选择逻辑。
- 多用户、权限和审批流。
- RAG、多 Agent、自动微调、自动规则学习。
- 多银行和多报文标准泛化。

## 5. 功能需求

### 5.1 DocIR 与 SchemaIR

DocIR Draft 至少保留接口编码、XML 格式、ASSEMBLY/PARSE、字段表、章节、XML 示例、条件、来源证据、冲突和不确定项。人工确认后形成 Final DocIR。

SchemaIR Draft 保存银行 XML element、attribute、完整 path、父子层级、类型、required、length、occurs、condition 和 evidence。SchemaIR Validator 必须提供字段级错误；人工修改后必须重新校验，确认后形成 Final SchemaIR。

### 5.2 规则包

Phase0 必须使用业务负责人确认的不可变 `configuration-rules/v1`，其中包含：

- Interface Standard 的路径、类型和约束映射规则；
- 六种 Value Mode 和模板处理策略；
- 稳定 Rule ID；
- 目标系统 field、function 和 mapping catalog。

资料未提供前，本项保持 Blocked，不得制造占位业务标识。

### 5.3 InterfaceStandardIR

LLM 结合 Final SchemaIR 和规则版本生成 Standard Draft，至少覆盖：

- `interfaceCode + direction`、稳定 ID 和不可变版本；
- fieldId、sequence、field name/description；
- parentPath 与 fullPath；
- required、length、illegal characters、regex；
- XML Keys；
- String/Boolean/Date/Number/Node/Object；
- VALUE、NO_CONSTRAINT、UNKNOWN；
- SchemaIR/Standard 差异、规则依据和人工结论。

Standard Validator 只校验结构、来源引用和确定性 invariant。人工确认后形成 Final Standard。

### 5.4 InterfaceTemplateIR

LLM 基于 Final Standard 和规则版本生成 Template Draft，至少覆盖：

- 精确 Standard ID/version/content hash 绑定；
- 标准字段的合法子集；
- FIXED_VALUE、EMPTY、FIELD、FUNCTION、MAPPING 和递归 CONCATENATE；
- 字段值与每个 XML Key 的独立表达式；
- empty/overlength handling、row limit、中文字符长度和有序替换；
- Rule ID、confidence、不确定原因和人工结论；
- 缺失字段的 Warning、omission reason 与 Review disposition。

未确认 omission 阻止 Final Template；确认有意省略后允许 Final 并继续进入 Workbook Warnings。Template Validator 不能代替人工判断 function、mapping 或 omission 的业务语义。

### 5.5 Configuration Workbook

Generator 只读取 Final SchemaIR、Final Standard、选定的 Final Template、三份匹配的校验结果、精确规则版本和显式 Standard Action。

工作簿固定包含 `Overview`、`Interface Standard`、`Interface Template`、`Value Expressions`、`Warnings`、`Rule References`、`Legend`。

`Value Expressions` 按树展开字段值和 XML Key 表达式，是 Final Template 的派生明细，不是额外事实源。已确认 omission 进入 Warnings，不在 Template Sheet 生成虚假行。

工作簿不直接导入目标系统，也不反向更新任一 IR。

## 6. Golden Regression

Phase0 golden regression 至少覆盖：

- ASSEMBLY 与 PARSE 独立标准和模板；
- parentPath/fullPath、sequence、Node/Object、XML Keys；
- VALUE、NO_CONSTRAINT、UNKNOWN；
- 六种 Value Mode 和递归 CONCATENATE；
- 模板字段子集、未确认/已确认 omission 和 EMPTY 的区别；
- 字段值与 XML Key expression tree；
- Standard version/hash mismatch；
- SchemaIR/Standard 差异、规则冲突和 warnings；
- 七个固定 workbook sheet、Standard Action 和状态列。

具体业务字段、function、mapping 和 Rule ID 只能来自已确认的 v1 catalog。

## 7. 通过条件

- 四类 IR 逻辑契约与机器格式均已冻结。
- `configuration-rules/v1` 内容可追溯且经业务负责人确认。
- 三个 Validator 都能返回可定位的错误。
- 四个 Draft generator 可运行，且不会绕过人工确认形成 Final。
- Template 只能基于精确绑定的 Final Standard 生成。
- 模板字段子集和 omission Review 可回归验证。
- 三份 Final 模型可以稳定生成一个方向模板的 Configuration Workbook。
- 完整链路可重复运行并通过测试。

catalog 未确认时，Phase0 不满足通过条件。
