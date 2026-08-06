# Phase0-PoC 执行计划

## Status

Active. P0-T3 is In Progress. The rule-package loader/validator and revised BKL-subset Draft candidate regression are implemented; the next gate is maintainer/business-reviewer confirmation of the new candidate before `configuration-rules/v1` can be released.

## 1. 目标与边界

Phase0-PoC 证明一条无 UI、可重复运行、可校验、可人工确认、可回归的可信链路：

```text
Raw Docs
→ DocIR Draft / Human Review / Final DocIR
→ SchemaIR Draft / Validator / Human Review / Final SchemaIR
→ InterfaceStandardIR Draft / Validator / Human Review / Final Standard
→ InterfaceTemplateIR Draft / Validator / Human Review / Final Template
→ deterministic Configuration Workbook
→ structured golden regression
```

LLM、Agent 或 workflow 只能生成 Draft。Validator 负责结构、引用和确定性 invariant，Human Review 负责业务判断并决定 Final；Validator 通过不能自动把 Draft 提升为 Final。Workbook Generator 只消费三份 Final 模型、三份与 Final 内容匹配的通过校验结果、精确规则版本和调用者显式指定的 Standard Action。

Phase0 不实现 UI、JSON 银行报文、目标系统 Import JSON/API、Excel 反向导入、目的系统业务 Condition、多目标行选择或生产集成。PARSE 固定输出对象中的 `List` 不扩大银行报文格式范围。

## 2. 当前状态与真实实现基线

### 2.1 Task 状态

| TASK | 状态 | 依赖 | 当前阻塞点 | 完成标志 |
|---|---|---|---|---|
| P0-T0：Bootstrap | Done | 无 | 无 | `ingest`、扁平 workspace artifact 协议和 `check --profile raw\|phase0a` 已实现；该 legacy profile 将在 P0-T3 SchemaIR v2 批次中迁移。 |
| P0-T1：`b2e0061` IR candidate / Review | Done | P0-T0 | 无 | Candidate DocIR / SchemaIR 经 Human Review 更新，正式 IR 设计和 reference 边界清晰。 |
| P0-T2：Review Golden sample boundary | Done | P0-T1 | 无 | Expected DocIR、修订前 expected SchemaIR、expected review notes 和 v1 validation result 已冻结为审查前 Golden。 |
| P0-T3：Trusted chain | In Progress | P0-T2、`configuration-rules/v1` Draft | 规则运行时已完成；v1 尚待双 reviewer 发布确认，存量 SchemaIR/workspace 尚未迁移，Standard/Template/Workbook 尚未实现 | 发布规则包，完成 SchemaIR v2、两个配置 IR/Validator、Workbook 和完整 trusted-chain regression。 |
| P0-T4：Draft generators | Blocked | P0-T3 | 三个 Final contract、Validator 和 trusted-chain 尚未冻结 | Provider-neutral generator interface 与四类确定性 stub 可运行，且无法绕过 Validator/Human Review 写入 Final。 |

状态定义：

- `Done`：完成标志与验证均已满足。
- `In Progress`：已有可验证子产物，但完整完成标志未满足。
- `Next`：依赖已满足，应优先执行。
- `Blocked`：存在明确前置条件，不能开始或继续关键工作。

### 2.2 已完成证据

- `samples/golden/b2eboc-b2e0061/docir.expected.md`
- `samples/golden/b2eboc-b2e0061/schemair.expected.json`
- `samples/golden/b2eboc-b2e0061/review-notes.expected.md`
- `samples/golden/b2eboc-b2e0061/schemair-validation.expected.json`
- SchemaIR Validator v1 及自动化测试
- `configuration-rules/v1` Draft、规则解释和 Review 记录
- 规则包 safe loader、严格 schema/semantic validator、聚合错误与 Draft candidate 正反向测试
- PR #12 / merge commit `2de9f69`：最新 requirements、design、ADR amendment、reference 边界和规则事实收束

