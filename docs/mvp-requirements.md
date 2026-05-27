# 银行接口文档解析 Agent MVP 需求文档

## Status

Proposed.

## Date

2026-05-27

## Confirmed Discussion Points

- MVP 使用真实脱敏银行接口文档作为验证样例，字段规模应接近真实业务，初步目标为 20 个以上字段。
- Import JSON 应贴近真实银企直连导入格式，后续由用户提供真实或接近真实的样例。
- DocIR 和 SchemaIR 的最小格式仍需继续分析确认。
- MVP 最终需要包含 UI，但第一阶段先做无 UI 的端到端验证。
- 技术栈仍需讨论，不在本需求文档中锁死。
- MVP 必须包含 golden sample。

## 1. 背景

银企直连系统通常需要根据银行接口文档配置报文标准、报文模板、页面字段、字段层级和转换规则。银行文档来源多样，字段表、XML/JSON 示例、必输规则、重复节点和条件说明经常分散在不同章节，实施人员需要人工阅读、整理和判断。

当前主要问题是：

- 银行接口文档格式不统一，人工解析成本高。
- 字段层级、必输、重复节点和条件说明依赖人工经验判断。
- 手工整理配置草稿耗时长，质量不稳定。
- 缺少可追溯的中间产物，后续 Review 与问题排查成本高。

本 MVP 目标不是替代人工，也不是直接生成生产可信配置，而是验证一条可审计的人机协同配置草稿生成链路。

## 2. MVP 目标

验证以下命题：

```text
对于一份真实脱敏的银行接口文本或 Markdown 文档，
系统能自动生成可人工 Review 的 DocIR，
再基于确认后的 DocIR 生成字段级 SchemaIR，
经 Validator 与人工修正后，
由确定性 Rule Engine 生成可预览和下载的 Import JSON 草稿。
```

## 3. 用户与场景

### 实施人员

上传或粘贴银行接口文档，检查系统生成的 DocIR 和 SchemaIR，修正明显错误，并确认进入下一阶段。

### 开发人员

维护文档解析、Prompt、LLM 调用、Validator、Rule Engine 和样例回归。

### 审核人员

检查最终配置草稿是否具备进入真实导入流程的基础质量。MVP 阶段只支持检查和下载，不直接导入生产配置库。

## 4. MVP 范围

### 4.1 In Scope

- 支持粘贴文本、上传 `.md`、上传 `.txt`。
- 基于原始文档生成 DocIR Draft。
- 在 UI 中展示、编辑、保存并确认 Final DocIR。
- MVP 最终包含 Review Workbench UI，但第一阶段允许先交付无 UI 端到端验证。
- 基于 Final DocIR 生成 SchemaIR Draft JSON。
- 使用 Java Validator 校验 SchemaIR Draft。
- 在 UI 中以表格形式展示 SchemaIR，允许修改关键字段。
- 确认 Final SchemaIR。
- 基于 Final SchemaIR 通过 Java Rule Engine 生成 Import JSON 草稿。
- 在 UI 中预览、复制和下载 Import JSON。
- 保存任务状态与关键中间产物。
- 对关键转换逻辑提供基本单元测试。
- 提供真实脱敏 golden sample，字段规模初步目标为 20 个以上字段。

### 4.2 Out of Scope

- 真实导入银企直连生产配置库。
- 生产权限体系、登录认证、审批流、多用户协同。
- `.docx` 解析。
- PDF、OCR、bbox、高亮和原文区域定位。
- 复杂 RAG、多 Agent 编排、自动微调、自动规则学习。
- condition DSL 或复杂条件配置生成。
- 通用多银行、多报文标准、全格式自动解析平台。

## 5. 核心流程

```text
Raw Docs
→ DocIR Draft
→ Human Review DocIR
→ Final DocIR
→ SchemaIR Draft
→ Java Validator
→ Human Review SchemaIR
→ Final SchemaIR
→ Java Rule Engine
→ Import JSON Draft
→ Preview / Download
```

Draft 未经人工确认时，不能被当作最终产物进入后续可信配置流程。

## 6. 功能需求

### 6.1 任务创建与文档输入

系统应支持创建解析任务。任务至少包含：

- 任务名称。
- 报文类型。
- 原始文档文本或上传的 `.md` / `.txt` 文件。

系统应保存原始输入，便于后续查看和追溯。

### 6.2 DocIR 生成与 Review

系统应基于原始文档生成 DocIR Draft。

DocIR 必须是强结构化 Markdown，至少保留：

- 报文名称、报文类型、格式、版本等基础信息，若原文缺失则留空或标记不确定。
- 原始字段表中的字段名、路径、类型、长度、出现次数、必输标记和说明。
- 章节结构。
- 条件说明。
- XML/JSON 示例。
- 无法确认的信息和需要人工检查的位置。

用户应能在 UI 中：

