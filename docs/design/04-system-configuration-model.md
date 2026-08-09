# 接口标准与接口模板模型设计

## Status

Draft. Logical contract confirmed; `configuration-rules/v1` is released and immutable, and machine wire schemas are now P0-T3 implementation work.

## 1. 目的与边界

目标系统配置分为两个有顺序的模型：

- InterfaceStandardIR 定义报文字段格式和层级结构。
- InterfaceTemplateIR 定义一份模板如何按方向连接系统字段与已确认 Standard Field，并进行取值和处理。

两者不包含连接、认证、证书、部署、目标系统 API、Import JSON 或全量系统配置。SchemaIR 继续保存银行原始事实，目标配置不得回写覆盖 SchemaIR。

## 2. 生命周期与身份

### 2.1 Interface Standard

```mermaid
stateDiagram-v2
    [*] --> Draft: LLM 基于 Final SchemaIR 与规则版本生成
    Draft --> DraftValidated: Standard Validator 生成 Draft Result
    DraftValidated --> Draft: 修正结构或事实
    DraftValidated --> FinalCandidate: Human 完成 Review 与 Final metadata
    FinalCandidate --> Draft: Review 修改导致候选失效
    FinalCandidate --> FinalValidated: Standard Validator 复验完整内容
    FinalValidated --> Final: hash 匹配且 finalEligible
    Final --> [*]
```

每个标准由 `standardId + standardVersion` 唯一标识，并属于一个 `interfaceCode + direction`。Final 版本不可原地覆盖；canonical 内容摘要用于防止模板错误绑定同名但不同内容的标准。

### 2.2 Interface Template

```mermaid
stateDiagram-v2
    [*] --> Draft: LLM 基于 Final Standard 与规则版本生成
    Draft --> DraftValidated: Template Validator 生成 Draft Result
    DraftValidated --> Draft: 修正结构或事实
    DraftValidated --> FinalCandidate: Human 完成 Review 与 Final metadata
    FinalCandidate --> Draft: Review 修改导致候选失效
    FinalCandidate --> FinalValidated: Template Validator 复验完整内容
    FinalValidated --> Final: hash 匹配且 finalEligible
    Final --> [*]
```

每份模板由 `templateId + templateVersion` 唯一标识，属于一个 `interfaceCode + direction`，并精确引用 `standardId + standardVersion + contentHash`。

一个标准可以被多份同方向模板复用。新增模板直接消费已有 Final Standard；标准发布新版本不会自动迁移或重新解释旧模板。

## 3. InterfaceStandardIR

### 3.1 逻辑结构

```text
InterfaceStandardIR
├── standardId
├── interfaceCode
├── direction
├── standardVersion
├── schemaIrReference + schemaIrContentHash
├── rulePackageVersion
├── xmlEncodingReference         # 指向 SchemaIR message；不是 Standard Field
├── fields[]
│   ├── fieldId
│   ├── sequence
│   ├── fieldName / fieldDescription
│   ├── parentPath / fullPath
│   ├── required
│   ├── lengthLimit
│   ├── illegalCharacters
│   ├── xmlKeys[]
│   ├── regex
│   ├── dataType
│   ├── conditionalConstraints[]
│   └── evidence / differences / review
└── review
```

这些字段描述逻辑契约，不是已经冻结的 JSON wire schema。

方向级 XML encoding 和显式 evidence 保存在 Final SchemaIR message。InterfaceStandardIR 只保存可追溯引用，Workbook `Overview` 展示确认值；encoding 不生成 Standard Field。`UNRESOLVED_CONFLICT` 必须产生 blocking Warning，不能由 Generator 选择；Human Review 处置 evidence 或给出新确认值并重新复验后才能继续。

### 3.2 Path 与层级

目标系统配置的 Path 是当前字段的父路径：

| Field | Data Type | Parent Path | Full Path |
|---|---|---|---|
| `Document` | `Object` | `Root` | `Root.Document` |
| `pain.001.001.02` | `Object` | `Root.Document` | `Root.Document.pain.001.001.02` |
| `MsgId` | `String` | `Root.Document.pain.001.001.02.GrpHdr` | `Root.Document.pain.001.001.02.GrpHdr.MsgId` |
| `PmtInf` | `Node` | `Root.Document.pain.001.001.02` | `Root.Document.pain.001.001.02.PmtInf` |