这些证据证明 DocIR/SchemaIR 的修订前 Review boundary、legacy SchemaIR Validator、P0-T3 资料契约和 Draft 规则运行时；不证明规则包已经 RELEASED，也不证明最新 SchemaIR wire、InterfaceStandardIR、InterfaceTemplateIR、Configuration Workbook 或完整可信链路已经实现。

### 2.3 存量代码差距

| 组件 | 当前实现 | 与最新契约的差距 | 迁移批次 |
|---|---|---|---|
| `schemair_validator.py` | `schemair-validation-result/v1`；接受 `XML | JSON` 和 JSON node kinds | 产品应为 XML-only；缺少 `messages[].xmlEncoding`、结构化银行 Condition、完整层级/type/occurs invariant 和输入内容 hash | P0-T3 SchemaIR v2 |
| SchemaIR validation result | 保存 summary、coverage 和 issues | 无法证明结果与当前 Final SchemaIR 内容一致；Review 修改后旧结果仍可能被误用 | P0-T3 SchemaIR v2 |
| `workspace.py` | 六个扁平 artifact；固定 `raw | phase0a` profile | 不支持分方向、版本化 Standard/Template、三个 validation result 或 Workbook | P0-T3 SchemaIR v2 起逐步迁移 |
| `cli.py` | `ingest` 和只检查文件/JSON 可解析性的 `check` | `phase0a` 命名已过期，无法验证完整 Phase0 trusted-chain | P0-T3 SchemaIR v2 / Workbook |
| 规则资产 | BKL 子集 YAML Draft、safe loader、严格 schema/semantic validator、聚合错误和正反向测试已实现 | 修订后的准确候选尚待 maintainer 与 business reviewer 重新确认发布日期和 RELEASED 结论 | P0-T3 规则发布门禁 |
| Standard / Template | 只有逻辑设计和正式导出证据 | 无 machine wire contract、Validator、Final fixture 或 validation result | P0-T3 Standard / Template |
| Workbook | 只有七个 sheet 和来源矩阵设计 | 无 openpyxl Generator、回读 assertions 或确定性 regression | P0-T3 Workbook |
| Draft generators | 未实现 | 四类核心 IR 仍依赖人工 fixture，Phase0 通过条件未满足 | P0-T4 |

当前测试通过说明 legacy baseline 与 Draft 规则运行时稳定，不能作为规则已经发布或其余 P0-T3 需求已经实现的证据。

## 3. 已确认迁移原则

### 3.1 SchemaIR 与 validation result v2

- 后续运行路径升级为 SchemaIR/validation-result v2，不维护 legacy v1 runtime。
- `messageFormat` 只允许 `XML`；SchemaIR node kind 只允许 `XML_ELEMENT`、`XML_ATTRIBUTE`、`SCALAR`。
- 每个 message 保存经 Review 的 `xmlEncoding`；b2e0061 两个方向已由 Human 与银行线下确认为 `UTF-8`。后续银行文档证据冲突必须产生 Warning 并阻止 Final，直到 Human Review 给出新结论。
- 银行文档中明确且落在 P0 子集内的条件使用结构化 `conditionalConstraints`；复杂条件继续保留 `conditionText` 和 evidence，不强行转换。
- 三类 validation result 都必须保存被校验 artifact 的稳定 identity/contract version 和内容 hash。Hash 使用 canonical UTF-8 JSON 的 SHA-256；三个 Validator 和 Workbook Generator 复用同一实现，禁止各自定义序列化口径。
- Validator 只返回是否满足结构和 Final eligibility 的机器结论，不负责写入 Final artifact 或伪造 Human Review。

### 3.2 Golden 迁移

- P0-T2 的 `docir.expected.md`、`schemair.expected.json`、`schemair-validation.expected.json` 和 `review-notes.expected.md` 保持原样，继续证明修订前 Review baseline。
- P0-T3 在独立 trusted-chain fixture 边界内新增经 Human Review 的 Final SchemaIR v2、双向 Standard/Template、三个 validation result、Workbook 和 assertions。
- Legacy fixture 不再作为当前 SchemaIR v2 Validator 的 expected output；必须增加明确拒绝 legacy contract 的测试。
- 正式 Standard/Template 导出继续只作证据，不直接成为 IR、Validator 或 Generator 输入。

