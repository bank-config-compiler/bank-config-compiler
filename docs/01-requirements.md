# 银行接口配置编译与 Configuration Workbook 需求文档

## Status

Draft.

## 1. 项目定位

本项目面向银企直连实施场景，将真实脱敏的银行接口文档整理为可 Review、可校验、可追溯、可回归的银行 XML 报文模型，并依次形成目标系统的接口标准、接口模板和供配置人员执行验收的 Configuration Workbook。

目标系统的真实配置顺序是：先配置接口标准，再基于该标准配置接口模板。两者通过 `interfaceCode` 关联，并按 `ASSEMBLY`（组装）与 `PARSE`（解析）方向分别管理。

项目目标不是全自动生成生产配置，也不承诺输出可直接导入目标系统的文件。LLM 只负责产生 Draft；Validator 和人工 Review 构成可信边界；最终工作簿只由已确认模型确定性生成。

| 阶段 | 定位 | 需求文档 |
|---|---|---|
| Phase0-PoC | 确认样例、格式、可信链路和技术边界，证明方向可行。 | `docs/phases/00-phase0-poc.md` |
| Phase1-MVP | 交付可重复运行、可 Review、可回归的最小产品能力。 | `docs/phases/01-phase1-mvp.md` |
| Phase2-Pilot | 在受控真实场景中试点，验证实施提效、配置质量和运维边界。 | `docs/phases/02-phase2-pilot.md` |
| Phase3-Production | 暂不定义目标和需求。 | `docs/phases/03-phase3-production.md` |

## 2. 核心产物与术语

IR 是 Intermediate Representation（中间表示）。它把来源不同、结构不同的信息转换为项目内部可持续处理的模型。

| 产物 | 更容易理解的名称 | 回答的问题 | 内容边界 | 可信状态 |
|---|---|---|---|---|
| `DocIR` | 结构化文档稿 | 银行文档写了什么？ | 章节、字段表、示例、条件、冲突、原文证据和不确定项。 | LLM 生成 Draft，人工确认后成为 Final DocIR。 |
| `SchemaIR` | 标准化报文模型 | 银行 XML 报文是什么结构？ | element、attribute、方向级 XML encoding、完整 path、父子层级、原始类型、必填、长度、出现次数和银行约束。 | LLM 生成 Draft，经 SchemaIR Validator 和人工 Review 后成为 Final SchemaIR。 |
| `InterfaceStandardIR` | 接口标准模型 | 目标系统应如何定义这个方向的银行报文字段格式和层级？ | 目标系统字段名称、描述、路径、基础/条件必填、长度、非法字符、XML 内键、正则、数据类型和顺序。 | LLM 生成 Draft，经 Standard Validator 和人工 Review 后成为 Final InterfaceStandardIR。 |
| `InterfaceTemplateIR` | 接口模板模型 | 当前模板如何连接银行标准字段与系统字段并进行取值和处理？ | 方向性 source/target、字段与 XML 内键取值表达式、处理策略、规则依据、ASSEMBLY omission 和人工结论。 | LLM 生成 Draft，经 Template Validator 和人工 Review 后成为 Final InterfaceTemplateIR。 |
| `Configuration Workbook` | 配置工作簿 | 配置人员要配置什么、依据是什么、执行与验证到哪一步？ | 一个方向标准的快照、一份模板、表达式明细、Warnings、规则引用和执行清单。 | 派生交付物，不是事实源。 |

“标准化报文模型”中的“标准化”只表示将不同银行文档统一为项目内部结构，不表示行业标准、XSD 或 JSON Schema。

本项目当前只承诺处理 XML 银行报文。各 IR 可以使用 JSON 作为机器可校验的序列化格式，但这不等于支持 JSON 银行报文。`List` 不得进入 XML InterfaceStandardIR；PARSE 固定输出对象的字段目录可以使用 `List` 表达 Java/JSON 对象层级，这不扩大银行报文格式范围。

## 3. 产品事实源与关联关系

项目采用三个相互独立、顺序关联的配置事实源：

- `Final SchemaIR` 保存银行报文结构和银行原始约束。
- `Final InterfaceStandardIR` 保存一个 `interfaceCode + direction` 下目标系统实际采用的接口标准。
- `Final InterfaceTemplateIR` 保存一份模板的方向性转换配置、Standard 约束镜像和结构绑定：ASSEMBLY 从系统字段写入银行 Standard Field；PARSE 从银行 Standard Field 写入固定 Parse Field。

