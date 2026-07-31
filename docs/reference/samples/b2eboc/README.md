# B2EBOC b2e0061 参考样例

## Status

Reference / Draft. Not golden sample.

## 文件说明

本目录是当前维护的 reference input。已过期的 toy 示例不再保留，避免与当前 Standard/Template Configuration Workbook 契约混淆。

`b2e0061.md` 已作为 Phase0 raw doc 输入，并在 `samples/golden/b2eboc-b2e0061/` 中形成 DocIR / SchemaIR Review Golden sample。本 reference 目录本身不是 golden sample；InterfaceStandardIR、InterfaceTemplateIR、对应 Validator 和 workbook assertions 仍受真实 catalog blocker 约束。

| 文件 | 说明 | 当前用途 |
|---|---|---|
| `b2e0061.md` | BOCB2E 公对私转账汇款接口 raw doc，已脱敏或不含真实业务数据。 | SchemaIR 设计和 golden raw doc 的参考输入。 |
| `b2e0061-assembly.json` | 目标系统历史导出的组装请求报文配置 JSON。 | 仅用于理解 `ASSEMBLY` 方向和目标系统历史形态。 |
| `b2e0061-parse.json` | 目标系统历史导出的处理响应报文配置 JSON。 | 仅用于理解 `PARSE` 方向和目标系统历史形态。 |

## 当前设计边界

项目当前不再以 Import JSON 作为最终目标产物。历史导出 JSON 不作为：

- 目标输出格式。
- MVP 验收标准。
- Workbook Generator 输入。
- SchemaIR 字段来源。
- Interface Standard / Template 规则或 fields/functions/mappings catalog 来源。

项目当前目标是依次确认 `Final SchemaIR`、`Final InterfaceStandardIR` 与 `Final InterfaceTemplateIR`，再结合三份校验结果、规则版本和 Standard Action 确定性生成 Configuration Workbook。真实 catalog 未提供前，不得从本目录历史 JSON 补齐目标配置。

## 样例价值

该样例用于证明：

- 一个接口可以同时包含 `ASSEMBLY` 和 `PARSE` 两个方向。
- XML 报文结构需要在 SchemaIR 中显式表达。
- 字段表、层级、必填、长度、条件说明和响应状态字段需要进入可 Review 的 SchemaIR。
- Configuration Workbook 以一个方向模板为边界，呈现该方向标准和模板配置。

## 注意事项

- 历史导出 JSON 中的 `standardHeadId`、`standardLineId`、`parentId` 是导出历史带出的 ID，不参与当前设计的生成或回归。
- 如 raw doc 与历史导出 JSON 存在差异，银行报文事实以人工确认后的 raw doc / SchemaIR 为准；目标系统配置事实只能来自经确认规则包和 Final InterfaceStandardIR / InterfaceTemplateIR。
