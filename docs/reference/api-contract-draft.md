# API Contract 参考草案

## Status

Reference / Draft. Not accepted API.

## Date

2026-05-27

## Context

本文从 `tmp/docs/api-contract.md` 整理候选 API。当前技术栈和第一阶段交付形态尚未确认，因此这些接口只作为后续规划参考。

第一阶段可能采用命令行、API 测试或本地脚本完成无 UI 端到端验证，不要求立即实现完整 HTTP API。

## Main App API 候选

### 创建任务

```http
POST /api/tasks
```

Request:

```json
{
  "taskName": "pain001-demo",
  "messageType": "pain.001",
  "rawDocumentText": "..."
}
```

Response:

```json
{
  "taskId": "task-001",
  "status": "RAW_DOC_CREATED"
}
```

### 生成 DocIR Draft

```http
POST /api/tasks/{taskId}/docir/generate
```

Response:

```json
{
  "taskId": "task-001",
  "status": "DOCIR_DRAFT_GENERATED",
  "docirDraft": "# Message\n..."
}
```

### 确认 Final DocIR

```http
PUT /api/tasks/{taskId}/docir/final
```

Request:

```json
{
  "docirFinal": "# Message\n..."
}
```

Response:

```json
{
  "taskId": "task-001",
  "status": "DOCIR_CONFIRMED"
}
```

### 生成 SchemaIR Draft

```http
POST /api/tasks/{taskId}/schemair/generate
```

Response:

```json
{
  "taskId": "task-001",
  "status": "SCHEMAIR_DRAFT_GENERATED",
  "schemairDraft": {}
}
```

### 校验 SchemaIR

```http
POST /api/tasks/{taskId}/schemair/validate
```

Response:

```json
{
  "valid": false,
  "errors": [
    {
      "path": "GrpHdr.MsgId",
      "message": "sourceText must not be empty"
    }
  ]
}
```

### 确认 Final SchemaIR

```http
PUT /api/tasks/{taskId}/schemair/final
```

Request:

```json
{
  "schemairFinal": {}
}
```

Response:

```json
{
  "taskId": "task-001",
  "status": "SCHEMAIR_CONFIRMED"
}
```

### 生成 Schema Workbook

```http
POST /api/tasks/{taskId}/schema-workbook/generate
```

Response:

```json
{
  "taskId": "task-001",
  "status": "SCHEMA_WORKBOOK_GENERATED",
  "workbook": {
    "fileName": "task-001-schema-workbook.xlsx",
    "sheets": ["Overview", "ASSEMBLY", "PARSE", "Warnings", "Legend"]
  }
}
```

## Agent API 候选

如果后续确认需要独立 Agent Sidecar，可参考以下接口。

### 生成 DocIR

```http
POST /agent/docir/generate
```

Request:

```json
{
  "taskId": "task-001",
  "rawDocumentText": "...",
  "messageType": "pain.001"
}
```

Response:

```json
{
  "docirDraft": "# Message\n...",
  "warnings": []
}
```

### 生成 SchemaIR

```http
POST /agent/schemair/generate
```

Request:

```json
{
  "taskId": "task-001",
  "docirFinal": "# Message\n..."
}
```

Response:

```json
{
  "schemairDraft": {},
  "warnings": []
}
```

## 错误格式候选

```json
{
  "code": "LLM_OUTPUT_INVALID",
  "message": "LLM output is not valid JSON",
  "detail": "..."
}
```

后续需要讨论：

- `detail` 是否允许包含 LLM 原始输出。
- 错误是否需要 `taskId`、`stage`、`timestamp`。
- Validator 错误是否和系统错误使用同一 envelope。
- 错误码命名是否需要稳定化。
