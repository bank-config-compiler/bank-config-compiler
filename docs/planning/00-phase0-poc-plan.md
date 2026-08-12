# Phase0-PoC 执行计划

## Status

**In Progress。当前唯一未完成主任务是 P0-T5：真实 LLM Draft-to-Workbook 验证。**

P0-T3 trusted chain 与 P0-T4 deterministic Draft-to-Workbook closure 已完成。P0-T5 的真实 provider adapter、严格流式传输、结构化 DocIR extraction、确定性 renderer/review notes、有界分段、attempt v2 evidence 和物理 subcall 绝对期限也已完成离线实现。

最新真实 attempt `docir-019` 的 Interface/Envelope 与联合 messages outline 均通过机械门禁；首个 ASSEMBLY detail 完整返回后，因 16 行中 4 行未包含空 wire 值所需的固定 Review 标记而原子失败，未发布 DocIR Draft。当前没有通过 Human Review 的真实 DocIR candidate，`docir-020` 未启动。下一步是完成 Proposed ADR-0015 的设计决策，而不是直接继续付费重跑。

本文档是 Phase0 的执行 source of truth：记录当前状态、剩余顺序、验收门禁和 commit 边界。阶段范围以 `docs/01-requirements.md` 与 `docs/phases/00-phase0-poc.md` 为准；长期设计理由以 `docs/adr/` 为准；字段级 contract 和 Workbook 投影细节以 `docs/design/`、schema、代码与测试为准。本文档不再重复这些实现说明。

## 1. 目标与不可变边界

### 1.1 目标链路

Phase0-PoC 要证明一条无 UI、可重复运行、可校验、可人工确认、可回归的可信链路：

```text
Raw Docs
→ DocIR Draft / Human Review / Final DocIR
→ SchemaIR Draft / Validator / Human Review / Final SchemaIR
→ InterfaceStandardIR Draft / Validator / Human Review / Final Standard
→ InterfaceTemplateIR Draft / Validator / Human Review / Final Template
→ deterministic Configuration Workbook
→ structured regression
```

P0-T3/P0-T4 已用 deterministic fixture 证明机械闭环；P0-T5 必须再用获准的真实 OpenAI-compatible Chat API 完成六个真实 Draft、逐层 Review/Final 和双方向 Workbook，fixture 不能替代该验收。

### 1.2 可信边界

- LLM、Agent 或 workflow 只能生成 Draft，不能生成可信 Final。
- Validator 负责结构、引用、生命周期和确定性 invariant；Validator 通过不等于业务正确。
- Human Review 负责来源忠实度、语义映射、冲突与不确定项，并只批准准确内容 hash。
- Workbook Generator 只消费 Final SchemaIR、对应方向的 Final Standard/Template、三份与 Final 内容完整匹配的 validation result、精确 RELEASED 规则版本和显式 Standard Action。
- 不自动 promotion，不新增 Golden evaluator，不用历史 Golden 自动判定新银行文档的语义正确性。

### 1.3 通用产品与 PoC 样例的边界

- 系统不是 `b2e0061` 专用转换器。该样例只验证通用 contract 和工具链，不能成为 runtime 的专用规则来源。
- 银行字段到目标系统字段的语义映射不能由代码硬编码，也不能从相近接口、正式导出或模型常识补猜；候选映射来自当前输入与规则，并由 Human Review 决定。
- 代码可以确定性生成 index、固定 Review 标记、hash、生命周期、排序、Markdown/JSON 和 Workbook 投影，但不能创造业务映射事实。
- Phase0 只用一份获准的脱敏 XML 银行接口文档做真实验证，不据此声称已证明多银行泛化。

### 1.4 Phase0 不实施

- UI、审批流、多用户权限。
- JSON 银行报文、PDF/OCR/富文档解析。
- 目标系统 Import JSON/API、生产连接、Excel 反向导入。
- 目的系统业务 Condition、多目标行运行时选择、RAG、多 Agent、自动规则学习或自动微调。

## 2. 当前阶段状态

### 2.1 Task 总览