三者不得相互覆盖。SchemaIR 与 InterfaceStandardIR 的 required、length、type 或其他约束存在差异时，必须同时保留两侧值；InterfaceStandardIR 记录差异原因、Rule ID 和人工 Review 结论，差异进入 Workbook `Warnings`。

银行字段、path、出现次数和约束以 raw-doc 经人工确认形成的 Final SchemaIR 为准；正式 Standard/Template 导出只证明目标系统表示方式和已观察配置，不能覆盖银行事实。b2e0061 Final Standard 因此保留 raw-doc 定义的 `@security` XML Key、排除只存在于正式导出的 `vamflag`，并将样例中观察到但协议说明未定义的 `@lang` 保留在 SchemaIR 和差异 Warning 中而不进入 Final Standard。

每个 SchemaIR message 使用 `xmlEncoding` 保存当前方向 XML declaration 的 encoding，并以 `xmlEncodingEvidence[]` 保存 `sourceKind`、`sourceRef`、`observedValue`、`disposition` 和 Review 说明。b2e0061 的 ASSEMBLY、PARSE 两个方向已由 Human 与银行线下确认均为 canonical `UTF-8`。显式 evidence 与确认值冲突时，Validator 产生 blocking Warning；Human 必须将其处置为 `RESOLVED_CONFLICT` 并说明原因，或更新确认值后重新 Review。Final 值只作为报文级元数据展示在 Workbook `Overview`，不生成 Interface Standard 字段或 XML Key。

一个方向标准可以被多份同方向模板复用。模板必须绑定不可变的 `standardId + standardVersion + contentHash`，不能仅凭 `interfaceCode` 自动跟随最新标准。标准升级后，已有模板仍指向原版本；迁移必须重新校验和 Review。

Configuration Workbook 不是事实源，不反向更新任何 IR。人工填写的执行状态、验证状态和备注也不回流 Final 模型。

## 4. 核心设计原则

- Human-in-the-loop 是必需能力。LLM 只能产生四类 IR Draft。
- Draft 未经对应 Validator（适用时）和人工 Review，不得成为 Final 产物。
- 三类 IR 使用显式 stable ID、不可变 artifact version、`DRAFT | FINAL` 状态和 `PENDING | APPROVED` Review。任何 `uncertain=true`、`UNKNOWN`、未决差异、未决 omission 或 blocking Warning 都阻止 Final eligibility。
- Human 先完成完整 Final candidate 和 Review metadata，再运行 Validator。Validation result 使用 canonical UTF-8 JSON SHA-256 绑定包括 Review 在内的全部语义内容；空白和属性顺序不影响 hash，任何语义值变化都使旧结果失效。
- 接口标准必须在接口模板之前形成 Final；新增模板直接复用已确认的标准，不重新生成标准。
- Validator 只校验结构、引用和确定性 invariant，不能代替人工判断 function、mapping 或场景性字段省略是否符合业务语义。
- Workbook Generator 只做确定性格式化和配置指导，不补业务字段、不临时推断配置逻辑、不对接目标系统、不承诺导入兼容性。
- ASSEMBLY 与 PARSE 分别拥有独立的标准和模板，并复用同一套 Value Expression 结构；两方向的 source/target 端点不同。
- 外部输入、LLM 输出和 third-party response 必须在信任边界处先校验。
- 真实银行文档和配置资料属于敏感输入，日志不得记录完整原文、凭证或 secret。
- 连接、认证、证书、部署或全量目标系统配置不属于上述 IR。

## 5. InterfaceStandardIR 能力

### 5.1 标准身份与字段

每份接口标准至少具有稳定内部 `standardId`、`interfaceCode`、`direction`、不可变版本和精确规则版本。每个标准字段至少表达：

- 稳定 `fieldId` 和同级 `sequence`；
- Field Name、Field Description；
- `parentPath` 与 `fullPath`；
- Required、Length Limit；
- Illegal Characters；
- XML Keys；
- Regex；
- Data Type；
- SchemaIR 来源、规则引用、差异、不确定性和人工 Review 结论。
- 与基础 Required 分离的银行文档条件约束、原文 evidence 和人工 Review 结论。