### 3.3 Workspace 与 CLI

- 后续代码批次直接以 `phase0` profile 替换 `phase0a`，不提供兼容别名；`raw` profile 继续保留。
- `phase0` workspace 支持 SchemaIR、按 direction/version 保存的 Standard、按 direction/template/version 保存的 Template、三个 validation result 和 Workbook。
- artifact 协议随对应运行时批次增量实现，不能等到 Workbook 阶段再一次性补齐所有路径。
- 发生 CLI 命令、artifact、配置或验证方式变化时，同一实现 commit 必须同步根 `README.md` 和相关设计说明。

### 3.4 Human Review 是 Final 门禁

- 规则包：`deng` 与 `configuration-reviewer` 对机器校验通过的准确版本确认发布日期和 RELEASED 结论。
- SchemaIR：落实两方向已确认的 `UTF-8`，并 Review 银行字段/约束、observed evidence 和结构化 Condition；未来 encoding 证据冲突时 Warning 并阻塞 Final，直到重新确认。
- Standard：Review 路径、类型、XML Keys、三态约束、银行 Condition 以及 SchemaIR/Standard 差异。
- Template：Review function、Mapping/Replacement、processing policy、方向性绑定和 ASSEMBLY omissions。
- 任一 Draft 在人工修改后必须重新运行对应 Validator；内容 hash 不匹配的旧结果失效。
- encoding 或其他证据冲突不阻止 loader、contract 和 Validator 开发；Validator 必须报告 Warning，并阻止相关 candidate 被确认为 Final，直到 Human Review。

### 3.5 敏感信息边界

- reference 中已脱敏的固定值和 Mapping target 不得还原。
- `<REDACTED>` 只证明结构，不得成为 LITERAL、Mapping 可执行 target、fixture 或 Workbook Generator 输入。
- Final Template 使用 `FIXED_VALUE + SECURE_INPUT_REF` 保存安全引用标识，不保存或展示真实值。
- Mapping catalog 中 `redacted: true` 的规则只能用于结构/Workbook 专项验证，Final Template 必须拒绝引用。
- 每个 fixture、Workbook 和发布 PR 在提交前执行高置信 secret 与敏感固定值扫描。

## 4. P0-T3：Trusted chain 实施批次

以下包含当前逻辑实施状态和未来 Review 门禁。每个后续批次只在前置条件满足后开始，并按当时最新 `master` 创建所需开发分支。

### 4.1 规则包 loader/validator 与 RELEASED

**状态：In Progress。loader/validator 与修订后的 BKL 子集契约已完成；RELEASED 双 reviewer 门禁待重新确认。**

**边界**

- 已加入 PyYAML，唯一使用 `yaml.safe_load` 和标准 YAML 类型。
- 已加载 `rules.yaml`、`fields.yaml`、`functions.yaml`、`mappings.yaml`，校验 version/status/治理 metadata 一致。
- 已校验 Rule ID、FIELD、function code 和 `mappingRuleName` 的唯一性、类型、基数和值域。
- 已校验所有 Rule Reference 和 catalog 引用闭合；拒绝未知引用、重复 source、非法参数位置和不安全 YAML tag。
- loader 不解释银行 raw-doc，不补 alias、未确认默认值或全量 catalog；严格验证已确认的字符长度默认值 `STANDARD_1`，默认拒绝非 RELEASED 版本。

**涉及模块**

- `configuration-rules/v1/*`
- 新规则 loader/validator 模块及 tests
- `pyproject.toml`、`uv.lock` 和必要 docs-sync

**完成标志**

