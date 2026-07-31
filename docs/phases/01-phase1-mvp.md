# Phase1-MVP 需求

## Status

Draft.

## 1. 阶段目标

Phase1-MVP 目标是将 Phase0-PoC 链路产品化为最小可用能力。

本阶段应提供可用的 Review 入口，支持 DocIR、SchemaIR、ConfigIR 的人工 Review、重新校验和确认，以及 Configuration Workbook 预览和下载，并建立基本测试、日志、错误处理和回归机制。

交付形态应是轻量 Review Tool，而不是完整生产系统。它可以是本地 Web UI、轻量服务或等价工具，但必须承载三层 IR Review、双 Validator、Workbook Generator、Configuration Workbook 预览下载和 golden sample regression。

## 2. In Scope

- 创建解析任务，保存任务名称、接口编码、报文格式和原始输入。
- UI 中查看 Raw Docs 和 DocIR Draft。
- 编辑、保存并确认 Final DocIR。
- 基于 Final DocIR 生成 SchemaIR Draft JSON。
- Validator 校验 SchemaIR Draft 并返回字段级错误列表。
- UI 中以表格形式展示 SchemaIR。
- 修改关键字段并重新校验。
- 确认 Final SchemaIR。
- 基于 Final SchemaIR 与指定规则版本生成 ConfigIR Draft。
- UI 中查看规则依据、差异、Value Expression 和 ConfigIR Validator 结果。
- 修改 ConfigIR 后重新校验，并确认 Final ConfigIR。
- Workbook Generator 基于双 Final 模型、两份校验结果和指定规则版本生成 Configuration Workbook。
- 预览和下载 Configuration Workbook。
- 保存任务状态与关键中间产物。
- 对 Validator 和 Workbook Generator 的关键转换逻辑提供基本单元测试。
- 提供真实脱敏 golden sample 和一键回归路径。

## 3. Out of Scope

- 真实导入银企直连生产配置库。
- 目标系统 Import JSON 生成或兼容性验证。
- 目标系统 API 写入、自动导入和 Excel 反向导入。
- JSON 银行报文。
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
- 报文格式：当前固定为 `XML`。
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

### 4.4 ConfigIR Review

用户应能：

- 按 ASSEMBLY / PARSE 和 SchemaIR path 查看系统字段配置。
- 查看并编辑六种 Value Mode 和递归 Value Expression。
- 查看规则版本、Rule ID、catalog 引用、confidence 和不确定原因。
- 对 SchemaIR/ConfigIR required、length 等差异作出人工结论。
- 查看 ConfigIR Validator 错误，修改后重新校验。
- 确认 Final ConfigIR。

### 4.5 Configuration Workbook 预览与下载

系统应由 Workbook Generator 基于 Final SchemaIR、Final ConfigIR、两份通过校验结果和指定规则版本生成 Configuration Workbook。

用户应能：

- 预览 Configuration Workbook 的七个 sheet、字段配置、Value Expressions、Warnings 和 Rule References。
- 下载 Configuration Workbook。

Configuration Workbook 不直接落库、不直接导入目标系统，也不反向更新 ConfigIR。

## 5. 通过条件

- 能输入一份真实脱敏 `.md` 或 `.txt` 银行接口样例。
- 系统能生成可读、可编辑的 DocIR Draft。
- Final DocIR 保留字段表、章节、条件说明和报文示例。
- SchemaIR Draft 覆盖样例 DocIR 中可识别字段，并保留 `sourceText`。
- Validator 能拦截明显错误并展示字段级错误信息。
- 用户能修正并确认 Final SchemaIR。
- 用户能 Review、重新校验并确认 Final ConfigIR。
- 未映射、规则冲突和 SchemaIR/ConfigIR 差异不会被静默忽略。
- Workbook Generator 能从双 Final 模型和指定规则版本稳定生成 Configuration Workbook。
- Configuration Workbook 能指导配置人员人工配置并记录执行/验证状态。
- UI 能预览和下载 Configuration Workbook。
- Golden sample 回归和关键转换测试通过。

## 6. 待确认问题

- Review Workbench 的最小页面结构。
- DocIR 编辑方式。
- SchemaIR 表格编辑能力边界。
- ConfigIR 递归表达式编辑方式。
- Validator 错误格式。
- 规则版本升级对已有 ConfigIR 的迁移与重新 Review 方式。
- 本地开发、依赖安装、模型配置和样例运行说明。
