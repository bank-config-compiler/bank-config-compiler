# 技术可行性分析

## Status

Proposed.

## Date

2026-05-27

## 1. 分析结论

银行接口文档解析 Agent MVP 在技术上可行，但必须收紧第一版范围。

高可行范围是：

```text
.md / .txt / 粘贴文本
→ DocIR Draft
→ Human Review
→ SchemaIR Draft
→ Validator
→ Human Review
→ Rule Engine
→ Import JSON Draft
```

低可行或不适合第一版的范围是：

- PDF/OCR/bbox 高亮。
- 复杂 Word 表格解析。
- 真实生产配置库导入。
- 多银行、多格式泛化。
- 自动规则学习。
- 无人工确认的全自动配置生成。

因此，该 MVP 的技术可行性成立，但其证明力依赖两个前提：

- 输入样例必须是真实脱敏银行接口文档，字段规模初步目标为 20 个以上字段。
- Import JSON 草稿必须贴近真实银企直连配置模型，并基于用户后续提供的样例确认字段模型。

## 2. 可行性分层

### 2.1 高可行

以下能力工程风险较低，适合作为 MVP 第一版：

- 文本和 Markdown 输入。
- 文件目录保存任务与中间产物。
- DocIR Draft 生成。
- DocIR Markdown 编辑与确认。
- SchemaIR JSON 生成。
- Java Validator 校验 SchemaIR。
- SchemaIR 表格展示与关键字段编辑。
- 基于规则的 Import JSON 草稿生成。
- Import JSON 预览、复制、下载。
- 样例闭环回归测试。
- 无 UI 端到端验证。

这些能力主要是工程集成、结构化数据处理和简单 UI，不依赖复杂文档解析。

### 2.2 中等可行

以下能力可做，但需要控制实现深度：

- LLM 输出 JSON 修复与重试。
- DocIR 质量提示和 `REVIEW` 标记。
- SchemaIR 的字段覆盖检查。
- 父子路径关系校验。
- condition 原文保留。
- Prompt 版本管理。
- 黄金样本回归。

这些能力有明确工程路径，但容易扩展过度。MVP 中应实现最小可验证版本。

### 2.3 第一版不建议做

以下能力会显著增加复杂度，不适合作为第一版成功条件：

- `.docx` 表格解析。
- PDF 文档解析。
- OCR。
- bbox、pageNo、原文区域高亮。
- 复杂 condition DSL。
- 真实生产库导入。
- 多用户协作和审批流。
- RAG 和多 Agent 编排。
- 自动学习银行规则。

这些能力不是没有价值，而是会分散 MVP 对核心链路的验证。

## 3. 建议技术边界

### 3.1 LLM 边界

LLM 只负责：

- 从 Raw Docs 生成 DocIR Draft。
- 从 Final DocIR 生成 SchemaIR Draft。
- 标记不确定信息。

LLM 不负责：

- 生成最终可信配置。
- 直接生成 Import JSON。
- 决定字段是否可进入生产配置。
- 绕过 Validator 或 Human Review。

### 3.2 Java 边界

Java 主应用适合承担：

- 任务状态管理。
- 中间产物保存。
- Review 状态保存。
- SchemaIR Validator。
- Rule Engine。
- Import JSON 生成。
- UI API。

Java 是系统可信边界，所有最终进入下游的结构化产物都应由 Java 校验或生成。

### 3.3 Python Sidecar 边界

Python Sidecar 适合承担：

- 文本/Markdown 解析。
- Prompt 编排。
- LLM 调用。
- DocIR Draft 生成。
- SchemaIR Draft 生成。
- LLM 输出格式修复和重试。

Python 不应保存核心业务状态，也不应决定最终配置可信性。

### 3.4 UI 边界

UI 应定位为 Review Workbench，而不是生产级配置平台。

第一版 UI 只需要支持：

- 创建任务。
- 查看 Raw Docs。
- 编辑和确认 DocIR。
- 查看和编辑 SchemaIR。
- 查看 Validator 错误。
- 预览、复制和下载 Import JSON。

不应加入权限、审批、多用户协同、复杂配置管理或 PDF 高亮。

## 4. 主要技术风险

### 4.1 DocIR 质量不足

风险表现：

- 字段表错列。
- 字段遗漏。
- Section 拆分错误。
- XML/JSON 示例与字段表关联错误。
- XML Path 推导错误。

缓解方式：

- 第一版只支持文本和 Markdown。
- DocIR 保留原始 sourceText 或足够来源信息。
- 对不确定内容加 `REVIEW` 标记。
- DocIR 必须经过人工确认。
- 用接近真实的样例做回归。

### 4.2 SchemaIR 静默丢字段

风险表现：

- LLM 只抽取容易识别的字段。
- 嵌套节点或重复节点遗漏。
- 条件字段被错误标记为普通可选字段。

缓解方式：

- SchemaIR 字段必须包含 `sourceText`。
- 缺少证据时设置 `uncertain=true`。
- Validator 检查路径重复、空字段和明显冲突。
- 样例回归中检查字段覆盖数量。
- UI 明确展示不确定字段。

### 4.3 Import JSON 证明力不足

风险表现：