- v1 可由仓库代码确定性安全加载并通过正反向测试。
- 27 个 Rule ID、221 个方向 FIELD、5 个正式导出观察到的 function 和 6 个 Mapping 可解析，实际数量以发布候选机器结果为准并在 Review 中记录。
- 所有 Release Checks 关闭，`deng` 与 `configuration-reviewer` 确认日期和结论，v1 切换为 `RELEASED` 并冻结。

**验证**

- unsafe YAML、重复标识、metadata 不一致、未知引用、错误类型、非法 Mapping source 的失败测试。
- 完整 pytest、YAML safe-load、Rule ID/引用闭合、BOM 和 docs-sync。

**下一批次开始条件**

规则包 v1 已 RELEASED，且样例所需规则不存在实现者猜测值。

### 4.2 SchemaIR v2 与 workspace/CLI 迁移

**依赖：P0-T3 规则包发布可并行准备；Final Standard 前必须完成。**

**边界**

- 将现有 SchemaIR Validator 升级到 v2，删除 legacy JSON 产品枚举。
- 增加 `messages[].xmlEncoding`、结构化银行 Condition、字段层级和相容性校验。
- 增加共享 canonical JSON SHA-256 和 validation-result 内容绑定。
- 保留 P0-T2 artifacts，新增独立 P0-T3 SchemaIR v2 candidate、validation result 和 Human Review 记录。
- 将 CLI/workspace 的 `phase0a` profile 迁移为 `phase0`，首先支持 SchemaIR v2 artifact 和 validation result；保留 `raw`。

**涉及模块**

- SchemaIR contract/validator 与共享 identity/hash helper
- workspace/CLI、P0-T3 fixtures 和 tests
- README 与相关设计文档同步

**完成标志**

- JSON message format/node kind 和 legacy result 被明确拒绝。
- Validation result 能检测输入内容被修改、旧结果失效。
- b2e0061 两方向 SchemaIR v2 candidate 通过 Validator，落实已由 Human 与银行线下确认的 Final `xmlEncoding=UTF-8`，并由 Human Review 确认银行 Condition 和 observed evidence。
- `check --profile phase0a` 被移除，`check --profile phase0` 按新 artifact 协议工作。

**验证**

- 缺失/非法 encoding、JSON enum、非法父子路径、type/children/multiple 冲突、Condition 引用失败和 hash mismatch 测试。
- P0-T2 fixture 内容不变检查、新 P0-T3 golden equality、CLI 回归和完整 pytest。

**下一批次开始条件**

Final SchemaIR v2、匹配 validation result 和 Human Review 记录已冻结；修改内容必须产生新 hash 并重新 Review。

### 4.3 InterfaceStandardIR contract、Validator 与双向 fixture

**依赖：RELEASED v1、Final SchemaIR v2。**

**边界**

- 冻结 InterfaceStandardIR 和 Standard validation-result machine contract。
- 实现 stable identity/version、SchemaIR hash、方向、fieldId、sequence、parent/full path、类型和 XML Keys。
- 实现 `VALUE | NO_CONSTRAINT | UNKNOWN`、银行条件、差异、Rule References 和 Final eligibility。
- 生成人工确认的 ASSEMBLY/PARSE expected Standard，不直接复制正式导出 ID、状态或冲突事实。

**涉及模块**

- Standard contract/validator、shared validation helpers 和 tests
- 双向 Standard fixtures、validation results 和 Review 记录
- workspace artifact 支持和必要 docs-sync

**完成标志**

- `@security` 进入 Final Standard XML Keys；`vamflag` 被排除；`@lang` 只保留为 observed evidence/difference Warning。
- `b2e0061-rq`、`b2e0061-rs` 按 raw-doc `0..1000` 为 `Node`。
- `obssid` 基础 Required 与 `transtype == "2"` 条件 Required 分离。
- `UNKNOWN`、未确认差异或未完成 Human Review 阻止 Final。
- 两方向 Final Standard 和匹配 validation result 经人工确认后冻结。

**验证**

- identity/hash、path/sequence、List 拒绝、XML Keys、三态约束、Condition 引用、差异 Review 和 Rule Reference 测试。
- 双向 golden equality、字段级 issue 定位和完整 pytest。

