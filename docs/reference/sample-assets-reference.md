# Sample Assets 参考说明

## Status

Reference / Draft. Current sample is not golden sample.

## Date

2026-05-27

## Context

`tmp/samples` 中包含一个 `pain.001` demo 样例。该样例有助于说明 Raw Docs、DocIR、SchemaIR 和 Import JSON 的关系，但它不满足当前正式文档对 MVP golden sample 的要求。

正式要求：

- 使用真实脱敏银行接口文档。
- 字段规模初步目标为 20 个以上字段。
- Import JSON 贴近真实银企直连导入格式。
- Golden sample 至少覆盖 Raw Docs、DocIR、SchemaIR、Validator 结果和 Import JSON。

## 当前 tmp sample 文件

| 文件 | 说明 | 是否可作为 golden sample |
|---|---|---|
| `tmp/samples/raw-docs-pain001-demo.md` | toy raw docs，字段数量少 | 否 |
| `tmp/samples/docir-pain001-demo.md` | toy DocIR | 否 |
| `tmp/samples/schemair-pain001-demo.json` | toy SchemaIR，只覆盖部分字段 | 否 |
| `tmp/samples/import-json-pain001-demo.json` | toy Import JSON | 否 |

这些内容已迁移到 `docs/reference/samples/pain001-toy/`，仅作为 reference sample 保留。

## 当前样例的参考价值

当前样例可以保留为：

- 文档链路说明示例。
- Prompt smoke test 的最小输入。
- Rule Engine 单字段或少字段映射示例。

当前样例不能用于：

- MVP 验收。
- 字段覆盖率证明。
- 真实业务价值证明。
- Import JSON 兼容性证明。

## 需要替换为正式 golden sample 的内容

建议后续 golden sample 结构：

```text
samples/golden/pain001-real-masked/
├── raw-doc.md
├── docir.expected.md
├── schemair.expected.json
├── schemair-validation.expected.json
├── import-json.expected.json
└── README.md
```

后续需要讨论：

- 是否将 golden sample 放在 `samples/`，还是 `src/test/resources/`。
- LLM 生成输出与 expected 文件如何比对。
- Import JSON expected 是否在用户提供真实样例后再创建。
- Validator 结果是否保存 warning、error 和 coverage 信息。
