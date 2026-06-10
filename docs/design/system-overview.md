# 系统设计总览

## Status

Draft.

## 1. 设计目标

系统设计目标是支持一条可审计的人机协同配置草稿生成链路：

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
→ Rule Engine
→ Import JSON Draft
→ Preview / Download
```

早期阶段可以省略 UI，以命令、API 测试或本地脚本模拟 Human Review。产品化阶段应提供可用的 Review 入口，但 UI 不应改变核心产物格式。

## 2. 交付形态

项目交付形态按阶段演进：

- Phase0-PoC：可重复运行的链路验证工具，例如 CLI、script 或 lightweight workflow runner，加文件 workspace、fixtures、Validator、Rule Engine 和 golden sample regression。
- Phase1-MVP：轻量 Review Tool，承载 Review、校验、确认、预览和下载。
- Phase2-Pilot：受控内部试点工具或小型内部系统，用于验证真实提效、稳定性和运维边界。
- Phase3-Production：暂不定义。

Skill、Agent 和 Dify workflow 的定位：

- Skill 可以辅助开发、验证或封装局部操作流程，但不是业务交付物。
- Agent 可以承担 DocIR Draft 和 SchemaIR Draft 生成，但不能决定最终配置可信性。
- Dify workflow 可以作为 Phase0-PoC 的 LLM 编排实验工具，但不应替代 Validator、Rule Engine、Human Review 边界和 golden sample regression。

## 3. 模块边界

### Main App

候选职责：

- 任务创建与状态流转。
- 保存 Raw Docs、DocIR、SchemaIR、Validator 结果和 Import JSON Draft。
- SchemaIR Validator。
- Rule Engine。
- 对 UI、命令或测试客户端提供入口。

设计约束：

- Main App 是可信边界，最终进入下游的结构化产物必须由 Main App 校验或生成。
- 技术栈尚未最终确认；如果采用 Java，Java 更适合承担 Validator、Rule Engine 和系统集成边界。

### Agent Sidecar

候选职责：

- 文本 / Markdown 解析。
- Parsed Blocks 生成。
- LLM 调用。
- Prompt 编排。
- DocIR Draft 生成。
- SchemaIR Draft 生成。
- LLM 输出格式修复与重试。

设计约束：

- Agent Sidecar 不保存核心业务状态。
- Agent Sidecar 不决定最终配置可信性。
- 是否需要独立 Sidecar 仍应在 Phase0-PoC 中确认。

### Review Workbench

候选职责：

- Raw Docs 输入。
- DocIR Markdown 展示、编辑、保存、确认。
- SchemaIR 表格展示、编辑、校验、确认。
- Import JSON Draft 预览、复制、下载。

设计约束：

- Review Workbench 是人工确认入口，不是生产级配置平台。
- 未进入相应阶段前，不应加入权限、审批、多用户协同、复杂配置管理或 PDF 高亮。

## 4. 候选任务状态

以下状态用于表达链路中的关键产物边界，具体命名仍可在实现计划中调整：

```text
RAW_DOC_CREATED
DOCIR_DRAFT_GENERATED
DOCIR_CONFIRMED
SCHEMAIR_DRAFT_GENERATED
SCHEMAIR_VALIDATED
SCHEMAIR_CONFIRMED
IMPORT_JSON_GENERATED
```

待确认：

- 是否需要 `FAILED` 状态。
- 是否需要记录阶段错误码。
- `SCHEMAIR_VALIDATED` 是否区分 valid / invalid。
- 无 UI 阶段人工确认如何映射状态。

## 5. 候选 Workspace 结构

```text
workspace/{taskId}/
├── raw-doc.txt
├── parsed-blocks.json
├── docir-draft.md
├── docir-final.md
├── schemair-draft.json
├── schemair-final.json
├── schemair-validation-result.json
└── import-json.json
```

待确认：

- Golden sample 是否复用同一产物结构。
- LLM 原始响应是否保存。
- Review 修改前后是否保存 diff。
- 敏感内容如何脱敏与排除日志。
- Workspace 目录是否进入版本库。
