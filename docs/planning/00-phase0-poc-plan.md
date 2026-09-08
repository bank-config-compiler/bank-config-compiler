# Phase0-PoC 执行计划

## Status

**In Progress。修正后的 Final DocIR 已获批；`schemair-005` 至 `schemair-007` 已消费且未形成可批准 SchemaIR。当前实施 F-007 修订版：可恢复分段、完整 fingerprint 复用和分层验证；离线完成前不得准备新的真实调用。**

P0-T3 trusted chain、P0-T4 deterministic Draft-to-Workbook closure 与历史 P0-T5 真实 DocIR Human Gate 已完成。`docir-026` 经 Human 修订后形成准确 Final DocIR `sha256:04e8e71b773dfb3f2203fe4ed10a30475fdbf1876d481bbe5fd9db9d1040258b`，0 ERROR、1 个已接受的非阻塞 `actacn` WARNING。`schemair-004` 以 batch 8 完成 9 个 subcall，使用 77,742 tokens并发布 16 ERROR、4 WARNING 的 Invalid Draft。`schemair-005` 在 metadata 调用超时，`schemair-006` 因已下架模型被拒绝，均未形成 Draft。更新模型后，`schemair-007` 已获得前 7 个有效段和完整第 8 段，但旧 validator 因 PARSE scalar 回显 `required:null` hard fail，第 9 段未执行；该 attempt 使用 109,896 tokens、耗时 28 分 59 秒。所有历史 attempt 保持 immutable；修订版 F-007 只离线验证兼容恢复，不自动调用 provider。

## 1. 目标与可信边界

```text
Raw Docs
→ DocIR Draft / validate / Human Review / Final DocIR
→ SchemaIR Draft / validate / Human Review / Final SchemaIR
→ ASSEMBLY/PARSE Standard Draft / validate / Human Review / Final Standard
→ ASSEMBLY/PARSE Template Draft / validate / Human Review / Final Template
→ deterministic Configuration Workbook
→ structured regression
```

- LLM、Agent 或 workflow 只能提出 Draft 语义，不能生成可信 Final。
- 代码负责显式身份和可唯一重算的机械投影，不创造银行或目标系统业务事实。
- Validator 证明结构、引用、生命周期和确定性 invariant，不证明 raw-doc 完整性或业务正确。
- Human approval 必须绑定当前准确内容 hash；任何修改都令旧 validation/approval 失效。
- DocIR、Standard、Template 的真实 provider attempt 不自动 retry/resume。SchemaIR 只允许 ADR-0021 规定的当前段有界重试和显式 fingerprint 复用；临时 response/candidate 不进入 Git。

## 2. Task 状态

| Task | 状态 | 完成标志 |
|---|---|---|
| P0-T0 Bootstrap | Done | `ingest`、raw workspace 边界 |
| P0-T1 IR candidate / Review | Done | DocIR/SchemaIR candidate 与 Review boundary |
| P0-T2 Review Golden boundary | Done | 审查前 Golden byte-stable |
| P0-T3 Trusted chain | Done | Final IR、Validator、规则和双方向 Workbook |
| P0-T4 Draft generators | Done | provider-neutral fixture 六 Draft closure |
| P0-T5 可信基础与真实 DocIR | Done | `docir-022` 真实 Final DocIR 已批准：`sha256:180dadcc10fea5cf364c72e7b36d6d36aad3bfc24d3edd172138b24869042ae6` |
| P0-T6 下游收割与 Phase0 收口 | In Progress | runtime 已离线实现；仍需五份下游真实 Final、双向 check/Workbook |

P0-T5 Done 不代表 Phase0 Done，也不授权进入 Phase1 planning。

## 3. P0-T5：可信基础与真实 DocIR

### 3.1 实现范围

1. 接受 ADR-0015，并同步 README、requirements、phase、design 和本计划。
2. 增加 `phase0-task/v1`、不可复用 attempt 目录、`draft-generation-result/v1` 和 CLI `0/2/3` 结果语义。
3. 增加内部 `docir-semantic-candidate/v2`，由代码根据有序树分配 index、固定九列 wire 和 Review marker。
4. 增加 `docir-validation-result/v1`、`validate-draft docir` 和 hash-bound `approve-draft docir`。
5. 离线全量门禁通过后，另获授权启动全新真实 attempt；Human 修改、重验并批准准确 hash 后形成 Final DocIR。

