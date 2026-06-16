# Phase1-MVP 需求

## Status

Draft.

## 1. 阶段目标

Phase1-MVP 目标是将 Phase0-PoC 链路产品化为最小可用能力。

本阶段应提供可用的 Review 入口，支持人工 Review、校验、确认、Schema Workbook 预览和下载，并建立基本测试、日志、错误处理和回归机制。

交付形态应是轻量 Review Tool，而不是完整生产系统。它可以是本地 Web UI、轻量服务或等价工具，但必须承载 Review、Validator、Workbook Generator、Schema Workbook 预览下载和 golden sample regression。

## 2. In Scope

- 创建解析任务，保存任务名称、接口编码、报文格式和原始输入。
- UI 中查看 Raw Docs 和 DocIR Draft。
- 编辑、保存并确认 Final DocIR。
- 基于 Final DocIR 生成 SchemaIR Draft JSON。
- Validator 校验 SchemaIR Draft 并返回字段级错误列表。
- UI 中以表格形式展示 SchemaIR。
- 修改关键字段并重新校验。
- 确认 Final SchemaIR。
- Workbook Generator 基于 Final SchemaIR 生成 Schema Workbook。
- 预览和下载 Schema Workbook。
- 保存任务状态与关键中间产物。
- 对 Validator 和 Workbook Generator 的关键转换逻辑提供基本单元测试。
- 提供真实脱敏 golden sample 和一键回归路径。

## 3. Out of Scope

- 真实导入银企直连生产配置库。
- 目标系统 Import JSON 生成或兼容性验证。
- Skill、纯 Agent 或单纯 Prompt workflow 作为完整交付物。
- 生产权限体系、登录认证、审批流、多用户协同。
- `.docx` 解析。
- PDF、OCR、bbox、高亮和原文区域定位。
- 复杂 RAG、多 Agent 编排、自动微调、自动规则学习。
- condition DSL 或复杂条件配置生成。
- 通用多银行、多报文标准、全格式自动解析平台。

## 4. 功能需求

### 4.1 任务创建与文档输入

系统应支持创建解析任务。任务至少包含：

- 任务名称。
- 接口编码。
- 报文格式：`XML` 或 `JSON`。
- 原始文档文本或上传的 `.md` / `.txt` 文件。

系统应保存原始输入，便于后续查看和追溯。

### 4.2 DocIR Review

用户应能：

- 查看 Raw Docs 和 DocIR Draft。
- 编辑 DocIR。
- 保存 DocIR 草稿。
- 确认 Final DocIR。

Final DocIR 必须保留字段表、章节、条件说明、报文示例和 `ASSEMBLY` / `PARSE` 方向信息。

### 4.3 SchemaIR Review

用户应能：

- 查看 SchemaIR 表格。
- 查看 Validator 错误列表。
- 修改 `path`、`fieldName`、`nodeKind`、`dataType`、`required`、`multiple`、`hasChildren`、`description`、`conditionText`、`uncertain`、`reviewNote` 等关键字段。
- 重新校验 SchemaIR。
- 确认 Final SchemaIR。

SchemaIR Draft 应覆盖样例 DocIR 中可识别字段，并保留 `sourceText`。

### 4.4 Schema Workbook 预览与下载

系统应由 Workbook Generator 基于 Final SchemaIR 生成 Schema Workbook。

用户应能：

- 预览 Schema Workbook 的 sheet 和字段清单。
- 下载 Schema Workbook。

Schema Workbook 不直接落库，不直接导入目标系统。

## 5. 通过条件

- 能输入一份真实脱敏 `.md` 或 `.txt` 银行接口样例。
- 系统能生成可读、可编辑的 DocIR Draft。
- Final DocIR 保留字段表、章节、条件说明和报文示例。
- SchemaIR Draft 覆盖样例 DocIR 中可识别字段，并保留 `sourceText`。
- Validator 能拦截明显错误并展示字段级错误信息。
- 用户能修正并确认 Final SchemaIR。
- Workbook Generator 能从 Final SchemaIR 稳定生成 Schema Workbook。
- Schema Workbook 能指导配置人员人工配置目标系统。
- UI 能预览和下载 Schema Workbook。
- Golden sample 回归和关键转换测试通过。

## 6. 待确认问题

- Review Workbench 的最小页面结构。
- DocIR 编辑方式。
- SchemaIR 表格编辑能力边界。
- Validator 错误格式。
- Workbook Generator 规则治理方式。
- 本地开发、依赖安装、模型配置和样例运行说明。
