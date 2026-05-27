# MVP 讨论记录

## Date

2026-05-27

## Status

Active discussion record.

## Context

在完成项目价值评估、MVP 需求草案和技术可行性分析后，本记录用于沉淀进一步讨论中已经明确的边界、仍需分析的问题，以及进入实现规划前的前置条件。

本文件记录讨论结论，不替代 `docs/mvp-requirements.md`。当讨论结论影响需求或可行性判断时，应同步更新对应正式文档。

## 已明确事项

### 输入样例

MVP 应使用真实脱敏银行接口文档作为验证样例。

样例字段规模应接近真实业务，初步目标为 20 个以上字段。样例不应只是玩具片段，否则无法证明项目对真实实施工作的价值。

### Import JSON 边界

Import JSON 应贴近真实银企直连导入格式。

后续将由用户提供真实或接近真实的 Import JSON 样例。实现 Rule Engine 前，需要基于该样例确认目标字段模型、字段命名、层级关系和兼容性边界。

### DocIR / SchemaIR 最小格式

DocIR 和 SchemaIR 的最小格式仍属于需求分析对象，需要继续讨论后给出。

当前只确认方向：

- DocIR 用于承接原始文档信息、辅助人工 Review 和后续 LLM 抽取。
- SchemaIR 用于机器校验、人工修正和 Rule Engine 输入。
- 两者都必须支持来源追溯与不确定信息标记。

具体字段、结构约束、推导规则和验收标准尚未最终确认。

### UI 分期

MVP 最终需要包含 UI。

但第一阶段不需要 UI，应先完成无 UI 的端到端验证。第一阶段重点是证明：

```text
Raw Docs
→ DocIR
→ SchemaIR
→ Validator
→ Import JSON
```

该链路可以在命令、API 或测试驱动方式下稳定跑通。

### 技术栈

技术栈仍需讨论，不应在当前阶段锁死。

已有草案中提到的 Java Spring Boot、Python FastAPI、React/Vue + Vite 可以作为候选方向，但正式规划前需要重新评估：

- 是否确实需要 Java/Python 双服务。
- 是否先以更轻量的无 UI 验证方式启动。
- 前端框架选型是否受团队熟悉度和集成方式影响。

### Golden Sample

MVP 必须包含 golden sample。

Golden sample 至少应覆盖：

- 真实脱敏 Raw Docs。
- 期望或确认后的 DocIR。
- 期望或确认后的 SchemaIR。
- Validator 结果。
- 期望或确认后的 Import JSON。

Golden sample 是后续回归、Prompt 调整、Rule Engine 修改和验收判断的核心证据。

## 待讨论项 Backlog

优先级定义：

- P0：进入实现规划前必须讨论，否则容易导致方向性返工。
- P1：影响交付质量和工程效率，建议在详细实施计划前讨论。
- P2：可以在后续阶段细化，不应阻塞第一阶段推进。

### P0：需求与产物边界

1. DocIR 的最小格式和质量标准。
   - 需要讨论：DocIR 是规范化原文，还是允许包含推导信息。
   - 需要讨论：DocIR 必须保留哪些章节、字段表、条件说明和示例。
   - 需要讨论：DocIR 中 `REVIEW` 或不确定标记的触发规则。

2. SchemaIR 的最小字段集合、字段类型枚举和校验规则。
   - 需要讨论：字段级 SchemaIR 至少包含哪些字段。
   - 需要讨论：`dataType`、`required`、`multiple`、`hasChildren` 的判断规则。
   - 需要讨论：SchemaIR 字段覆盖率如何验收。

3. 来源追溯与推导规则。
   - 需要讨论：`sourceText` 粒度是整行、单元格，还是章节片段。
   - 需要讨论：XML/JSON Path 是否允许根据示例推导。
   - 需要讨论：推导出的 path、dataType、multiple 是否必须标记来源。
   - 需要讨论：`uncertain=true` 的强制触发条件。

4. Import JSON 真实格式边界。
   - 需要讨论：用户提供样例后，MVP 输出是完整真实格式还是真实格式子集。
   - 需要讨论：哪些字段必须生成，哪些字段允许留空、默认或暂不支持。
   - 需要讨论：无法从文档推导的信息如何表达。
   - 需要讨论：Import JSON 是否需要版本号、schema 标识或兼容性说明。

5. 第一阶段无 UI 端到端验证形态。
   - 需要讨论：第一阶段用命令行、API 测试，还是二者同时提供。
   - 需要讨论：人工确认 DocIR / SchemaIR 在无 UI 阶段如何表达。
   - 需要讨论：每次运行产物保存到哪里，如何对比。

