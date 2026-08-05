# DocIR / SchemaIR / InterfaceStandardIR / InterfaceTemplateIR 设计

## Status

Draft. DocIR / SchemaIR 的 P0-T2 baseline 已反映在 b2e0061 Review Golden sample；`configuration-rules/v1` Draft 已提供，InterfaceStandardIR / InterfaceTemplateIR wire schema 进入 P0-T3 实现但尚未冻结。

## 1. 设计原则

四层 IR 的职责不同：

- `DocIR` 是适合 LLM 和 Human Review 的强结构化 Markdown，负责稳定呈现 raw document 中的章节、字段表、条件、示例和 review 信息。
- `SchemaIR` 是可机器校验、可人工 Review 的标准化报文模型，负责表达银行 XML 报文的 element、attribute、path、父子层级、类型和银行原始约束。
- `InterfaceStandardIR` 是可机器校验、可人工 Review 的接口标准模型，负责表达目标系统实际配置的银行报文字段格式、层级和银行条件约束。
- `InterfaceTemplateIR` 是可机器校验、可人工 Review 的接口模板模型，负责表达 ASSEMBLY 的系统字段到银行标准字段、PARSE 的银行标准字段到固定 Parse Field 的取值和处理。
- `review-notes.md` 是面向人的 Review 入口，每次 IR Draft 生成都应产出，用于汇总低置信、推导、冲突、差异、omission 和人工确认项。

Raw doc 仍表示受控输入源。本次 `b2e0061` 样例以人工修正后的 `raw-doc.md` 作为正确 source；正常流程中不应在转换阶段静默改写 raw doc。

“标准化”表示项目内部统一表达，不表示行业标准、XSD 或 JSON Schema。当前只承诺 XML 银行报文；IR 使用 JSON 序列化不等于支持 JSON 银行报文。

## 2. DocIR

### 2.1 职责

- 保留原始文档中的字段表、章节结构、XML 示例和条件说明。
- 清洗 Markdown 格式噪声，使字段表稳定可读。
- 在 `Interface`、`Envelope`、`Message: ASSEMBLY`、`Message: PARSE` 中用 metadata 表格表达关键上下文。
- 标记无法确认、由规则推导或需要人工检查的位置。

### 2.2 非职责

- 不作为最终业务语义模型。
- 不生成 Configuration Workbook。
- 不表达目标系统导入 JSON、历史 ID、父子 ID 或配置状态。
- 不把复杂条件转换为正式 DSL。

### 2.3 Metadata 结构

`Interface`、`Envelope` 和每个 `Message` 必须使用 `## Metadata` 表格，而不是把多个 key/value 写成连续散行。

```md
# Interface

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Interface Code | b2e0061 |  |
| Interface Name | 公对私转账汇款 |  |
| Message Format | XML |  |
| Version | 120 | raw doc 示例也出现 100，需确认。 |
| Source Document | samples/golden/b2eboc-b2e0061/raw-doc.md |  |
```

```md
# Envelope

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Root Path | Root.bocb2e |  |
| Head Path | Root.bocb2e.head | 可复用 BOCB2E head。 |
| Body Path | Root.bocb2e.trans | 交易消息容器。 |
```

### 2.4 Message 结构

```md
# Message: ASSEMBLY

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Function Type | ASSEMBLY |  |
| Message Name | b2e0061-rq |  |
| Root Path | Root.bocb2e.trans.trn-b2e0061-rq |  |

## Description

...

## Fields

| Index | Or | Message Item | Mult. | Type | Required | 说明 | 前置机校验点/格式 | 接口平台校验点 | Review |
|---|---|---|---|---|---|---|---|---|---|
| 2 |  | `trn-b2e0061-rq` | [1..1] | Object | Y | 转账交易请求 |  |  | 交易包装节点。 |
| 2.1 |  | 　`ceitinfo` | [0..1] | String | N | 数字签名 |  | 该标签由前置机自动添加，企业无需上送 | 是否进入可配置字段需确认。 |
| 2.2 |  | 　`transtype` | [0..1] | String | N | 交易类型 | 不超过1位数字；可空 | 1 委托待授权；2 授权退回修改；非空只能为1或2 |  |
| 2.3 |  | 　`b2e0061-rq` | [0..1000] | Node | Y | 转账请求内容 | 不超过1000笔 |  | 每次出现表示一个重复交易元素。 |
| 2.3.1 |  | 　　`insid` | [1..1] | String | Y | 指令ID；客户端唯一标识 | 非空字符串；长度1-32 | 客户号下不能重复；不支持中文 |  |
```