| Task | 状态 | 已满足的完成标志 | 当前动作 |
|---|---|---|---|
| P0-T0 Bootstrap | Done | `ingest`、`check --profile raw` 与严格 workspace 输入边界可运行 | 无 |
| P0-T1 IR candidate / Review | Done | 样例 DocIR/SchemaIR candidate 经 Review，正式 IR 与 reference 边界明确 | 无 |
| P0-T2 Review Golden boundary | Done | 审查前 Golden 保持独立且 byte-stable | 无 |
| P0-T3 Trusted chain | Done | 规则包、三类 Final IR/Validator、双方向 Workbook 与完整 regression 闭合 | 保持回归 |
| P0-T4 Draft generators | Done | provider-neutral contract、六个 fixture Draft、Human Review gate 与 deterministic closure 闭合 | 保持回归 |
| P0-T5 真实 LLM 验证 | In Progress | 离线 runtime 已完成；尚无真实 Final DocIR、下游真实 Final chain 或双方向 Workbook | 先完成 ADR-0015 设计 Gate |

### 2.2 已完成能力基线

| 能力 | 当前基线 | 权威证据 |
|---|---|---|
| 规则 | `configuration-rules/v1`、v2 均为不可变 RELEASED；Standard 绑定 v1，Template 绑定 v2 | 规则包及其 Review/README |
| SchemaIR | `schemair/v2`、canonical hash/result、XML-only、encoding evidence、Condition 与 Final gate | `samples/trusted-chain/b2eboc-b2e0061/` |
| Standard | `interface-standard/v1`、Validator、ASSEMBLY/PARSE Final/results/Review | 同上 `standards/` |
| Template | `interface-template/v1`、Validator、六种 Value Mode、binding、omission、Mapping/Replacement contract | 同上 `templates/` |
| Workbook | 完整 Final/result/rule gate、固定七 sheet、安全文本、原子发布、双方向 Golden | 两份 `configuration-workbook.xlsx` 与 Workbook tests |
| Workspace/CLI | 显式 `Phase0Selection`、`check --profile phase0`、`generate-workbook`、`generate-draft` | runtime、CLI tests 与根 README |
| Draft baseline | `DraftProvider`、严格 response/case、六个 deterministic responses、无自动 promotion | P0-T4 regression |
| 真实 provider | 流式 Chat adapter、显式配置、DocIR 分段、v2 evidence、无 SDK retry、物理绝对期限 | ADR-0012/0013/0014、Commit 8A1–8A4 |

`b2e0061` trusted-chain 的关键冻结 hash：

| Artifact | Hash |
|---|---|
| Final DocIR fixture | `sha256:31d7fc002ccc2b840f401206f54665e36771f2bb5502d480566defdff9ac7585` |
| Final SchemaIR | `sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162` |
| ASSEMBLY Final Standard | `sha256:9c77e0e92447907fa89d6ef705501dc0947d695998b80bb154476f696e9b982e` |
| PARSE Final Standard | `sha256:33efa544460ac19f216734712c1e6ae2610321ea17eb750eff35493ecca9d57e` |
| ASSEMBLY Final Template | `sha256:b9966a449ddc29e08fa29c6cf7838273ce3cab91e00dbb38092767d21af2f561` |
| PARSE Final Template | `sha256:16eb305b6ac3944f28cb1060b943fdfc2d471f69e6bf8ea52ce059c797fb22f9` |

这些 hash 证明 fixture trusted chain 的准确审查边界，不是新接口的语义 Golden。

### 2.3 尚未完成

- 还没有真实 DocIR candidate 通过全部机械门禁和独立 Human Review。
- 还没有基于真实 Final DocIR 生成并冻结真实 SchemaIR。
- 还没有真实 ASSEMBLY/PARSE Standard 和 Template Draft/Final/Review chain。
- 还没有两条真实 Final chain 通过 `check --profile phase0` 并生成、验证 Workbook。
- ADR-0015 仍为 Proposed；Validator-guided 单次修正、Structured Outputs 的验收角色和修正 evidence 语义尚未确认。

因此 P0-T5 与 Phase0-PoC 都不能标记为 Done。

## 3. P0-T5：当前证据与执行计划

### 3.1 真实 DocIR evidence 摘要

