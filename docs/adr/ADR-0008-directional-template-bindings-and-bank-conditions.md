# ADR-0008: 银行事实投影、方向性模板绑定与条件约束

## Status

Accepted. Amends ADR-0005 and ADR-0007. Its MAPPING and Replacement scope is amended by ADR-0009.

## Date

2026-08-03

## Context

ADR-0007 将 InterfaceTemplateIR 统一描述为“对所绑定 Standard 字段取值和处理”，并要求模板字段是 Standard 字段子集。正式 b2e0061 Template 导出和固定 `parseFields` 对象表明，这个描述只适用于 ASSEMBLY：

- ASSEMBLY 从系统请求字段取值，写入银行请求 Standard Field。
- PARSE 从银行响应 Standard Field 取值，写入固定 Parse Field/Java 对象。

Parse Field 具有独立 name、path 和 datatype，由高代码固定维护，不在银行 Interface Standard 中配置。要求 PARSE Template 覆盖所有 Standard Field，或要求固定 Parse Field 全部配置，都会生成没有业务依据的 omission。

同时，银行文档存在会改变字段 required 语义的明确条件。例如 b2e0061 在 `transtype=2` 时要求 `obssid` 非空。只保存 `obssid.required=false` 会丢失银行约束；把所有 Condition 都作为 future candidate 也无法形成可信 Workbook。

目标系统正式导出还包含业务 Condition，但这类规则通常依赖具体业务选择，不能仅由银行文档和字段目录可靠推断。

后续人工确认还关闭了四个会影响 wire contract 的问题：

- raw-doc/Final SchemaIR 是银行字段、path、出现次数和约束的事实源；正式导出只证明目标系统形态和已观察配置。
- Template 的 Required、Length、Data Type 是需要实际配置的值，本期必须显式镜像 Standard/raw-doc，不允许内部业务覆盖。
- Node/Object 是无值结构，不应因为缺少普通 Template 行而产生 omission；PARSE 重复银行节点可以绑定固定输出对象的 List 元素。
- XML declaration encoding 属于方向级报文元数据；样例中观察到但协议未定义的 XML attribute 不能自动进入 Final Standard。

## Decision

### Bank Fact Authority and Standard Projection

- raw-doc 经人工确认形成的 Final SchemaIR 决定银行字段、完整 path、出现次数、Required、Length、Data Type 和银行条件。
- 正式 Standard/Template 导出只能作为目标系统表示方式和已观察配置的证据；冲突时使用差异记录，不能覆盖银行事实。
- 在当前已确认的 raw-doc 范围内，没有写出的 Length、Illegal Characters、Regex 等约束为 `NO_CONSTRAINT`；只有证据冲突或仍无法判定时才为 `UNKNOWN`。
- b2e0061 Final Standard 保留 raw-doc 定义的 `@security` XML Key，排除只存在于正式导出的 `vamflag`。
- raw-doc 样例中的 `@lang` 继续保留在 SchemaIR 作为 observed evidence，并形成 `SCHEMA_STANDARD_DIFFERENCE` Warning；协议说明未定义它，因此不进入 Final Standard。

SchemaIR 每个 direction message 使用 `xmlEncoding` 保存 XML declaration encoding。建议值与示例值冲突时必须人工 Review；Final 值显示在 Workbook `Overview`，不形成 Standard Field 或 XML Key。

### Directional Template Binding

InterfaceTemplateIR 使用方向性端点：

- ASSEMBLY：target 是绑定 Standard 的 `standardFieldRef`；source 是 ASSEMBLY FIELD、literal、function 或其他受支持 Value Expression。
- PARSE：target 是 `parseFieldRef`；Value Expression 的 FIELD_REF 引用绑定 Standard 的 `standardFieldRef`，也可按受支持模式使用 literal、function 或 CONCATENATE。

两方向继续绑定同一个精确 `standardId + standardVersion + contentHash` 版本，但 Template field config 不再被统一定义为 Standard Field 子集。

