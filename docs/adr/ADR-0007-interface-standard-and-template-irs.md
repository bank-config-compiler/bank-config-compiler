# ADR-0007: 独立接口标准与接口模板模型

## Status

Accepted.

## Date

2026-07-31

## Context

ADR-0006 使用一个 ConfigIR 同时表达目标系统字段结构、取值和处理策略。后续确认的目标系统真实配置流程不是一次性配置字段，而是两个有顺序且可独立复用的步骤：

1. 按银行接口文档配置接口标准，定义报文字段格式与层级结构。
2. 基于已存在的接口标准配置接口模板，定义系统数据如何转换和赋值。

接口标准与接口模板通过 `interfaceCode` 关联，ASSEMBLY 与 PARSE 分别拥有不同的标准。一个方向标准可以被多份同方向模板复用，因此标准与模板具有不同生命周期。

接口标准还采用目标系统特有的结构语义：Path 表示父路径；XML attribute 作为所属 element 的 XML Keys；重复无值容器使用 `Node`，单一无值容器使用 `Object`。这些配置不能直接等同于保存银行原始事实的 SchemaIR。

## Decision

### 独立 InterfaceStandardIR 与 InterfaceTemplateIR

项目使用三个顺序关联的配置事实源：

- Final SchemaIR 保存银行 XML 报文结构与银行原始约束。
- Final InterfaceStandardIR 保存一个 `interfaceCode + direction` 的目标系统接口标准。
- Final InterfaceTemplateIR 保存一份模板对所绑定标准字段的取值和处理配置。

LLM 先根据 Final SchemaIR 和指定规则版本生成 InterfaceStandardIR Draft；标准经 Validator 与人工 Review 形成 Final 后，才能作为 InterfaceTemplateIR Draft 的输入。

### 标准身份、版本和复用

- ASSEMBLY 与 PARSE 的标准相互独立。
- 一个方向标准可以关联多份同方向模板。
- 标准和模板使用稳定内部 ID 与不可变 artifact version。
- 模板精确绑定 `standardId + standardVersion + contentHash`，不自动跟随最新版。
- 新增模板复用已有 Final Standard，不重新生成标准。
- 标准升级不会静默改变已有模板；迁移必须重新校验和人工 Review。

`interfaceCode` 是关联和检索键，不足以唯一标识标准版本、模板或 Workbook。

### 标准字段与模板字段

InterfaceStandardIR 保存目标系统实际配置的字段名称、描述、父路径、完整路径、必填、长度、非法字符、XML Keys、正则、数据类型和同级顺序。SchemaIR 原始值与目标配置存在差异时，两侧均保留，并记录差异原因、Rule ID 和人工结论。

InterfaceTemplateIR 通过稳定 `standardFieldRef` 引用标准字段。模板字段是标准字段的子集：

- 每个标准字段在同一模板中最多一行。
- 场景不需要的字段可以省略，但必须生成 Warning。
- 每个省略项保存 field reference、省略原因和人工 Review 结论。
- 未确认 omission 阻止 Final Template；确认后允许 Final，且 omission 继续出现在 Workbook Warnings。
- omission 与存在模板行并明确取空值的 `EMPTY` 不同。

同一标准字段通过 condition 配置多行是 future candidate，本期不支持，也不预留未验证的 condition wire 字段。

### XML Keys 与 Value Expressions

XML attribute 不形成独立接口标准行，而作为所属 element 的 XML Keys。若元素存在模板行，每个 XML Key 必须具有独立 Value Expression。

Value Expressions 是 InterfaceTemplateIR 的结构化 Workbook 视图，用于完整展开字段值表达式、XML Key 表达式、递归 `CONCATENATE`、function 参数和 mapping 引用。它不是新的事实源。

### Configuration Workbook 粒度

一份 Configuration Workbook 对应一个 `interfaceCode + direction + templateId + templateVersion`，包含一份模板及其绑定的一个方向标准快照。

固定主 Sheet 为 `Interface Standard` 与 `Interface Template`，不把两个方向强行打包，也不保留空方向 Sheet。辅助 Sheet 为 `Overview`、`Value Expressions`、`Warnings`、`Rule References` 和 `Legend`。

Workbook 通过调用者显式提供的 `Standard Action = CREATE | REUSE | UPDATE` 表达标准是否需要执行。Generator 不连接目标系统推断该状态。`REUSE` 时标准 Sheet 仅供核对，不要求重复配置。

## Relationship to Previous ADRs

本 ADR supersede ADR-0006 的以下内容：

- 用两个目标配置 IR 取代单一 ConfigIR。
- 用三个顺序关联的配置事实源取代双事实源。
- 将 Workbook 从“每接口双方向合并”调整为“每方向模板一份”。
- 将目标系统 required、length、illegal characters 等结构约束归入 InterfaceStandardIR，将取值与处理策略归入 InterfaceTemplateIR。

ADR-0006 关于版本化规则包、LLM Draft、人工 Review、Validator、确定性 Generator、不生成 Import JSON 和 Workbook 不是事实源的决定继续有效。

ADR-0004 中“不生成或兼容目标系统 Import JSON”的决定继续有效。

## Alternatives Considered

### 保留 ConfigIR 并增加两个子对象

Pros:

- 保留已有名称，文档改动较少。

Cons:

- 掩盖标准先于模板、标准可复用的真实生命周期。
- 容易继续把结构约束和转换策略放入同一 Review/Validator 边界。

Why not chosen:

- 两类配置的身份、版本、依赖和人工操作均不同，应独立建模。

### 直接把 SchemaIR 当作接口标准

Pros:

- 少一个模型和生成步骤。

Cons:

- SchemaIR 的完整 path、银行类型和 XML attribute 表达与目标系统的父路径、Node/Object、XML Keys 不同。
- 银行原始约束与目标系统实际配置差异无法清晰保留。

Why not chosen:

- SchemaIR 和接口标准回答不同问题，不能互相覆盖。

### 每个 interfaceCode 生成一份 Workbook

Pros:

- 单一接口只有一个交付文件。

Cons:

- ASSEMBLY/PARSE 标准和模板生命周期独立。
- 一个标准关联多模板时会导致无业务依据的模板配对或持续膨胀的工作簿。

Why not chosen:

- Workbook 应以一次可执行的方向模板配置为交付和验收边界。

### Final Template 必须覆盖全部标准字段

Pros:

- 容易校验是否漏配。

Cons:

- 正式报文在特定业务场景下可能不需要部分标准字段。
- 强制补行会把“有意省略”错误表达为 `EMPTY` 或无意义配置。

Why not chosen:

- 使用字段子集、Warning 和可追溯 omission Review，既允许合法场景差异，又保留防漏配能力。

## Consequences

- Phase0 trusted chain 增加 Standard 与 Template 两个 Draft/Validator/Review 阶段。
- Workbook Generator 输入增加 Final InterfaceStandardIR、Final InterfaceTemplateIR 和对应校验结果。
- Interface Template Review 必须同时展示实际配置行和未覆盖标准字段的 omission 列表。
- 标准变更需要显式评估所有绑定模板，而不是静默传播。
- Golden regression 必须覆盖父路径、sequence、Node/Object、XML Keys、模板字段子集、omission Review 和字段/XML Key Value Expressions。
- `configuration-rules/v1` 尚未提供，因此两个新 IR 的 wire schema、fixture、Validator 和 Workbook Generator 实现继续 Blocked。
- 如果未来支持同字段多行 condition、JSON `List`、Import JSON 或目标系统 API，必须另行确认契约和兼容成本。
