# ADR-0014: DocIR 使用 attempt 原子化的有界分段提取

## Status

Accepted. Amends ADR-0013's single-response DocIR extraction mechanism and ADR-0012's v1 provider evidence format.

## Date

2026-08-11

## Context

ADR-0013 将 DocIR 从模型直出 Markdown 改为严格结构化提取与确定性渲染，消除了机械排版的不确定性。`docir-011` 进一步证明直接返回 extraction 根能避免外层 envelope 歧义，但模型在正常 `finish_reason=stop` 下仍只返回到不完整的 ASSEMBLY，缺少 PARSE。单次响应同时承担 Interface、Envelope、两个方向的全部字段详情，输出规模和语义跨度仍然过大。

拆分调用不能破坏现有公开 `DraftProvider`、`draft-provider-response/v1`、DocIR Markdown wire、Human Review 或 trusted-chain 边界，也不能把中间候选变成新的 workspace artifact。失败后的局部续跑会让一次 attempt 混入不同上下文或模型状态，并增加证据、恢复和一致性协议。

## Decision

- 一个 DocIR attempt 按固定顺序执行：完整 `interface-envelope` → 一个联合 `messages-outline` → ASSEMBLY 字段详情批次 → PARSE 字段详情批次 → 确定性合并、既有 extraction 校验与 renderer。
- `interface-envelope` 一次返回 Interface、Source Context 和完整 Envelope；`messages-outline` 一次同时返回 ASSEMBLY/PARSE metadata、conditions 与紧凑的 `{index,item}` 字段大纲。不得把两个方向拆成两个 outline 调用。
- 字段详情只按方向和大纲中的连续有界批次调用。默认每批最多 16 个字段；`generate-draft docir --provider openai-chat` 可通过正整数 `--docir-field-batch-size` 覆盖。该参数不进入环境变量，不适用于 fixture 或其他 artifact。
- 每个物理调用都携带同一份准确 raw-doc。字段详情调用额外携带已经校验的目标大纲 selector；selector 只限制返回字段身份与顺序，不是新的业务事实来源。
- 每个 segment 在进入下一调用前严格校验 contract、方向、batch index 与准确 outline 覆盖；最终合并必须再次通过完整 `docir-extraction/v1` 与 Markdown wire 校验。任一失败立即停止，后续 subcall 不执行。
- 一个 attempt 原子执行，不自动重试、不 resume、不复用成功前缀。失败后只能由操作者使用新的 attempt ID 从第一段重新开始；需要时可显式选择更小的 batch size。
- 公开 `DraftProvider.generate()` 与 `draft-provider-response/v1` 保持不变。内部 segment 不写 workspace，不成为公开 IR、Final 输入或 trusted-chain artifact。
- 成功与失败的 attempt 摘要升级为 `draft-provider-call-result/v2` 和 `draft-provider-failure-result/v2`，按 sequence 记录有序 `calls`：segment、outcome、response hash、model/response ID、usage、时间、Prompt/segment contract 与完成状态。非 DocIR artifact 仍记录一个 `complete-artifact` call。
- DocIR 失败时，对已收到内容的各 subcall 分别保存 `docir-provider-failure-response-<sequence>-<segment>.txt`，最后写入失败摘要作为该组 evidence 的提交标记。文件仍是被 Git 忽略的开发诊断，不是 Draft 或 trusted-chain artifact。
- 不新增 Golden evaluator。机械 contract、outline 与 merge 门禁只判断结构完整性；真实候选的字段语义、来源忠实度和完整性仍由 Human Review 判断。

## Alternatives Considered

### 保持单次完整 extraction

优点是调用与证据结构最简单；缺点是 `docir-011` 已表明输出规模可能在 transport 正常结束时仍导致语义截断，因此不再采用。

### 分别生成 ASSEMBLY/PARSE outline

优点是单次更小；缺点是两个方向缺少同一次全局字段盘点，调用数更多，也更容易产生方向间遗漏或不一致，因此采用一个联合 outline。

### 按 raw-doc 字符或 token 切片

优点是输入可控；缺点是会切断表格、示例和跨段来源关系，并需要新的文档解析与拼接语义，因此不采用。

### 自动重试失败 batch 或从成功段 resume

优点是可能减少付费重算；缺点是一次 attempt 会混合不同调用状态，需要持久 checkpoint、兼容协议和更复杂的审计语义。Phase0 没有这一需求，因此保持显式新 attempt 全量重跑。

