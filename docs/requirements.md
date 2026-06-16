# 银行接口文档解析与 Schema Workbook 需求文档

## Status

Draft.

## 1. 项目定位

本项目是面向银企直连实施场景的银行接口文档解析与配置辅助系统。

项目目标不是“全自动生成生产可信银行配置”，也不再追求直接或间接生成目标系统可导入 JSON。项目目标是把高经验依赖的银行接口配置整理过程产品化、可审计化、半自动化：系统应将真实脱敏银行接口文档转换为可人工 Review、可机器校验、可追溯、可回归的 `Final SchemaIR`，并确定性生成面向配置人员的强格式化 Schema Workbook。

`Final SchemaIR` 是系统内部事实源。Schema Workbook 是交付给配置人员用于人工配置目标系统的工作簿，不是事实源，也不承诺可直接导入目标系统。

项目分为四个阶段：

| 阶段 | 定位 | 需求文档 |
|---|---|---|
| Phase0-PoC | 确认样例、格式、链路和技术边界，证明方向可行。 | `docs/phases/phase0-poc.md` |
| Phase1-MVP | 交付可重复运行、可 Review、可回归的最小产品能力。 | `docs/phases/phase1-mvp.md` |
| Phase2-Pilot | 在受控真实场景中试点，验证实施提效、稳定性和运维边界。 | `docs/phases/phase2-pilot.md` |
| Phase3-Production | 暂不定义目标和需求。 | `docs/phases/phase3-production.md` |

具体阶段需求应记录在对应 phase 文档中。本文只记录项目级定位、通用原则、总体流程和跨阶段约束。

## 2. 交付形态

项目交付形态不是 Skill，也不是纯 Agent，而是一条逐步产品化的人机协同工具链。

阶段交付形态如下：

| 阶段 | 交付形态 |
|---|---|
| Phase0-PoC | 可重复运行的链路验证工具，例如 CLI、script 或 lightweight workflow runner，加文件 workspace、fixtures、Validator、Workbook Generator 和 golden sample regression。 |
| Phase1-MVP | 轻量 Review Tool，支持实施人员 Review、校验、确认、预览和下载 Schema Workbook。 |
| Phase2-Pilot | 受控内部试点工具或小型内部系统，用于真实或准真实项目验证提效和稳定性。 |
| Phase3-Production | 暂不定义。 |

Skill、Agent 或 Dify workflow 可以作为 Phase0/Phase1 中的 LLM 草稿生成组件或辅助开发工具，但不能作为完整交付物，也不能作为可信边界。

## 3. 背景与问题

银企直连系统通常需要根据银行接口文档配置报文标准、报文模板、页面字段、字段层级和转换规则。银行文档来源多样，字段表、XML/JSON 示例、必输规则、重复节点和条件说明经常分散在不同章节，实施人员需要人工阅读、整理和判断。

当前主要问题是：

- 银行接口文档格式不统一，人工解析成本高。
- 字段层级、必输、重复节点和条件说明依赖人工经验判断。
- 手工整理配置清单耗时长，质量不稳定。
- 缺少可追溯的中间产物，Review 与问题排查成本高。
- LLM 如果直接生成最终配置指导或目标系统导入文件，缺少可信边界、审计证据和可回归能力。

因此，本项目的核心价值在于让配置整理过程具备明确的中间表示、人工确认点、校验规则、确定性 workbook 生成规则和验收证据。

## 4. 核心设计原则

