# Phase1-MVP 需求

## Status

Draft.

## 1. 阶段目标

Phase1-MVP 将 Phase0-PoC 链路产品化为最小可用的轻量 Review Tool。

本阶段支持 DocIR、SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR 的人工 Review、重新校验与确认，以及按方向模板生成的 Configuration Workbook 预览和下载。它不是完整生产系统，也不直接写入目标系统。

## 2. In Scope

- 创建解析任务并保存接口编码、XML 格式和原始输入。
- Review、编辑并确认 Final DocIR。
- 生成、校验、Review 并确认 Final SchemaIR。
- 生成、校验、Review 并确认 ASSEMBLY/PARSE 的 Final Interface Standard。
- 基于已有 Final Standard 创建和 Review 多份同方向 Interface Template。
- 精确展示模板绑定的 Standard ID/version/content hash。
- 展示并校验 Template 对 Standard required/length/dataType 的显式镜像。
- 展示 `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM`，并分别呈现 PARSE Standard source 与 Parse target 的 name/path/datatype。
- 编辑标量字段值和 XML Key 的六种 Value Expression，并明确展示 Node/Object 无字段值表达式。
- Review ASSEMBLY 模板未覆盖标量 Standard Field 的 omissions；Node/Object 不参加 coverage，PARSE 只 Review 实际配置的 Parse Field targets。
- 基于三份 Final 模型和匹配校验结果生成 Configuration Workbook。
- 预览和下载工作簿。
- 保存任务状态、规则版本、审计结论和关键中间产物。
- Validator、Generator 和 golden regression 的基本测试与日志。

## 3. Out of Scope

- 真实导入银企直连生产配置库。
- Import JSON、目标系统 API 写入、自动导入和 Excel 反向导入。
- JSON 银行报文；Parse Field Catalog 中固定输出对象的 List 不扩大银行报文范围。
- Skill、纯 Agent 或单纯 Prompt workflow 作为完整交付物。
- 生产权限体系、审批流和多用户协同。
- `.docx`、PDF、OCR、bbox 和原文区域定位。
- 复杂 RAG、多 Agent 编排、自动微调和自动规则学习。
- 目的系统业务 Condition 和同目标字段多行配置；银行文档明确条件属于 Standard Review。
- 通用多银行、多报文标准、全格式自动解析平台。

## 4. 功能需求

### 4.1 任务创建与文档输入

任务至少包含名称、interfaceCode、固定 `XML` 报文格式和 `.md`/`.txt` 或粘贴原文。系统保存原始输入以便追溯。

### 4.2 DocIR Review

用户可以查看 Raw Docs 和 DocIR Draft、编辑并保存草稿、确认 Final DocIR。Final DocIR 保留字段表、章节、条件说明、XML 示例和 ASSEMBLY/PARSE 方向。

### 4.3 SchemaIR Review

用户可以：

- 以表格查看 SchemaIR 和字段级 Validator issue；
- 修改 path、fieldName、nodeKind、dataType、required、multiple、description、condition、uncertain 和 review note；
- Review 每个方向的 XML encoding 证据、冲突与 Final 值；
- 修改后重新校验；
- 确认 Final SchemaIR。

### 4.4 Interface Standard Review

用户可以按 interfaceCode 和 direction：

- 查看 Standard Draft 与 SchemaIR 来源；
- 编辑 field name/description、parentPath/fullPath、sequence；
- 编辑 required、length、illegal characters、regex、XML Keys 和 data type；
- Review 基础 required 与银行文档条件 required；
- 区分 VALUE、NO_CONSTRAINT 与 UNKNOWN；
- Review SchemaIR/Standard 差异、Rule ID 和不确定项；
- 修改后重新运行 Standard Validator；
- 确认不可变版本的 Final Standard。

标准发布新版本时，UI 必须展示受影响模板，不得静默迁移。

### 4.5 Interface Template Review

用户可以基于选定的 Final Standard：

