# ADR-0015: 六类 LLM Draft 的确定性物化与 Human Gate

## Status

Accepted. 本 ADR 修订 ADR-0012 的真实验证执行边界、ADR-0013 的确定性生成职责和 ADR-0014 的 fail-fast 语义；未被本 ADR 明确修改的约束继续有效。

## Date

2026-08-12

## Context

Phase0 要验证的不是“LLM 一次输出完全合格的严格 IR”，而是一条能把不可信候选收割为可信 Final 的工作流。`docir-012` 至 `docir-019` 表明，真实候选既可能因 transport/incomplete failure 完全无法使用，也可能已经包含可审查的主体语义，只违反固定 Review 标记、index 或其他机械约束。

继续要求模型直接承担身份、层级编号、路径、生命周期、固定标记和序列化，会把可确定的机械工作留在概率边界内。相反，代码也不能替代 LLM/Human 判断字段是否存在、银行语义、方向差异和目标系统映射。

六类 Draft——DocIR、SchemaIR、ASSEMBLY/PARSE InterfaceStandardIR、ASSEMBLY/PARSE InterfaceTemplateIR——需要遵守同一可信状态模型；DocIR 是第一条实现和真实验证链路。

## Decision

### Candidate、物化和公开 Draft

- LLM 返回 provider 内部、版本化的 semantic candidate；candidate 不是公开 IR，也不是下游事实源。
- 代码根据显式请求、可信上游和 RELEASED 规则注入锁定身份，并确定性生成可唯一派生的 wire 字段。
- 代码不能推导的业务语义由 LLM 提议、Human 最终确认；输入不足时保留缺失或不确定性，不得猜测。
- 公开 `draft-provider-response/v1` 与六类现有 IR contract 保持兼容。

### 最小可物化边界

DocIR candidate 必须提供无歧义、有序、可遍历的 Envelope、ASSEMBLY、PARSE 语义树。节点必须具有 XML 名称和 element/attribute 类型；attribute 不得有 children，同父同名不得重复。

- 根、父子关系、兄弟顺序或完整 detail coverage 缺失，或者出现多父、孤儿、环等结构歧义：hard failure，不发布 Draft。
- 结构树完整但 required/type/multiplicity 等语义属性缺失：代码以契约允许的空值和固定 Review marker 物化，发布 Invalid Draft。
- 结构自洽不代表对 raw-doc 完整；Validator 不承担无法由确定性输入证明的来源完整性判断。

### 字段职责

- 锁定身份：task/interface/artifact ID、version、direction、source hash、rule version。只能来自调用请求或可信上游。
- 规范化派生：DocIR index，SchemaIR path/parentPath/level/hasChildren，Standard sequence/fullPath/XML Keys。它们由当前有序结构和可信上游重算；Human 可以修正结构，但派生值必须继续满足规范。
- 业务语义：字段存在性、父子语义、兄弟顺序、required/type/multiplicity、条件、差异以及 Template binding/expression/policy。由 LLM/Human 负责。
- Template `xmlKeyExpressions` 不是结构派生；它表达目标系统配置语义。

### 状态和 Human Gate

- Provider failure：没有可物化 Draft，CLI 返回 `2`。
- Invalid Draft：完成物化但 Validation Result 含 ERROR，仍发布 `DRAFT/PENDING`，CLI 返回 `3`。
- Reviewable Draft：零 ERROR，但仍是 `DRAFT/PENDING`，CLI 返回 `0`。
- Final：Human 明确批准当前准确 hash，并通过 Final Validator 后原子发布；不得自动 promotion。

`invalid/reviewable` 是匹配 Validation Result 的派生状态，不增加 IR lifecycle enum。Phase0 不实现自动或人工触发的 LLM correction；Structured Outputs 仅是未来可选 provider capability。

### Workspace 血缘

- `phase0-task/v1` 的 `task.json` 绑定 task/interface、XML scope、raw document 和 hash。
- 每次真实调用写入不可复用的 Git-ignored attempt 目录；原始 response/candidate 是临时受控证据，可按数据保留策略清理。
- `draft-generation-result/v1` 统一记录请求、source、attempt、candidate、materializer 和初始 Draft hash；不再拆分独立 materialization result。
- Validation Result 与 Review Notes 绑定当前工作 Draft；Human 修改后必须重新生成。
- `draft-approval-result/v1` 记录获批 Draft hash、reviewer、note、时间及 Final hash。

### Phase0 任务拆分

- P0-T5：完成公共可信基础和真实 DocIR 的 candidate → materialize → Human edit → validate → approve → Final 闭环。
- P0-T6：顺序收割 SchemaIR、两个 Standard、两个 Template，最后完成双方向 `check --profile phase0` 与 Workbook 验收。
- P0-T5 Done 不代表 Phase0 Done；任何下游生成都必须等待准确上游 Human-approved Final。

## Alternatives Considered

### 继续收紧 Prompt 或减小 batch

可以改善单次成功率，但不能把固定机械 invariant 从概率边界移出，也会增加调用次数和 transport 暴露面，因此只保留为调参手段。

### Validator-guided LLM correction

会增加调用、状态机和语义漂移风险，并把 Human-first 流程重新变成模型修复流程。Phase0 不采用。

### 所有不合格响应都发布 Draft

缺少可遍历结构的空壳产物没有稳定审查语义，容易把“未生成”误解成“银行没有字段”。仅完整可物化候选可以发布 Invalid Draft。

### 分离 generation 和 materialization result

两者在 Phase0 生命周期一致且高度重叠。采用单一 generation lineage contract，只有未来 materializer 成为独立公共服务时再拆分。

## Consequences

- 需要为六类 Draft 增加 materializer、重校验和显式 approval 能力。
- 当前 DocIR outline/index contract 将演进为 code-owned selector 和有序语义树；旧 attempt 只保留历史诊断意义。
- Validator 必须能从当前结构或可信上游独立重算规范化派生字段。
- Human 可以修正业务语义和树结构，但不能改写 task/source/artifact identity。
- 真实 provider evidence、离线自动化和 Human approval 必须分别报告，不能互相替代。
