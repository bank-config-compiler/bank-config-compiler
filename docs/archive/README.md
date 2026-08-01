# Archive 索引

## Status

Archive Only.

## Purpose

`docs/archive/` 保存已经被正式文档替代、明确放弃或不再作为设计输入的历史材料。归档内容不构成当前承诺，不参与 source-of-truth 优先级，也不得作为实现、规则或 API 契约的依据。

归档文档原则上保持冻结，只允许修正损坏链接、补充归档元数据或处理安全问题。需要恢复某项历史方案时，应基于当前 requirements 和 ADR 重新设计，不能直接把归档内容恢复为 Active。

## Archived Documents

| 当前路径 | 原路径 | 归档日期 | 原因 | 当前替代 |
|---|---|---|---|---|
| `design/90-import-json-mapping.md` | `docs/design/90-import-json-mapping.md` | 2026-07-31 | Import JSON 方案已被正式决策放弃。 | `docs/adr/ADR-0004-schemair-and-workbook-artifacts.md`、`docs/adr/ADR-0007-interface-standard-and-template-irs.md` |
| `reference/01-architecture-reference.md` | `docs/reference/01-architecture-reference.md` | 2026-07-31 | 旧架构草案未覆盖当前 InterfaceStandardIR / InterfaceTemplateIR 和可信链路，且已由正式系统设计替代。 | `docs/design/01-system-overview.md` |
| `reference/02-api-contract-draft.md` | `docs/reference/02-api-contract-draft.md` | 2026-07-31 | 未接受的 API 草案使用旧状态和旧 Workbook 契约。 | 尚无正式 API；未来设计以 requirements、ADR 和 system overview 为输入。 |
| `reference/03-docir-schemair-draft.md` | `docs/reference/03-docir-schemair-draft.md` | 2026-07-31 | 早期 IR 草案已被正式四层 IR 设计替代。 | `docs/design/02-intermediate-representations.md`、`docs/design/03-ir-field-reference.md`、`docs/design/04-system-configuration-model.md` |
| `reference/04-prompt-drafts.md` | `docs/reference/04-prompt-drafts.md` | 2026-07-31 | Prompt 结构未覆盖当前 envelope、evidence、InterfaceStandardIR 和 InterfaceTemplateIR 契约。 | 尚无正式 Prompt；未来实现以当前 IR 设计和规则包为输入。 |

## Archive Rules

- Superseded ADR 继续保留在 `docs/adr/`，不移入 archive。
- 当前仍用于设计、验证或 golden sample 的参考输入继续保留在 `docs/reference/`。
- Draft、Placeholder 不自动等于废弃；只有明确不再作为当前设计输入的材料才归档。
- Active 目录不再使用 `90-99` 表示历史文档；历史状态统一由 `docs/archive/` 承载。
- 归档文件可以保留原文件名和编号，以便追踪历史链接。