`Message Item` 存 XML item name，不带尖括号；XML attribute 使用 `@version` 形式。DocIR 字段主表不展示完整 `path`，避免人工 review 表过宽；完整 path 属于 SchemaIR 字段对象。`Index` 是结构编号而不是行号：同级递增最后一段，子节点追加一段，例如 `2.3` 的子节点从 `2.3.1` 开始；`Message Item` 前的缩进必须与 `Index` 层级一致。

### 2.5 Review 要点

- 字段表是否完整，列是否错位，字段是否遗漏。
- Message Item 层级是否能正确还原 XML 树；推导 path 是否能在 SchemaIR 中对应。
- 请求组装和响应处理是否正确区分为 `ASSEMBLY` / `PARSE`。
- 可复用 envelope/head 字段是否被保留。
- 条件说明、枚举、长度冲突和平台/前置机约束是否保留。

## 3. SchemaIR

SchemaIR 使用 JSON。`Final SchemaIR` 是银行 XML 报文结构与银行原始约束的事实源。目标系统接口标准与接口模板分别由后续 IR 表达；SchemaIR 不承载目标系统配置。

### 3.1 顶层结构

```json
{
  "interfaceCode": "b2e0061",
  "interfaceName": "公对私转账汇款",
  "messageFormat": "XML",
  "version": "120",
  "sourceDocument": "samples/golden/b2eboc-b2e0061/raw-doc.md",
  "envelope": {},
  "messages": []
}
```

顶层 `version` 可保留当前候选值，便于 Overview 展示；如果 version 存在不确定性，必须在 `envelope.fields` 中的属性字段表达，例如 `Root.bocb2e.@version`。

### 3.2 Envelope 结构

`envelope` 表达可复用 BOCB2E XML envelope，不归入 `messages`。

```json
{
  "rootPath": "Root.bocb2e",
  "description": "BOCB2E XML envelope",
  "fields": []
}
```

`envelope.fields` 至少覆盖：

- `Root.bocb2e`
- `Root.bocb2e.@version`
- `Root.bocb2e.@security`
- `Root.bocb2e.@locale`
- `Root.bocb2e.head`
- `Root.bocb2e.head.termid`
- `Root.bocb2e.head.trnid`
- `Root.bocb2e.head.custid`
- `Root.bocb2e.head.cusopr`
- `Root.bocb2e.head.trncod`
- `Root.bocb2e.head.token`
- `Root.bocb2e.trans`

### 3.3 Message 结构

`messages` 只表达接口交易消息，不重复定义 envelope 对象。

```json
{
  "functionType": "ASSEMBLY",
  "messageName": "b2e0061-rq",
  "rootPath": "Root.bocb2e.trans.trn-b2e0061-rq",
  "xmlEncoding": "UTF-8",
  "description": "组装请求报文",
  "fields": []
}
```

`functionType` 枚举：

- `ASSEMBLY`：组装请求报文。
- `PARSE`：处理响应报文。

当前 `messageFormat` 只允许 `XML`。JSON 银行报文属于未验证的 future candidate。

`messages[].xmlEncoding` 保存该方向 XML 报文的 Final encoding。raw-doc、XML 声明或其他证据出现冲突时必须进入 Review；确认值只展示在 Workbook `Overview`，不得伪造一个 Interface Standard 字段。上例的 `UTF-8` 仅说明 wire 形态；b2e0061 raw-doc 同时出现 UTF-8 建议和 GB2312 示例，两个方向的 Final 值必须在后续 SchemaIR fixture Review 时分别确认。

实现同步说明：当前已实现的 SchemaIR Validator v1 仍接受早期 `JSON` 和 JSON node kind 枚举。该行为不构成产品能力，后续代码批次必须按本契约收紧；本次文档调整不修改代码或测试。

### 3.4 字段结构

`envelope.fields` 和 `message.fields` 使用同一字段结构。

