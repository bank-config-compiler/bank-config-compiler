# Phase0-PoC 执行计划

## Status

**In Progress。P0-T5 离线实现已完成，等待真实 DocIR 与 Human Gate；P0-T6 runtime 已离线实现，但真实下游链受 Final DocIR 阻塞。**

P0-T3 trusted chain 与 P0-T4 deterministic Draft-to-Workbook closure 已完成。ADR-0015 已接受 candidate → deterministic materialization → Invalid/Reviewable Draft → Human Gate 的六类 Draft 共同策略，ADR-0016/0017 收敛 DocIR Type、非重复 Multiplicity、九列 contract、Required 证据门禁与确定性 Review Notes，ADR-0018 将 Object Required 明确为 N/A。`docir-020` 是未发布 Draft 的历史失败 attempt；`docir-021` 与 `docir-022` 均为不可复用的真实 attempt。前者保留历史 evidence；后者的根工作 Draft 已迁移并重新校验，仍需完成标量 Required 与跨字段歧义的 Human Gate。

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
- 真实 provider attempt 不自动 retry/resume，不复用旧 attempt ID；临时 response/candidate 不进入 Git。

## 2. Task 状态

| Task | 状态 | 完成标志 |
|---|---|---|
| P0-T0 Bootstrap | Done | `ingest`、raw workspace 边界 |
| P0-T1 IR candidate / Review | Done | DocIR/SchemaIR candidate 与 Review boundary |
| P0-T2 Review Golden boundary | Done | 审查前 Golden byte-stable |
| P0-T3 Trusted chain | Done | Final IR、Validator、规则和双方向 Workbook |
| P0-T4 Draft generators | Done | provider-neutral fixture 六 Draft closure |
| P0-T5 可信基础与真实 DocIR | In Progress | 公共 lineage/validation/approval 已离线实现；仍需一份真实 Final DocIR |
| P0-T6 下游收割与 Phase0 收口 | Blocked | runtime 已离线实现；仍需五份下游真实 Final、双向 check/Workbook |

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
- [x] `draft-prompt/v16` 与 `docir-semantic-materializer/v4` 规范化 Type/非重复 Mult.，采用九列 Fields contract；Object Required=N/A，标量 Required 缺证据为 ERROR。
- [x] `docir-021` candidate 只读离线重放为 49 fields、15 ERROR；未改写其真实 Draft、validation 或 lineage。
- [x] Review Notes 由当前 attempt candidate/Draft 与 Validation Result 确定性生成，生成期间不发起额外 LLM 调用。
- [ ] 一份真实 DocIR 完成 candidate → Draft → Human edit → validate → approval → Final。

## 4. P0-T6：下游收割与 Phase0 收口

P0-T6 只能消费 P0-T5 获批的 Final DocIR，并按以下顺序执行：

1. **P0-T6.1 SchemaIR**：显式 schema identity；支持 invalid/revalidate/approve；真实 Human-approved Final SchemaIR。
2. **P0-T6.2 Standard**：代码投影 path/sequence/XML Keys；ASSEMBLY/PARSE 分别形成真实 Final。
3. **P0-T6.3 Template**：代码投影 Standard target；LLM/Human 负责 binding/expression/policy；两个方向分别形成真实 Final。
4. **P0-T6.4 Closure**：两个 `check --profile phase0`、两个 Workbook、结构化/安全检查和 Phase0 状态收口。

每一小节必须等待上一层准确 Final，不能集中到最后一次批准。

SchemaIR、Standard、Template 的 semantic materializer、统一 validate/approve CLI 和离线回归已经实现。该实现不改变执行依赖：没有 P0-T5 获批的真实 Final DocIR 时，不得把 fixture closure 记为 P0-T6 真实验收。

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
| 5 | 非敏感 P0-T5 真实验收摘要 | 真实 Final DocIR 与 approval evidence 确认 | P0-T6 开始 |
| 6 | SchemaIR 闭环 | 真实 Final SchemaIR | Standard 开始 |
| 7 | 两个 Standard 闭环 | 两个真实 Final Standard | Template 开始 |
| 8 | 两个 Template 闭环 | 两个真实 Final Template | closure 开始 |
| 9 | 双向 Workbook 与 Phase0 收口 | 全部门禁通过，Phase0 Done | Phase1 planning |

同一行为所需 code、tests 和已知 docs 放在同一 commit。真实调用是外部 Gate，不用网络成功替代离线 contract 证据。

## 6. 验证

每个实现批次运行目标测试与受影响回归；连贯 implementation batch 后运行 docs-sync。最终离线门禁：

```powershell
uv --cache-dir .uv-cache run --group dev pytest -q -p no:cacheprovider --basetemp .pytest-p0
uv lock --check
uv --cache-dir .uv-cache build --out-dir tmp\build-phase0
git diff --check
```

另检查 UTF-8 no BOM、secret、Workbook 公式/宏/外链和生成物结构。真实 provider、Human approval 和离线自动化证据分别报告。

## 7. 当前阻塞

- P0-T5 真实 Final DocIR 仍需 Human 处理已迁移的 `docir-022` 当前工作 Draft中的未确认标量 Required 和跨字段歧义，并完成重验和 approval；Object Required 固定为空且不参与该门禁。准确 issue 数量与证据以当前 hash-bound Validation Result/Review Notes 为准。`docir-020`、`docir-021` 与离线重放均不得复用为 generation lineage，`docir-022` attempt evidence 不得改写。
- P0-T6 的每一层均受前一层 Human-approved Final 阻塞。
- Phase0 Done 仍受五份下游真实 Final、双方向 `check --profile phase0` 和 Workbook 验收阻塞。

若本计划与 Accepted ADR、当前代码/测试或准确真实 evidence 冲突，应停止执行并先修正文档或建立 superseding decision。