### 3.2 完成标志

- [x] hard failure 不发布 Draft；可物化语义缺失或值不受支持时以空值和 Review marker 发布 Invalid Draft并返回 `3`。
- [x] DocIR Validator 聚合 issues，并绑定当前 Markdown bytes hash。
- [x] attempt ID 不可覆盖；Generation Result 保持初始 lineage，不随 Human 编辑改写。
- [x] `validate-draft` 原子刷新 result/notes，不修改 Draft。
- [x] `approve-draft` 交互模式无需手输 hash；非交互模式必须显式提供 expected hash。
- [x] `draft-prompt/v18` 与 `docir-semantic-materializer/v4` 规范化 Type/非重复 Mult.，采用九列 Fields contract；Object Required=N/A，标量 Required 缺证据为 ERROR，Conditions 只接受明确条件分支；task `interfaceCode` 在 provider selector、segment Validator 和 merge 中保持 code-owned。
- [x] `docir-021` candidate 只读离线重放为 49 fields、15 ERROR；未改写其真实 Draft、validation 或 lineage。
- [x] Review Notes 由当前 attempt candidate/Draft 与 Validation Result 确定性生成，生成期间不发起额外 LLM 调用。
- [x] `docir-022` 完成 candidate → Draft → Human edit → validate → approval → Final；Final hash 为 `sha256:180dadcc10fea5cf364c72e7b36d6d36aad3bfc24d3edd172138b24869042ae6`。

## 4. P0-T6：下游收割与 Phase0 收口

P0-T6 只能消费 P0-T5 获批的 Final DocIR，并按以下顺序执行：

1. **P0-T6.1 SchemaIR**：provider 调用前校验匹配的 DocIR approval evidence 与准确 Final bytes；显式 schema identity；支持 invalid/revalidate/approve；真实 Human-approved Final SchemaIR。
2. **P0-T6.2 Standard**：代码投影 path/sequence/XML Keys；ASSEMBLY/PARSE 分别形成真实 Final。
3. **P0-T6.3 Template**：代码投影 Standard target；LLM/Human 负责 binding/expression/policy；两个方向分别形成真实 Final。
4. **P0-T6.4 Closure**：两个 `check --profile phase0`、两个 Workbook、结构化/安全检查和 Phase0 状态收口。

每一小节必须等待上一层准确 Final，不能集中到最后一次批准。

SchemaIR、Standard、Template 的 semantic materializer、统一 validate/approve CLI 和离线回归已经实现。SchemaIR generation/validation/approval 会重新校验 `docir-approval-result.json` 的 task/interface、artifact kind/path、Draft→Final hash 映射和当前 Final 准确 bytes hash。F-007 原实现按 ADR-0020 使用 `draft-prompt/v11`：一个联合 metadata segment 加按 Final DocIR selector 覆盖的 Envelope/ASSEMBLY/PARSE 有界字段批次。ADR-0021 将其修订为默认 batch 16、当前段最多重试一次、显式完整 fingerprint 复用，以及通用 Kernel 与内置 `BankXmlSchemaIRProfile` 的分层验证。`schemair-materializer/v2`、公开 SchemaIR v2 和 Standard/Template 单次 `complete-artifact` 均保持不变。该修订不把 Invalid Draft 记为 P0-T6.1 真实验收完成。

## 5. Commit Plan

