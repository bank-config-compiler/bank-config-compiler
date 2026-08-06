# Configuration Rules v1 解释

## Status

Draft.

## 1. 权威边界

本规则包保存目标系统规则和已确认的方向性 catalog。它不替代银行文档或 SchemaIR：

- 银行 XML 结构、银行 required、长度、条件和 direction-level encoding 来自人工确认后的 Final SchemaIR。
- 目标系统 Standard/Template 形态、实际策略代码和 function 来自正式导出或明确业务确认。
- 两侧冲突时使用 `STD.DIFFERENCE.PRESERVE` 同时保留，不用一侧覆盖另一侧。
- 导出 JSON 是证据，不是 Generator 输入或项目目标输出。

在当前人工确认的银行文档范围内，“原文没有写该约束”表示 `NO_CONSTRAINT`；只有证据冲突或仍无法判断时才使用 `UNKNOWN`。来源路径中的接口标识只用于 provenance，规则包不保存接口专属结构、字段或条件实例。

方向级 XML declaration encoding 保存为 SchemaIR `messages[].xmlEncoding`。后续银行文档与已确认值冲突时必须产生 Warning 并阻止 Final，直到 Human Review 给出新结论。encoding 只展示在 Workbook `Overview`，不属于 Standard Field 或 XML Key。

## 2. Interface Standard 规则

### 2.1 路径与顺序

- `parentPath` 对应目标系统的 Path，仅包含父节点路径。
- `fullPath` 包含当前字段名，用于稳定引用、审计和差异定位。
- 同一 `parentPath` 下的 `sequence` 从 1 开始，必须唯一且连续，不能依赖数组或 Workbook 行号隐式表达。
- XML attribute 不形成独立 Standard Field，而作为所属 element 的 XML Key。

### 2.2 数据类型

XML InterfaceStandardIR 只允许 `String`、`Boolean`、`Date`、`Number`、`Node`、`Object`。`List` 只属于 PARSE 固定输出对象的字段目录，不能进入银行 XML Standard。

### 2.3 约束三态

Length、Illegal Characters 和 Regex 等可空约束必须区分：

- `VALUE`：存在明确目标配置值。
- `NO_CONSTRAINT`：人工确认目标系统无需该约束。
- `UNKNOWN`：资料不足，不能形成 Final Standard。

空值不能同时表示 `NO_CONSTRAINT` 与 `UNKNOWN`。

### 2.4 银行文档条件

银行文档明确且能无歧义转换为受支持谓词的条件，作为 Standard 的结构化条件约束保存，不能压缩成单一 `required` 布尔值。

当前通用契约只接受 `EQUALS`、`IS_EMPTY` 和 `REQUIRED` 效果。具体接口条件属于对应 SchemaIR 与 Human Review，不得写入 BKL 规则包。无法可靠结构化的复合业务规则继续保留 `conditionText`、原文证据和人工 Review，不得强行转换。

## 3. Interface Template 方向

### 3.1 ASSEMBLY

ASSEMBLY 的目标是银行 Interface Standard Field，数据源可以是：

- `fields.yaml` 中 ASSEMBLY catalog 的扁平 FIELD；
- 字面量；
- 已声明 function；
- CONCATENATE 子表达式；
- 明确空值。

### 3.2 PARSE

PARSE 的目标是 `fields.yaml` 中的 Parse Field；其 Value Expression 从银行响应 Interface Standard Field、literal、function 或 CONCATENATE 产生目标值，其中 FIELD_REF 必须引用绑定 Standard 的银行字段。Parse Field 定义固定 JSON/Java 对象的字段名、path 和 datatype，由高代码维护，不需要在 Interface Standard 中配置。

PARSE 只要求实际配置的目标 Parse Field 存在且 path/datatype 与 catalog 相容。未配置的 `instructionId`、`lineReturnMessageList`、`sourceCode` 等字段默认不产生 omission 或 warning，也不能被全局推断为代码赋值字段。将来若某个接口明确要求某目标字段必须配置，需要另行增加可追溯规则。

ASSEMBLY catalog 的每个 code 必须有来源描述。PARSE catalog 原样保留 `parseFields.txt` 的 code/description/path/datatype；来源中未提供的 `instructionId`、`sourceCode` description 保持 null，不根据字段名补猜。

### 3.3 Standard 镜像与结构绑定

每个 Template field config 必须显式保存 `standardProjection.required`、`standardProjection.length` 和 `standardProjection.dataType`，并与绑定 Final Standard 的状态和值完全相同。PARSE 的 Standard projection 描述银行 source；Parse Field 的 name/path/datatype 描述系统 target，两者不能合并。

`bindingKind` 值域：

- `VALUE`：标量值绑定；
- `STRUCTURE_ONLY`：Node/Object 结构或 XML Key 配置，不具有字段值表达式；
- `COLLECTION_ITEM`：每个重复 Standard Node 创建 Parse List 的一个元素，子字段在当前元素内解析。

ASSEMBLY omission coverage 只适用于应配置值的标量 Standard Field。Node/Object 不产生 omission；具有 XML Key 的容器必须存在适用结构绑定并提供完整 key expressions。普通容器使用 `STRUCTURE_ONLY`；同时承担 Parse collection source 时由 `COLLECTION_ITEM` 行承载。

