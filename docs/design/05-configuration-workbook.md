# Configuration Workbook 设计

## Status

Draft. Product contract confirmed; generation remains blocked by the unavailable `configuration-rules/v1` catalog and Final InterfaceStandardIR / InterfaceTemplateIR fixtures.

## 1. 目的与粒度

Configuration Workbook 是供配置人员使用的配置规格和执行清单，不是事实源，也不是目标系统可导入文件。

一份工作簿只服务一个方向模板：

```text
interfaceCode + direction + templateId + templateVersion
```

它携带该模板绑定的一份 Interface Standard 完整快照，不把 ASSEMBLY 与 PARSE 强行打包，也不包含同一标准的其他模板。

Generator 输入：

- Final SchemaIR；
- Final InterfaceStandardIR；
- 选定的 Final InterfaceTemplateIR；
- 与三份 Final 内容匹配的通过校验结果；
- Standard 与 Template 实际使用的精确 configuration-rules 版本；
- 调用者显式提供的 `Standard Action = CREATE | REUSE | UPDATE`；
- 生成时间等非业务任务上下文。

Workbook Generator 不得补字段、选择 Value Mode、猜测 Rule ID、判断目标系统是否已有标准或反向更新 Final IR。

## 2. 固定 Sheet

| Sheet | 用途 |
|---|---|
| `Overview` | 接口、方向、标准/模板身份、版本、Standard Action、规则版本、生成信息和校验摘要。 |
| `Interface Standard` | 当前模板绑定的一个方向标准完整快照和标准配置执行清单。 |
| `Interface Template` | 当前模板实际配置的标准字段子集和模板执行清单。 |
| `Value Expressions` | 将字段值与 XML Key 的 Value Expression 按树展开。 |
| `Warnings` | 差异、omissions、规则冲突、不确定项和 Validator issue。 |
| `Rule References` | 本工作簿实际使用的规则版本、Rule ID 和来源。 |
| `Legend` | 列、枚举、状态、颜色、空值和 omission 约定。 |

所有工作簿保持相同 sheet 名称和顺序。Direction 写入 `Overview` 和相关行，不通过动态 sheet 名表达。

## 3. Overview

`Overview` 至少记录：

- Interface Code；
- Direction；
- Standard ID / Version / Content Hash；
- Template ID / Version；
- SchemaIR / Standard / Template artifact references；
- SchemaIR / Standard / Template validation summaries；
- Standard / Template Rule Package Versions；
- Standard Action；
- 生成时间、生成器版本和交付状态。

Standard Action 的行为：

| Action | 含义 | Standard Sheet 行为 |
|---|---|---|
| `CREATE` | 目标环境需要新建该标准。 | 进入执行与验证清单。 |
| `REUSE` | 目标环境已存在同版本标准。 | 仅作只读核对快照，不要求重复配置。 |
| `UPDATE` | 配置人员需要按新标准版本更新。 | 进入执行与验证清单，并显示版本差异提示。 |

Generator 只展示调用者提供的 Action，不连接目标系统验证它是否真实。

## 4. Interface Standard

每个 InterfaceStandardIR field 一行，包括 Object、Node 和标量字段。XML attribute 不单独成行，显示在所属 element 的 XML Keys 列。

### 4.1 标准配置列

| 列 | 来源 | 含义 |
|---|---|---|
| `Field ID` | InterfaceStandardIR | 模板引用的稳定字段标识。 |
| `Sequence` | InterfaceStandardIR | 同一父节点下的 XML 顺序。 |
| `Field Name` | InterfaceStandardIR | 目标系统字段名称。 |
| `Field Description` | InterfaceStandardIR | 字段说明。 |
| `Parent Path` | InterfaceStandardIR | 目标系统实际配置的 Path。 |
| `Full Path` | InterfaceStandardIR | 包含当前字段名的完整定位路径。 |
| `Required` | InterfaceStandardIR | 目标系统接口标准的必填配置。 |
| `Length Limit` | InterfaceStandardIR | 配置值或明确的 `NO_CONSTRAINT`。 |
| `Illegal Characters` | InterfaceStandardIR | 配置列表或明确的 `NO_CONSTRAINT`。 |
| `XML Keys` | InterfaceStandardIR | 挂在该 element 上的 XML attribute 名称。 |
| `Regex` | InterfaceStandardIR | 格式校验表达式或明确的 `NO_CONSTRAINT`。 |
| `Data Type` | InterfaceStandardIR | String/Boolean/Date/Number/Node/Object。 |