`parentPath + fieldName` 用于解释层级；`fullPath` 用于唯一定位和审计。模板不得使用可能产生歧义的显示名称引用标准字段，而必须使用 stable `fieldId`。

同一父节点下使用 `sequence` 保存 XML 输出顺序。sequence 必须是唯一、连续的正整数，不能依赖 JSON object 属性顺序或 Workbook 当前行号。

### 3.3 数据类型

| 类型 | XML 语义 |
|---|---|
| `String` | 字符串叶子。 |
| `Boolean` | 布尔叶子。 |
| `Date` | 日期叶子；具体格式保留规则依据。 |
| `Number` | 数值叶子。 |
| `Node` | 可重复出现的无值容器节点。 |
| `Object` | 不可重复的无值容器节点。 |
| `List` | JSON-only；当前 XML Final Standard 禁止使用。 |

容器类型可根据 Final SchemaIR 的 children、value 和 occurs 确定。标量类型或 Date 格式信息不足时必须标记 `UNKNOWN`，不得依据相近字段名猜测。

### 3.4 XML Keys

XML attribute 在 SchemaIR 中仍是独立银行报文事实；目标系统接口标准不为它创建独立字段行，而把名称挂在所属 element 的 `xmlKeys` 中，例如：

```text
fieldId: document-field
fieldName: Document
xmlKeys: [@version, @locale]
```

XML Keys 必须能追溯到 SchemaIR attribute。key 的值不属于接口标准，由绑定模板中的 XML Key Value Expression 定义。

### 3.5 约束与差异

Required、Length Limit、Illegal Characters、Regex 和 Data Type 是目标系统实际接口标准配置；SchemaIR 中的对应值仍保留为银行原始事实。

可能缺失的约束使用三态语义：

| 状态 | 含义 | 是否允许 Final |
|---|---|---|
| `VALUE` | 有明确配置值。 | 是。 |
| `NO_CONSTRAINT` | 人工确认无该约束。 | 是。 |
| `UNKNOWN` | 尚无法确定。 | 否。 |

SchemaIR 与 Standard 值不一致时必须记录：

- SchemaIR source reference 和原值；
- Standard 配置值；
- Difference Reason；
- Rule References；
- confidence / uncertain reason；
- 人工 Review 结论。

银行字段、路径、出现次数和约束由 raw-doc/Final SchemaIR 决定；正式导出只证明目标系统配置形态。当前已确认范围内，raw-doc 没写的约束投影为 `NO_CONSTRAINT`，证据冲突或无法判断时为 `UNKNOWN`。b2e0061 Final Standard 保留 `@security`、排除 `vamflag`；正式导出 observed `@lang` 只保留在来源和 Review 证据中，不作为 Final SchemaIR 或 Standard 字段。

银行文档明确的条件 required 与基础 `required` 分开保存。P0 条件结构包含 controlling field reference、`EQUALS | IS_EMPTY`、可选 literal、target field reference、`REQUIRED` effect、银行原文 evidence 和 Review。Validator 校验结构与引用，但不执行条件。

## 4. InterfaceTemplateIR

### 4.1 逻辑结构

```text
InterfaceTemplateIR
├── templateId
├── interfaceCode
├── direction
├── templateVersion
├── standardRef
│   ├── standardId
│   ├── standardVersion
│   └── contentHash
├── rulePackageVersion
├── fieldConfigs[]
│   ├── bindingKind               # VALUE | STRUCTURE_ONLY | COLLECTION_ITEM
│   ├── standardFieldRef          # ASSEMBLY target；PARSE source
│   ├── standardProjection        # required / length / dataType 的显式镜像
│   ├── parseTarget?              # PARSE ref/name/path/dataType
│   ├── valueExpression?          # 仅 VALUE 标量绑定
│   ├── xmlKeyExpressions{}
│   ├── processingPolicies
│   └── evidence / review
├── omissions[]
└── review
```

### 4.2 方向性绑定与 omission

ASSEMBLY 的标量 `fieldConfigs` 以 Standard Field 为 target，是标准标量字段集合的子集。同一 target `standardFieldRef` 最多出现一次；缺失字段不是自动错误，也不生成空模板行。

Template Validator 为每个未覆盖的 ASSEMBLY 标量 Standard Field 产生 `MISSING_TEMPLATE_FIELD` Warning 和 omission candidate。omission 至少包含：

- Standard Field Reference；
- Omission Reason；
- Review Disposition；
- Review Note；
- reviewer / reviewed-at 等审计信息的候选位置。