目标系统配置中的 Path 表示父路径，因此映射为 `parentPath`。`fullPath` 包含当前字段名，用于唯一定位、审计和引用。例如 `Document` 的 parentPath 为 `Root`；`MsgId` 的 parentPath 可以为 `Root.Document.pain.001.001.02.GrpHdr`。

XML attribute 不形成独立接口标准行，而作为所属 element 标准行的 XML Keys，例如 `@version`。SchemaIR 仍独立保存银行 XML attribute 事实，不因目标系统的配置形态而丢失。同一 parent 下的 `sequence` 必须是唯一、连续的正整数，不能依赖当前数组或 Excel 行顺序隐式表达。

### 5.2 XML 数据类型

当前 XML 接口标准使用以下目标系统类型：

- `String`
- `Boolean`
- `Date`
- `Number`
- `Node`：XML 中可重复出现的无值容器节点。
- `Object`：XML 中不可重复的无值容器节点。

`List` 仅用于 JSON，不得出现在当前 XML Final InterfaceStandardIR。容器类型根据 SchemaIR 的层级、是否有值和出现次数确定；标量类型依据银行文档事实确定，信息不足时不得猜测。

### 5.3 约束状态

银行文档未给出长度、非法字符、正则等信息时，必须区分：

- `VALUE`：存在明确配置值；
- `NO_CONSTRAINT`：在当前已人工确认的 raw-doc 范围内没有写该约束，或人工确认目标系统无需该约束；
- `UNKNOWN`：证据相互冲突或仍无法判定。

`UNKNOWN` 必须进入 Review，未经确认不得形成 Final InterfaceStandardIR。空值不能同时表示“无约束”和“尚不确定”。

### 5.4 银行文档条件约束

银行文档明确、无歧义且落在规则包支持子集内的条件必须结构化保存，不能只压缩为基础 Required。例如 b2e0061 的 `obssid` 基础 Required 为 `false`，同时保存 `transtype EQUALS "2" => obssid REQUIRED`。

P0 只支持 `EQUALS`、`IS_EMPTY` 谓词和 `REQUIRED` 效果。条件必须引用同方向已存在字段，并保留银行原文 evidence 与人工 Review。复杂或无法可靠结构化的约束继续保存为 `conditionText` 和 Review 提示，不得丢失或猜测。

## 6. InterfaceTemplateIR 能力

### 6.1 模板身份与标准引用

每份模板属于一个 `interfaceCode + direction`，具有稳定内部 `templateId` 和不可变版本，并精确绑定一个 Final InterfaceStandardIR 版本。一个标准可以关联多份模板，模板按方向独立，不在 ASSEMBLY 与 PARSE 间自动配对。

### 6.2 方向性字段绑定与 omission

每个 Template field config 必须显式保存 `standardProjection`，其中的 Required、Length 和 Data Type 完整镜像所绑定 Final Standard 的约束状态和值。Template Validator 必须逐项校验完全相等；当前项目不接受出于内部业务需要缩短 Length、改变 Required 或改变 Standard Data Type。

模板字段使用以下结构绑定类型：

- `VALUE`：标量 Standard Field 与一个字段值表达式关联；
- `STRUCTURE_ONLY`：Node/Object 仅承担结构或 XML Key 配置，不具有字段值表达式；
- `COLLECTION_ITEM`：PARSE 中每个重复 Standard Node 创建目标 Parse List 的一个元素，其子字段在当前元素内解析。

ASSEMBLY 模板行以 Standard Field 为目标，以 ASSEMBLY FIELD catalog 或其他 Value Expression 为数据源。ASSEMBLY omission coverage 只适用于应配置值的标量 Standard Field：

- 同一模板中，一个标准字段最多出现一条模板行。
- 当前场景不需要报送的标量标准字段可以没有模板行。
- 缺失的适用标量字段产生 `MISSING_TEMPLATE_FIELD` Warning，而不是自动生成 `EMPTY` 行。
- 每个缺失的适用标量字段必须保存 omission 记录，至少包含 `standardFieldRef`、省略原因和人工 Review 结论。
- omission 未确认时模板保持 Draft；人工确认有意省略后，允许形成 Final InterfaceTemplateIR。
- 已确认的 omission 仍保留在 Workbook `Warnings`，不得静默隐藏。

“不配置字段”与 `EMPTY` 不同：omission 表示该模板没有这个字段配置；`EMPTY` 表示该字段存在模板行且明确取空值。