```json
{
  "path": "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.acttyp",
  "fieldName": "acttyp",
  "displayName": "收款账户类型",
  "parentPath": "Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn",
  "level": 6,
  "nodeKind": "XML_ELEMENT",
  "dataType": "string",
  "format": null,
  "length": {
    "max": 3,
    "min": 0,
    "raw": "0-3"
  },
  "required": false,
  "multiple": false,
  "hasChildren": false,
  "occurs": "0..1",
  "description": "收款账户类型",
  "conditionText": null,
  "sourceText": "| <acttyp> | 收款账户类型 | 数码 长度0-3 | ... |",
  "evidence": {
    "kind": "DIRECT",
    "note": "字段名、说明和长度来自同一 raw-doc 字段行。"
  },
  "confidence": 0.95,
  "uncertain": false,
  "uncertainReason": null,
  "reviewNote": null
}
```

`conditionText` 保留银行原始条件说明。银行文档明确、无歧义且落在规则包支持范围内的跨字段条件还需要形成结构化 `conditionalConstraints[]`，至少包含 controlling field path、operator、literal（适用时）、target field path、effect、sourceText/evidence 和人工 Review。P0 只支持 `EQUALS`、`IS_EMPTY` 与 `REQUIRED`；复杂条件继续保留文本，不强行转换。

目标系统配置指导不属于 SchemaIR 字段；它由 InterfaceStandardIR 与 InterfaceTemplateIR 分层表达。正式导出中 observed `@lang` 只作为 SchemaIR evidence/difference Warning 保留，不进入 b2e0061 Final Standard。该 Standard 以银行文档为准保留 `@security`，排除正式导出中的 `vamflag`。

### 3.5 nodeKind 枚举

- `XML_ELEMENT`
- `XML_ATTRIBUTE`
- `SCALAR`

XML attribute 必须作为字段建模，例如：

```json
{
  "path": "Root.bocb2e.@version",
  "fieldName": "version",
  "nodeKind": "XML_ATTRIBUTE"
}
```

### 3.6 dataType 枚举

- `string`
- `integer`
- `decimal`
- `boolean`
- `date`
- `datetime`
- `object`
- `array`

银行账号、联行号、币种、交易代码、流水号和枚举代码即使原文写“数码/数字”，也默认使用 `string`，避免丢失前导零或编码语义。

### 3.7 evidence

`evidence.kind` 枚举：

- `DIRECT`：字段名、约束或说明能从 raw doc 对应行直接得到。
- `DERIVED`：由表格层级、路径规则或字段上下文推导得到。
- `ASSUMED`：缺少明确证据但为保持结构完整而临时假设，必须设置 `uncertain=true`。

`sourceText` 仍保存展示给 human reviewer 的字段行级证据；`evidence` 说明该字段值是直接证据、推导还是假设。

### 3.8 confidence 与 review 规则

| confidence | Review 级别 | 规则 |
|---|---|---|
| `>= 0.9` | 常规 | 直接证据充分，常规抽查。 |
| `0.7 - 0.89` | 注意 | 存在推导、冲突或局部缺失，需要 review。 |
| `< 0.7` | 重点 | 缺证据或影响配置正确性，必须优先 review。 |

无论 confidence 分值多少，只要 `uncertain=true`，都必须进入 `review-notes.md` 和 Workbook `Warnings`。

### 3.9 required / multiple 规则

| 原文 | SchemaIR |
|---|---|
| M / Mandatory / Required / 必输 / 非空 | `required=true` |
| O / Optional / 可选 / 可空 | `required=false` |
| C / Conditional / 条件必输 | `required=false`，并保留 `conditionText` |
| `1..n` / `0..n` / List / Array / Repeating / 多笔 | `multiple=true` |
| `1..1` / `0..1` / 空 | `multiple=false` |

容器节点如果必填性来自子字段而非原文，应使用 `evidence.kind="DERIVED"` 并降低 confidence。

## 4. InterfaceStandardIR

### 4.1 职责边界

InterfaceStandardIR 回答“目标系统如何定义这个方向的报文字段格式与层级”。它从 Final SchemaIR 派生，但不是 SchemaIR 的别名：

- SchemaIR 保存银行原始完整 path、attribute、occurs 和类型事实。
- InterfaceStandardIR 保存目标系统实际 parent path、Node/Object 类型、XML Keys 和配置约束。
- 两侧值不得相互覆盖；差异必须记录原因、Rule ID 和人工 Review 结论。

### 4.2 候选顶层结构

下例只表达逻辑契约，不是已冻结 wire schema：

```json
{
  "standardId": "internal-stable-id",
  "interfaceCode": "b2e0061",
  "direction": "ASSEMBLY",
  "version": "artifact-version",
  "schemaIrRef": "schemair-final.json",
  "schemaIrContentHash": "content-hash",
  "rulePackageVersion": "published-version",
  "fields": [],
  "review": {
    "status": "PENDING"
  }
}
```