### 4.2 来源与可信列

| 列 | 来源 | 含义 |
|---|---|---|
| `SchemaIR Path` | InterfaceStandardIR | 对应的银行报文事实。 |
| `Bank Required` | SchemaIR | 银行原始必填约束。 |
| `Bank Length` | SchemaIR | 银行原始长度约束。 |
| `Bank Occurs` | SchemaIR | 银行原始出现次数。 |
| `Rule Reference` | InterfaceStandardIR | 支撑标准配置的 Rule ID。 |
| `Difference Reason` | InterfaceStandardIR | 与 SchemaIR 不同的原因。 |
| `Confidence` | InterfaceStandardIR | 配置决定置信度。 |
| `Validator Issue` | validation result | 与字段相关的错误或警告摘要。 |

### 4.3 执行列

`Standard Action=CREATE/UPDATE` 时包含：

- Execution Status；
- Verification Status；
- Operator Note。

`Standard Action=REUSE` 时这些列锁定为 `NOT_APPLICABLE`，标准内容只用于核对版本和字段结构。

## 5. Interface Template

每个 InterfaceTemplateIR field config 一行。标准中被省略的字段不在此 sheet 制造空行，而在 `Warnings` 中展示 omission。

### 5.1 模板配置列

| 列 | 来源 | 含义 |
|---|---|---|
| `Standard Field Ref` | InterfaceTemplateIR | 对应的稳定标准字段 ID。 |
| `Field Name` | InterfaceStandardIR | 便于人工查看的字段名称快照。 |
| `Parent Path` | InterfaceStandardIR | 对应标准字段的目标系统 Path。 |
| `Data Type` | InterfaceStandardIR | 对应标准字段类型。 |
| `Value Mode` | InterfaceTemplateIR | 六种取值模式之一。 |
| `Value Summary` | Generator | 字段值表达式的确定性可读摘要。 |
| `XML Key Summary` | Generator | 各 XML Key 与表达式摘要。 |
| `Empty Handling` | InterfaceTemplateIR | 源值为空时的处理策略。 |
| `Overlength Handling` | InterfaceTemplateIR | 超长时报错或截断。 |
| `Row Limit` | InterfaceTemplateIR | 重复节点或多行处理上限。 |
| `Chinese Character Length` | InterfaceTemplateIR | 中文字符长度权重。 |
| `Replacement Rules` | InterfaceTemplateIR | 按顺序执行的字符替换。 |

`EMPTY`、Empty Handling 和 omission 是三个不同概念：

- `EMPTY`：存在模板行且表达式明确取空值；
- Empty Handling：存在输入但值为空时如何处理；
- omission：该模板没有这个标准字段配置。

### 5.2 可信与执行列

| 列 | 来源 | 含义 |
|---|---|---|
| `Rule Reference` | InterfaceTemplateIR | 支撑表达式和处理策略的 Rule ID。 |
| `Confidence` | InterfaceTemplateIR | 模板决定置信度。 |
| `Uncertain` | InterfaceTemplateIR | 是否仍有不确定性。 |
| `Validator Issue` | validation result | 与该配置相关的错误或警告摘要。 |
| `Execution Status` | 配置人员 | 模板字段配置状态。 |
| `Verification Status` | 配置/复核人员 | 配置完成后的验证状态。 |
| `Operator Note` | 配置/复核人员 | 阻塞、验证或返工说明。 |

人工状态只存在于工作簿，不回流 Final Template。

## 6. Value Expressions

### 6.1 作用

`Interface Template` 主 sheet 必须保持一行对应一个标准字段，因此只适合展示 Value Mode 和简短摘要。以下内容无法可靠压入单个单元格：

- 递归 `CONCATENATE`；
- FUNCTION 的结构化参数；
- MAPPING 引用；
- 一个 element 上多个 XML Key 的独立表达式。

`Value Expressions` 将这些表达式按树逐节点展开，使配置人员可 Review、Validator 可关联、结构化 workbook assertions 可还原。它完全派生自 Final InterfaceTemplateIR，不是额外事实源。

### 6.2 列

