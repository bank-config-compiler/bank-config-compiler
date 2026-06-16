# 架构参考草案

## Status

Reference / Draft. Not accepted architecture.

## Date

2026-05-27

## Context

本文整理 `tmp/` 中的架构草案，并按当前正式文档中的讨论结果调整边界。它不锁定最终技术栈，也不要求第一阶段必须同时实现 Java、Python 和 UI。

第一阶段目标是无 UI 端到端验证；最终 MVP 需要 Review Workbench UI。

## 候选端到端流程

```text
Raw Docs
→ Parser / Extractor
→ Parsed Document Blocks
→ LLM DocIR Normalizer
→ DocIR Draft
→ Human Review
→ Final DocIR
→ LLM SchemaIR Extractor
→ SchemaIR Draft
→ SchemaIR Validator
→ Human Review
→ Final SchemaIR
→ Workbook Generator
→ Schema Workbook
→ Preview / Download
```

第一阶段可以先通过命令、API 测试或本地脚本模拟 Human Review，例如以人工确认后的 fixture 文件作为 `Final DocIR` 和 `Final SchemaIR`。

## 候选模块边界

### Main App

候选职责：

- 任务创建与状态流转。
- 保存 Raw Docs、DocIR、SchemaIR、Validator 结果和 Schema Workbook。
- SchemaIR Validator。
- Workbook Generator。
- 对 UI 或测试客户端提供 API。

当前讨论结论：

- Java 是候选实现，但技术栈尚未最终确认。
- 如果采用 Java，它更适合承担可信边界、Validator、Workbook Generator 和系统集成边界。

### Agent Sidecar

候选职责：

- 文本 / Markdown 解析。
- Parsed Blocks 生成。
- LLM 调用。
- Prompt 编排。
- DocIR Draft 生成。
- SchemaIR Draft 生成。
- LLM 输出格式修复与重试。

当前讨论结论：

- Python FastAPI 是候选实现，不是已确认事实。
- 第一阶段是否需要独立 Sidecar 仍需讨论。

### Review Workbench

候选职责：

- Raw Docs 输入。
- DocIR Markdown 展示、编辑、保存、确认。
- SchemaIR 表格展示、编辑、校验、确认。
- Schema Workbook 预览和下载。

当前讨论结论：

- MVP 最终需要 UI。
- 第一阶段不需要 UI，应先完成无 UI 端到端验证。
- UI 不应改变无 UI 链路的核心产物格式。

## 候选任务状态

以下状态来自 `tmp` 草案，仅作为候选：

```text
RAW_DOC_CREATED
DOCIR_DRAFT_GENERATED
DOCIR_CONFIRMED
SCHEMAIR_DRAFT_GENERATED
SCHEMAIR_VALIDATED
SCHEMAIR_CONFIRMED
IMPORT_JSON_GENERATED
```

后续需要讨论：

- 是否需要 `FAILED` 状态。
- 是否需要记录阶段错误码。
- `SCHEMAIR_VALIDATED` 是否区分 valid / invalid。
- 无 UI 阶段人工确认如何映射状态。

## 候选 Workspace 结构

以下结构来自 `tmp` 草案，仅作为候选：

```text
workspace/{taskId}/
├── raw-doc.txt
├── parsed-blocks.json
├── docir-draft.md
├── docir-final.md
├── schemair-draft.json
├── schemair-final.json
├── schemair-validation-result.json
└── schema-workbook.xlsx
```

后续需要讨论：

- golden sample 是否复用同一产物结构。
- LLM 原始响应是否保存。
- Review 修改前后是否保存 diff。
- 敏感内容如何脱敏与排除日志。
- workspace 目录是否进入版本库。

## 候选技术栈

`tmp` 草案建议：

- Main App：Java 17 + Spring Boot。
- Agent Sidecar：Python + FastAPI。
- UI：React/Vue + Vite。
- 存储：文件目录或 H2。

当前正式文档结论：

- 技术栈仍需讨论。
- 第一阶段应优先证明无 UI 端到端链路。
- 不应为了符合草案而提前扩大架构。
