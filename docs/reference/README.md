# Reference 索引

## Status

Reference Only.

## Purpose

`docs/reference/` 保存当前仍用于设计、验证或讨论的输入证据。这里的材料不是正式规则包，也不能覆盖 requirements、ADR、design、phase 或 planning 文档；正式导出和字段清单可以作为规则 Review 的来源，但必须先经过 `configuration-rules/` 治理或人工确认，不能直接成为 Final IR/Workbook 输入。

reference 中的正式导出必须原样保留其冲突字段和源系统形态；不得为贴合 Final 结论修改导出文件，也不得把冲突内容直接复制进 Final fixture。银行字段、路径、出现次数和约束以 raw-doc/Final SchemaIR 为准，导出只证明目标系统形态。

## Documents

- `samples/`：参考输入与样例，不自动等同于正式 golden fixture。
- `samples/mapping.txt`：目标系统预设 Mapping catalog 的 JSON 格式样例子集，是 `configuration-rules/v1/mappings.yaml` 的来源之一。

已经被替代或明确放弃的草案统一迁移到 `docs/archive/`。