每个方向拥有独立标准。Final Standard 版本不可原地覆盖；`interfaceCode` 只用于关联，不能替代 stable ID、version 和 content hash。

### 4.3 标准字段

每个标准字段至少包含：

- stable `fieldId`；
- `sequence`；
- `fieldName`、`fieldDescription`；
- `parentPath`、`fullPath`；
- Required、Length Limit；
- Illegal Characters；
- XML Keys；
- Regex；
- Data Type；
- SchemaIR source reference、Rule References、Difference Reason；
- 银行文档结构化条件约束及其 evidence；
- confidence、uncertain、uncertainReason 和人工 Review 结论。

目标系统 Path 表示父路径。`fullPath` 由 parent path 与当前字段身份构成，用于唯一定位和模板引用。XML attribute 继续存在于 SchemaIR，但在接口标准中作为所属 element 行的 XML Keys，不单独生成标准行。

同一 parent 下的 `sequence` 必须是唯一、连续的正整数，并保存 XML 输出顺序。Validator 不得依赖 JSON 数组当前物理顺序代替该约束。

### 4.4 数据类型与约束状态

XML 目标类型为 `String`、`Boolean`、`Date`、`Number`、`Node`、`Object`：

- 重复且无值的容器为 `Node`；
- 不重复且无值的容器为 `Object`；
- 有值叶子使用四种标量类型；
- JSON-only `List` 不得进入当前 XML Final Standard。

Length、Illegal Characters、Regex 等可能缺失的约束必须区分 `VALUE`、`NO_CONSTRAINT` 和 `UNKNOWN`。`UNKNOWN` 阻止 Final；人工确认无约束后使用 `NO_CONSTRAINT`，不能以普通 null 混淆两者。

在当前已确认范围内，raw-doc 没有写某项约束表示该项为 `NO_CONSTRAINT`；只有证据冲突或无法判定时才使用 `UNKNOWN`。不得从正式导出覆盖银行字段、路径、出现次数或约束事实。

基础 `required` 与条件 `required` 分开保存。例如 `obssid.required=false` 不覆盖 `transtype EQUALS "2" => obssid REQUIRED`。Standard Validator 校验条件引用、受支持 operator/effect、literal 类型和 evidence，不执行银行业务条件。

## 5. InterfaceTemplateIR

### 5.1 职责边界与标准绑定

InterfaceTemplateIR 回答“一份模板如何连接系统字段与已确认 Standard Field，并进行取值和处理”。它必须绑定一个 `standardId + standardVersion + contentHash`，不能自动解析到最新标准。

- ASSEMBLY：source 是 Value Expression，target 是 `standardFieldRef`。
- PARSE：target 是 `parseFieldRef`；Value Expression 中的 FIELD_REF 引用 `standardFieldRef`。

一个标准可以关联多份同方向模板。新增模板复用已有 Final Standard；标准版本变化不会静默改变已有模板。

### 5.2 候选顶层结构

```json
{
  "templateId": "internal-stable-id",
  "interfaceCode": "b2e0061",
  "direction": "ASSEMBLY",
  "version": "artifact-version",
  "standardRef": {
    "standardId": "internal-stable-id",
    "version": "artifact-version",
    "contentHash": "content-hash"
  },
  "rulePackageVersion": "published-version",
  "fieldConfigs": [],
  "omissions": [],
  "review": {
    "status": "PENDING"
  }
}
```

每个 `fieldConfig` 至少还包含：

- `bindingKind`: `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM`；
- `standardFieldRef`：ASSEMBLY target 或 PARSE source；
- `standardProjection.required/length/dataType`：绑定 Standard 的显式镜像；
- PARSE 时的 `parseTarget`：Parse Field ref/name/path/datatype；
- 标量绑定的 `valueExpression`，或容器绑定的 XML Key/collection 信息。

Template Validator 必须逐值比较 `standardProjection` 与所绑定 Final Standard；任一状态或值不一致均为 error。镜像用于 Workbook 展示和防止 Standard/Template 漂移，不允许 Template 覆盖 Standard。

### 5.3 方向性绑定与 omissions

ASSEMBLY 每条标量 `fieldConfig` 以一个存在的 `standardFieldRef` 为 target，同一模板中不得重复。未出现在 `fieldConfigs` 的 ASSEMBLY 标量 Standard Field 必须生成 omission candidate。每条 omission 至少保留：