每个 field config 必须显式保存 `standardProjection.required`、`standardProjection.length` 和 `standardProjection.dataType`。三项的约束状态和值必须与绑定 Standard 完全相同，Validator 不允许模板使用内部业务缩短后的 Length、不同 Required 或不同 Standard Data Type。

`standardProjection` 与 Parse target 是两组信息：ASSEMBLY 的 Standard 是 target；PARSE 的 Standard 是 source，而 Parse Field 是 target。Workbook 必须分别展示两端，不能用 Standard 的 name/path/datatype 代替 Parse target。

### Structural Binding and Coverage

Template field config 的 `bindingKind` 为：

- `VALUE`：标量字段值绑定；
- `STRUCTURE_ONLY`：Node/Object 结构或 XML Key 配置，无字段值表达式；
- `COLLECTION_ITEM`：PARSE 中每个重复 Standard Node 创建目标 Parse List 的一个元素，子字段在当前元素内解析。

ASSEMBLY omission coverage 只适用于应配置值的标量 Standard Field。Node/Object 不产生 omission；无 XML Key、无结构绑定需求的容器可以没有 Template 行。Standard 容器存在 XML Key 时必须具有适用结构行和完整 key expressions：普通容器使用 `STRUCTURE_ONLY`，Parse collection source 使用 `COLLECTION_ITEM`。缺失时报告 XML Key 错误而不是 omission。

b2e0061 raw-doc 将 `b2e0061-rq` 与 `b2e0061-rs` 定义为 `0..1000`，Final Standard 均使用 `Node`。PARSE 以 `COLLECTION_ITEM` 将每个 `b2e0061-rs` 映射为 `paymentLineList(List)` 的一个元素，子节点写入当前元素；正式导出的 `Object` 只保留为差异证据。

### Secure Fixed Values

Value Mode 仍只有六种。`SECURE_INPUT_REF` 是 `FIXED_VALUE` payload kind，与 `LITERAL` 二选一；IR、Workbook 和日志只保存安全引用标识，不能保存或展示真实值。正式导出中的 `<REDACTED>` 只证明原位置存在敏感配置，不是可执行字面量。

### Parse Field Catalog

Parse Field Catalog 保存固定输出 JSON/Java 对象的字段 name、parent path 和 datatype：

- 它是目标端高代码契约，不属于银行 InterfaceStandardIR。
- Catalog 中的 `List` 只描述固定输出对象层级，不表示支持 JSON 银行报文，也不得进入 XML InterfaceStandardIR。
- Template Validator 只校验实际配置的 Parse Field 引用、path 和 datatype。
- 未配置 Parse Field 默认不产生 omission 或 warning。
- 不根据单个接口的配置情况把 Parse Field 全局推断为“由代码赋值”。

未来如需声明某个 Parse Field 对特定接口必配，必须增加显式、可追溯规则。

### Bank-document Conditions

银行文档明确、无歧义且落在规则包支持子集内的条件，作为 SchemaIR/InterfaceStandardIR 的结构化条件约束保存，并进入 Workbook：

- 基础 `required` 与条件 required 分开保存。
- P0 只支持 `EQUALS`、`IS_EMPTY` 谓词和 `REQUIRED` 效果。
- 条件必须引用同方向已存在字段，并保存银行原文 evidence 和人工 Review。
- b2e0061 至少包含 `transtype EQUALS "2" => obssid REQUIRED`。
- `toibkn IS_EMPTY => tobknm REQUIRED` 属于同一受支持类型。

不能稳定结构化的银行约束继续保存为 `conditionText` 和 Review 提示，不能静默丢失或强制转换。

### Target-system Business Conditions

目标系统具有业务 Condition、多行同目标字段和复合逻辑能力。P0 只在文档中记录该能力：

- 不从正式导出推导通用业务规则。
- 不在 InterfaceTemplateIR 预留未经验证的通用 Condition AST。
- 不实现运行时 Condition 求值或目的系统业务 Condition 生成。
- 正式导出中的业务 Condition 只能作为能力和人工对照证据。