Node/Object 不参加 ASSEMBLY omission coverage。无 XML Key、无需结构绑定的容器可以没有 Template 行；容器存在 XML Key 时必须有结构绑定行并提供全部 key expression：普通容器使用 `STRUCTURE_ONLY`，同时承担 Parse collection source 时由 `COLLECTION_ITEM` 行承载。缺失时报告 XML Key 配置错误而不是 omission。

PARSE 模板行以 Parse Field catalog 为目标；Value Expression 中的 FIELD_REF 引用绑定 Standard 的银行字段，也可以使用受支持的 literal、function 或 CONCATENATE。Standard source 与 Parse target 的 name、path 和 datatype 必须分别保存和展示，不能用 Standard Data Type 代替 Parse target Data Type。Validator 只校验实际配置的 Parse Field 引用、path 和 datatype；未配置 Parse Field 默认不产生 omission 或 warning，也不能根据 b2e0061 的配置情况将其全局分类为代码赋值字段。

b2e0061 raw-doc 将 `b2e0061-rq` 和 `b2e0061-rs` 都定义为 `0..1000`，因此两者在 Final Standard 中均为 `Node`，不能沿用正式导出的 `Object`。PARSE 使用 `COLLECTION_ITEM` 将每个 `b2e0061-rs` 映射为 `paymentLineList` 的一个 `List` 元素；其 `status`、`insid`、`obssid` 等子字段写入当前元素。

同一目标字段通过目的系统业务 Condition 配置多条模板行是已知 future candidate。本期不支持多行、不定义通用 Template Condition wire 字段，Validator 必须拒绝超出当前 contract 的重复目标引用。第 5.4 节的银行文档条件属于 Standard 约束，不属于这里的业务 Condition。

### 6.3 取值表达式和处理策略

String、Boolean、Date、Number 标量字段的字段值，以及 XML Key 的值，在两个方向统一支持：

- `FIXED_VALUE`
- `EMPTY`
- `FIELD`
- `FUNCTION`
- `MAPPING`
- `CONCATENATE`

FUNCTION 参数只允许 FIELD reference 或 literal。`CONCATENATE` 按顺序包含任意模式的子表达式并允许递归；只有 CONCATENATE children 可以递归 Value Expression。表达式必须保存为机器可校验的树，不能压缩成只能由自然语言解释的字符串。

六种 Value Mode 不增加第七种安全值模式。`FIXED_VALUE` 的 payload 必须在 `LITERAL` 与 `SECURE_INPUT_REF` 中二选一；安全输入只保存引用标识，不在 IR、Workbook 或日志中保存或展示真实值。正式导出中的 `<REDACTED>` 不是可执行字面量，不能进入 Final fixture。

所有 Function 输入、参数和返回值都是 String。MAPPING expression 使用一个 String FIELD reference 作为输入，并通过全局唯一 `mappingRuleName` 引用预设 catalog；对完整值精确匹配，未匹配必须报错。Template/IR 不内联 mapping entries。

Replacement 在 Value Expression 完成后引用一个 `mappingRuleName` 处理结果 String；命中片段替换为 target，空 target 表示删除，未命中内容原样保留。每个 MAPPING expression 或 Replacement policy 都只能选择一个规则。MAPPING 与 Replacement 纳入 P0 IR、Validator、Workbook 和专项 golden。

标量模板行必须具有一个字段值表达式。`Node`、`Object` 是无值容器，模板行不得配置字段值表达式；它们仍可保存适用的处理策略，以及下述独立 XML Key 表达式。

模板行还表达：

- Empty Handling；
- Overlength Handling；
- Row Limit；
- Chinese Character Length；
- 一个 Replacement `mappingRuleName`；
- Rule References、confidence、不确定原因和人工 Review 结论。

Processing policy 的 P0 值域为：Empty Handling `BLANK | DELETE`；Overlength `INTERCEPT | TRUNCATE_FRONT | OVERLONG_LINE_BREAK | TRUNCATE_BACK`；Row Limit 为正整数；字符长度使用 `STANDARD_1..6`，默认值为 `STANDARD_1`。具体语义和字符权重以 `configuration-rules/v1/rules.yaml` 为准；其他仍未知的默认值不能由实现者补猜。

ASSEMBLY 中，表达式描述系统请求字段如何转换为银行 Standard Field；PARSE 中，表达式描述银行响应 Standard Field 如何转换为固定 Parse Field。

