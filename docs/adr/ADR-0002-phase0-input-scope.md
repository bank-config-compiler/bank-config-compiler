# ADR-0002: Phase0-PoC 仅支持文本、Markdown 和粘贴输入

## Status

Accepted.

## Context

银行接口文档可能以 `.docx`、PDF、扫描件、复杂表格或混合格式出现。完整覆盖这些格式会引入文档解析、OCR、bbox、高亮、页码定位和表格结构恢复等复杂问题。

Phase0-PoC 的目标是证明核心链路可行，而不是证明系统能处理所有银行文档格式。

## Decision

Phase0-PoC 输入范围限定为：

- `.md`
- `.txt`
- 粘贴文本

暂不支持：

- `.docx`
- PDF
- OCR
- bbox / pageNo / 原文区域高亮
- 复杂 Word 表格解析

## Alternatives Considered

### Phase0 同时支持 `.docx` / PDF

Pros:

- 更贴近真实文档来源。
- 后续格式兼容压力更早暴露。

Cons:

- 显著增加 Phase0 复杂度。
- 容易把核心链路验证变成文档解析平台建设。
- OCR 和 bbox 问题会掩盖 DocIR / SchemaIR / Workbook Generator 的真实风险。

Why not chosen:

- 会分散 Phase0 对核心链路的验证，不符合最小可验证闭环目标。

### 只支持手工录入 Final DocIR

Pros:

- 实现最简单。
- 可以直接验证 SchemaIR 和 Workbook Generator。

Cons:

- 无法证明系统具备 DocIR Draft 自动生成能力。
- 无法验证从 Raw Docs 到 DocIR 的价值。

Why not chosen:

- 不满足“AI 辅助生成可 Review 配置草稿”的项目目标。

## Consequences

- Phase0 的 golden sample 必须使用真实脱敏文本或 Markdown 文档。
- 富文档解析能力应在后续阶段重新评估，不能作为 Phase0 成功条件。
- Phase0 仍需要保留原始输入和中间产物，确保后续能复盘字段来源。