**下一批次开始条件**

两份 Final Standard identity/version/hash 稳定并可供 Template 精确绑定。

### 4.4 InterfaceTemplateIR contract、Validator 与双向 fixture

**依赖：Final Standard fixtures、可用的 v1 FIELD/function/Mapping catalog。**

**边界**

- 冻结 Template 和 Template validation-result contract。
- 实现 Standard identity/version/hash 精确绑定与 `standardProjection.required/length/dataType` 镜像。
- 实现 `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM`、方向性 source/target、六种 Value Mode 和 XML Key expressions。
- 实现 function String 参数、递归 CONCATENATE、MAPPING、Replacement 和完整 processing policies。
- 实现 ASSEMBLY 标量 omission coverage；Node/Object 不产生 omission，PARSE 只校验实际配置 target。
- `FIXED_VALUE` payload 只允许 `LITERAL | SECURE_INPUT_REF`；Template Condition 继续 fail closed。

**涉及模块**

- Template contract/validator、expression/processing helpers 和 tests
- 双向 Template fixtures、validation results、omission Review 和专项受控 fixtures
- workspace artifact 支持和必要 docs-sync

**完成标志**

- `b2e0061-rs(Node) → paymentLineList(List)` 使用 `COLLECTION_ITEM`，两端类型独立保存。
- 标量字段必须有字段值表达式，Node/Object 不得有字段值表达式。
- 未确认 omission、未知 catalog 引用、镜像漂移、缺失 XML Key、redacted Mapping Final 引用和重复 target 均 fail closed。
- Function、Mapping/Replacement、processing policy 和 omissions 经 Human Review。
- 两方向 Final Template 与匹配 validation result 冻结。

**验证**

- 六种 Value Mode、递归/非法递归、function 参数、MAPPING unmatched error、Replacement 片段语义和 secure ref 测试。
- omission/EMPTY/Empty Handling、容器 coverage、PARSE configured targets、Standard hash mismatch 和双向 golden regression。

**下一批次开始条件**

三份 Final 模型、三份匹配校验结果和精确规则版本均已冻结。

### 4.5 Configuration Workbook 与 trusted-chain regression

**依赖：Final SchemaIR、Final Standard、Final Template 及匹配 validation results。**

**边界**

- 使用 openpyxl 为一个 `interfaceCode + direction + templateId + templateVersion` 生成一份 Workbook。
- 固定七个 sheet：`Overview`、`Interface Standard`、`Interface Template`、`Value Expressions`、`Warnings`、`Rule References`、`Legend`。
- Generator 输入增加显式 `Standard Action = CREATE | REUSE | UPDATE`，不得连接目标系统自行判断。
- 扩展 workspace/CLI 的完整 `phase0` artifact 检查和 Workbook 生成入口。
- 为 ASSEMBLY/PARSE 分别生成 Golden Workbook，并使用 openpyxl 回读结构化 assertions。

**涉及模块**

- Workbook generator、workspace/CLI 和 tests
- 双方向 workbook assertions 与 trusted-chain regression
- openpyxl 依赖、README 和相关 docs-sync

**完成标志**

- Standard 快照、Template 镜像、PARSE target、三种 binding 和两端 datatype 分列可还原。
- encoding、银行 Condition、SchemaIR/Standard 差异、已确认 omissions、Validator issues 和 Rule References 不被静默丢失。
- Value Expressions 可还原标量字段值与 XML Key expression tree；Node/Object 不产生 FIELD_VALUE 节点。
- MAPPING/Replacement 只展示 rule name，不复制 entries；SECURE_INPUT_REF 不泄露真实值。
- 相同 Final 输入、校验结果、规则版本和 Standard Action 生成相同结构化业务内容。
- P0-T3 全部验收通过后改为 `Done`，P0-T4 解锁。

**验证**

