# b2e0061 Review Golden Sample

## 状态

Review Golden.

## 目的

本样例冻结 `b2e0061` raw document 对应的 expected DocIR、SchemaIR 和 review notes。它不是最终业务答案，也不是运行时最终契约。

这些 expected artifacts 是 ADR-0008 修订前形成的“审查前”Golden，本批次保持原样。方向级 `xmlEncoding`、银行事实投影、Standard 镜像和结构绑定将在后续 P0-T3 SchemaIR/Standard/Template fixture 中落实；本目录只通过本 README 指向新契约。

`review-notes.expected.md` 中的未确认问题是有意保留的。它们定义后续生成器必须保留的 review 输出，包括不确定性、confidence、evidence 和人工确认点。

## 产物

| 产物 | 用途 |
|---|---|
| `raw-doc.md` | 本样例的受控 raw document 来源。 |
| `docir.expected.md` | 从 raw document 生成的 expected DocIR 结构。 |
| `schemair.expected.json` | 从 expected DocIR 生成的 expected SchemaIR。 |
| `schemair-validation.expected.json` | expected SchemaIR Validator result，状态为 `passed_with_warnings`，无阻断错误。 |
| `review-notes.expected.md` | expected 人工 review notes，包含未解决的确认点。 |

## 边界

- 目标系统正式导出 JSON 只能作为人工 review 与规则治理证据。
- 正式导出 JSON 不得用于覆盖 raw-doc 银行事实、进入 expected SchemaIR，或直接作为回归输入。
- 当前投影和迁移边界见 [`ADR-0008`](../../../docs/adr/ADR-0008-directional-template-bindings-and-bank-conditions.md)。
- `workbook-assertions.expected.json` 有意延后到 Workbook Generator 与 Workbook assertion 边界实现时再补齐。
