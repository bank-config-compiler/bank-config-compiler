# B2EBOC b2e0061 参考样例

## Status

Reference / Draft. Not golden sample.

## 文件说明

| 文件 | 说明 | 当前用途 |
|---|---|---|
| `b2e0061.md` | BOCB2E 公对私转账汇款接口 raw doc，已脱敏或不含真实业务数据。 | 当前 SchemaIR / Schema Workbook 设计依据。 |
| `b2e0061-assembly.json` | 目标系统历史导出的组装请求报文配置 JSON。 | 仅用于理解 `ASSEMBLY` 方向和目标系统历史形态。 |
| `b2e0061-parse.json` | 目标系统历史导出的处理响应报文配置 JSON。 | 仅用于理解 `PARSE` 方向和目标系统历史形态。 |

## 当前设计边界

项目当前不再以 Import JSON 作为最终目标产物。历史导出 JSON 不作为：

- 目标输出格式。
- MVP 验收标准。
- Workbook Generator 输入。
- SchemaIR 字段来源。

项目当前目标是基于 raw doc 生成并确认 `Final SchemaIR`，再确定性生成 Schema Workbook，用于指导配置人员人工配置目标系统。

## 样例价值

该样例用于证明：

- 一个接口可以同时包含 `ASSEMBLY` 和 `PARSE` 两个方向。
- XML 报文结构需要在 SchemaIR 中显式表达。
- 字段表、层级、必填、长度、条件说明和响应状态字段需要进入可 Review 的 SchemaIR。
- Schema Workbook 需要分别呈现请求组装字段和响应处理字段。

## 注意事项

- 历史导出 JSON 中的 `standardHeadId`、`standardLineId`、`parentId` 是导出历史带出的 ID，不参与当前设计的生成或回归。
- 如 raw doc 与历史导出 JSON 存在差异，应以人工确认后的 raw doc / SchemaIR 为准。
