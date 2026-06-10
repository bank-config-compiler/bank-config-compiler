# Golden Sample 设计

## Status

Draft.

## 1. 目的

Golden sample 是后续回归、Prompt 调整、Rule Engine 修改和验收判断的核心证据。

Golden sample 不只是演示样例。它必须证明系统对真实或接近真实银行接口文档有帮助，并能让团队判断输出变化是可接受调整还是退化。

## 2. 最低要求

正式 golden sample 至少应覆盖：

- 真实脱敏 Raw Docs。
- 期望或确认后的 DocIR。
- 期望或确认后的 SchemaIR。
- Validator 结果。
- 期望或确认后的 Import JSON Draft。

样例字段规模应接近真实业务，初步目标为 20 个以上字段。

## 3. 当前 reference sample 边界

`docs/reference/samples/pain001-toy/` 只能作为 reference sample 保留。

它可以用于：

- 文档链路说明示例。
- Prompt smoke test 的最小输入。
- Rule Engine 单字段或少字段映射示例。

它不能用于：

- MVP 验收。
- 字段覆盖率证明。
- 真实业务价值证明。
- Import JSON 兼容性证明。

## 4. 候选目录结构

```text
samples/golden/pain001-real-masked/
├── raw-doc.md
├── docir.expected.md
├── schemair.expected.json
├── schemair-validation.expected.json
├── import-json.expected.json
└── README.md
```

## 5. 待确认点

- 是否将 golden sample 放在 `samples/`，还是 `src/test/resources/`。
- LLM 生成输出与 expected 文件如何比对。
- Import JSON expected 是否在用户提供真实样例后再创建。
- Validator 结果是否保存 warning、error 和 coverage 信息。