- 七个 sheet、列顺序、关键单元格/样式、Warnings、REUSE 状态和表达式树回读断言。
- Generator 对非 Final、hash mismatch、DRAFT rules、缺失 Standard Action 和敏感占位值 fail closed。
- 完整 pytest、golden regression、docs-sync、BOM、diff 和敏感信息扫描。

## 5. P0-T4：Provider-neutral Draft generators

### 5.1 技术边界

- 定义 provider-neutral Draft Generator interface，不在 Phase0 绑定 OpenAI-specific API、网络配置或模型实现。
- 为 DocIR、SchemaIR、InterfaceStandardIR、InterfaceTemplateIR 提供四个确定性 stub，用受控输入稳定生成合法 Draft。
- Provider 和 stub 只能写 Draft artifact；不得写 Final、构造 Human Review 结论或调用 Workbook Generator 绕过可信链路。
- SchemaIR generator 只输出 XML；Standard generator 必须接收 Final SchemaIR 与明确规则版本；Template generator 必须接收精确 Final Standard identity/version/hash 和规则版本。
- 外部 provider response 在信任边界处校验；缺配置、未知 catalog 或不合法输出 fail closed。
- 日志只记录 task/artifact identifier、provider、contract version 和 outcome，不记录完整银行原文、生成内容、secret 或安全固定值。

### 5.2 完成标志

- 四类 Draft generator 均可通过同一 provider contract 调用，stub 输出确定且通过对应结构校验。
- LLM/provider 输出无法直接形成 Final；人工修改后必须重新 Validator。
- Standard/Template generator 在规则版本不存在、Standard 非 Final 或 hash 不匹配时拒绝运行。
- 完整 Phase0 回归能从受控 Draft 输入经过 Validator/Human Review fixtures 生成双方向 Workbook。
- P0-T4 改为 `Done` 后，Phase0-PoC 才满足通过条件。

### 5.3 验证

- 四类 stub golden、provider error translation、非法输出、缺配置、Final 写入拒绝和敏感日志测试。
- 完整 pytest、Draft-to-Workbook regression、docs-sync 和用户命令 smoke test。

## 6. 逻辑 Commit Plan

以下 commit 是未来实施边界，不要求本计划更新预先创建对应分支或 worktree。每个实施批次开始时再从最新 `master` 建立一个普通开发分支，并通过 PR 合入。

### 已完成：P0-T3 文档与规则事实契约

- Evidence：PR #12 / merge commit `2de9f69`。
- Scope：requirements、design、ADR amendments、phase/planning、reference 和 `configuration-rules/v1` Draft。
- Completion signal：最新银行事实投影、Standard 镜像、结构绑定、Mapping/Replacement、processing policy、Human Review 和脱敏边界已一致记录；后续修订将 v1 收束为接口无关的 BKL 子集。

### Current Commit 1：DRAFT 规则包运行时

- Suggested message：`feat: add configuration rule package validation`
- Scope/Files：safe loader、严格 schema/semantic validator、聚合错误、日志保护、BKL 子集 scope、正式导出 function、业务确认 String、字符长度默认 `STANDARD_1`、tests、PyYAML dependency 和 docs-sync；v1 保持 DRAFT。
- Completion signal：Draft 候选的机器校验与完整回归通过，默认加载仍拒绝非 RELEASED 版本。
- Verification：规则正反向测试、完整 pytest、build、BOM、diff、敏感信息和引用闭合检查。
- Next starts when：向 maintainer 与 business reviewer 展示准确 commit、机器结果和候选 diff。

### Future Commit 2：发布 `configuration-rules/v1`

- Suggested message：`chore: release configuration rules v1`
- Scope/Files：四份 YAML status、确认日期、Review/README/phase/planning 状态和 RELEASED 模式测试；不增加规则事实。
- Completion signal：双 reviewer 对准确 Draft 候选确认，v1 切换为不可变 RELEASED，默认 loader 验证通过。
- Verification：RELEASED 正反向测试、完整 pytest、build、docs-sync、BOM、diff 和敏感信息检查。
- Next starts when：RELEASED v1 可以被 Final IR 精确引用。

