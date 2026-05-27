# 团队讨论导读

## Status

Meeting guide.

## Date

2026-05-27

## 1. 会议目标

本次讨论目标不是直接敲定完整实现方案，而是让团队对以下问题形成共同理解：

- 这个项目要解决什么问题。
- MVP 做什么，不做什么。
- 第一阶段预期交付什么结果。
- 当前方案是否具备业务价值和技术可行性。
- 哪些事项必须在进入实现规划前确认。

## 2. 项目一句话定义

本项目是一个面向银企直连实施场景的银行接口文档解析 Agent MVP，用于把真实脱敏银行接口文档转换为可人工 Review、可校验、可追溯的配置草稿。

它不是全自动生产配置生成器，也不是通用文档理解平台。

## 3. 为什么值得做

银行接口文档格式不统一，字段层级、必输规则、重复节点、条件说明和报文示例需要实施人员反复阅读和判断。当前工作强依赖经验，交付周期长，质量也不稳定。

该 MVP 的价值是验证：

```text
AI 能否生成有用草稿，
人工能否高效修正，
机器能否校验结构，
规则能否确定性生成配置草稿，
全过程能否追溯。
```

项目价值不在于替代人工，而在于把高经验依赖的配置整理过程产品化、可审计化、半自动化。

## 4. MVP 做什么

MVP 目标链路：

```text
Raw Docs
→ DocIR Draft
→ Human Review DocIR
→ Final DocIR
→ SchemaIR Draft
→ Validator
→ Human Review SchemaIR
→ Final SchemaIR
→ Rule Engine
→ Import JSON Draft
→ Preview / Download
```

当前已确认方向：

- 使用真实脱敏银行接口文档作为验证样例，字段规模初步目标为 20 个以上字段。
- Import JSON 应贴近真实银企直连导入格式，后续由用户提供样例。
- LLM 只生成 DocIR Draft 和 SchemaIR Draft。
- Import JSON 只能由确定性 Rule Engine 生成。
- MVP 最终包含 Review Workbench UI。
- 第一阶段先做无 UI 端到端验证。
- 必须建立 golden sample。

## 5. MVP 不做什么

MVP 第一版不做：

- 真实导入生产配置库。
- 无人工 Review 的全自动配置生成。
- `.docx` 解析。
- PDF、OCR、bbox 和原文区域高亮。
- 生产权限体系、审批流、多用户协作。
- 复杂 RAG、多 Agent、自动微调、自动规则学习。
- 复杂 condition DSL。
- 通用多银行、多报文标准、全格式解析平台。

## 6. 简单用户旅程

### 阶段 1：无 UI 端到端验证

1. 开发人员准备一份真实脱敏银行接口文档作为 Raw Docs。
2. 系统基于 Raw Docs 生成 DocIR Draft。
3. 实施人员或产品负责人检查 DocIR Draft，并形成 Final DocIR fixture。
4. 系统基于 Final DocIR 生成 SchemaIR Draft。
5. Validator 检查 SchemaIR Draft，输出错误和不确定项。
6. 实施人员修正 SchemaIR，并形成 Final SchemaIR fixture。
7. Rule Engine 基于 Final SchemaIR 生成 Import JSON Draft。
8. 团队将 Raw Docs、Final DocIR、Final SchemaIR、Validator 结果和 Import JSON Draft 固化为 golden sample。

这个阶段的目标是证明核心链路成立，不验证 UI 体验。

### 阶段 2：Review Workbench MVP

1. 实施人员在 UI 中创建任务，上传或粘贴银行接口文档。
2. 系统生成 DocIR Draft，实施人员在 UI 中查看、编辑并确认 Final DocIR。
3. 系统生成 SchemaIR Draft，Validator 返回错误和不确定项。
4. 实施人员在表格中修正 SchemaIR 关键字段，并重新校验。
5. 实施人员确认 Final SchemaIR。
6. 系统生成 Import JSON Draft。
7. 审核人员预览、复制或下载 Import JSON Draft，判断是否具备进入真实导入流程的基础质量。

这个阶段的目标是验证人机协同 Review 流程是否可用。

## 7. 预期结果

一次 MVP 验收应至少留下这些证据：

- 真实脱敏 Raw Docs。
- DocIR Draft 和 Final DocIR。
- SchemaIR Draft 和 Final SchemaIR。
- Validator 结果。
- Import JSON Draft。
- Golden sample regression 结果。
- 已知缺陷和不确定字段列表。

团队需要能回答：

- 这条链路是否比从零人工整理更有效。
- 哪些错误必须由人工 Review 发现。
- 哪些错误可以由 Validator 或 Rule Engine 拦截。
- Import JSON 是否足够贴近真实导入格式。
- 是否值得进入下一阶段建设。

## 8. 建议实施阶段

### Phase 0：样例和格式确认

确认真实脱敏样例、Import JSON 样例、DocIR / SchemaIR 最小格式、golden sample 结构和第一阶段验证方式。

### Phase 1：无 UI 端到端闭环

用命令、API 测试或本地脚本跑通 Raw Docs 到 Import JSON Draft，并固化 golden sample。

### Phase 2：Review Workbench UI

补上最小 UI，支持 DocIR Review、SchemaIR Review 和 Import JSON 预览下载。

### Phase 3：质量护栏

强化 Validator、Rule Engine 测试、LLM 输出校验、字段覆盖检查和错误可观测性。

## 9. 明天优先讨论的 P0 问题

1. DocIR 最小格式和质量标准。
2. SchemaIR 最小字段集合、字段类型枚举和校验规则。
3. `sourceText`、推导规则和 `uncertain` 标记规则。
4. Import JSON 真实格式边界和样例提供方式。
5. 第一阶段无 UI 端到端验证形态。
6. Golden sample 目录结构、文件命名和回归方式。
7. 技术栈选择原则。

## 10. 会议结束时建议形成的结论

- 是否认可当前 MVP 目标和边界。
- 是否确认第一阶段先做无 UI 端到端验证。
- 是否确认真实脱敏样例和 Import JSON 样例的提供方式。
- 是否确认 DocIR / SchemaIR 最小格式的下一步负责人和时间点。
- 是否确认 golden sample 结构和验收方式。
- 是否可以进入正式实施规划。

## 11. 阅读顺序

建议团队按以下顺序阅读：

1. `docs/team-discussion-guide.md`
2. `docs/project-value-assessment.md`
3. `docs/mvp-requirements.md`
4. `docs/technical-feasibility-analysis.md`
5. `docs/mvp-discussion-record.md`
6. `docs/reference/README.md`