- 创建和识别多份同方向模板；
- 查看 Standard ID/version/content hash 绑定；
- 对照 Standard 快照查看 `standardProjection.required/length/dataType`，不允许 Template 覆盖；
- 查看和编辑 `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM`；PARSE 的 Standard source 与 Parse target 分列展示；
- 查看和编辑标量字段值 Value Expression；
- 对 Node/Object 展示无字段值表达式，不提供 Value Mode 编辑；无结构需求时不生成 omission，有 XML Key/结构需求时使用适用结构绑定；
- 为每个 XML Key 编辑独立 Value Expression；
- 编辑 Empty/Overlength Handling、Row Limit、Chinese Character Length 和单一 Replacement Rule Name；
- 查看 Rule ID、catalog 引用、confidence 和不确定原因；
- ASSEMBLY 查看未覆盖标量 Standard Field 及 `MISSING_TEMPLATE_FIELD` Warnings；
- PARSE 查看 Standard source 到 Parse Field target，未配置 Parse Field 不自动产生 omission；
- `b2e0061-rs(Node) -> paymentLineList(List)` 以 COLLECTION_ITEM 展示并写入当前列表元素；
- FIXED_VALUE 选择 LITERAL 或 SECURE_INPUT_REF，后者只展示安全引用标识；
- 为每个 omission 填写原因并接受或拒绝；
- 修改后重新运行 Template Validator；
- 确认 Final Template。

UI 必须明确区分 omission、EMPTY 和 Empty Handling，并按方向展示 source/target。目的系统业务 Condition 和同目标字段多行不属于本阶段；银行文档条件在 Standard Review/Workbook 中只展示和确认，不执行。

### 4.6 Configuration Workbook

用户选择一个 Final Template 和 Standard Action 后，系统基于 Final SchemaIR、绑定的 Final Standard、Final Template 和三份匹配校验结果生成工作簿。

用户可以预览并下载：

- Overview；
- Interface Standard；
- Interface Template；
- Value Expressions；
- Warnings；
- Rule References；
- Legend。

Overview 必须展示方向级 XML encoding。Interface Template 必须将 Standard 快照、Template 镜像和 Parse target 分列。Value Expressions 必须能展开标量字段值和 XML Key 的递归表达式，且不为 Node/Object 生成 FIELD_VALUE 节点。已确认标量 omissions 继续显示在 Warnings，不在 Template Sheet 生成空行；Node/Object 不制造 omission。

工作簿不直接落库、不直接导入目标系统，也不反向更新任何 IR。

## 5. 通过条件

- 能输入一份真实脱敏 XML 银行接口样例。
- 四类 Draft 均可读、可 Review 且不能绕过可信边界形成 Final。
- 三个 Validator 返回字段级、可定位错误。
- 用户能确认 Final SchemaIR、Final Standard 和 Final Template。
- Template 只能绑定精确 Final Standard 版本。
- 一个 Standard 可被多份同方向 Template 复用。
- ASSEMBLY 标量字段子集/omission、容器结构绑定、PARSE configured targets、EMPTY 和 XML Key expressions 行为清晰可验证。
- Standard 镜像、COLLECTION_ITEM 两端类型和 SECURE_INPUT_REF 不泄露真实值可验证。
- 差异、规则冲突、omissions 和不确定项不会被静默忽略。
- Workbook Generator 能稳定生成一个方向标准加一份模板的工作簿。
- UI 能预览和下载工作簿。
- Golden regression 和关键转换测试通过。

## 6. 待确认问题

- Review Workbench 的最小页面结构。
- DocIR 与 SchemaIR 的具体编辑控件。
- Standard/Template artifact version 的 UI 展示与选择方式。
- 递归表达式编辑方式。
- Omission 批量 Review 与审计展示方式。
- Validator 错误格式。
- 规则和标准版本升级的影响分析方式。
- 本地开发、依赖安装、模型配置和样例运行说明。
