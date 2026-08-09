# B2EBOC b2e0061 参考样例

## Status

Reference / Draft. Not golden sample.

## 文件说明

本目录是当前维护的 reference input。已过期的 toy 示例不再保留，避免与当前 Standard/Template Configuration Workbook 契约混淆。

`b2e0061.md` 已作为 Phase0 raw doc 输入，并在 `samples/golden/b2eboc-b2e0061/` 中形成 DocIR / SchemaIR Review Golden sample。本 reference 目录本身不是 golden sample；正式导出和字段清单已经进入已发布规则包的证据链。InterfaceStandardIR/InterfaceTemplateIR Validator 与双方向 Final fixtures/results 已在 `samples/trusted-chain/b2eboc-b2e0061/` 落地并冻结；workbook assertions 尚未实现。

| 文件 | 说明 | 当前用途 |
|---|---|---|
| `b2e0061.md` | BOCB2E 公对私转账汇款接口 raw doc，已脱敏或不含真实业务数据。 | SchemaIR 设计和 golden raw doc 的参考输入。 |
| `assemblyFields.txt` | ASSEMBLY 系统请求字段清单。 | `configuration-rules/v1` 的 ASSEMBLY FIELD catalog 来源。 |
| `parseFields.txt` | PARSE 固定 JSON/Java 输出对象字段、path 和 datatype。 | `configuration-rules/v1` 的 PARSE FIELD catalog 来源；该对象由高代码维护，不属于 Interface Standard。 |
| `b2e0061-assembly-standard.json` | 目标系统正式导出的组装方向 Interface Standard。 | b2e0061 ASSEMBLY Standard 结构和实际配置证据。 |
| `b2e0061-parse-standard.json` | 目标系统正式导出的解析方向 Interface Standard。 | b2e0061 PARSE Standard 结构和实际配置证据。 |
| `b2e0061-assembly-template.json` | 目标系统正式导出的组装方向 Interface Template，客户/环境固定值已脱敏。 | Value Expression、processing policy、function 和目的系统 Condition 能力证据。 |
| `b2e0061-parse-template.json` | 目标系统正式导出的解析方向 Interface Template。 | Standard source 到 Parse Field target、Value Expression、function 和目的系统 Condition 能力证据。 |
| `others.json` | 一个 MAPPING Template 行及所选预设规则的导出 snapshot，公司名称 target 已脱敏。 | `FIELD_REF + mappingRuleName` 配置形态、MAPPING processing policy 和 catalog 引用证据；不是 b2e0061 fixture。 |

## 当前设计边界

项目当前不再以导出 JSON 作为最终目标产物。正式导出 JSON 不作为：

- 目标输出格式。
- MVP 验收标准。
- Workbook Generator 输入。
- SchemaIR 字段来源。
- 未经治理的 Rule ID 或全量 catalog。

正式导出可以作为 b2e0061 目标配置事实和实际调用形态证据，但必须先进入版本化规则包或人工确认的 expected fixture；不得直接复制数据库 ID、审批状态或未解释业务 Condition。项目目标仍是依次确认 `Final SchemaIR`、`Final InterfaceStandardIR` 与 `Final InterfaceTemplateIR`，再结合三份校验结果、规则版本和 Standard Action 确定性生成 Configuration Workbook。

## 样例价值

该样例用于证明：

- 一个接口可以同时包含 `ASSEMBLY` 和 `PARSE` 两个方向。
- ASSEMBLY 从系统 FIELD 写入银行 Standard Field；PARSE 从银行 Standard Field 写入固定 Parse Field。
- XML 报文结构需要在 SchemaIR 中显式表达。
- 字段表、层级、必填、长度、条件说明和响应状态字段需要进入可 Review 的 SchemaIR。
- Configuration Workbook 以一个方向模板为边界，呈现该方向标准和模板配置。

## 注意事项

- 正式导出 JSON 中的 `standardHeadId`、`standardLineId`、`parentId` 是源系统数据库标识，不参与当前设计的生成或回归。
- `termid`、`trnid`、`custid`、`cusopr` 固定值以及 `others.json` 公司名称 Mapping target 已替换为 `<REDACTED>`；占位值不得进入 fixture 或 Workbook。
- 如 raw doc 与正式导出存在差异，银行报文事实以人工确认后的 raw doc / SchemaIR 为准；目标配置事实保留导出值、差异原因和 Review，不覆盖银行事实。
- b2e0061 Final Standard 以银行文档保留 `@security`、排除导出中的 `vamflag`；导出 observed `@lang` 只保留为 SchemaIR evidence 和差异 Warning。正式导出文件本身必须原样保留，不按 Final 结论修改。
- `b2e0061-rq` 与 `b2e0061-rs` 依据 raw-doc `0..1000` 为 Standard `Node`；PARSE 的 `paymentLineList` 是固定输出对象中的 `List`，两端通过 `COLLECTION_ITEM` 连接而不是合并 datatype。
- Template 中安全固定输入使用 `FIXED_VALUE + SECURE_INPUT_REF`，IR/Workbook 只记录安全引用标识，不复制真实值。
