# ADR-0011: Phase0-PoC 的 raw-doc 仅接受文件输入

## Status

Accepted. Partially supersedes ADR-0002 for pasted-text input only.

## Date

2026-08-10

## Context

当前 Phase0 CLI 的 `ingest` 仅接受一个 UTF-8 no BOM 的 `.md` 或 `.txt` 文件路径，并把其内容保存为 `raw-doc.md`。受控 fixture 还需要以该文件的准确 UTF-8 bytes hash 匹配响应。

ADR-0002 曾将“粘贴文本”列为输入范围，但没有定义其 CLI、stdin 或 API 入口、编码语义和可复现边界。保留这一承诺会让 Phase0 文档超出真实实现，也无法为受控 fixture 提供稳定输入。

## Decision

Phase0-PoC 的 raw-doc 输入仅支持 UTF-8 no BOM 的 `.md` 与 `.txt` 文件：

- 调用方通过 `ingest --input <file>` 显式提供文件路径。
- runtime 将文件内容保存为 workspace 中固定的 `raw-doc.md`。
- 粘贴文本、stdin、HTTP/API body 和 UI 输入均不属于 Phase0-PoC 契约。

本 ADR 仅 supersede ADR-0002 中“粘贴文本”输入范围；其余 `.md` / `.txt` 支持和富文档排除决定继续有效。

## Alternatives Considered

### 在 Phase0 增加粘贴或 stdin 输入

Pros:

- 交互式试用更直接。

Cons:

- 需要新增公开输入接口、编码与长度语义、敏感文本处理和回归用例。
- 不增加当前受控 fixture 对 Draft、Validator、Human Review 和 Workbook 链路的验证价值。

Why not chosen:

- 当前目标是使已实现的最小、可复现文件链路成为准确契约，而不是扩展输入方式。

### 保留未实现的粘贴文本承诺

Pros:

- 后续可能无需修改文档。

Cons:

- 文档与 CLI 行为不一致，使用者无法按承诺完成验证。

Why not chosen:

- Phase0 的完成状态必须以实际可运行、可回归的能力为准。

## Consequences

- Phase0 使用者必须先将原始内容保存为符合编码要求的 `.md` 或 `.txt` 文件。
- fixture 文档必须注明其精确绑定的 raw-doc，避免将相近 reference 文档误用于 hash 匹配。
- 后续若要支持粘贴、stdin 或 API 输入，必须先定义其公开契约、敏感数据边界和验证方式；该能力不会从 ADR-0002 自动继承。