银行文档条件与目标系统业务 Condition 是两个不同来源、不同可信边界的概念，不能合并处理。

## Relationship to Previous ADRs

本 ADR 修订 ADR-0007 的以下内容：

- “Template 字段是 Standard 字段子集”只保留给 ASSEMBLY；PARSE 改为 Standard source 到 Parse Field target。
- ASSEMBLY omission 只覆盖适用标量字段；Node/Object 不产生 omission；未配置 Parse Field 也不自动产生 omission。
- Template 显式保存 Standard Required/Length/Data Type 镜像，并由 Validator 强制相等。
- PARSE 重复 Standard Node 使用 `COLLECTION_ITEM` 绑定 Parse List 元素。
- “所有 condition 都是 future candidate”调整为：银行文档明确的最小条件约束属于当前 Standard 能力，目的系统业务 Condition 仍不属于 P0。

ADR-0007 关于独立 Standard/Template 生命周期、不可变版本绑定、XML Keys、Value Expressions、Workbook 粒度和 Human Review 的决定继续有效。

本 ADR 同时扩展 ADR-0005：方向级 XML encoding 进入 SchemaIR message metadata；observed-only attribute 可以保留在 SchemaIR 而不进入 Standard，并通过差异与 Review 保持可追溯。

## Alternatives Considered

### 两方向继续统一为 Standard Field 子集

Pros:

- IR 结构更对称。

Cons:

- PARSE 的真实目标是固定 Parse Field 对象。
- 无法正确表达银行 source field 与系统 target field。
- 会对未配置 Parse Field 或未消费 Standard Field制造错误 omission。

Why not chosen:

- 与正式导出和高代码固定输出对象不一致。

### 把银行条件放入 InterfaceTemplateIR

Pros:

- 接近目标系统 Condition 配置界面。

Cons:

- `obssid` 条件是银行 Standard 约束，不是某一模板的取值选择。
- 当前 b2e0061 ASSEMBLY Template 对 `transtype`、`obssid` 都配置为 EMPTY，放入 Template 会歪曲模板事实。
- 容易把银行规范与业务 Condition 混为一体。

Why not chosen:

- 条件的事实来源和生命周期属于 SchemaIR/Standard，而不是 Template。

### Template 约束只在 Workbook 从 Standard 派生

Pros:

- TemplateIR 不重复保存 Required、Length 和 Data Type。

Cons:

- 无法表达目标系统 Template 确实存在这些配置值。
- 无法由 Template Validator 直接发现 Template 与 Standard/raw-doc 漂移。
- PARSE 时容易继续把 Standard source 类型误当成 Parse target 类型。

Why not chosen:

- 本期要求 Standard 和 Template 两侧都按 raw-doc 配置并显式校验一致。

### P0 忽略全部 Condition

Pros:

- 实现最简单。

Cons:

- `required=false` 会丢失 `transtype=2` 时 `obssid` 必填的关键约束。
- Workbook 会给配置人员错误指导。

Why not chosen:

- 破坏 trusted chain 的完整性。

## Consequences

- InterfaceTemplateIR contract 和 Validator 必须按 direction 校验不同 source/target 端点。
- Template Validator 必须校验 Standard projection 完全相等、binding kind 合法、容器 coverage 与 `COLLECTION_ITEM` 层级关系。
- Parse Field Catalog 成为规则包中的独立方向性 catalog。
- PARSE golden 只覆盖实际配置的 Parse Field，不制造 catalog coverage omission。
- SchemaIR/InterfaceStandardIR 需要支持最小结构化条件约束；现有 `conditionText` 继续用于复杂或未结构化说明。
- Workbook 的 Overview、Standard、Template 和 Warnings 必须分别展示 XML encoding、银行条件、Standard/Template 镜像、Parse target 和差异来源，不执行条件。
- 目的系统业务 Condition 与多行模板行仍是 future candidate；MAPPING/Replacement 由 ADR-0009 纳入 P0。
