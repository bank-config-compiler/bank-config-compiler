# b2e0061 Review Golden Sample

## 状态

Review Golden.

## 目的

本样例冻结 `b2e0061` raw document 对应的 expected DocIR、SchemaIR 和 review notes。它不是最终业务答案，也不是运行时最终契约。

`review-notes.expected.md` 中的未确认问题是有意保留的。它们定义后续生成器必须保留的 review 输出，包括不确定性、confidence、evidence 和人工确认点。

## 产物

| 产物 | 用途 |
|---|---|
| `raw-doc.md` | 本样例的受控 raw document 来源。 |
| `docir.expected.md` | 从 raw document 生成的 expected DocIR 结构。 |
| `schemair.expected.json` | 从 expected DocIR 生成的 expected SchemaIR。 |
| `review-notes.expected.md` | expected 人工 review notes，包含未解决的确认点。 |

## 边界

- 历史导出 JSON 只能作为人工 review 对照材料。
- 历史导出 JSON 不得用于补字段、进入 expected SchemaIR，或作为回归输入。
- `schemair-validation.expected.json` 和 `workbook-assertions.expected.json` 有意延后到 Validator 与 Workbook assertion 边界实现时再补齐。
