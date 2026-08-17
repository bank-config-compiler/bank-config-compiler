# ADR-0019: DocIR Conditions 只表达明确条件分支

## Status

Accepted. 本 ADR supersede ADR-0017 中“只要来源支持即可进入 Conditions”的宽泛边界；九列格式、Required 证据门禁和确定性 Review Notes 继续有效。

## Date

2026-08-13

## Context

真实 `docir-022` 将请求最大笔数、字段长度、唯一性、枚举、必填性和普通业务校验大量复制到 `Conditions`。这些事实已经属于 `Mult.`、`说明` 或 `校验点`，重复收录既降低 Human Review 可读性，也把普通约束错误表达成流程分支。

`Conditions` 的独立价值是表达 raw doc 明确写出的“条件谓词 → 结果或动作”，例如“当交易类型为 2 时，网银交易流水号必须非空”。代码可以检查当前文字是否具有明确分支形式，但不能证明该分支忠实来自 raw doc；后者仍由 LLM 提议、Human 对照原文确认。

## Decision

- ASSEMBLY/PARSE `Conditions` 只允许 raw doc 明确表达的条件分支，例如“当/如果/若 A 时/则 B”或等价的 `if ... then ... else ...`。
- 不要求必须存在 `else`；单边 `if → consequence` 仍是条件分支。
- 最大笔数、出现次数、格式、长度、枚举、唯一性、基础 Required 和一般业务校验只保留在对应字段的 `Mult.`、`说明` 或 `校验点`，不得复制到 Conditions。
- 同一条文字在条件分支前夹带普通字段约束时不合格；Conditions 只保留分支本身。
- 某方向没有明确条件分支时，使用唯一占位符“原文未提供可确认条件。”。
- Validator 对不具备明确分支形式的条目产生 blocking `DOCIR_CONDITION_NOT_EXPLICIT_BRANCH`；它只校验当前 Draft 的表达形式，不重新读取 raw doc 或自动改写条件。
- Prompt 升级为 `draft-prompt/v17`。DocIR candidate/extraction shape、九列 Markdown wire、`docir-semantic-materializer/v4` 和 Validation Result JSON shape 不变。

## Alternatives Considered

### 保留所有来源支持的字段规则

会让 Conditions 退化为字段表的重复副本，无法突出真正的条件控制关系，因此不采用。

### 由代码从 raw doc 自动抽取或重写条件

需要代码承担自然语言语义判断，并可能静默丢失或创造业务事实，超出确定性 materializer 的职责，因此不采用。

### 只依赖 Prompt，不增加 Validator

真实 attempt 已证明模型可能忽略宽泛指令；缺少 fail-closed 门禁会让污染继续进入 Human working Draft，因此不采用。

## Consequences

- Review Notes 会阻塞普通字段约束进入 Conditions，并复制原条目供 Human 定位。
- 字段事实不会因为从 Conditions 删除而丢失；它们必须仍存在于对应 Fields 内容中。
- Human 可以修改条件文字，但修改后必须重新运行 `validate-draft` 并批准准确 hash。
- 历史 provider attempt evidence 保持 immutable；仓库 fixture 和真实根工作 Draft按新边界迁移。
