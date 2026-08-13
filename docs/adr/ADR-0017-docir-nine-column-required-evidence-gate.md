# ADR-0017: DocIR 九列格式与 Required 证据门禁

## Status

Accepted. 本 ADR supersede ADR-0016 中“DocIR Markdown 列结构保持兼容”的决定；ADR-0016 的 Type、Multiplicity 与 Required 职责划分继续有效。

## Date

2026-08-13

## Context

原 DocIR 将银行字段校验拆成“前置机校验点/格式”和“接口平台校验点”。这是 B2E 文档的来源结构，不是所有银行接口共有的模型。固定保留两列会把单一银行文档的组织方式误写成通用 DocIR contract。

`docir-022` 还暴露了另一问题：模型可能把“当某条件成立时此项必填”保留在说明中，却遗漏结构化 `Required=C`。Review Notes 旧实现只展示 `Review` 单元格，导致已存在的 Required 证据没有进入人工入口。代码可以发现有限的明确矛盾，但不能可靠解析自然语言中的主语、条件和跨字段义务，因此不能据关键词自动写回 `Y/N/C`。

## Decision

### 九列 DocIR

- Fields 固定为 `Index | Or | Message Item | Mult. | Type | Required | 说明 | 校验点 | Review`。
- 内部 candidate 使用单一 `validation` 字段。来源中的多段校验文字按原顺序保留，不增加特定银行的来源标签，也不做语义去重。
- Renderer、Validator、approval 和 SchemaIR materializer 只接受九列格式；十列格式 fail closed，不提供运行时兼容或迁移器。
- 仓库 Final、Golden 和 fixture 迁移至九列并重建 hash；Git-ignored 的历史 attempt evidence 保持原样。

### Required 证据边界

- LLM 依据当前字段上下文提议 `Y/N/C`，Human 对最终值负责。
- 代码只对同一 attempt candidate 或其 Human working Draft 中的 `说明`、`校验点`、Conditions 和 Required 做确定性一致性检查。
- 明确冲突产生 blocking ERROR；可能涉及其他字段的文本产生 WARNING。代码不得自动修改 Required，也不得重新读取 raw-doc 作第二次语义提取。
- “可空 + 条件成立时本字段必填”支持 `C`；“可空，非空时检查格式”仍支持 `N`；要求上送另一字段的文字不改变当前字段 Required。

### Review Notes

- Initial Notes 只使用同一 `docir-xxx` 的 candidate、物化 Draft 和 Validation Result。
- Human 修改后，`validate-draft` 只读取当前工作 Draft和确定性 Validation Result。
- Notes renderer 只复制 issue 与显式 Review 证据，不调用 provider 或任何其他 LLM，不翻译、概括或从 raw-doc 重新提取语义。

Contract 版本升级为 `draft-prompt/v15`、`docir-semantic-candidate/v2`、`docir-extraction/v2` 和 `docir-semantic-materializer/v3`；相关 semantic segment 升级为 v2，纯结构 messages tree contract 保持 v1。

## Alternatives Considered

### 保留两列并允许为空

仍会把 B2E 来源结构暴露为通用契约，并持续增加 DocIR 宽度，因此不采用。

### 同时接受九列和十列

会形成长期双 wire、双解析和 hash 语义。Phase 0 尚未发布外部稳定接口，选择一次性迁移并让旧格式 fail closed。

### 由代码按关键词自动填写 Required

无法可靠区分“当前字段条件必填”“非空时仅校验值”和“要求上送另一个字段”。误填会把启发式判断写入 trusted chain，因此代码只做门禁。

## Consequences

- DocIR 对不同银行文档保持通用，校验信息仍完整保留。
- 旧十列 DocIR 必须在进入当前 runtime 前完成受控迁移。
- Required 漏抽和冲突会携带原证据进入 Review Notes，但仍需要 Human 决策。
- Notes 不再接受额外 LLM 加工，生成与重验结果可由相同输入确定性复现。