- Import JSON 只是演示格式，不能说明真实配置提效。
- 字段模型与现有系统偏差过大。
- 后续接入真实系统时需要重做 Rule Engine。

缓解方式：

- 尽早确认真实导入格式或真实格式子集。
- 如果真实格式暂不可得，明确标记为 MVP Draft Format。
- Rule Engine 保持简单、确定、可测试。
- 避免把 MVP 草稿格式承诺为长期外部接口。

### 4.4 Java/Python 双服务复杂度

风险表现：

- 启动和联调成本增加。
- 错误定位跨服务。
- 本地开发环境复杂。

缓解方式：

- Python Sidecar 只暴露少量接口。
- Java 保存任务状态和最终产物。
- 明确任务 ID 贯穿日志。
- 提供最小健康检查。
- 第一版避免异步队列和复杂部署。

### 4.5 LLM 输出不稳定

风险表现：

- 输出格式不合法。
- 抽取结果随模型或 Prompt 变化。
- 长文档截断。

缓解方式：

- Prompt 版本化。
- 输出进入后续流程前先做格式校验。
- JSON 输出失败时修复或重试。
- 保存 Draft 和错误信息。
- 建立黄金样本回归。

## 5. 推荐验证路径

### Phase 0：样例和格式确认

目标：

- 确认一份真实脱敏银行接口样例，字段规模初步目标为 20 个以上字段。
- 基于用户提供的样例确认 Import JSON 真实格式子集。
- 确认第一版只支持 `.md`、`.txt` 和粘贴文本。
- 确认 DocIR 和 SchemaIR 的最小格式。
- 确认第一阶段无 UI 端到端验证的交付形态。

通过条件：

- 样例文档进入仓库或测试资源。
- 样例字段数量、层级和条件说明足以证明链路价值。
- Import JSON 边界已写入文档。
- Golden sample 目录结构和回归命令已定义。

### Phase 1：无 UI 最小链路闭环

目标：

- 跑通 Raw Docs 到 Import JSON Draft。
- 所有中间产物可查看。
- Draft 必须经过人工确认才能进入下一阶段。
- 暂不要求 UI，优先用命令、API 或测试方式证明端到端链路。

通过条件：

- 中间产物写入 workspace。
- 样例可重复运行。
- Golden sample 输出可对比。

### Phase 2：Review Workbench UI

目标：

- 增加最小 UI。
- 支持 DocIR Review、SchemaIR Review 和 Import JSON 预览下载。

通过条件：

- UI 能串起完整流程。
- UI 不改变无 UI 链路的核心产物格式。

### Phase 3：质量护栏

目标：

- 增加 Validator 和关键转换单元测试。
- 增加 LLM 输出格式校验。
- 增加字段覆盖回归检查。

通过条件：

- Validator 能拦截明显错误。
- 关键规则转换测试通过。
- SchemaIR 不静默丢弃样例中的可识别字段。

### Phase 4：证明 MVP 价值

目标：

- 使用真实脱敏样例验证实施提效。
- 记录人工修改点和不确定字段。
- 判断是否值得进入下一阶段。

通过条件：

- 人工从 DocIR 和 SchemaIR 草稿开始修改，而不是从零整理。
- 最终 Import JSON Draft 与预期结构可比对。
- 风险和缺口可以明确归类，而不是停留在“LLM 不稳定”。

## 6. 建议验收证据

MVP 验收不应只看页面能否点击，而应保留以下证据：

- 原始样例文档。
- DocIR Draft。
- Final DocIR。
- SchemaIR Draft。
- Validator 结果。
- Final SchemaIR。
- Import JSON Draft。
- 关键转换测试输出。
- 一次完整流程的运行说明。
- 已知缺陷与不确定字段列表。

## 7. Go / No-Go 判断

### Go

满足以下条件时，可以进入实现规划：

- 第一版输入范围确认只包含 `.md`、`.txt` 和粘贴文本。
- 有真实脱敏样例，字段规模初步目标为 20 个以上字段。
- Import JSON 样例已提供，或至少明确样例提供时间点和实现阻塞边界。
- DocIR 和 SchemaIR 最小格式已确认。
- 第一阶段无 UI 端到端验证形态已确认。
- 技术栈已确认。
- Golden sample 结构已确认。
- 用户认可 Human-in-the-loop 是 MVP 必需能力。
- 用户认可 LLM 不直接生成 Import JSON。

### No-Go

出现以下情况时，不建议进入实现：

- 期望第一版直接支持 PDF/OCR 或复杂 Word。
- 期望无人工 Review 自动生成生产配置。
- 无法提供任何真实脱敏样例。
- Import JSON 既要求接近真实系统，又无法提供目标字段模型。
- MVP 成功标准只剩“页面能演示”，无法证明实施提效。

## 8. 结论

该 MVP 具备可行性，建议推进，但必须以最小闭环为第一目标。

第一版不应验证“系统能处理所有银行文档”，而应验证：

```text
在受控输入范围内，
AI 可以生成有用草稿，
人工可以高效修正，
机器可以校验结构，
规则可以确定性生成配置草稿，
全过程可以追溯。
```

如果这一点成立，再讨论 `.docx`、PDF、真实生产导入、多银行泛化和更复杂的配置能力。
