# Schema Workbook 设计

## Status

Draft.

## 1. 目的

Schema Workbook 是面向配置人员的人工配置交付物。它不是系统内部事实源，也不应被反向解析为可信输入。

Workbook Generator 必须基于通过校验的 `Final SchemaIR` 确定性生成 workbook。生成过程只做格式化、排序、分 sheet、提示和配置指导，不补业务字段，不对接目标系统导入格式。

## 2. Workbook 结构

每个接口生成一个 `.xlsx` 文件。

固定 sheet：

| Sheet | 用途 |
|---|---|
| `Overview` | 接口编码、接口名称、报文格式、来源文档、生成时间、校验摘要。 |
| `ASSEMBLY` | 组装请求报文字段清单。 |
| `PARSE` | 处理响应报文字段清单。 |
| `Warnings` | 不确定字段、条件必填、字段冲突、缺失来源、人工确认项。 |
| `Legend` | 列含义、枚举值、颜色说明。 |

如果某个接口暂时只有一个方向，仍应保留固定 sheet；缺失方向的字段 sheet 可以为空，并在 `Overview` 标记。

不新增独立 `ENVELOPE` sheet。`ASSEMBLY` 和 `PARSE` sheet 都应先展示 `SchemaIR.envelope.fields` 中的 BOCB2E envelope/head/trans 字段，再展示对应方向的交易消息字段。重复展示 envelope/head 是有意设计，用于让配置人员在单个方向 sheet 内完整 review 报文结构。

## 3. 字段 sheet 列

`ASSEMBLY` 和 `PARSE` sheet 使用相同列：

| 列名 | 来源 | 说明 |
|---|---|---|
| `No` | generator | 当前 sheet 内序号。 |
| `Level` | SchemaIR | 字段层级。 |
| `Path` | SchemaIR | 完整字段路径。 |
| `Parent Path` | SchemaIR | 父级路径。 |
| `Field Name` | SchemaIR | 字段名。 |
| `Node Kind` | SchemaIR | `XML_ELEMENT`、`XML_ATTRIBUTE`、`JSON_OBJECT`、`JSON_ARRAY` 或 `SCALAR`。 |
| `Data Type` | SchemaIR | 标准化数据类型。 |
| `Required` | SchemaIR | 普通必填标记。 |
| `Length Raw` | SchemaIR | 原文长度描述。 |
| `Length Min` | SchemaIR | 解析后的最小长度。 |
| `Length Max` | SchemaIR | 解析后的最大长度。 |
| `Occurs` | SchemaIR | 原文出现次数。 |
| `Multiple` | SchemaIR | 是否重复节点。 |
| `Description` | SchemaIR | 字段说明。 |
| `Condition` | SchemaIR | 条件必填或条件约束。 |
| `Source Text` | SchemaIR | 字段来源文本。 |
| `Uncertain` | SchemaIR | 是否不确定。 |
| `Review Note` | SchemaIR | 人工 Review 备注。 |
| `Config Guidance` | SchemaIR / generator | 配置建议。 |

字段排序规则：

1. 先输出 envelope/head/trans 字段。
2. 再输出当前方向的交易 wrapper、payload、业务字段或响应字段。
3. 同一字段集合内按 `Path` 层级和原文顺序稳定排序。

字段来源规则：

- `Source Text` 必须来自 SchemaIR 字段，不允许由 generator 补写。
- `Evidence Kind` 后续可以作为列加入 workbook；Phase0 最小 workbook 可先把 evidence 信息合并到 `Review Note` 或 `Warnings`。
- `uncertain=true`、`confidence < 0.9` 或 `evidence.kind != "DIRECT"` 的字段必须进入 `Warnings`。

## 4. 格式规则

- 冻结表头。
- 启用筛选。
- 按 `Level` 对 `Field Name` 做视觉缩进。
- 必填字段高亮。
- `Condition` 非空字段使用条件标记高亮。
- `Uncertain=true` 字段使用人工确认高亮。
- `Warnings` sheet 必须列出不确定字段和 Validator warning。
- `Source Text` 可以换行，但不得省略。
- 不依赖公式表达关键语义，避免人工修改破坏事实。

## 5. Warnings sheet

`Warnings` sheet 至少包含：

| 列名 | 说明 |
|---|---|
| `Severity` | `ERROR`、`WARNING` 或 `INFO`。 |
| `Function Type` | `ASSEMBLY` 或 `PARSE`。 |
| `Path` | 相关字段路径。 |
| `Message` | 问题说明。 |
| `Source` | `Validator`、`Generator` 或 `Review`。 |

Validator `ERROR` 存在时，不应生成最终交付 workbook；可以生成 debug workbook，但必须明确标记为不可交付。

## 6. 回归策略

自动化测试不应比较 `.xlsx` 二进制整体。

应读取 workbook 后断言：

- sheet 名称。
- 字段 sheet 表头。
- 关键字段行。
- warning 行。
- 冻结窗格和筛选是否存在。
- 必填、条件、不确定字段的基础样式是否存在。

`schema-workbook.expected.xlsx` 可作为人工查看用参考输出；机器回归以结构化 assertions 为准。