| Commit | Scope | Completion | Next starts when |
|---|---|---|---|
| 1 | ADR-0015 与 P0-T5/T6 文档同步 | 所有文档表达同一状态/边界，diff/BOM 通过 | ADR 成为实现事实源 |
| 2 | task/attempt/generation lineage、原子发布、退出码 | identity、non-reuse、0/2/3 tests 通过 | 公共 lineage 稳定 |
| 3 | DocIR semantic tree/materializer/parser/Validator | tree→wire 确定性、hard/soft boundary tests 通过 | DocIR 离线生成可用 |
| 4 | `validate-draft` / `approve-draft` Human Gate | stale hash、TOCTOU、交互/非交互 tests 通过 | 可授权真实 DocIR |
| 4A | ADR-0016、DocIR v14 prompt/v2 materializer 与 occurs 投影 | Type/Mult. 机械缺口消除，Required Gate 和历史 wire 回归通过 | 可单独授权 `docir-022` |
| 4B | ADR-0017、九列 DocIR v3 contract、Required 证据门禁与 fixtures 迁移 | 十列输入 fail closed，Notes 保留原证据且不增加 provider 调用，trusted-chain regression 通过 | 可迁移 `docir-022` 当前工作 Draft |
| 4C | ADR-0018、DocIR v4 Object Required=N/A 与 SchemaIR v2 materializer | Object 不再产生虚假 Required Gate；标量 marker 明确；SchemaIR Object 出现性独立审查 | 可继续 `docir-022` 标量 Human Gate |
| 4D | ADR-0019、DocIR v17 Prompt 与 Conditions Validator | 最大笔数、格式、唯一性和一般校验不再污染 Conditions；明确条件分支与无条件占位符回归通过 | 可继续 `docir-022` Conditions Human Gate |
| 5 | 非敏感 P0-T5 真实验收摘要 | 真实 Final DocIR 与 approval evidence 确认 | P0-T6 开始 |
| 5A | P0-T6.1 DocIR approval gate、失败证据与 SchemaIR candidate contract 修复 | 审批前置、attempt evidence、v10 prompt/strict materialization 离线门禁通过；`schemair-003` 已验证 hard-fail 边界 | F-007 开始 |
| 5B | ADR-0020 与 F-007 有界 SchemaIR 分段提取 | Done：联合 metadata、默认 8 字段批次、Envelope/ASSEMBLY/PARSE selector coverage、原子 evidence、离线回归/docs-sync/review；`schemair-004` 已完成并暴露 Root Path/prompt 缺口 | 已满足；真实后续验证暴露的恢复成本转入 5C |
| 5C | ADR-0021 与 F-007 可恢复分段及分层验证 | In Progress：默认 batch 16、当前段有界重试、完整 fingerprint 显式复用、attempt budget、evidence v3、内置 Bank XML Profile | 离线 replay、全量测试、docs-sync 和独立 review 全绿后，才可准备 `schemair-008` 授权摘要 |
| 6 | SchemaIR 闭环 | 真实 Final SchemaIR | Standard 开始 |
| 7 | 两个 Standard 闭环 | 两个真实 Final Standard | Template 开始 |
| 8 | 两个 Template 闭环 | 两个真实 Final Template | closure 开始 |
| 9 | 双向 Workbook 与 Phase0 收口 | 全部门禁通过，Phase0 Done | Phase1 planning |

同一行为所需 code、tests 和已知 docs 放在同一 commit。真实调用是外部 Gate，不用网络成功替代离线 contract 证据。

## 6. 验证

每个实现批次运行目标测试与受影响回归；连贯 implementation batch 后运行 docs-sync。最终离线门禁：

```powershell
.\scripts\test.ps1
uv --cache-dir .uv-cache lock --check
uv --cache-dir .uv-cache build --out-dir tmp\build-phase0
git diff --check
```

另检查 UTF-8 no BOM、secret、Workbook 公式/宏/外链和生成物结构。真实 provider、Human approval 和离线自动化证据分别报告。

## 7. 当前阻塞

- 历史 P0-T5 已完成且 `docir-022` approval 事实保持不变；当前执行 workspace 按操作者决策不恢复该链，必须由新的 DocIR Draft 重新经过 Human Gate。`docir-023`/`docir-024`/`docir-025` 和 `schemair-001`/`schemair-002`/`schemair-003` 均已消费且不得复用。
- F-007 修订版正在消除分段失败导致的整体重跑成本：SchemaIR 将使用默认 16 字段批次、当前段有界重试、显式 fingerprint 复用和分层验证；不得覆盖 selector、猜测 Object required，或自动选择历史 evidence 绕过门禁。
- `schemair-004` 至 `schemair-007` 均已消费且保持 immutable。`schemair-007` 仅允许作为显式 resume 的离线兼容样本，预计前 8 段可由当前 Profile 重新验证且只缺 PARSE 第 2 批；不得在本轮真实续跑。修订版离线实现、docs-sync 和独立 review 完成后，只能准备 `schemair-008` 精确外发摘要，并等待新的真实调用授权。
- P0-T6 的每一层均受前一层 Human-approved Final 阻塞。
- Phase0 Done 仍受五份下游真实 Final、双方向 `check --profile phase0` 和 Workbook 验收阻塞。

若本计划与 Accepted ADR、当前代码/测试或准确真实 evidence 冲突，应停止执行并先修正文档或建立 superseding decision。
