# ADR-0006: 独立 ConfigIR 与 Configuration Workbook

## Status

Superseded by ADR-0007.

## Date

2026-07-31

## Superseded Scope

ADR-0007 以独立的 InterfaceStandardIR 与 InterfaceTemplateIR 取代本 ADR 的单一 ConfigIR，并重新定义标准复用、模板字段子集和 Configuration Workbook 粒度。

本 ADR 关于以下事项的决定继续有效：版本化自然语言规则包、LLM 只能生成 Draft、人工 Review 与 Validator 组成可信边界、不生成 Import JSON、Workbook 不是事实源且必须确定性生成。

## Context

ADR-0004 将 Final SchemaIR 定义为单一事实源，并由它确定性生成 Schema Workbook。这一边界解决了 Import JSON 适配成本，但后续需求讨论确认：仅有银行报文结构不足以指导目标系统配置。

配置人员还需要知道：

- 字段值来自固定值、空值、业务字段、function、mapping 还是组合表达式；
- 目标系统实际 required、length、empty、overlength、row limit 和字符处理策略；
- 这些配置基于哪个规则版本和 Rule ID；
- 目标系统配置与银行原始约束为何不同；
- 哪些配置仍不确定或需要人工判断。

这些内容不是银行文档事实，不能写回 SchemaIR；如果只存在 Excel，又无法稳定校验、Review 和重新生成。

同时，目标系统规则以自然语言和 catalog 为主。LLM 适合结合 Final SchemaIR 产生候选配置，但 function、mapping 等业务语义不能仅靠结构 Validator 确认。

## Decision

### 独立 ConfigIR

项目引入 `ConfigIR`，作为目标系统字段配置模型：

- Final SchemaIR 保存银行 XML 报文结构和银行原始约束。
- Final ConfigIR 保存目标系统字段取值与处理策略。
- SchemaIR 与 ConfigIR 是两个独立事实源，不相互覆盖。
- 两者出现 required、length 等差异时，同时保留双方值；ConfigIR 记录差异原因、Rule ID 和人工 Review 结论。

### 自然语言规则包

正式规则资产位于仓库顶层 `configuration-rules/`，采用不可变版本目录和稳定 Rule ID：

- `rules.md` 保存六种取值方式和字段处理规则。
- `fields.md`、`functions.md`、`mappings.md` 保存真实目标系统 catalog。
- `docs/reference/` 不是权威规则来源。
- 缺少真实 catalog 时，不得从历史 JSON、LLM 或相近概念推断。

### LLM Draft 与人工确认

- LLM 结合 Final SchemaIR 和指定规则版本生成 ConfigIR Draft。
- ConfigIR Validator 只校验结构、SchemaIR/规则/catalog 引用和确定性 invariant。
- function、mapping 和其他业务语义必须由人工 Review 确认。
- 未映射、规则冲突、差异或未确认项阻止 Final ConfigIR。

### Configuration Workbook

Configuration Workbook 是配置规格和执行清单，不是事实源：

- 输入为 Final SchemaIR、Final ConfigIR、两份匹配的通过校验结果和指定规则版本。
- Workbook Generator 只做确定性格式化，不临时推断业务配置。
- 工作簿保存配置指导、Value Expression 展开、Warnings、Rule References 和人工执行/验证状态。
- Excel 中的状态和备注不回流 ConfigIR。
- 工作簿不是目标系统可导入文件。

### 当前报文范围

当前只承诺 XML 银行报文。IR 使用 JSON 序列化不等于支持 JSON 银行报文；JSON 银行报文保留为未验证的 future candidate。

## Relationship to Previous ADRs

本 ADR 部分 supersede ADR-0004：

- 将“Final SchemaIR 是系统内部单一事实源”调整为 Final SchemaIR 与 Final ConfigIR 两个事实源。
- 将 Workbook 输入从 Final SchemaIR 调整为双 Final 模型、两份校验结果和指定规则版本。
- 将 Schema Workbook 调整为 Configuration Workbook。

ADR-0004 中“不生成或兼容目标系统 Import JSON”“Excel 不是事实源”“Generator 必须确定性”的决定继续有效。

本 ADR 也扩展 ADR-0001：LLM 现在可以生成 ConfigIR Draft，但 Human Review、Validator 和确定性生成器仍是可信边界。

## Alternatives Considered

### 扩展 SchemaIR 保存系统配置

Pros:

- 模型数量更少。
- Generator 只需要一个输入对象。

Cons:

- 银行原始约束与目标系统配置混在一起。
- required、length 等差异容易互相覆盖。
- SchemaIR 失去“银行 XML 报文是什么结构”的清晰职责。

Why not chosen:

- 两类事实来源、生命周期和 Review 责任不同，强行合并会降低可追溯性。

### 配置只存在 Excel

Pros:

- 最贴近配置人员当前工作方式。
- 无需新增 ConfigIR wire schema。

Cons:

- Excel 难以做精确 diff、引用校验和递归表达式校验。
- 人工状态、样式和配置事实容易混杂。
- 无法稳定重新生成或判断规则版本影响。

Why not chosen:

- 不满足可机器校验、可回归和双事实源要求。

### 将全部自然语言规则强行编码

Pros:

- 运行时结果完全确定。
- 可以减少 LLM 配置判断。

Cons:

- 当前规则和 catalog 尚未整理，无法准确编码。
- function/mapping 选择包含业务语义判断，过早编码会制造大量未经证实的分支。
- 维护成本会从规则治理转移为程序规则和例外清单。

Why not chosen:

- 当前更合适的边界是自然语言规则包 + LLM Draft + 结构 Validator + 人工 Review。

### 恢复 Import JSON

Pros:

- 更接近自动导入。
- 如果目标格式稳定，可能减少人工步骤。

Cons:

- 重新引入历史 ID、父子引用、状态字段、导入模板和目标系统兼容性成本。
- 扩大当前阶段的集成与生产风险。
- 与“配置规格和人工执行清单”的产品定位不同。

Why not chosen:

- ConfigIR 和 Configuration Workbook 提供目标系统感知的人工配置指导，不需要恢复导入适配器。

## Consequences

- Phase0 trusted chain 增加规则包、ConfigIR fixture、ConfigIR Validator 和双模型 Workbook Generator。
- Phase1 增加 ConfigIR Review UI 和工作簿预览/下载。
- Phase2 需要统计映射接受率、人工修改率、未映射项、function/mapping 选择质量和规则版本影响。
- `configuration-rules/v1` 未确认前，ConfigIR wire schema、fixture、Validator 和 Workbook Generator 保持 Blocked。
- Workbook regression 必须验证六种 Value Mode、递归 `CONCATENATE`、Warnings 和 Rule References。
- 如果未来恢复 Import JSON 或 JSON 银行报文，必须另立 ADR 明确范围和兼容成本。