| Attempt | 结果 | 对计划的影响 |
|---|---|---|
| `docir-005`–`011` | 长流可完成，但 Markdown、外层 envelope 或单响应完整性不稳定 | 形成 ADR-0013 的结构化 extraction 与 ADR-0014 的分段方案 |
| `docir-012`–`016` | 依次暴露 `sourceContext` shape、segment 职责、空值 Review 与 index/name 格式问题 | Prompt 收紧到 v12；说明多次返回内容基本可读，但局部机械合同仍有方差 |
| `docir-017` | Interface/Envelope 通过；联合 outline `ReadTimeout`，无完整 response/usage/finish reason | 定位 scalar I/O timeout 不等于物理总期限；Commit 8A4 增加绝对墙钟 watchdog |
| `docir-018` | 首段请求约 5 秒内 `APIConnectionError`；后续 TLS/HTTP 诊断未复现持续故障 | 归类为该 attempt 的瞬时 transport failure，不归因于 Prompt/Validator/deadline |
| `docir-019` | 前两段通过；首个 16-field ASSEMBLY detail 完整 `stop`/usage 后，4 行漏固定 Review 标记 | 证明当前主要阻塞可表现为 complete-but-invalid candidate；触发 ADR-0015 评审 |

当前准确 evidence：

- `workspace/phase0-real-20260812-docir-018/docir-provider-failure-result.json`
- `workspace/phase0-real-20260812-docir-019/docir-provider-failure-result.json`
- `docir-019` 三个物理调用共 36,372 tokens；失败摘要文件 hash 为 `sha256:36fe89a9db7cfdfabd2b4dfc56f830bbb3defc5954f0ba06d37cbd6ed0523641`。

真实 workspace 与失败响应均为被 Git 忽略的诊断 evidence，不是 Draft、Final 或 trusted-chain artifact；不得清理、重写或复用旧 attempt 的成功前缀。

### 3.2 当前生效的运行时合同

- provider/model 由运行时显式选择；系统只要求 OpenAI-compatible Chat API，不绑定单一厂商。
- API key、HTTPS base URL、精确 model ID 和 timeout 只从白名单环境配置或显式非敏感 CLI 参数进入；secret、endpoint 原文和银行原文不得写入日志或版本库。
- 编排层只向 provider 提供当前准确上游内容、source hash、selector 和适用 RELEASED 规则；provider 不扫描 workspace，也不读取 Final/Golden 作为新接口事实。
- 每个物理 subcall 必须同时满足 `finish_reason=stop`、最终 usage、完整 JSON 和当前 segment contract；否则 fail closed。
- 同一个 timeout 同时作为 SDK connect/read/write/pool I/O 上限与物理 subcall 绝对墙钟期限；期限覆盖 stream create 和完整迭代。
- DocIR 顺序固定为 Interface/Envelope → 联合 ASSEMBLY/PARSE outline → ASSEMBLY detail batches → PARSE detail batches → 完整 extraction 校验 → 确定性 Markdown/Review Notes。
- field detail 默认每批最多 16 行；只能在新 DocIR attempt 开始前通过显式正整数 CLI 参数调整，不能在失败后作为 resume 参数继续旧 attempt。
- segment、outline 和内部 `docir-extraction/v1` 不落盘、不成为公开 IR；成功只发布一个 DocIR Draft。
- 当前 Accepted 语义仍是 ADR-0014：SDK 自动 retry 关闭，attempt fail-fast、不 resume；失败后必须以新 attempt ID 从第一段开始。
- 成功/失败保存 v2 attempt evidence；失败 evidence 不授权继续下游或自动发起下一次付费调用。

### 3.3 ADR-0015 设计 Gate

ADR-0015 当前仅为 Proposed。它比较四个方向：继续调 Prompt/batch、将 Structured Outputs 作为可选 provider capability、由代码承担更多机械生成、以及 Validator-guided 单次修正。

进入任何实现前必须确认：

1. 是否接受“最终严格 Validator 不变，但 complete-but-invalid candidate 最多获得一次校验反馈修正”。真正放宽 Final Validator 不在当前推荐语义内。
2. 修正应重生成整个 DocIR，还是只替换失败 segment。两者的成本、语义漂移和 evidence 状态机不同，不能在编码时默认选择。
3. 哪些失败 eligible。当前候选边界是仅完整响应的本地 contract/Validator 失败；request/connection/deadline、流中断、refusal 或 incomplete response 仍立即失败。
4. Validator 是否先聚合全部问题，以及 original/correction 是否需要 evidence contract 升版。
5. Structured Outputs 是 P0-T5 早期 provider/model 选择条件，还是仅作为可选优化。无论哪种，本地严格校验都必须保留。