- `standardFieldRef`；
- omission reason；
- Review disposition；
- reviewer / reviewed-at 等审计信息的候选位置。

未确认 omission 阻止 Final Template。人工确认有意省略后，模板可以 Final，但 omission 继续进入 Workbook `Warnings`。omission 不等同于 `EMPTY`，也不生成虚假模板行。

Node/Object 不参加 ASSEMBLY omission coverage。容器没有 XML Key 且不承担结构绑定时可以没有 Template 行；有 XML Key 或结构绑定需求时必须有适用结构行：普通容器使用 `STRUCTURE_ONLY`，Parse collection source 使用 `COLLECTION_ITEM`。缺失 key expression 是 XML Key error，不得伪装成 omission。

PARSE 每条 `fieldConfig` 以 Parse Field 为 target；Value Expression 中的 FIELD_REF 引用绑定 Standard 的银行 source field，也可使用 literal、function 或 CONCATENATE。Parse Field Catalog 是固定 JSON/Java 输出对象定义，不属于银行 Standard。Validator 只校验实际配置的 `parseFieldRef`、path 和 datatype；未配置 Parse Field 默认不产生 omission 或 warning，也不被推断为代码赋值字段。

`b2e0061-rq` 与 `b2e0061-rs` 都因 raw-doc `0..1000` 建模为 Standard `Node`。PARSE 中 `b2e0061-rs -> paymentLineList` 使用 `COLLECTION_ITEM`：每出现一个银行 `b2e0061-rs` Node，就创建一个 `paymentLineList(List)` 元素，子字段写入当前元素。Standard `Node` 与 Parse target `List` 是两端不同类型，不得压成同一 Data Type。

同一目标字段多行并按目的系统业务 Condition 选择是 future candidate；当前 Validator 拒绝 contract 之外的重复 target，不预留半实现 Template Condition 字段。银行文档明确条件属于 SchemaIR/InterfaceStandardIR，不属于此处。

### 5.4 取值表达式与 XML Keys

String、Boolean、Date、Number 标量字段的字段值和 XML Key 的值统一使用以下表达式模式：

- `FIXED_VALUE`
- `EMPTY`
- `FIELD`
- `FUNCTION`
- `MAPPING`
- `CONCATENATE`

FUNCTION 参数只允许 FIELD reference 或 literal；Function 输入、参数和返回值均为 String。`CONCATENATE` 按顺序包含任意模式的子表达式并允许递归，且只有其 children 可以递归 Value Expression。`EMPTY` 表示存在配置且明确取空值，不表示字段被省略，也不等同于 Empty Handling。

`SECURE_INPUT_REF` 不是第七种 Value Mode，而是 `FIXED_VALUE` 的 payload kind；它与 `LITERAL` 二选一。IR 只保存可安全解析的引用标识，不保存真实敏感值，Workbook 也只展示引用标识。

MAPPING expression 保存一个 String FIELD_REF 和一个全局唯一 `mappingRuleName`，不内联 entries。它对完整值精确匹配，未匹配必须报错。Replacement 不是 Value Expression：field config 在 Value Expression 完成后最多引用一个 `replacementRuleName`，命中片段替换为空 target 时删除，未命中内容保留。

标量 field config 必须具有一个字段值表达式。`Node`、`Object` 是无值容器，其 field config 不得具有字段值表达式；容器仍可保存适用的处理策略和 XML Key 表达式。

每个 field config 还可以表达 Empty Handling、Overlength Handling、Row Limit、Chinese Character Length、单一 Replacement Rule、Rule References 和 Review 信息。MAPPING 与 Replacement 均进入 P0 wire contract、Validator、Workbook 和专项 golden。

如果标准字段定义了 XML Keys，存在该字段模板行时，每个 key 必须具有独立 Value Expression。引用未知 key 或缺少表达式是错误；整个字段被确认省略时，其 keys 一并省略。

## 6. Validator 边界

SchemaIR Validator 必须校验：

- `interfaceCode` 非空。
- `messageFormat` 属于允许枚举。
- `envelope.fields` 至少包含可复用 BOCB2E root/head/trans 字段。
- `messages` 至少包含一个 message。
- `functionType` 属于允许枚举。
- 所有字段的 `path`、`fieldName`、`nodeKind`、`dataType`、`sourceText`、`evidence.kind` 非空。
- `required`、`multiple`、`hasChildren`、`uncertain` 是 boolean。
- `confidence` 在 0 到 1 之间。
- 同一字段集合内 `path` 不重复。
- 父子路径关系可解释。
- `hasChildren`、`multiple`、`dataType`、`nodeKind` 不存在明显冲突。