| 列 | 含义 |
|---|---|
| `Template ID` | 当前模板身份。 |
| `Standard Field Ref` | 表达式所属标准字段。 |
| `Expression Scope` | `FIELD_VALUE` 或 `XML_KEY`。 |
| `XML Key` | Scope 为 XML_KEY 时的 key，例如 `@version`。 |
| `Expression ID` | 当前表达式节点的稳定 ID。 |
| `Parent Expression ID` | 父节点 ID；根表达式为空。 |
| `Sequence` | 同一父节点下的执行顺序。 |
| `Mode` | FIXED_VALUE/EMPTY/FIELD/FUNCTION/MAPPING/CONCATENATE。 |
| `FIELD Reference` | FIELD catalog 引用。 |
| `Fixed Value` | FIXED_VALUE 的值。 |
| `Function Reference` | FUNCTION catalog 引用。 |
| `Function Parameters` | 结构化参数的确定性展示。 |
| `Mapping Reference` | MAPPING catalog 引用。 |
| `Rule Reference` | 支撑该表达式节点的 Rule ID。 |

每个存在模板行的标准 XML Key 必须恰好具有一个根表达式。`CONCATENATE` 子节点按 Parent Expression ID 与 Sequence 还原；禁止压缩成无法校验的自由文本。

## 7. Warnings

`Warnings` 至少包含：

| 列 | 含义 |
|---|---|
| `Severity` | ERROR、WARNING 或 INFO。 |
| `Direction` | ASSEMBLY 或 PARSE。 |
| `Standard Field Ref` | 相关标准字段。 |
| `Category` | 稳定问题类别。 |
| `Message` | 可执行说明。 |
| `Rule Reference` | 相关 Rule ID。 |
| `Review Disposition` | PENDING、ACCEPTED、REJECTED 或 NOT_REQUIRED。 |
| `Omission Reason` | 场景性字段省略原因。 |
| `Source` | SchemaIR/Standard/Template Validator、Review 或 Generator。 |

稳定类别至少包括：

- `SCHEMA_STANDARD_DIFFERENCE`
- `MISSING_TEMPLATE_FIELD`
- `UNKNOWN_CONSTRAINT`
- `XML_KEY_EXPRESSION`
- `UNMAPPED`
- `RULE_CONFLICT`
- `STANDARD_VERSION_MISMATCH`
- `VALIDATOR`

未确认 omission 不允许进入 Final Template，因而不能出现在可交付 Workbook。已确认 omission 仍以 WARNING 或 INFO 保留，展示原因和 `ACCEPTED` disposition。

存在 Validator ERROR、未形成任一 Final 输入或校验结果与 Final 内容不匹配时，不得生成可交付工作簿。排障用 debug workbook 必须在 `Overview` 明确标记不可交付。

## 8. Rule References

只列出当前工作簿实际引用的规则，至少包含：

- Artifact Scope：STANDARD 或 TEMPLATE；
- Rule Package Version；
- Rule ID；
- Rule Title；
- Source File / Section；
- Used By Field / Expression。

规则文本以不可变规则包为准，工作簿摘要不得成为新规则来源。

## 9. 状态流转

Execution Status：

```text
NOT_STARTED → IN_PROGRESS → CONFIGURED
                    ↘
                    BLOCKED → IN_PROGRESS

CONFIGURED → IN_PROGRESS
```

Verification Status：

```text
NOT_VERIFIED → PASSED
             → FAILED
```

约束：

- 只有 `CONFIGURED` 才能进入 PASSED 或 FAILED。
- 配置修改后 Verification 重置为 NOT_VERIFIED。
- 一行完成条件是 `CONFIGURED + PASSED`。
- REUSE 标准行为 `NOT_APPLICABLE`，不参与完成率。
- 人工状态和备注不回流 Final IR。

## 10. 确定性生成与回归

相同 Final SchemaIR、Final Standard、Final Template、三份校验结果、规则版本和 Standard Action 必须生成相同结构化业务内容。生成时间等任务上下文允许变化，但不得改变字段排序、表达式树、Warnings 或规则引用。

结构化 assertions 至少验证：

- 固定 sheet 名称与顺序；
- Standard/Template identity 和版本绑定；
- parentPath/fullPath、sequence、Node/Object 与 XML Keys；
- 模板字段是标准字段子集；
- 已确认 omissions 出现在 Warnings 而不出现在 Template rows；
- 字段值与 XML Key expression tree 可完整还原；
- Rule References 可解析；
- Standard Action=REUSE 时标准执行列为 NOT_APPLICABLE；
- 工作簿不是导入文件或 IR 的反向输入。