Gate 未完成前：

- 不实现修正逻辑，不改变 Prompt、Validator、provider/evidence contract；
- 不启动 `docir-020`；
- 不把 ADR-0015 视为对 ADR-0014 的隐式修订。

### 3.4 Gate 后的执行顺序

1. **冻结设计。** 将 ADR-0015 更新为 Accepted 或明确不采用，并同步本计划。若决定改变 runtime，先补充一个可独立回滚、具有确切 Files/Completion/Verification/Next 条件的实现 commit plan。
2. **条件性离线实现。** 仅在 Accepted 设计要求代码变化时，以 TDD 完成专项与完整 pytest、build、docs-sync、diff/BOM/secret 检查；不得在离线门禁通过前访问真实 provider。
3. **重新生成真实 DocIR。** 另获用户授权，使用全新 attempt ID 从 Interface/Envelope 开始；不得复用 `docir-019` 前两段或任何旧 attempt prefix。
4. **独立 Review Final DocIR。** 机械门禁通过后停止，向用户展示完整 candidate、Review Notes 与准确 bytes hash；只有用户批准该 hash 才能冻结 Final DocIR。
5. **生成真实 SchemaIR。** 只消费获批 Final DocIR；生成 Draft、运行 Draft Validator、Human Review、冻结 Final，再生成匹配的 Final validation result。
6. **生成双方向 Standard。** ASSEMBLY/PARSE 分别只消费同一 Final SchemaIR 和适用 RELEASED 规则；各自 Draft、Review、Final、validation result 独立完成。
7. **生成双方向 Template。** 每个方向只消费精确绑定的 Final Standard 和适用 RELEASED 规则；各自 Draft、Review、Final、validation result 独立完成。
8. **闭合两条 trusted chain。** 分别执行 `check --profile phase0`，再生成 ASSEMBLY/PARSE Workbook，并做结构化回读、公式/宏/外链和敏感信息检查。
9. **判定 Phase0。** 只有第 4 节全部门禁通过，才能将 P0-T5 与 Phase0-PoC 改为 Done。

所有新的真实 provider attempt 都必须显式授权、使用唯一 attempt ID，并保留失败 evidence。任何上游 Draft 未冻结为准确 Final 时，不得提前调用下游。

### 3.5 Human Review Gate

| Artifact | Draft 机器门禁 | Human 必须确认 | Final 门禁 |
|---|---|---|---|
| DocIR | 全部 subcall、完整 extraction、确定性 Markdown wire 与最小结构检查通过 | 来源忠实度、字段完整性、冲突、不确定项与准确 bytes hash | 只有获批 hash 可写入 `docir-final.md` |
| SchemaIR | 0 ERROR、`DRAFT/PENDING`、`finalEligible=false` | 银行字段、层级、类型、约束、encoding、condition、evidence 与准确 hash | `FINAL/APPROVED` 后重新校验，result 与内容完整匹配且 `finalEligible=true` |
| ASSEMBLY/PARSE Standard | 各自 0 ERROR、`DRAFT/PENDING` | 路径、类型、XML Keys、三态约束、银行 Condition、差异与准确 hash | 两方向分别具有匹配 Final result |
| ASSEMBLY/PARSE Template | 各自 0 ERROR、`DRAFT/PENDING` | function、Mapping/Replacement、processing、binding、omission 与准确 hash | 两方向分别具有匹配 Final result |

Review 必须逐层、逐 artifact 完成；不能在最后一次集中批准，也不能由 Agent、Validator 或测试 fixture 代替。

## 4. 验收门禁

### 4.1 P0-T5 完成标志