6. Golden sample 体系。
   - 需要讨论：目录结构、文件命名和版本管理。
   - 需要讨论：Raw Docs、DocIR、SchemaIR、Validator 结果、Import JSON 是否都保存 expected 文件。
   - 需要讨论：回归时严格全文比对，还是结构化字段比对。
   - 需要讨论：LLM 输出变化时如何判断是可接受变化还是退化。

7. 技术栈选择原则。
   - 需要讨论：第一阶段是否需要 Java/Python 双服务。
   - 需要讨论：Rule Engine 是否必须从第一天就在 Java 中实现。
   - 需要讨论：LLM 调用是否必须独立 Python Sidecar。
   - 需要讨论：单仓库多模块还是其他组织方式。

### P1：工程质量与协作机制

1. 项目分期策略。
   - 需要讨论：Phase 0 是否只做样例、格式和验证命令。
   - 需要讨论：Phase 1 是否只交付无 UI 闭环。
   - 需要讨论：UI 是 Phase 2 补上，还是与后端并行。
   - 需要讨论：每个阶段的停止点、验收方式和下一阶段开始条件。

2. 验收与测试策略。
   - 需要讨论：每个阶段的验收命令是什么。
   - 需要讨论：Parser、Validator、Rule Engine 哪些必须单测。
   - 需要讨论：LLM 相关测试如何稳定化。
   - 需要讨论：是否需要单独的 golden sample regression 命令。
   - 需要讨论：CI 中跑哪些检查，哪些只本地跑。

3. 错误处理与可观测性。
   - 需要讨论：是否使用统一 `taskId` 贯穿日志和产物。
   - 需要讨论：每个阶段失败时保存哪些错误信息。
   - 需要讨论：LLM 原始响应是否保存，以及如何脱敏。
   - 需要讨论：日志中哪些银行文档内容禁止输出。
   - 需要讨论：Validator 错误格式。

4. Human Review 职责边界。
   - 需要讨论：DocIR Review 主要检查哪些内容。
   - 需要讨论：SchemaIR Review 主要检查哪些内容。
   - 需要讨论：哪些字段允许人工修改，哪些字段不建议直接改。
   - 需要讨论：确认动作是否记录 reviewer、时间和备注。
   - 需要讨论：MVP 是否需要显式审核结论。

5. Import JSON Rule Engine 规则治理。
   - 需要讨论：字段编码规则由哪里定义。
   - 需要讨论：parent-child、list、node、controlType 的真实规则。
   - 需要讨论：规则变化如何回归验证。
   - 需要讨论：MVP 规则是否允许硬编码，还是需要显式规则表。

6. 本地开发和运行体验。
   - 需要讨论：第一阶段是否要求一个命令跑通。
   - 需要讨论：依赖安装、模型配置和样例运行如何说明。
   - 需要讨论：本地 workspace 目录和临时产物如何清理。

### P2：长期维护与后续扩展

1. 文档与 ADR 策略。
   - 需要讨论：技术栈最终确定后是否写 ADR。
   - 需要讨论：Java/Python 边界是否写 ADR。
   - 需要讨论：DocIR Markdown vs JSON 是否写 ADR。
   - 需要讨论：LLM 不直接生成 Import JSON 是否写 ADR。
   - 需要讨论：`tmp/` 草案后续保留、归档还是迁移。

2. 交付协作规则。
   - 需要讨论：每个阶段是否单独 commit。
   - 需要讨论：文档、代码、测试是否分 commit。
   - 需要讨论：超过多少文件或行数必须拆分提交。
   - 需要讨论：每个阶段完成后是否强制 docs-sync。
   - 需要讨论：什么情况下停止实现并回到需求讨论。

3. UI 体验范围。
   - 需要讨论：Review Workbench 的最小页面结构。
   - 需要讨论：DocIR 编辑器使用 textarea 还是专业编辑器。
   - 需要讨论：SchemaIR 表格编辑能力到什么程度。
   - 需要讨论：Import JSON 只读预览是否足够。

4. 后续格式扩展。
   - 需要讨论：`.docx` 何时进入范围。
   - 需要讨论：PDF/OCR/bbox 的触发条件。
   - 需要讨论：多银行、多报文标准泛化的前置条件。

## 当前进入实现规划前的阻塞项

- 尚未确认 DocIR 最小格式。
- 尚未确认 SchemaIR 最小格式。
- 尚未提供真实或接近真实的 Import JSON 样例。
- 尚未确认第一阶段技术栈和无 UI 验证形态。