### 6.4 XML Key 表达式

接口标准 element 行只定义 XML Keys 的名称。若该标准字段存在模板行，每个 XML Key 必须在模板行中具有独立 Value Expression，例如 `@version → FIXED_VALUE("1.0")`。

模板行引用未知 XML Key 或缺少已定义 XML Key 的表达式时，Template Validator 必须报错。标量字段已通过 omission Review 确认省略时，其 XML Keys 随字段一起省略；Node/Object 不使用 omission，具有 XML Key 的容器必须存在适用的结构绑定配置。

## 7. 正式规则资产

InterfaceStandardIR 与 InterfaceTemplateIR 的权威目标系统规则来源位于仓库顶层 `configuration-rules/`，不位于 `docs/reference/`。

规则包采用版本目录；`DRAFT` 可补充，`RELEASED` 后不可变。每条可被 IR 引用的规则使用稳定 Rule ID；字段、function 和 Mapping catalog 保存有来源的原始标识。MAPPING 与 Replacement 使用预设 catalog 的全局唯一 `mappingRuleName`，不在 IR 内联 entries。每个 Final IR 记录自己实际使用的精确规则版本，不要求标准和后续模板必须使用同一版本。

`configuration-rules/v1` 是根据正式导出、`bkl.md`、ASSEMBLY/PARSE 字段清单、Mapping 样例和业务确认建立的 BKL configuration rules 子集，不绑定具体银行接口，也不声称覆盖全量 catalog。Function catalog 只包含正式导出中实际观察到的条目，不使用 `bkl.md` 的 function 内容；Function 类型统一为 String。v1 已于 2026-08-06 发布为不可变的 `RELEASED` 版本，可以被 Final IR 精确引用。字符长度默认值已确认为 `STANDARD_1`；其他仍未知的系统默认值必须保持 `UNKNOWN`，不得从相近概念推断。

## 8. 可信流程

```mermaid
flowchart TD
    A["Raw Docs"] --> B["LLM 生成 DocIR Draft"]
    B --> C["人工 Review DocIR"]
    C -->|"修正后重新 Review"| B
    C -->|"确认"| D["Final DocIR"]

    D --> E["LLM 生成 SchemaIR Draft"]
    E --> F["SchemaIR Validator / Draft Result"]
    F -->|"结构错误：修正后重新校验"| E
    F --> G["人工 Review SchemaIR"]
    G -->|"修改事实"| E
    G -->|"完成 Final metadata"| HC["完整 Final SchemaIR Candidate"]
    HC --> FV["SchemaIR Validator 复验"]
    FV -->|"失败：返回 Review"| G
    FV -->|"通过且 hash 匹配"| SV["Final SchemaIR Validation Result"]
    SV --> H["Eligible Final SchemaIR"]

    H --> I["LLM 生成 InterfaceStandardIR Draft"]
    RS["Standard 使用的 configuration-rules 版本"] --> I
    I --> J["Standard Validator / Draft Result"]
    J -->|"结构错误：修正后重新校验"| I
    J --> K["人工 Review Interface Standard"]
    K -->|"修改事实"| I
    K -->|"完成 Final metadata"| LC["完整 Final Standard Candidate"]
    LC --> JV["Standard Validator 复验"]
    JV -->|"失败：返回 Review"| K
    JV -->|"通过且 hash 匹配"| STV["Final Standard Validation Result"]
    STV --> L["Eligible Final InterfaceStandardIR"]

    L --> M["LLM 生成 InterfaceTemplateIR Draft"]
    RT["Template 使用的 configuration-rules 版本"] --> M
    M --> N["Template Validator / Draft Result"]
    N -->|"结构错误：修正后重新校验"| M
    N --> O["人工 Review Interface Template / Omissions"]
    O -->|"修改事实"| M
    O -->|"完成 Final metadata"| PC["完整 Final Template Candidate"]
    PC --> NV["Template Validator 复验"]
    NV -->|"失败：返回 Review"| O
    NV -->|"通过且 hash 匹配"| TV["Final Template Validation Result"]
    TV --> P["Eligible Final InterfaceTemplateIR"]

    H --> Q["确定性 Workbook Generator"]
    L --> Q
    P --> Q
    SV -->|"匹配 Final SchemaIR"| Q
    STV -->|"匹配 Final Standard"| Q
    TV -->|"匹配 Final Template"| Q
    RS -->|"Standard 精确规则版本"| Q
    RT -->|"Template 精确规则版本"| Q
    X["人工指定 Standard Action"] --> Q
    Q --> W["Configuration Workbook"]
```