- [ ] DocIR、SchemaIR、ASSEMBLY/PARSE Standard、ASSEMBLY/PARSE Template 共六个 Draft 均由真实 adapter 发起并成功发布；fixture 未替代任何一个。
- [ ] DocIR 的所有 subcall、合并、Markdown wire 和 Human Review rubric 通过。
- [ ] 五份 JSON Draft 均为 0 ERROR、`DRAFT/PENDING`、`finalEligible=false`。
- [ ] 六个 artifact 均有独立具名 Human Review、准确内容 hash 和可追溯结论；未发生自动 promotion。
- [ ] SchemaIR、双方向 Standard、双方向 Template 的 Final 均有内容匹配且 `finalEligible=true` 的 validation result。
- [ ] ASSEMBLY/PARSE 两条 Final chain 分别通过 `check --profile phase0`。
- [ ] 两份 Workbook 均可打开并通过结构化回读；不存在业务公式、宏、外链、`<REDACTED>`、Mapping entries/target 或安全输入真实值泄漏。
- [ ] fixture regression、完整 pytest、build、docs-sync、UTF-8 no BOM、diff 和 secret 检查继续通过。
- [ ] 经数据保留审查后保存最小非敏感运行摘要；真实 artifact 不自动加入 Git。

### 4.2 Phase0-PoC 最终状态

| Gate | 状态 | 证据 |
|---|---|---|
| P0-T3 trusted chain | PASS | Final IR/results、RELEASED 规则、双方向 Golden Workbook 与 regression |
| P0-T4 deterministic Draft-to-Workbook | PASS | 六个 fixture Draft、显式 Human Review fixture gate 与双方向 closure |
| P0-T5 real LLM Draft-to-Workbook | IN PROGRESS | 离线 runtime 已完成；真实 DocIR/下游 Final chain 尚缺 |
| Phase0-PoC | IN PROGRESS | 必须等待 P0-T5 全部完成标志 |

P0-T5 完成前，不得进入 Phase1 planning，也不得把局部真实调用成功、Validator 通过或 fixture closure 表述为 Phase0 完成。

### 4.3 每个实现批次的验证

- 对应模块字段级、引用级和失败路径 UT。
- `uv --cache-dir .uv-cache run --group dev pytest -q -p no:cacheprovider --basetemp .pytest-p0`
- `uv lock --check`
- `uv --cache-dir .uv-cache build --out-dir tmp/build-phase0`
- `git diff --check`
- 所有文本 UTF-8 no BOM；Rule ID、内部链接和 artifact reference 闭合。
- 对真实/脱敏 fixture、日志、evidence 和待提交文件执行高置信 secret/固定敏感值扫描。
- coherent code batch 完成后运行 docs-sync；用户可见命令、配置、artifact、验证方式或阶段状态变化时强制检查根 `README.md`。
- 真实调用验证与离线自动化证据分开报告；网络成功不能替代 contract/Review，fixture 成功不能替代真实 provider evidence。

## 5. 决策与 Commit Plan

### 5.1 已完成的 P0-T5 基础批次

| Batch | 状态 | 完成边界 |
|---|---|---|
| Commit 8A1 | Done | 真实 OpenAI-compatible provider、显式配置、严格流式 transport、成功/失败 evidence 与 mock transport tests |
| Commit 8A2 | Done | `docir-extraction/v1`、严格结构化校验、确定性 Markdown/Review Notes renderer；ADR-0013 |
| Commit 8A3 | Done | DocIR 有界分段、exact outline coverage、原子 merge、attempt evidence v2；ADR-0014 |
| Commit 8A4 / `25e03ce` | Done | stream create/iterate 物理绝对期限、稳定 deadline 分类与非敏感诊断；231 项 warnings-as-errors pytest、build/docs-sync/diff/BOM/secret 通过 |

这些批次已经完成，不在本文档重复其逐文件实施过程；准确决策和修订历史见 ADR-0012/0013/0014 与 Git。

### 5.2 当前 Gate：ADR-0015

- **性质**：设计 Gate，不是实现 commit。
- **Files**：`docs/adr/ADR-0015-llm-draft-reliability-options.md`、本计划。
- **完成标志**：第 3.3 节五个问题得到明确结论；ADR 状态与 ADR-0014 的关系清楚；P0-T5 最终门禁不变。
- **验证**：无未决语义被写成 Accepted；无 runtime、Prompt、Validator 或 evidence contract 被提前修改。
- **下一步条件**：若不改 runtime，进入新的真实 attempt 授权；若改 runtime，先新增并执行独立 implementation commit plan。