未确认 omission 阻止 Final Template。人工确认该业务场景确实不需要字段后，omission 允许进入 Final，并继续显示在 Workbook Warnings。

Node/Object 不参加 ASSEMBLY omission coverage。容器只有在需要配置 XML Key 或承载明确结构绑定时才创建结构行：普通容器使用 `STRUCTURE_ONLY`，Parse collection source 使用 `COLLECTION_ITEM`。缺少必需的 XML Key expression 是配置错误，不是 omission。

必须区分：

- omission：没有模板行，不配置该字段；
- `EMPTY`：存在模板行，字段明确取空值；
- Empty Handling：存在源值为空时的处理策略。

PARSE 的 target 是固定 Parse Field；Value Expression 的 FIELD_REF 引用绑定 Standard 的银行 source field，也可以使用 literal、function 或 CONCATENATE。Parse Field Catalog 定义最终 JSON/Java 对象的 name、path 和 datatype，不属于银行 Standard。Validator 只检查实际配置的 target；未配置 Parse Field 默认不产生 omission 或 warning，也不推断为代码赋值字段。

三种结构绑定含义：

- `VALUE`：标量值绑定；
- `STRUCTURE_ONLY`：Node/Object 结构或 XML Key 配置，不包含字段值表达式；
- `COLLECTION_ITEM`：PARSE 每个重复 Standard Node 创建一个 Parse List 元素。

b2e0061 的请求 `b2e0061-rq` 按 `1..1000`、响应 `b2e0061-rs` 按 `0..1000` 建模为 `Node`。`b2e0061-rs -> paymentLineList` 使用 `COLLECTION_ITEM`，其子字段写入当前列表元素；Standard source 的 `Node` 与 Parse target 的 `List` 必须分别保存和展示。

每个 field config 都显式保存 `standardProjection.required/length/dataType`。这三个值完整镜像所绑定 Final Standard 的状态和值，不是 Template 覆盖项；任一不一致必须由 Validator 拒绝。

### 4.3 Value Expression

String、Boolean、Date、Number 标量 field config 必须具有一个字段值表达式。`Node`、`Object` 是无值容器，不具有字段值表达式；Validator 必须拒绝容器 field config 中出现 `valueExpression`。容器仍可保存适用的 Processing Policies，并按 4.4 节配置 XML Key Expressions。

| Mode | 语义 | 必要内容 |
|---|---|---|
| `FIXED_VALUE` | 使用固定 payload。 | `LITERAL` 或 `SECURE_INPUT_REF` 二选一。安全输入只保存引用标识，不保存真实值。 |
| `EMPTY` | 表达式明确取空值。 | 无。 |
| `FIELD` | 使用 catalog 中的业务字段。 | Field reference。 |
| `FUNCTION` | 调用 catalog 中的 function。 | Function reference；输入、参数和输出均为 String，参数只允许 FIELD reference 或 literal。 |
| `MAPPING` | 使用预设规则对完整 FIELD String 精确查表。 | 一个 FIELD reference、一个全局唯一 `mappingRuleName` 和 Rule Reference；未匹配报错。 |
| `CONCATENATE` | 按顺序组合子表达式。 | 一个或多个有序子表达式，可递归。 |

只有 `CONCATENATE` children 允许递归 Value Expression。ASSEMBLY 和 PARSE 使用同一表达结构，但端点相反：ASSEMBLY 从系统数据形成银行 Standard Field；PARSE 从银行 Standard Field 形成固定 Parse Field。

### 4.4 XML Key Expressions

若标准字段存在模板行，则标准定义的每个 XML Key 必须恰好具有一个独立 Value Expression。标量字段值表达式与 XML Key 表达式共享六种 Mode，但使用不同 Scope。Node/Object 没有字段值表达式，但不影响其 XML Key 使用这些 Mode。

```text
standardFieldRef: document-field
fieldValueExpression: ...
xmlKeyExpressions:
  @version: FIXED_VALUE("1.0")
  @locale: FIELD(<catalog-field-ref>)
```

引用标准未定义的 key 或缺少已定义 key 均为 Validator error。若整个字段具有已确认 omission，其 keys 随字段一起省略。

### 4.5 Processing Policies

模板行保存转换和赋值阶段的处理策略：

- Empty Handling；
- Overlength Handling；
- Row Limit；
- Chinese Character Length；
- 一个 Replacement `mappingRuleName`。