人工 Review 修改 Draft 后，必须先形成完整 Final candidate，再重新运行对应 Validator，旧校验结果不得复用。每份 validation result 保存 artifact kind、stable ID、artifact version、contract version、canonical content hash、`finalEligible` 和带 `blocking` 标记的 issues。Generator 只能接收三份 Final 模型、三份 identity/version/contract/hash 全部匹配且 `finalEligible=true` 的结果、各自产物记录的精确规则版本和显式 Standard Action。

## 9. Configuration Workbook 成功标准

一份工作簿对应一个 `interfaceCode + direction + templateId + templateVersion`，固定包含：

- `Overview`
- `Interface Standard`
- `Interface Template`
- `Value Expressions`
- `Warnings`
- `Rule References`
- `Legend`

`Interface Standard` 保存模板所绑定标准的完整快照；`Interface Template` 只列出当前模板实际配置的字段。`Overview` 记录标准与模板身份、版本、内容摘要、规则版本、当前方向 Final `xmlEncoding`、校验结果和调用者指定的 `Standard Action = CREATE | REUSE | UPDATE`。

`Interface Template` 必须将 Standard snapshot、Template `standardProjection` 和 Parse target 分列展示。ASSEMBLY 的 Standard 是 target；PARSE 的 Standard 是 source，并额外展示 Parse target 的 name/path/datatype。例如 `b2e0061-rs(Node)` 与 `paymentLineList(List)` 必须同时可见，不能合并为一个含糊的 Data Type 列。

`Value Expressions` 是模板表达式的结构化明细视图，不是额外事实源。主 sheet 对标量字段展示 Value Mode 和可读摘要；`Node`、`Object` 行的 Value Mode 和 Value Summary 留空，并由 `Legend` 说明该字段没有值表达式。该 sheet 按树展开递归 `CONCATENATE`、function 参数和 mapping 引用，并通过 Expression Scope 区分标量字段值表达式与 XML Key 表达式。

`Warnings` 必须展示约束差异、银行条件、ASSEMBLY 标量字段 omission、规则冲突、不确定项和 Validator issue。已确认的场景性 omission 仍须显示原因和 Review Disposition；未确认 omission 不能进入 Final Template，因此不能生成可交付工作簿。Node/Object 不产生 omission，未配置 Parse Field 不自动进入 Warnings。

相同 Final 输入、校验结果、规则版本和 Standard Action 必须稳定生成相同结构化内容。工作簿不是目标系统导入文件，也不是 IR 的反向输入。

## 10. 目标用户

- 实施与配置人员：Review 四类 IR，使用 Configuration Workbook 人工配置接口标准和接口模板，并记录执行/验证状态。
- 开发人员：维护解析、Prompt、LLM adapter、Validator、规则资产、Workbook Generator、样例回归和工程护栏。
- 审核人员：检查 Final 模型、校验结果、规则版本、omission 结论和工作簿证据。系统不直接写入生产配置。

## 11. Out of Scope

- Import JSON 生成或兼容性承诺。
- 目标系统 API 写入、自动导入或生产库直连。
- 从 Excel 反向导入或更新任一 IR。
- 连接、认证、证书、部署和全量目标系统配置。
- 当前阶段的 JSON 银行报文；Parse Field Catalog 中用于固定输出对象的 `List` 不表示支持 JSON 银行报文。
- 目的系统业务 Condition、多条同目标模板行及运行时选择逻辑。
- 未经业务负责人确认的字段、function 或 Mapping 行为推断。

## 12. 验收场景

文档、后续 wire contract、Validator 和 golden regression 必须覆盖：