### 5.3 条件性实现批次

ADR-0015 未 Accepted 前，不存在可执行的实现 commit。不能提前假设“整份 DocIR 修正”或“失败 segment 修正”，也不能提前确定 evidence 是否升版。

如果最终决定改变行为，必须先在本节补齐：

- 精确 Scope 与非目标；
- code/tests/docs 的确切 Files；
- Red-Green-Refactor 验证点；
- Completion signal、兼容性和 evidence readback；
- 下一次真实调用的开始条件。

补齐并获确认前不得实施。

### 5.4 Commit 8B：真实 LLM 验收与 Phase0 状态收束

- **Scope**：按第 3.4 节依次完成六个真实 Draft、逐层 Review/Final validation、双方向 `phase0` check 与 Workbook；Git 只记录经批准的非敏感验收摘要和阶段状态，不自动提交真实业务 artifact。
- **Files（Git）**：`docs/planning/00-phase0-poc-plan.md`、`docs/phases/00-phase0-poc.md`、根 `README.md`；`workspace/phase0-real-*` 继续被 Git 忽略。
- **完成标志**：第 4.1 节全部勾选，P0-T5 与 Phase0-PoC 状态可改为 Done。
- **验证**：双方向 `check --profile phase0`、Workbook 结构化/安全检查、完整 pytest、build、docs-sync、BOM/diff/secret 检查和人工 Review readback。
- **下一步条件**：Phase0 最终状态经证据复核；只有确认 Done 后才可开始 Phase1 planning。

Commit 8B 只有在 ADR-0015 Gate 已关闭、任何条件性实现已通过全部离线验证、且用户重新授权真实调用后才能开始。

## 6. 历史实施索引

以下只用于定位已完成边界，不再作为当前执行顺序：

| 阶段 | 历史批次 | 结果 |
|---|---|---|
| 范围与规则事实 | PR #12 / `2de9f69`、Commit 1–2 | requirements/design/ADR 收束，`configuration-rules/v1` 发布 |
| SchemaIR | Commit 3A–3B | SchemaIR v2 runtime、Draft/Review、Final/result 冻结 |
| Standard 与规则投影 | Commit 4A–4D | 双方向 Standard Final；`configuration-rules/v2` 修订并发布 |
| Template | Commit 5A–5B | 双方向 Template Final/results/Review 冻结 |
| Workbook | Commit 6A–6B | 核心 Generator、workspace/CLI、双方向 Golden 与 regression |
| Deterministic Draft closure | Commit 7A–7D + Human Review Gate | provider-neutral runtime、Final DocIR fixture、完整 Draft-to-Workbook closure |
| 真实 provider 基础 | Commit 8A1–8A4 | transport、结构化 DocIR、分段 evidence、物理绝对期限 |

历史批次的详细 contract、取舍、hash 与实现细节分别由 ADR、`samples/trusted-chain/`、`docs/design/`、代码、测试和 Git 保存；本计划不再维护第二份逐 commit 流水账。

## 7. 权威参考

| 主题 | Source of truth |
|---|---|
| Phase0 需求与范围 | `docs/01-requirements.md`、`docs/phases/00-phase0-poc.md` |
| Human Review 与 Final 边界 | ADR-0001、ADR-0012 |
| Standard/Template/Workbook 数据模型 | ADR-0007–0010、`docs/design/02-intermediate-representations.md`、`docs/design/05-configuration-workbook.md` |
| 真实 provider 与 evidence | ADR-0012 |
| DocIR 结构化 extraction / renderer | ADR-0013 |
| DocIR 分段与 attempt 原子性 | ADR-0014 |
| Draft 可靠性方案讨论 | ADR-0015（Proposed） |
| deterministic trusted chain evidence | `samples/trusted-chain/b2eboc-b2e0061/` |
| 当前真实失败 evidence | `workspace/phase0-real-20260812-docir-018/`、`workspace/phase0-real-20260812-docir-019/` |

若本文档与 Accepted ADR、当前代码/测试或准确真实 evidence 冲突，应停止执行，先修正文档或明确 superseding decision，不得以相近概念补全。