## 4. Value Expression

六种能力为 `FIXED_VALUE`、`EMPTY`、`FIELD`、`FUNCTION`、`MAPPING`、`CONCATENATE`。

- FUNCTION 参数只允许 `FIELD_REF` 或 `LITERAL`，不允许任意递归表达式。
- 只有 CONCATENATE children 允许递归 Value Expression，并按 sequence 计算顺序。
- Node/Object 是无值容器，不具有字段值表达式；其 XML Keys 可以拥有独立表达式。
- `EMPTY` 表示模板行存在且明确取空值，不等于字段未配置。

`FIXED_VALUE` 的 payload kind 为 `LITERAL | SECURE_INPUT_REF`。`SECURE_INPUT_REF` 不是第七种 Value Mode；IR、Workbook 和日志只保存引用标识，禁止保存或展示实际敏感值。`<REDACTED>` 仅是参考导出占位符，不能作为 Final literal。

### 4.1 MAPPING

目标系统具有预设 Mapping catalog。MAPPING expression 只保存：

- 一个 String `FIELD_REF` 输入；
- 一个全局唯一 `mappingRuleName`；
- `TPL.VALUE.MAPPING` Rule Reference。

source-target entries 由同版本 `mappings.yaml` 提供，不能复制到 IR 或 Workbook。执行时对完整 String 值精确匹配；未找到 source 时必须报错。一个 expression 只能选择一个规则。

正式导出会携带所选规则的 snapshot，但该 snapshot 只用于对照，不改变“Template 只引用名称、规则包保存 entries”的项目契约。

### 4.2 Replacement

Replacement 与 MAPPING 使用同一个预设 Mapping catalog，但执行语义不同：

- 每个 field config 最多选择一个 `mappingRuleName`；
- 在 Value Expression 完成后处理结果 String；
- 命中片段替换为 target；target 为空字符串时删除命中片段；
- 未命中的内容原样保留。

因此 MAPPING 的“完整值未匹配报错”不能套用到 Replacement。

## 5. Processing Policy

完整值域如下。字符长度默认使用 `STANDARD_1`；其他 processing policy 默认值仍未知，因此 IR 必须显式保存选择：

| Policy | 值 | 含义 |
|---|---|---|
| Empty Handling | `BLANK` | 空值报送。 |
| Empty Handling | `DELETE` | 删除栏位。 |
| Overlength Handling | `INTERCEPT` | 超长时校验失败。 |
| Overlength Handling | `TRUNCATE_FRONT` | 保留前面的内容。 |
| Overlength Handling | `OVERLONG_LINE_BREAK` | 超长内容换行。 |
| Overlength Handling | `TRUNCATE_BACK` | 保留后面的内容。 |
| Row Limit | 正整数 | 该栏位允许出现的行数。 |

字符长度标准：

| 标准 | 字母、数字、半角标点 | 全角标点 | 其他字符 |
|---|---:|---:|---:|
| `STANDARD_1` | 1 | 2 | 2 |
| `STANDARD_2` | 1 | 3 | 3 |
| `STANDARD_3` | 1 | 2 | 5 |
| `STANDARD_4` | 1 | 1 | 1 |
| `STANDARD_5` | 1 | 2 | 1 |
| `STANDARD_6` | 1 | 2 | 3 |

除已确认的字符长度 `STANDARD_1` 外，未由资料确认的默认值保持 `UNKNOWN`。

## 6. Condition 能力边界

正式 Template 导出证明目标系统存在 Condition，并包含多行同目标字段和组合谓词。但这些条件来自具体业务选择，仅凭系统字段与银行文档无法判断是否应该配置。

- 只在仓库文档中记录目的系统具有业务 Condition 能力；
- 不从正式导出的业务 Condition 反推通用规则；
- 不实现目的系统 Condition AST、运行时求值或多行选择；
- 仅对银行文档明确条件使用第 2.4 节的 Standard 条件约束模型。

## 7. Fail-closed 规则

以下情况不得进入 Final IR：

- Rule ID 或 catalog 引用不存在；
- Standard 的约束状态为 `UNKNOWN`；
- 银行条件引用未知字段、缺少原文证据或超出受支持谓词却被当作结构化条件；
- FIELD 引用使用错误方向 catalog；
- Template Standard projection 的 required、length 或 dataType 与绑定 Standard 不一致；
- binding kind 与 Standard/Parse Field 结构不相容，或 `COLLECTION_ITEM` 的 target 不是 List；
- Node/Object 被纳入 ASSEMBLY omission coverage，或具有 XML Key 的容器缺少适用结构绑定/key expressions；
- Function 参数位置、必填性、String 类型或引用种类与 catalog 不符；
- MAPPING/Replacement 引用未知或重复的 `mappingRuleName`；
- Final Template 引用 `redacted: true` 的 Mapping rule；
- MAPPING 使用非 FIELD_REF 输入、配置多个规则或完整值未匹配；
- Replacement 配置多个规则或没有在 Value Expression 后执行；
- `FIXED_VALUE` 同时配置 LITERAL 与 SECURE_INPUT_REF、缺少 payload，或安全引用携带真实值；
- 实现者为除已确认 `STANDARD_1` 之外的未知 processing policy 或 Parse Field coverage 添加默认值。