### Future Commit 3：SchemaIR v2 与 Phase0 workspace

- Suggested message：`refactor: align SchemaIR with the XML-only contract`
- Scope/Files：SchemaIR v2、validation result/hash、workspace/CLI、P0-T3 Schema fixtures、tests 和 docs-sync。
- Completion signal：legacy runtime/profile 被替换，Final SchemaIR v2 经 Human Review 冻结。
- Verification：SchemaIR/CLI/golden/compatibility rejection tests 和完整 pytest。
- Next starts when：Final SchemaIR identity/hash/encoding 和匹配结果稳定。

### Future Commit 4：InterfaceStandardIR trusted chain

- Suggested message：`feat: add InterfaceStandardIR validation chain`
- Scope/Files：Standard contract/validator、双向 fixtures/results、workspace support、tests 和 docs-sync。
- Completion signal：双向 Final Standard 经 Human Review 冻结。
- Verification：Standard UT、golden equality、字段级 issues 和完整 pytest。
- Next starts when：Template 可以精确绑定两份 Final Standard。

### Future Commit 5：InterfaceTemplateIR trusted chain

- Suggested message：`feat: add InterfaceTemplateIR validation chain`
- Scope/Files：Template/expression/processing contract、validator、双向 fixtures/results、tests 和 docs-sync。
- Completion signal：双向 Final Template、omissions 和专项 Mapping/Replacement evidence 经 Human Review 冻结。
- Verification：Template UT、专项 fixtures、双向 golden 和完整 pytest。
- Next starts when：Workbook 所需三份 Final 与三份结果完整。

### Future Commit 6：Configuration Workbook 与完整 regression

- Suggested message：`feat: generate configuration workbooks`
- Scope/Files：openpyxl Generator、workspace/CLI、双方向 Workbook assertions、tests、dependencies 和 docs-sync。
- Completion signal：P0-T3 trusted-chain regression 完成并改为 Done。
- Verification：Workbook 回读、完整 regression、CLI smoke、pytest、BOM、diff 和敏感信息检查。
- Next starts when：P0-T4 解锁。

### Future Commit 7：四类 Draft generators

- Suggested message：`feat: add provider-neutral IR draft generators`
- Scope/Files：provider contract、四类 deterministic stub、workspace/CLI entrypoints、tests 和 docs-sync。
- Completion signal：Draft 生成不会绕过可信边界，完整 Phase0 验收闭合。
- Verification：stub/provider/错误路径/敏感日志测试和 Draft-to-Workbook regression。
- Next starts when：Phase0-PoC 满足全部通过条件，可进入 Phase1 planning。

## 7. 整体验收与验证要求

### 7.1 每个实现批次

- 对应模块的字段级/引用级正反向 UT。
- `uv --cache-dir .uv-cache run --group dev pytest -q -p no:cacheprovider --basetemp .pytest-p0`
- `git diff --check`
- UTF-8 no BOM 检查。
- Rule ID、内部链接和 artifact reference 检查。
- 真实/脱敏 fixture 与高置信 secret 扫描。
- code、tests 和已知文档同步在同一逻辑 commit；完成后运行 docs-sync。
- 用户可见命令、artifact、配置、验证方式或阶段状态变化时强制检查根 `README.md`。

### 7.2 Phase0 最终门禁

- `configuration-rules/v1` 为 RELEASED 且不可变。
- SchemaIR/Standard/Template machine contract 和 validation result contract 已冻结。
- 三份 Final artifact 均具有 Human Review 证据和匹配 validation result。
- ASSEMBLY/PARSE 的 Standard、Template 和 Workbook 均有 golden regression。
- 六种 Value Mode、MAPPING/Replacement、三种 binding、Standard 镜像、银行 Condition、XML Key expression、omission 和 secure input 均被覆盖。
- 四类 deterministic Draft generator 可运行且不能产生 Final。
- 完整链路可重复执行，不依赖未确认业务默认值、历史导出 ID 或模型常识。
