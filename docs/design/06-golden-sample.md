# Golden Sample 设计

## Status

Draft.

## 1. 目的

Golden sample 是后续回归、Prompt 调整、SchemaIR / ConfigIR Validator 修改、Workbook Generator 修改和验收判断的核心证据。

Golden sample 不只是演示样例。它必须证明系统对真实或接近真实银行接口文档有帮助，并能让团队判断输出变化是可接受调整还是退化。

Phase0 先采用 Review Golden sample：冻结 expected DocIR、expected SchemaIR 和 expected review notes。Review notes 中的 unresolved questions 是样例价值的一部分，用于定义后续生成器必须暴露的人工确认入口，而不是成为 sample 的阻塞项。

## 2. 最低要求

正式 Review Golden sample 至少应覆盖：

- 真实脱敏 Raw Docs。
- 期望 DocIR。
- 期望 SchemaIR。
- 期望 review notes，包含低置信、推导、冲突和人工确认项。

Trusted chain 阶段再补充：

- 经人工确认的 expected ConfigIR。
- ConfigIR validation expected result。
- Configuration Workbook expected assertions。

ConfigIR golden 覆盖必须至少包含 `FIELD`、`FIXED_VALUE`、`EMPTY`、`FUNCTION`、`MAPPING` 和递归 `CONCATENATE`，并同时覆盖 ASSEMBLY 与 PARSE。具体 FIELD、FUNCTION、MAPPING 标识和 Rule ID 只能来自已确认的 `configuration-rules/v1`，不能使用占位业务标识。

样例字段规模应接近真实业务，初步目标为 20 个以上字段。

## 3. 当前 reference sample 边界

`docs/reference/samples/b2eboc/` 是当前 reference sample。它包含一个真实语境下的接口 raw doc，以及历史导出 JSON 用于理解 `ASSEMBLY` / `PARSE` 两个方向。

它可以用于：

- 当前 SchemaIR / Configuration Workbook 讨论的参考输入。
- CLI ingest smoke test 的输入。
- 已构造 b2e0061 Review Golden sample 的 raw doc 来源。

它不能用于：

- 直接作为 MVP 验收。
- 在缺少 expected DocIR / SchemaIR / review notes 时作为回归基准。
- 将历史导出 JSON 重新定义为目标产物或 Workbook Generator 输入。
- 在缺少真实规则 catalog 和 Final ConfigIR 时证明 Configuration Workbook 指导人工配置能力。

## 4. Review Golden 目录结构

```text
samples/golden/b2eboc-b2e0061/
├── raw-doc.md
├── docir.expected.md
├── schemair.expected.json
├── schemair-validation.expected.json
├── review-notes.expected.md
└── README.md
```

Trusted chain 阶段可继续添加：

```text
samples/golden/b2eboc-b2e0061/
├── configir.expected.json
├── configir-validation.expected.json
├── workbook-assertions.expected.json
└── configuration-workbook.expected.xlsx
```

这些文件当前尚不存在，并受 `configuration-rules/v1` catalog blocker 约束。`configuration-workbook.expected.xlsx` 可作为人工查看用的参考输出；自动回归不应比较整个 xlsx 二进制，而应读取 workbook 后按 `workbook-assertions.expected.json` 做结构化断言。

## 5. Workbook expected assertions

Workbook 回归至少应断言：

- Sheet 名称按顺序包含 `Overview`、`ASSEMBLY`、`PARSE`、`Value Expressions`、`Warnings`、`Rule References`、`Legend`。
- 字段 sheet 表头与设计列一致。
- `ASSEMBLY` 包含关键请求字段，例如 `acttyp`。
- `PARSE` 包含关键响应字段，例如 `rspcod`、`rspmsg`、`insid`、`obssid`。
- `messageFormat` 能在 `Overview` 中展示。
- 六种 Value Mode 均有覆盖，递归 `CONCATENATE` 可以在 `Value Expressions` 中还原。
- 未映射、规则冲突、SchemaIR/ConfigIR 差异、`uncertain=true` 和 Validator warning 进入 `Warnings`。
- workbook 能由 Final SchemaIR、Final ConfigIR、两份校验结果和指定规则版本确定性重新生成。

## 6. 待确认点

- Golden sample 是否放在 `samples/`，还是 `src/test/resources/`。
- LLM 生成输出与 expected 文件如何比对。
- Workbook 样式断言的最小集合。
- `configuration-workbook.expected.xlsx` 是否进入版本库，还是只保存结构化 assertions。
- 真实 catalog 确认后如何选择能够覆盖六种 Value Mode 的业务字段。
