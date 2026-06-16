# Golden Sample 设计

## Status

Draft.

## 1. 目的

Golden sample 是后续回归、Prompt 调整、Validator 修改、Workbook Generator 修改和验收判断的核心证据。

Golden sample 不只是演示样例。它必须证明系统对真实或接近真实银行接口文档有帮助，并能让团队判断输出变化是可接受调整还是退化。

## 2. 最低要求

正式 golden sample 至少应覆盖：

- 真实脱敏 Raw Docs。
- 期望或确认后的 DocIR。
- 期望或确认后的 SchemaIR。
- Validator 结果。
- Schema Workbook expected assertions。

样例字段规模应接近真实业务，初步目标为 20 个以上字段。

## 3. 当前 reference sample 边界

`docs/reference/samples/pain001-toy/` 只能作为 reference sample 保留。

它可以用于：

- 文档链路说明示例。
- Prompt smoke test 的最小输入。
- Workbook Generator 单字段或少字段格式示例。

它不能用于：

- MVP 验收。
- 字段覆盖率证明。
- 真实业务价值证明。
- Schema Workbook 指导人工配置能力证明。

## 4. 候选目录结构

```text
samples/golden/b2eboc-b2e0061/
├── raw-doc.md
├── docir.expected.md
├── schemair.expected.json
├── schemair-validation.expected.json
├── workbook-assertions.expected.json
├── schema-workbook.expected.xlsx
└── README.md
```

`schema-workbook.expected.xlsx` 可作为人工查看用的参考输出。自动回归不应比较整个 xlsx 二进制，而应读取 workbook 后按 `workbook-assertions.expected.json` 做结构化断言。

## 5. Workbook expected assertions

Workbook 回归至少应断言：

- Sheet 名称包含 `Overview`、`ASSEMBLY`、`PARSE`、`Warnings`、`Legend`。
- 字段 sheet 表头与设计列一致。
- `ASSEMBLY` 包含关键请求字段，例如 `acttyp`。
- `PARSE` 包含关键响应字段，例如 `rspcod`、`rspmsg`、`insid`、`obssid`。
- `messageFormat` 能在 `Overview` 中展示。
- `uncertain=true`、条件字段和 validator warning 能进入 `Warnings` 或被高亮。
- workbook 能由 `schemair.expected.json` 确定性重新生成。

## 6. 待确认点

- Golden sample 是否放在 `samples/`，还是 `src/test/resources/`。
- LLM 生成输出与 expected 文件如何比对。
- Validator 结果是否保存 warning、error 和 coverage 信息。
- Workbook 样式断言的最小集合。
- `schema-workbook.expected.xlsx` 是否进入版本库，还是只保存结构化 assertions。