Validator 失败时必须返回字段级错误列表，不能只返回通用失败信息。

Standard Validator 还必须校验：

- parentPath、fullPath、fieldId、sequence 和 SchemaIR source reference 合法；
- Node/Object/标量映射与 SchemaIR 结构相容；
- XML 不使用 List；
- XML Keys 能追溯到 SchemaIR attribute；
- 差异具有原因、Rule Reference 和人工结论；
- 银行条件引用、operator/effect、literal 和 evidence 合法；
- `UNKNOWN` 约束不能成为 Final。

Template Validator 还必须校验：

- Standard identity、version 和 content hash 精确匹配；
- 每个 field config 的 `standardProjection.required/length/dataType` 与 Final Standard 完全一致；
- `bindingKind` 与方向、Standard 类型和 Parse target 相容；
- ASSEMBLY target Standard Field reference 存在且不重复；
- PARSE target Parse Field reference 存在、path/datatype 与 catalog 相容，表达式内 Standard FIELD_REF 存在；
- 标量字段值与 XML Key Value Expression 的结构、递归关系和顺序合法；
- String/Boolean/Date/Number field config 必须有字段值表达式，Node/Object field config 不得有字段值表达式；
- Rule ID、FIELD、FUNCTION 和 `mappingRuleName` 引用存在；Function 与 Mapping 数据类型为 String；
- MAPPING 只接受一个 FIELD_REF 和一个规则，完整值未匹配时报错；Replacement 只接受一个规则并在 Value Expression 后执行；
- `redacted: true` 的 Mapping rule 只用于结构验证，不能被 Final Template 引用；
- field config 存在时，XML Key expressions 完整且不包含未知 key；
- 所有缺失 ASSEMBLY 标量 Standard Field 均有 Warning 与 omission；Node/Object 不参加 omission coverage，未配置 Parse Field 不自动生成 coverage issue；
- 有 XML Key 或结构绑定需求的容器缺少适用结构行/key expression 时直接失败；
- FIXED_VALUE payload 只允许 `LITERAL | SECURE_INPUT_REF`，安全引用不得携带真实值；
- 未确认 omission、规则冲突或不确定配置不能成为 Final。

Validator 不能代替人工判断 function、mapping、目的系统业务 Condition 或场景性 omission 是否符合业务语义。

## 7. Workbook Generator 输入边界

Workbook Generator 只能读取：

- `Final SchemaIR`
- `Final InterfaceStandardIR`
- 选定的 `Final InterfaceTemplateIR`
- `schemair-validation-result.json`
- Standard / Template validation results
- Standard 与 Template 实际使用的 configuration-rules 版本
- 调用者显式指定的 Standard Action
- 任务上下文，例如生成时间和源文件名

Workbook Generator 不允许：

- 反向解析 Excel 作为事实源。
- 根据目标系统导入模板补业务字段。
- 临时推断 Value Mode、Rule ID 或 catalog 引用。
- 连接目标系统推断 Standard Action。
- 静默丢弃 `uncertain=true`、omission、规则冲突或差异字段。
- 把 omission 转换为 `EMPTY`。
- 把条件必填字段强行改成普通必填字段。

一份 Workbook 只包含一个方向标准和一份绑定模板。固定主 sheet 为 `Interface Standard` 与 `Interface Template`，不保留另一方向的空 sheet。`Value Expressions` 按 Expression Scope 分别展开标量字段值和 XML Key 的表达式树，不为 Node/Object 创建 FIELD_VALUE 表达式节点。

## 8. 正式导出 JSON 边界

`docs/reference/samples/b2eboc/` 中的四份 `b2e0061-*-standard.json` / `b2e0061-*-template.json` 是目标系统正式导出，可作为 b2e0061 Standard/Template 实际配置、processing policy 和 function 调用形态的证据，但必须经过规则包治理或 expected fixture 人工确认：

- 不作为 SchemaIR 字段来源。
- 不进入 expected SchemaIR。
- 不直接作为 IR、Workbook Generator 或 golden regression 输入。
- 不引入 database ID、parent ID、approvalStatus、configStatus 或目标系统导入 contract。
- 不把正式导出的目的系统业务 Condition 推导成通用规则。
