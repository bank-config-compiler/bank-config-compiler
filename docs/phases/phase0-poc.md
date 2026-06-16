# Phase0-PoC 需求

## Status

Draft.

## 1. 阶段目标

Phase0-PoC 目标是确认样例、格式、链路和技术边界，证明项目方向可行。

本阶段不追求产品化 UI，不验证生产集成。成功标准是核心链路能够基于真实脱敏样例稳定产出可检查、可追溯、可回归的中间产物和 Schema Workbook。

交付形态应是可重复运行的链路验证工具，例如 CLI、script 或 lightweight workflow runner，加文件 workspace、golden sample fixtures、Validator 和 Workbook Generator。

Skill、Agent 或 Dify workflow 可以作为 LLM 草稿生成组件，但不能作为 Phase0 的完整交付物，因为它们不能单独证明控制、校验、人工确认和回归边界。

## 2. In Scope

- 使用一份真实脱敏银行接口文档作为验证样例。
- 样例字段规模应接近真实业务，初步目标为 20 个以上字段。
- 确认 `.md`、`.txt` 和粘贴文本作为第一阶段输入范围。
- Raw Docs 到 DocIR Draft。
- 人工确认 Final DocIR fixture。
- Final DocIR 到 SchemaIR Draft。
- SchemaIR Validator 最小规则。
- 人工确认 Final SchemaIR fixture。
- Workbook Generator 基于 Final SchemaIR 生成 Schema Workbook。
- 保存 Raw Docs、DocIR、SchemaIR、Validator 结果和 Schema Workbook。
- 确认 DocIR、SchemaIR 和 Schema Workbook 的最小格式。
- 确认无 UI 端到端验证形态和 golden sample 结构。
- 提供 golden sample 回归命令或等价验证路径。

## 3. Out of Scope

- UI。
- Skill、纯 Agent 或单纯 Prompt workflow 作为完整交付物。
- 真实生产库导入。
- 目标系统 Import JSON 生成或兼容性验证。
- `.docx`、PDF、OCR、bbox 和原文区域高亮。
- 多用户协作、权限、审批流。
- RAG、多 Agent、自动微调、自动规则学习。
- 复杂 condition DSL。
- 多银行、多报文标准泛化。

## 4. 功能需求

### 4.1 文档输入

系统应支持读取或接收原始银行接口文档文本。输入范围限定为：

- `.md`
- `.txt`
- 粘贴文本

系统应保存原始输入，便于后续查看和追溯。

### 4.2 DocIR 生成与确认

系统应基于原始文档生成 DocIR Draft。

DocIR 必须是强结构化 Markdown，至少保留：

- 接口编码、接口名称、报文格式和版本等基础信息，若原文缺失则留空或标记不确定。
- 请求组装与响应处理方向，分别对应 `ASSEMBLY` 和 `PARSE`。
- 原始字段表中的字段名、路径、类型、长度、出现次数、必输标记和说明。
- 章节结构。
- 条件说明。
- XML/JSON 示例。
- 无法确认的信息和需要人工检查的位置。

Phase0 可以通过人工维护 fixture 的方式表达 Final DocIR。

### 4.3 SchemaIR 生成与确认

系统应基于 Final DocIR 生成 SchemaIR Draft JSON。

SchemaIR 顶层至少包含：

- `interfaceCode`
- `interfaceName`
- `messageFormat`
- `version`
- `messages`

每个 message 至少包含：

- `functionType`
- `messageName`
- `rootPath`
- `fields`

每个字段至少包含：

- `path`
- `fieldName`
- `nodeKind`
- `dataType`
- `required`
- `multiple`
- `hasChildren`
- `sourceText`
- `confidence`
- `uncertain`
- `uncertainReason`

SchemaIR 字段应覆盖样例 DocIR 中可识别的字段。若字段缺少充分证据，系统应保留字段并设置 `uncertain=true`，而不是静默丢弃。

Phase0 可以通过人工维护 fixture 的方式表达 Final SchemaIR。

### 4.4 SchemaIR Validator

Validator 至少应校验：

- `interfaceCode` 非空。
- `messageFormat` 属于允许枚举。
- `functionType` 属于允许枚举。
- `path` 非空。
- `fieldName` 非空。
- `nodeKind` 属于允许枚举。
- `dataType` 属于允许枚举。
- `required` 是 boolean。
- `multiple` 是 boolean。
- `hasChildren` 是 boolean。
- `confidence` 在 0 到 1 之间。
- `sourceText` 非空。
- 同一 message 内 `path` 不重复。
- 父子路径关系可解释。
- `hasChildren`、`multiple`、`dataType` 和 `nodeKind` 不存在明显冲突。

Validator 失败时，应返回可展示的字段级错误列表，不能只返回通用失败信息。

### 4.5 Schema Workbook 生成

系统应由 Workbook Generator 基于通过校验的 Final SchemaIR 生成 Schema Workbook。

Schema Workbook 不直接落库、不直接导入目标系统。它应是配置人员可阅读、可筛选、可核对的强格式化 Excel 工作簿，用于指导人工配置。

## 5. 通过条件

- 样例文档进入仓库或受控测试资源。
- 样例字段数量、层级和条件说明足以证明链路价值。
- DocIR / SchemaIR 最小格式已确认。
- Schema Workbook 最小结构和字段列已确认。
- Golden sample 目录结构和回归命令已定义。
- 无 UI 链路可重复运行，并产出可比较结果。

## 6. 待确认问题

- DocIR 最小格式和质量标准。
- SchemaIR 最小字段集合、字段类型枚举和校验规则。
- `sourceText` 粒度、推导规则和 `uncertain` 标记规则。
- Schema Workbook 样式、sheet 和列的最小验收标准。
- 无 UI 端到端验证形态。
- Golden sample 目录结构、文件命名和回归方式。
- 技术栈选择原则。