Template 不覆盖 Standard 约束；但每个配置行必须以 `standardProjection` 显式镜像绑定 Standard 的 Required、Length Limit 和 Data Type，用于确定性校验与 Workbook 展示。Illegal Characters 与 Regex 仍只保存在 InterfaceStandardIR。

Empty Handling 支持 `BLANK`（空值报送）与 `DELETE`（删除栏位）。Overlength 支持 `INTERCEPT`（校验失败）、`TRUNCATE_FRONT`（保留前部）、`OVERLONG_LINE_BREAK`（超长换行）和 `TRUNCATE_BACK`（保留后部）。Row Limit 是该栏位允许出现的行数，必须为正整数。Chinese Character Length 使用 `STANDARD_1..6`，默认值为 `STANDARD_1`，具体字符权重来自规则包。

Replacement 在 Value Expression 后处理结果 String：每个 field config 最多引用一个全局唯一 `mappingRuleName`；命中片段替换为 target，空 target 删除片段，未命中内容保留。MAPPING 与 Replacement 共用 `mappings.yaml`，但匹配边界与 unmatched 行为不同。

## 5. Validator 边界

Standard Validator 必须校验：

- identity、direction、SchemaIR 和规则版本引用；
- fieldId、parent/full path、sequence 与层级；
- Node/Object/标量类型和 XML-only 限制；
- XML Keys 与 SchemaIR attribute 的对应关系；
- 约束状态和 SchemaIR/Standard 差异记录；
- 银行条件引用、operator/effect、literal 和 evidence；
- 所有 Final 决定均已完成人工 Review。

Template Validator 必须校验：

- standard ID、version 和 content hash 精确匹配；
- 每个 `standardProjection.required/length/dataType` 与 Final Standard 完全一致；
- `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM` 与方向、Standard 类型和 Parse target 相容；
- ASSEMBLY target Standard Field reference 存在且不重复；
- PARSE target Parse Field reference 存在、path/datatype 与 catalog 相容，表达式内 Standard FIELD_REF 存在；
- 表达式结构、递归顺序和 catalog 引用；
- String/Boolean/Date/Number field config 必须有字段值表达式，Node/Object field config 不得有字段值表达式；
- XML Key expressions 完整且无未知 key；
- 每个缺失 ASSEMBLY 标量 Standard Field 都有 omission Warning；Node/Object 不参加 omission coverage，未配置 Parse Field 不自动产生 coverage issue；
- 有 XML Key 或结构绑定需求的容器必须有适用结构行和完整 key expressions；
- FIXED_VALUE payload 只允许 `LITERAL | SECURE_INPUT_REF`，且安全引用不得包含真实值；
- 每个 Final omission 已记录原因和接受结论；
- uncertain、规则冲突或未确认配置不能成为 Final。

Validator 不能判断 function、具体 Mapping 选择、目的系统业务 Condition 或 omission 是否符合业务语义；这类决定必须由人工 Review。Validator 仍必须确定性校验 Function/MAPPING/Replacement 的 catalog 引用、String 类型、单规则基数和执行结构；Template Condition 不属于 P0。

Mapping catalog 中标记 `redacted: true` 的规则只允许验证结构与 Workbook 表达，Final Template 必须拒绝引用，防止 `<REDACTED>` 成为可执行 target。

## 6. Final 条件

Final InterfaceStandardIR 必须满足：

- Standard Validator 通过且结果与当前内容匹配；
- 不含 `UNKNOWN` 约束；
- 差异和推导均有规则依据与人工结论；
- 银行条件具有有效引用、证据和人工结论；
- 标准身份和版本已冻结。

Final InterfaceTemplateIR 必须满足：

- Template Validator 通过且结果与当前内容匹配；
- 绑定的 Final Standard identity/version/hash 精确匹配；
- 所有适用的标量字段值和 XML Key expression 引用有效，Node/Object 不包含字段值表达式；
- 每个未覆盖 ASSEMBLY 标量 Standard Field 都有已确认 omission；Node/Object 不产生 omission，PARSE 只要求实际配置目标合法；
- function、MAPPING、Replacement 和其他 P0 业务语义已人工确认；Template Condition 不得进入 P0 Final；
- 模板身份和版本已冻结。

标准、模板或规则版本变化后，旧校验结果失效。不得通过原地覆盖 Final artifact 绕过迁移和重新 Review。