- Human-in-the-loop 是必需能力。Draft 未经人工确认，不能被当作最终可信产物。
- LLM 只生成可 Review 的草稿，不直接生成最终 Schema Workbook。
- `Final SchemaIR` 是系统内部事实源，必须支持来源追溯、不确定信息标记和人工修正。
- Schema Workbook 必须由确定性 Workbook Generator 基于通过校验的 `Final SchemaIR` 生成。
- Workbook Generator 只做确定性格式化和配置指导，不补业务字段、不对接目标系统、不承诺导入兼容性。
- XML 和 JSON 报文格式是一等模型能力，必须在 SchemaIR 中显式表达。
- 一个接口可以包含两个方向：`ASSEMBLY` 用于组装请求报文，`PARSE` 用于处理响应报文。
- 外部输入、LLM 输出和 third-party response 必须先校验，再进入后续业务流程。
- 真实银行文档内容属于敏感输入，日志中不得输出完整原文。
- 阶段边界必须清晰，后续阶段能力不能提前塞入当前阶段。
- 阶段需求必须在对应 phase 文档中维护，避免主文档和 phase 文档重复发散。

IR：Intermediate Representation。

## 5. 目标用户与场景

### 实施人员

上传或粘贴银行接口文档，检查系统生成的 DocIR 和 SchemaIR，修正明显错误，确认 `Final SchemaIR`，并下载 Schema Workbook 指导人工配置目标系统。

### 开发人员

维护文档解析、Prompt、LLM 调用、Validator、Workbook Generator、样例回归、运行命令和工程质量护栏。

### 审核人员

检查 `Final SchemaIR` 和 Schema Workbook 是否具备指导人工配置的基础质量。系统只支持检查、复制和下载，不直接导入生产配置库。

### 运维与平台负责人

关注部署、日志、审计、权限、数据保留、故障定位和生产变更治理。具体要求在相应阶段确认后进入 phase 文档。

## 6. 总体流程

```text
Raw Docs
→ DocIR Draft
→ Human Review DocIR
→ Final DocIR
→ SchemaIR Draft
→ Validator
→ Human Review SchemaIR
→ Final SchemaIR
→ Workbook Generator
→ Schema Workbook
→ Preview / Download
```

阶段可以根据成熟度采用不同交付形态。早期阶段可以通过命令、API 测试或本地脚本模拟 Human Review；产品化阶段应提供可用的 Review 入口。

## 7. 跨阶段非功能要求

- 关键中间产物必须可查看、可复制、可下载。
- `Final SchemaIR` 必须可版本化、可回归、可重新生成 Schema Workbook。
- 任务状态必须可追踪。
- LLM 调用失败时必须返回明确错误。
- LLM 输出进入后续流程前必须经过格式校验。
- 不允许在日志中输出完整银行文档敏感内容。
- 日志应包含任务标识、阶段和错误原因，便于定位。
- 文件编码使用 UTF-8 with NO BOM。
- 关键转换逻辑必须有基本单元测试。
- 对外接口和产物格式不能把早期草稿细节泄漏成长期兼容承诺。

## 8. 跨阶段失败标准

出现以下任一情况，应视为当前阶段失败或需要调整范围：

- DocIR 只能人工编写，系统没有自动生成能力。
- LLM 直接生成最终 Schema Workbook。
- Draft 未经人工确认就进入最终配置指导流程。
- SchemaIR 没有 Validator。
- SchemaIR 静默丢弃可识别字段。
- Schema Workbook 不能从 `Final SchemaIR` 稳定生成。
- 只能跑玩具样例，无法证明对真实脱敏文档有帮助。
- Schema Workbook 不足以指导配置人员人工配置目标系统。

## 9. 文档维护规则

- 本文只维护项目级需求，不记录历史归档内容。
- 各阶段的目标、范围、验收、阻塞项和待确认问题应记录在 `docs/phases/` 下的对应文档。
- 系统设计、模块边界、IR 结构、workbook 结构和验证规则应记录在 `docs/design/`。
- 已形成约束的关键技术决策应记录在 `docs/adr/`。
- 阶段需求发生变化时，优先更新对应 phase 文档；只有项目级定位、通用原则或总体流程变化时才更新本文。
- `docs/reference/` 中的材料是候选草案和参考输入，不是正式承诺。正式实现前必须从本文、phase 文档、design 文档、实施计划或 ADR 中确认。