- Interface Standard 的父路径、完整路径、同级顺序、`Node`/`Object`/标量映射和 XML Keys。
- `NO_CONSTRAINT` 与 `UNKNOWN` 明确区分，后者阻止 Final Standard。
- SchemaIR 与 InterfaceStandardIR 约束不一致时保留双方值、原因、Rule ID 和人工结论。
- ASSEMBLY 目标是 Standard Field；PARSE 目标是 Parse Field，表达式内 FIELD_REF 引用绑定 Standard。
- ASSEMBLY 缺失的适用标量字段产生 Warning；Node/Object 不产生 omission；未确认 omission 阻止 Final，确认后允许 Final 且继续显示在 Workbook。
- PARSE 只校验实际配置的 Parse Field；未配置 catalog 字段默认不产生 omission 或 Warning。
- Template `standardProjection.required/length/dataType` 与绑定 Standard 完全相等，Workbook 分别展示 Standard、Template 镜像和 Parse target。
- `b2e0061-rs(Node) → paymentLineList(List)` 使用 `COLLECTION_ITEM`，每个响应节点生成一个列表元素。
- omission 与 `EMPTY` 明确区分。
- 六种 Value Mode 均进入 P0；MAPPING 使用单一预设规则引用并对未匹配完整值报错。
- `SECURE_INPUT_REF` 作为 `FIXED_VALUE` payload 与 `LITERAL` 二选一，不成为第七种 Value Mode。
- Replacement 使用单一预设规则引用，按片段替换/删除并保留未命中内容。
- String/Boolean/Date/Number 标量模板行必须有字段值表达式，Node/Object 模板行不得有字段值表达式。
- 存在模板行时，每个 XML Key 都具有独立表达式；未知或缺失 Key 是错误。
- 银行文档明确条件在 SchemaIR/InterfaceStandardIR/Workbook 可追溯，基础 Required 不覆盖条件 Required。
- `messages[].xmlEncoding` 与显式 evidence 经人工 Review 后进入 Workbook Overview，不生成 Standard 字段；未处置的银行文档 evidence 冲突产生 blocking Warning。
- SchemaIR v2 明确拒绝 legacy contract、JSON message format、JSON node kind、未知属性、bool 冒充整数以及非 object/重复 key/NaN JSON 输入。
- Validation result 的 canonical hash 对格式和属性顺序稳定，对任一语义值变化敏感；旧结果不能与修改后的 Final artifact 配对。
- ASSEMBLY 与 PARSE 使用同一表达结构但具有相反 source/target 端点。
- `Value Expressions` 能还原标量字段值和 XML Key 的递归表达式树。
- 当前 XML Standard 拒绝 `List`；Parse Field Catalog 可以使用 `List`。
- Configuration Workbook 不被描述为可导入文件或 IR 的反向输入。

## 13. 跨阶段失败标准

出现以下任一情况，应视为当前阶段失败或需要调整范围：

- 任一核心 IR 只能人工从零编写，系统没有相应 Draft 生成能力。
- LLM 直接产生 Final 模型或最终 Configuration Workbook。
- 接口模板绕过未确认的接口标准生成或自动跟随未知最新版标准。
- Draft 未经要求的校验和人工确认即进入后续可信链路。
- 使用无来源规则、无法解析的 Rule ID 或不存在的 catalog 标识。
- 缺少 catalog 事实时由导出相似字段、函数名称或模型常识猜测补齐配置。
- 约束差异、模板 omission、规则冲突或不确定项被静默忽略。
- omission 被错误转换为 `EMPTY`，或未确认 omission 进入 Final Template。
- Node/Object 被错误纳入 ASSEMBLY omission coverage，或具有 XML Key 的容器缺少适用结构绑定/key expressions 却未报错。
- 未配置 Parse Field 被自动生成 omission/warning，或被全局推断为代码赋值字段。
- Template 镜像值与绑定 Standard 不一致，或 PARSE 将 Standard source datatype 与 Parse target datatype 混为一列。
- 银行条件被丢失、误当作基础 Required，或与目的系统业务 Condition 混为一体。
- Workbook Generator 临时补业务字段、选择表达式或判断目标系统是否已存在标准。
- Configuration Workbook 不能从绑定版本的 Final 模型稳定重建，或不足以指导人工配置与验证。
- 当前正式文档或产品把 JSON 银行报文描述为已支持。

## 14. 文档维护规则

- 本文维护项目级产品契约；具体模型见 `docs/design/`，任务状态见 `docs/planning/`。
- 已形成约束的关键决策记录在 `docs/adr/`。
- `docs/reference/` 中的 raw-doc、正式导出和 catalog 样例只能作为证据；必须经过人工确认或规则治理后才能进入 Final IR，且不得修改正式导出来迎合 Final 结论。
- 规则资产必须遵守 `configuration-rules/README.md`，不能以普通设计文档替代。
