# DocIR / SchemaIR / ConfigIR 设计

## Status

Draft. DocIR / SchemaIR 的 P0-T2 baseline 已反映在 b2e0061 Review Golden sample；ConfigIR wire schema 受真实 catalog blocker 约束，尚未冻结。

## 1. 设计原则

三层 IR 的职责不同：

- `DocIR` 是适合 LLM 和 Human Review 的强结构化 Markdown，负责稳定呈现 raw document 中的章节、字段表、条件、示例和 review 信息。
- `SchemaIR` 是可机器校验、可人工 Review 的标准化报文模型，负责表达银行 XML 报文的 element、attribute、path、父子层级、类型和银行原始约束。
- `ConfigIR` 是可机器校验、可人工 Review 的系统配置模型，负责表达目标系统对 SchemaIR 字段的取值和处理策略。
- `review-notes.md` 是面向人的 Review 入口，每次 DocIR / SchemaIR / ConfigIR Draft 生成都应产出，用于汇总低置信、推导、冲突、差异和人工确认项。

Raw doc 仍表示受控输入源。本次 `b2e0061` 样例以人工修正后的 `raw-doc.md` 作为正确 source；正常流程中不应在转换阶段静默改写 raw doc。

“标准化”表示项目内部统一表达，不表示行业标准、XSD 或 JSON Schema。当前只承诺 XML 银行报文；SchemaIR 和 ConfigIR 使用 JSON 序列化不等于支持 JSON 银行报文。

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
| 2.3 |  | 　`b2e0061-rq` | [0..1000] | Object | Y | 转账请求内容 | 不超过1000笔 |  | 最小出现次数需确认。 |
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

SchemaIR 使用 JSON。`Final SchemaIR` 是银行 XML 报文结构与银行原始约束的事实源。Workbook Generator 还必须读取通过校验并经人工确认的 Final ConfigIR；SchemaIR 不承载目标系统配置。

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
- `Root.bocb2e.@locale` 或 observed `Root.bocb2e.@lang`
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
  "description": "组装请求报文",
  "fields": []
}
```

`functionType` 枚举：

- `ASSEMBLY`：组装请求报文。
- `PARSE`：处理响应报文。

当前 `messageFormat` 只允许 `XML`。JSON 银行报文属于未验证的 future candidate。

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

目标系统配置指导不属于 SchemaIR 字段；它由 ConfigIR 表达。

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

## 4. ConfigIR

### 4.1 职责边界

ConfigIR 回答“当前目标系统应如何配置这个报文字段”。它只覆盖字段取值与处理策略，不覆盖连接、认证、证书、部署或全量系统配置。

Final SchemaIR 与 Final ConfigIR 是两个独立事实源：

- SchemaIR 保存银行原始 required、length、occurs 和 condition。
- ConfigIR 保存目标系统实际 configured required、configured length、取值方式和处理策略。
- 两侧值不得相互覆盖。存在差异时，ConfigIR 必须记录原因、Rule ID 和人工 Review 结论，并进入 Workbook `Warnings`。

ConfigIR 的详细生命周期、递归表达式、策略和 Validator 边界见 `docs/design/04-system-configuration-model.md`。

### 4.2 候选顶层结构

下例只表达逻辑契约，不是已冻结 wire schema：

```json
{
  "interfaceCode": "b2e0061",
  "schemaIrRef": "schemair-final.json",
  "rulePackageVersion": "v1",
  "directions": [],
  "review": {
    "status": "PENDING"
  }
}
```

`rulePackageVersion` 必须精确指向 `configuration-rules/` 中已发布版本。当前 `v1` catalog 尚未提供，因此不得创建带占位业务标识的 Final ConfigIR。

### 4.3 方向与字段配置

`ASSEMBLY` 和 `PARSE` 使用同一字段配置结构。每个字段配置必须引用一个存在的 SchemaIR `path`，并包含：

- 递归 Value Expression；
- Configured Required；
- Empty Handling；
- Overlength Handling；
- Configured Length；
- Row Limit；
- Chinese Character Length；
- Illegal Characters；
- 有序 Replacement Rules；
- Rule References；
- confidence、uncertain、uncertainReason；
- 与 SchemaIR 差异的 Difference Reason；
- 人工 Review 结论。

字段、function 和 mapping 引用必须来自规则包 catalog。缺少引用或无法确认业务语义时，该项保持未确定，整个 ConfigIR 不能进入 Final。

### 4.4 取值表达式

允许模式：

- `FIXED_VALUE`
- `EMPTY`
- `FIELD`
- `FUNCTION`
- `MAPPING`
- `CONCATENATE`

`CONCATENATE` 按顺序包含任意模式的子表达式，并允许递归。`EMPTY` 表示该表达式取固定空值，不等同于字段值为空时的 Empty Handling。

## 5. Validator 边界

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

ConfigIR Validator 还必须校验：

- SchemaIR path 引用存在；
- Value Expression 结构、递归关系和顺序合法；
- Rule ID 属于指定规则版本；
- FIELD、FUNCTION 和 MAPPING 引用存在于 catalog；
- required/length 等差异具有 Difference Reason 和 Rule Reference；
- uncertain、未映射、规则冲突或未完成人工 Review 的配置不能成为 Final。

ConfigIR Validator 只校验结构、引用和确定性 invariant，不能代替人工判断 function 或 mapping 是否符合业务语义。

## 6. Workbook Generator 输入边界

Workbook Generator 只能读取：

- `Final SchemaIR`
- `Final ConfigIR`
- `schemair-validation-result.json`
- `configir-validation-result.json`
- 指定的 configuration-rules 版本
- 任务上下文，例如生成时间和源文件名

Workbook Generator 不允许：

- 反向解析 Excel 作为事实源。
- 根据目标系统导入模板补业务字段。
- 临时推断 Value Mode、Rule ID 或 catalog 引用。
- 静默丢弃 `uncertain=true`、未映射、规则冲突或差异字段。
- 把条件必填字段强行改成普通必填字段。

Envelope/head 字段应并入 `ASSEMBLY` 和 `PARSE` 字段 sheet，再接各自交易消息字段。不新增独立 `ENVELOPE` sheet。

## 7. 历史导出 JSON 边界

`docs/reference/samples/b2eboc/b2e0061-assembly.json` 和 `b2e0061-parse.json` 只能作为人工 review 对照：

- 不作为 SchemaIR 字段来源。
- 不进入 expected SchemaIR。
- 不作为 golden regression 输入。
- 不引入历史 ID、parent ID、approvalStatus、configStatus 或目标系统导入字段。