## Consequences

- DocIR Prompt contract 升级为 `draft-prompt/v8`，物理调用数随两个方向的字段数和 batch size 确定；默认调用数为 `2 + ceil(ASSEMBLY/16) + ceil(PARSE/16)`。
- 更小批次可降低单个字段详情响应的输出压力，但增加调用数、总输入 token 与延迟；操作者在新 attempt 开始前显式选择该取舍。
- 成功仍只发布一个 DocIR Markdown Draft、Human Review Notes 和 attempt v2 摘要；失败不发布部分 Draft。
- ADR-0012/0013 中关于 v1 attempt evidence 和单响应 extraction 的描述保留为历史记录，以本 ADR 为当前约束。

### Implementation amendment (2026-08-11)

- 首次真实分段 attempt `docir-012` 的 `interface-envelope` subcall 正常结束并返回四个顶层属性，但 `sourceContext` 是 object，而 Validator 要求非空字符串数组。attempt v2 evidence 正确记录唯一失败 subcall，后续 outline/detail 未执行，也未发布部分 Draft。
- 根因是 segment prompt 只列出 `sourceContext` 属性名，未声明其 JSON shape；这是 prompt/Validator contract mismatch，不是需要放宽机械门禁的银行语义差异。
- `draft-prompt/v8` 的 Interface/Envelope response shape 现明确要求 `sourceContext` 为非空字符串数组且不得返回 object。该修正不改变 segment contract、公开 provider response、batch、merge 或 Human Review 语义；后续真实验证必须使用新 attempt ID 从第一段开始。
- 新 attempt `docir-013` 的首段正常结束，但严格 JSON 因重复属性而被拒绝；按普通 JSON 诊断时还能看到 Envelope 越过 `trans`，包含 ASSEMBLY/PARSE 根及其字段详情。该结果不是有效 Envelope，也不是有效紧凑 outline，而是一次分段职责混淆。
- `draft-prompt/v9` 将公共内容收缩为信任与输出安全边界，并为 Interface/Envelope、联合 messages outline、field details 分别定义完整且互斥的响应合同。Envelope 明确在共享 `trans` 容器截止且 `sourceContext` 不得枚举交易字段；outline 只允许 `{index,item}`；detail 骨架写入当前方向和批次并只覆盖已校验 selector。机械 Validator、公开 contract、attempt 原子性和 Human Review 边界不变。
- `docir-014` 证明 v9 的职责隔离有效：12-node Envelope 在 `trans` 截止，ASSEMBLY/PARSE outline 分别为 27/10 行且只有 `{index,item}`。首个 16-field ASSEMBLY detail 随后因空 `multiplicity`/`type`/`required` 没有对应 Review 标记而被既有 Validator 拒绝；后续批次未执行。
- 根因是 detail prompt 的 “wire value” 没有被模型执行成逐行后置条件。`draft-prompt/v10` 只加强 detail 合同：每行十个属性均必须存在；逐行检查 `multiplicity`、`type`、`required`，任一为空时 `review` 必须包含 `原文未说明，待人工确认`。不修改已经通过的 Envelope/outline 合同或 Validator。
- `docir-015` 没有进入 detail：其 13-node Envelope 仍正确在 `trans` 截止，但同一空值 Review invariant 在 Envelope 字段中随机复现并于第一段 fail-fast。这证明一次通过不足以把笼统规则视为抗模型方差。
- `draft-prompt/v11` 将同一十属性完整性和逐行空值后置检查加入 Interface/Envelope full-field 合同；outline 仍不包含任何字段详情指令。该修订统一两个 full-field 阶段与既有 Validator，不放宽门禁或改变分段职责。
- `docir-016` 证明 v11 的 Review 修订生效：空 wire 值均带固定标记，12-node Envelope 也仍在 `trans` 截止；但三个属性 index 被写成 `1.@version` 等 XML 名路径，而非纯数字层级，因此第一段仍被既有 index 门禁拒绝。
- `draft-prompt/v12` 在 Envelope 与两个方向 outline 中给出准确纯数字层级 regex，并明确 index 只编码位置、XML item/attribute 名只进入 `item`；有效 `1.1`/`@version` 与无效 `1.@version` 示例直接对应真实失败。detail 继续逐字复制已校验 outline selector，不重新生成 index。