- 查看 Raw Docs 和 DocIR Draft。
- 编辑 DocIR。
- 保存 DocIR 草稿。
- 确认 Final DocIR。

### 6.3 SchemaIR 生成与 Review

系统应基于 Final DocIR 生成 SchemaIR Draft JSON。

SchemaIR 顶层至少包含：

- `messageName`
- `messageType`
- `format`
- `version`
- `fields`

每个字段至少包含：

- `path`
- `fieldName`
- `dataType`
- `required`
- `multiple`
- `hasChildren`
- `sourceText`
- `confidence`
- `uncertain`
- `uncertainReason`

SchemaIR 字段应覆盖样例 DocIR 中可识别的字段。若字段缺少充分证据，系统应保留字段并设置 `uncertain=true`，而不是静默丢弃。

用户应能在 UI 中：

- 查看 SchemaIR 表格。
- 查看 Validator 错误列表。
- 修改 `path`、`fieldName`、`dataType`、`required`、`multiple`、`hasChildren`、`description`、`uncertain` 等关键字段。
- 重新校验 SchemaIR。
- 确认 Final SchemaIR。

### 6.4 SchemaIR Validator

Java Validator 至少应校验：

- `path` 非空。
- `fieldName` 非空。
- `dataType` 属于允许枚举。
- `required` 是 boolean。
- `multiple` 是 boolean。
- `hasChildren` 是 boolean。
- `confidence` 在 0 到 1 之间。
- `sourceText` 非空。
- `path` 不重复。
- 父子路径关系可解释。
- `hasChildren`、`multiple` 和 `dataType` 不存在明显冲突。

Validator 失败时，应返回可展示的错误列表，不能只返回通用失败信息。

### 6.5 Import JSON 生成与预览

系统应由 Rule Engine 基于 Final SchemaIR 生成 Import JSON 草稿。

Import JSON MVP 阶段只用于预览和下载，不直接落库。Import JSON 应贴近真实银企直连导入格式；在用户提供真实或接近真实的样例后，需要补充目标字段模型、字段命名、层级关系和兼容性约束。

Import JSON 至少应体现：

- 报文标识。
- 字段编码。
- 字段名称。
- 字段路径。
- 字段类型。
- 控件类型。
- 必输标记。
- 父字段关系。
- 层级。
- 是否重复。
- 草稿来源和状态。

## 7. 非功能需求

- 关键中间产物必须可查看、可复制、可下载。
- 任务状态必须可追踪。
- LLM 调用失败时必须返回明确错误。
- LLM 输出进入后续流程前必须经过格式校验。
- 不允许在日志中输出完整银行文档敏感内容。
- 日志应包含任务标识、阶段和错误原因，便于定位。
- 文件编码使用 UTF-8 with NO BOM。
- MVP 应提供一份真实脱敏 golden sample 和一键回归路径。

## 8. 成功标准

MVP 通过必须同时满足：

- 能输入一份真实脱敏的 `.md` 或 `.txt` 银行接口样例，字段规模初步目标为 20 个以上字段。
- 系统能生成可读、可编辑的 DocIR Draft。
- Final DocIR 保留字段表、章节、条件说明和报文示例。
- SchemaIR Draft 覆盖样例 DocIR 中可识别字段，并保留 `sourceText`。
- Validator 能拦截明显错误并展示字段级错误信息。
- 用户能修正并确认 Final SchemaIR。
- Rule Engine 能从 Final SchemaIR 稳定生成 Import JSON 草稿。
- Import JSON 草稿贴近用户提供的真实或接近真实导入格式样例。
- UI 能预览、复制、下载 Import JSON。
- 第一阶段无 UI 端到端验证能够稳定生成 golden sample 输出。
- 关键转换逻辑测试通过。

## 9. 失败标准

出现以下任一情况，应视为 MVP 失败或需要调整范围：

- DocIR 只能人工编写，系统没有自动生成能力。
- LLM 直接生成 Import JSON。
- Draft 未经人工确认就进入最终配置流程。
- SchemaIR 没有 Validator。
- SchemaIR 静默丢弃可识别字段。
- UI 无法串起 DocIR Review、SchemaIR Review 和 Import JSON 预览。
- Import JSON 不能从 Final SchemaIR 稳定生成。
- 只能跑玩具样例，无法证明对真实脱敏文档有帮助。

## 10. Open Questions

- DocIR 最小格式应包含哪些章节、字段和来源标记？
- SchemaIR 最小格式应包含哪些字段、类型枚举和校验规则？
- XML/JSON 示例推导出的 path 是否需要单独标记推导来源？
- 企业模型网关是否兼容 OpenAI-style API？
- 第一阶段无 UI 端到端验证采用命令行、API 测试，还是二者同时提供？
- 技术栈是否采用 Java/Python 双服务，还是先用更小实现证明链路？
- Golden sample 的目录结构、文件命名和回归命令如何定义？
- 审核人员在 MVP 中只下载草稿，还是需要留下显式审核结论？
