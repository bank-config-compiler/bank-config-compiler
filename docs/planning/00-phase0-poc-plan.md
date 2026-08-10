# Phase0-PoC 执行计划

## Status

In Progress. P0-T3 trusted chain 与 P0-T4 deterministic Draft-to-Workbook closure 均已完成；P0-T5 真实 LLM 全链路验证为新增完成门槛，尚未开始，Phase0-PoC 最终门禁未通过。

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
| P0-T0：Bootstrap | Done | 无 | 无 | `ingest` 与 `check --profile raw` 保留；legacy `phase0a` 已在 SchemaIR v2 批次移除。 |
| P0-T1：`b2e0061` IR candidate / Review | Done | P0-T0 | 无 | Candidate DocIR / SchemaIR 经 Human Review 更新，正式 IR 设计和 reference 边界清晰。 |
| P0-T2：Review Golden sample boundary | Done | P0-T1 | 无 | Expected DocIR、修订前 expected SchemaIR、expected review notes 和 v1 validation result 已冻结为审查前 Golden。 |
| P0-T3：Trusted chain | Done | P0-T2、`configuration-rules/v1` 与 v2 RELEASED | 无 | 两个配置 IR/Validator、Workbook 和完整 trusted-chain regression 已完成。 |
| P0-T4：Draft generators | Done | P0-T3、reviewed Final DocIR | 无 | Provider-neutral generator interface 与四类确定性 stub 可运行，显式 Human Review gate 和双方向 Workbook Golden closure 已通过。 |
| P0-T5：真实 LLM Draft-to-Workbook 验证 | Next | P0-T4、用户批准的 OpenAI-compatible Chat API provider 与测试样例 | 当前仅有 fixture provider；真实 provider、运行时配置、逐层 Review/Final evidence 和双方向 Workbook evidence 均不存在 | 真实调用六份 Draft；每层分别 Review/Final validation；ASSEMBLY/PARSE 均从该 Final chain 通过 `phase0` check 并生成 Workbook。 |

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
- SchemaIR v2 Validator、canonical hash/result helper、严格 workspace JSON I/O 及自动化测试
- `samples/trusted-chain/b2eboc-b2e0061/` 下 49-field Final、匹配 validation result 和 APPROVED review 记录；准确 hash 为 `sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162`
- `configuration-rules/v1` RELEASED、规则解释、双 reviewer 确认和 Review 记录
- `configuration-rules/v2` RELEASED：catalog 与 v1 一致，只修订 `TPL.BIND.STANDARD_PROJECTION`；准确候选 `f2cf454b53541ccfa171f8f3ede59dae9e609583` 已完成双签
- 规则包 safe loader、严格 schema/semantic validator、聚合错误与 RELEASED/DRAFT 正反向测试
- `interface-standard/v1`、Standard Validator、双方向 Final/results 与 APPROVED Review；ASSEMBLY hash `sha256:9c77e0e92447907fa89d6ef705501dc0947d695998b80bb154476f696e9b982e`，PARSE hash `sha256:33efa544460ac19f216734712c1e6ae2610321ea17eb750eff35493ecca9d57e`
- `interface-template/v1`、Template Validator、双方向 Final/results 与 APPROVED Review；ASSEMBLY hash `sha256:b9966a449ddc29e08fa29c6cf7838273ce3cab91e00dbb38092767d21af2f561`，保留 4 个经接受 omission 和 4 个非阻塞 Warning；PARSE hash `sha256:16eb305b6ac3944f28cb1060b943fdfc2d471f69e6bf8ea52ce059c797fb22f9`，0 WARNING；两者均为 0 ERROR、0 blocking、`finalEligible=true`
- Configuration Workbook 运行时、三份 result 完整相等门禁、Standard/Template 双规则版本门禁、固定七个 sheet、安全文本、脱敏日志与同目录原子发布
- 显式 `Phase0Selection`、固定六 artifact 路径、只读 `check --profile phase0` 和固定目标 `generate-workbook` CLI；不扫描、不推断最新版
- provider-neutral Draft runtime、严格 `draft-provider-response/v1` / `draft-stub-case/v1`、固定 Draft publication、`generate-draft` CLI 和六个 b2e0061 deterministic responses
- `deng` 批准的 byte-identical Final DocIR、APPROVED Review 记录和准确 bytes hash regression；hash 为 `sha256:31d7fc002ccc2b840f401206f54665e36771f2bb5502d480566defdff9ac7585`
- 提交的 ASSEMBLY/PARSE CREATE Golden Workbook 与结构化回读 regression；行数分别为 Standard 36/19、Template 26/8、Expression 30/13、Warning 38/15
- PR #12 / merge commit `2de9f69`：最新 requirements、design、ADR amendment、reference 边界和规则事实收束

这些证据与完整受控 Draft-to-Workbook regression 共同证明 P0-T3、P0-T4 已完成；它们不能替代 P0-T5 的真实 LLM 调用证据，因此不能证明 Phase0-PoC 最终门禁已完成。

### 2.3 存量代码差距

| 组件 | 当前实现 | 与最新契约的差距 | 迁移批次 |
|---|---|---|---|
| `schemair_validator.py` | `schemair/v2` 与 result v2；XML-only、encoding evidence、Condition、层级/type/occurs、lifecycle 和 hash 已实现 | 无；b2e0061 Final facts 与 Review metadata 已冻结 | 已完成 |
| SchemaIR validation result | 保存 identity/version/contract/hash、`finalEligible`、summary、coverage 和 blocking issues | 无；已存在与 Final hash 匹配且 `finalEligible=true` 的结果 | 已完成 |
| `workspace.py` | `raw` profile、受边界保护的嵌套严格 JSON I/O、不可变 `Phase0Selection`、固定链路路径和加载 | 无；`phase0` 显式选择固定六份输入 artifact 与 Workbook 输出路径 | 已完成 |
| `cli.py` | `ingest`、`check --profile raw|phase0`、`generate-workbook` 与 `generate-draft docir|schemair|standard|template`；`phase0a` 已移除 | 仅允许 `fixture` provider；缺少 OpenAI-compatible Chat API provider 的显式选择、运行时配置与安全错误上下文 | P0-T5 Commit 8A |
| 规则资产 | v1 已于 2026-08-06 发布并冻结；v2 继承 catalog 并修订方向性 Standard projection，已于 2026-08-09 发布并冻结 | 无；Template 必须显式绑定适用的 RELEASED 规则版本 | 已完成 |
| Standard | `interface-standard/v1`、result v1、Validator、双方向 Final/results 和 APPROVED Review 已实现 | 无；两份 Final identity/version/hash 已冻结 | 已完成 |
| Template | `interface-template/v1`、result v1、Validator、双方向 Final/results 和 APPROVED Review 已实现并绑定 RELEASED v2 | 无；两份 Final identity/version/hash 与四条 ASSEMBLY omission 已冻结 | 已完成 |
| Workbook | openpyxl Generator、完整 Final/result/rule gate、七个 sheet 投影、safe text、原子写入、双方向 Golden Workbook、structured/CLI regression 已实现 | 无；P0-T3 完成门禁已覆盖 | 已完成 |
| Draft generators | provider-neutral runtime、四类 orchestration、六个受控 response、CLI、Draft publication、reviewed Final DocIR 与完整 closure regression 已实现 | 缺少真实 Chat API adapter；没有真实 Draft、逐层 Review/Final validation 和双方向 Workbook 验证证据 | P0-T5 Commit 8A / 8B |

当前 regression、三类 Final validation results、v1/v2 发布记录、Standard/Template Final golden、双方向 Configuration Workbook 与显式 Human Review gate 证明 fixture trusted chain 稳定闭合；P0-T5 完成前，Phase0-PoC 不得标记为 Done。

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

- SchemaIR v2 批次移除 `phase0a`，不提供兼容别名；过渡期 CLI 只保留 `raw` profile。
- 完整 `phase0` profile 在 Workbook 批次启用，只读校验一条显式选择的 Final trusted chain；它不生成或修改任何 artifact，也不读取生成后的 Workbook 作为 IR 反向输入。
- 调用者必须显式提供 `direction + standardVersion + templateId + templateVersion + standard rule package path + template rule package path`。Standard 与 Template 可以引用不同的不可变规则版本；当前 b2e0061 Final Standard 使用 v1，Final Template 使用 v2，因此禁止合并为单一规则路径。
- `phase0` 不扫描全部目录、不自动选择最新版本、不新增 manifest，也不把仓库内 `configuration-rules/` 设为隐式默认路径。
- 固定 workspace 路径为：

  ```text
  schemair-final.json
  schemair-validation-result.json
  standards/{direction}/{standardVersion}/standard-final.json
  standards/{direction}/{standardVersion}/standard-validation-result.json
  templates/{direction}/{templateId}/{templateVersion}/template-final.json
  templates/{direction}/{templateId}/{templateVersion}/template-validation-result.json
  templates/{direction}/{templateId}/{templateVersion}/configuration-workbook.xlsx
  ```

- `check --profile phase0` 校验前六份 JSON、两个显式规则包及其完整引用闭合，不要求 Workbook 已存在；`generate-workbook` 复用同一输入门禁并写入固定 Workbook 路径。两者都保留现有 `raw` profile 和 `ingest` 行为。
- `generate-workbook` 默认拒绝覆盖已有文件，只有显式 `--overwrite` 才允许原子替换；生成失败不得留下半写入文件。
- artifact 协议随对应运行时批次增量实现，不能等到 Workbook 阶段再一次性补齐所有路径。
- 发生 CLI 命令、artifact、配置或验证方式变化时，同一实现 commit 必须同步根 `README.md` 和相关设计说明。

### 3.4 Human Review 是 Final 门禁

- 规则包：`deng` 与 `configuration-reviewer` 对机器校验通过的准确版本确认发布日期和 RELEASED 结论。
- SchemaIR：落实两方向已确认的 `UTF-8`，并 Review 银行字段/约束、observed evidence 和结构化 Condition；未来 encoding 证据冲突时 Warning 并阻塞 Final，直到重新确认。
- Standard：Review 路径、类型、XML Keys、三态约束、银行 Condition 以及 SchemaIR/Standard 差异。
- Template：Review function、Mapping/Replacement、processing policy、方向性绑定和 ASSEMBLY omissions。
- Human 先完成包括 `status=FINAL` 和 `review=APPROVED` 在内的完整 candidate，再运行对应 Validator；canonical 内容 hash 不匹配的旧结果失效。
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

**状态：Done。loader/validator 与 BKL 子集契约已完成；双 reviewer 已确认候选 `60c3ca18665cc0e3c85bb7f1c6f2212bba1d4c4d`，v1 于 2026-08-06 切换为 `RELEASED` 并冻结。**

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

### 4.2A SchemaIR v2 runtime 与 Draft candidate

**状态：Done。Final 事实不在本批次范围。**

**已完成边界**

- SchemaIR runtime 升级到 `schemair/v2`，明确拒绝 legacy contract、JSON message format 和 JSON node kind。
- 实现 stable identity/version、`DRAFT | FINAL`、`PENDING | APPROVED`、canonical SHA-256、validation-result v2 和 blocking Final eligibility。
- 实现 `xmlEncodingEvidence`、最小结构化银行 Condition、字段层级/type/occurs 相容性以及严格 JSON/workspace trust boundary。
- 保留 P0-T2 四份 artifacts 的 byte hash；新增独立 50-field SchemaIR v2 Draft、匹配 result 和 PENDING review 记录。
- 移除 `phase0a`；过渡期只公开 `raw` profile，完整 `phase0` 延后到 Workbook 批次。

**机器完成标志**

- Draft coverage 为 13 envelope、27 ASSEMBLY、10 PARSE，共 50 fields。
- 结果为 0 ERROR、38 WARNING、35 INFO、21 blocking issues，`finalEligible=false`。
- ASSEMBLY/PARSE 均保存已确认的 `UTF-8` Human/银行 evidence；当前无 encoding conflict。
- 完整 pytest、legacy rejection、hash、strict JSON、CLI、P0-T2 byte-identical 回归通过。

### 4.2B Final SchemaIR v2 Review 与冻结

**状态：Done。**

**边界**

- Human 已按 `schemair-review.md` 关闭 uncertain fields、请求 repeated node 的 required/occurs 冲突和 `transtype == "2" => obssid REQUIRED` 条件。
- Final candidate 已填入 reviewer/timestamp，并仅使用明确评审结论，不从正式导出或相近概念补猜答案。
- `deng` 已确认准确 canonical hash `sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162`；匹配结果已由 v2 Validator 重新生成。

**完成标志**

- Final SchemaIR 无 `uncertain=true` 或 blocking issue，`finalEligible=true`。
- review 记录引用准确 Final hash；修改任一语义值都要求重新 Review 和复验。
- coverage 为 12 个 envelope、27 个 ASSEMBLY、10 个 PARSE，共 49 个 fields；结果为 0 ERROR、0 WARNING、34 INFO、0 blocking issue。

**下一批次开始条件**

已满足；可开始 Standard runtime。

### 4.3 InterfaceStandardIR contract、Validator 与双向 fixture

**状态：Done。Commit 4A Draft runtime 与 Commit 4B Final freeze 均已完成。**

**边界**

- 已冻结 InterfaceStandardIR 和 Standard validation-result machine contract。
- 已实现 stable identity/version、SchemaIR hash、方向、fieldId、sequence、parent/full path、类型和 XML Keys。
- 已实现 `VALUE | NO_CONSTRAINT | UNKNOWN`、银行条件、差异、Rule References 和 Final eligibility。
- 已冻结人工确认的 ASSEMBLY/PARSE Final Standard，不直接复制正式导出 ID、状态或冲突事实。

**涉及模块**

- Standard contract/validator、shared validation helpers 和 tests
- 双向 Standard fixtures、validation results 和 Review 记录
- trusted-chain sample 路径和必要 docs-sync；workspace/CLI 集成仍延后到 Workbook 批次

**完成标志**

- `@security` 进入 Final Standard XML Keys；`vamflag` 被排除；observed `@lang` 只保留在来源和 Review 证据中，不成为 Final SchemaIR 或 Standard 字段。
- 请求 `b2e0061-rq` 按 `1..1000`、响应 `b2e0061-rs` 按 `0..1000` 为 `Node`。
- `obssid` 基础 Required 与 `transtype == "2"` 条件 Required 分离。
- `UNKNOWN`、未确认差异或未完成 Human Review 阻止 Final。
- 两方向 Final Standard 和匹配 validation result 经人工确认后冻结。

**当前机器结果**

- ASSEMBLY：36 fields、3 XML Keys、1 condition、0 ERROR、0 WARNING、0 blocking；email Regex 经 Human 确认为 `NO_CONSTRAINT`，Final hash 为 `sha256:9c77e0e92447907fa89d6ef705501dc0947d695998b80bb154476f696e9b982e`。
- PARSE：19 fields、3 XML Keys、4 approved differences、0 ERROR、0 WARNING、0 blocking；`rspcod=50` / `rspmsg=500` 已确认，Final hash 为 `sha256:33efa544460ac19f216734712c1e6ae2610321ea17eb750eff35493ecca9d57e`。
- 两份结果均为 `finalEligible=true`；准确 hash 已由 `deng` 确认。

**验证**

- identity/hash、path/sequence、List 拒绝、XML Keys、三态约束、Condition 引用、差异 Review 和 Rule Reference 测试。
- 双向 golden equality、字段级 issue 定位和完整 pytest。

**下一批次开始条件**

已满足；两份 Final Standard identity/version/hash 稳定，可开始 Template runtime。

### 4.4 InterfaceTemplateIR contract、Validator 与双向 fixture

**状态：Done。Machine contract、Validator、双向 Final/results 与 APPROVED Review 已完成。**

**边界**

- 冻结 Template 和 Template validation-result contract。
- 实现 Standard identity/version/hash 精确绑定、ASSEMBLY `standardTarget.standardProjection` 镜像与 PARSE source projection 确定性解析。
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

已满足；三份 Final 模型、三份匹配校验结果和精确规则版本均已冻结，可开始 Workbook。

### 4.5 Configuration Workbook 与 trusted-chain regression

**状态：Done。Commit 6A 核心运行时与 Commit 6B workspace/CLI、双方向 Golden Workbook 和完整 regression 均已完成。**

**依赖**

- Final SchemaIR 与精确匹配的 `schemair-validation-result/v2`。
- 当前方向的 Final InterfaceStandardIR 与精确匹配的 `interface-standard-validation-result/v1`。
- 当前方向选定的 Final InterfaceTemplateIR 与精确匹配的 `interface-template-validation-result/v1`。
- Standard 实际引用的 RELEASED 规则包和 Template 实际引用的 RELEASED 规则包；两者必须分别显式加载，不能假设版本相同。
- 调用者显式提供 `Standard Action = CREATE | REUSE | UPDATE` 和带时区的生成时间。

**已确认决策与取舍**

- `check --profile phase0` 保持只读；新增独立 `generate-workbook` 命令负责写文件，避免“检查”命令产生副作用。
- `Interface Template` 主 sheet 严格一条 `fieldConfig` 一行。PARSE 复合表达式的多个 Standard source 以相同顺序在对应 Standard snapshot 列中使用换行分隔；完整树只在 `Value Expressions` 展开，不复制主行。
- Generator 不信任调用者传入的 validation result 摘要。它重新运行三个现有 Validator，并要求传入 result 与重新计算结果完整对象相等；只比较 hash 或 `finalEligible` 不足以进入 trusted chain。
- 非法输入直接 fail closed，不生成 debug Workbook。本批不实现排障工作簿、旧 Standard diff、Excel 反向校验或运行时目标系统查询。
- `UPDATE` 没有旧 Standard 输入，因此只在 `Overview` 显示“需人工与目标环境现有版本对照”的固定提示，不声称生成真实版本差异。
- b2e0061 两份 Final Template 不使用 MAPPING/Replacement。Workbook 对这两类表达的投影通过既有 `tests/fixtures/interface-template-v1/mapping-replacement.json` 做 unit-level 专项测试，不把该 fragment 伪装成完整 Final chain，也不向 b2e0061 Workbook 注入虚假银行事实。
- 以上决定是现有 ADR-0007/0008/0009 的实现收束，不改变长期架构，无需新增 ADR；实现时只同步受影响的设计说明。

**公开接口与错误契约**

- 新增 `bank_config_compiler.configuration_workbook`，公开以下只读门禁供 `phase0` check 和 Generator 复用：

  ```python
  validate_configuration_workbook_inputs(
      *,
      schemair: dict[str, Any],
      schemair_validation_result: dict[str, Any],
      standard: dict[str, Any],
      standard_validation_result: dict[str, Any],
      template: dict[str, Any],
      template_validation_result: dict[str, Any],
      standard_rule_package: RulePackage,
      template_rule_package: RulePackage,
  ) -> None
  ```

- 同一模块公开生成入口：

  ```python
  generate_configuration_workbook(
      *,
      schemair: dict[str, Any],
      schemair_validation_result: dict[str, Any],
      standard: dict[str, Any],
      standard_validation_result: dict[str, Any],
      template: dict[str, Any],
      template_validation_result: dict[str, Any],
      standard_rule_package: RulePackage,
      template_rule_package: RulePackage,
      standard_action: str,
      output_path: Path,
      generated_at: datetime,
      overwrite: bool = False,
  ) -> Path
  ```

- 模块定义 `WORKBOOK_FORMAT_VERSION = "v1"`；`Overview` 记录该版本和项目版本，避免把内部函数名承诺为长期格式协议。
- `generated_at` 必须为 offset-aware `datetime`。库调用显式传入，CLI 使用当前带时区时间；golden tests 注入固定值。
- `WorkbookGenerationError` 聚合稳定的 `{code, artifact, path, message}` issues；任何错误均不返回或保留部分 Workbook。
- 模块级 logger 在入口记录 `DEBUG`，成功记录 `INFO`（interface、direction、template、sheet/row counts、outcome），预期输入错误记录一次 `WARNING`。禁止记录 LITERAL、Mapping target、原始 YAML、银行原文全文或安全输入真实值。
- 保存采用输出目录内临时文件后原子替换。输出已存在且 `overwrite=False`、父路径不是目录、保存/回读失败均转译为带上下文的 `WorkbookGenerationError`。

**输入可信链门禁**

1. 要求两个依赖均为 `RulePackage`、状态为 `RELEASED`，且 version 分别等于 Standard/Template 中记录的 `rulePackageVersion`；CLI 只能通过 `load_rule_package(...)` 获取它们。
2. 运行 `validate_schemair(schemair)`，要求结果与传入 SchemaIR result 完整相等且 `finalEligible=true`。
3. 使用 SchemaIR 和 Standard 规则包运行 `validate_interface_standard(...)`，要求结果与传入 Standard result 完整相等且 `finalEligible=true`。
4. 使用绑定 Standard 和 Template 规则包运行 `validate_interface_template(...)`，要求结果与传入 Template result 完整相等且 `finalEligible=true`。
5. 再校验 `interfaceCode`、direction、artifact identity/version/contract/hash 和 Template→Standard 引用均与实际对象一致；任一不一致拒绝生成。workspace loader 另外负责 selector 与实际 artifact 的一致性。
6. `standard_action` 只允许 `CREATE | REUSE | UPDATE`，拒绝 bool、空字符串、大小写 alias 或隐式默认值。
7. 任一业务单元格待写值包含 `<REDACTED>`、非法控制字符、超过 Excel 32,767 字符限制或无法安全表示为 literal text 时拒绝生成，不截断、不执行、不降级。

**Workbook 固定结构与顺序**

- 固定七个 sheet 且顺序唯一：`Overview`、`Interface Standard`、`Interface Template`、`Value Expressions`、`Warnings`、`Rule References`、`Legend`。
- 不使用 merged cells、宏、外部链接或业务公式。表格 sheet 使用首行 header、`freeze_panes = "A2"`、auto filter、自动换行和顶端对齐；样式常量集中定义，不为单个样例硬编码坐标。
- 固定样式为：header fill `1F4E78`、白色粗体；REUSE/只读 fill `D9E1F2`；WARNING fill `FFF2CC`；ERROR fill `F4CCCC`；INFO fill `D9EAD3`。ID/path 列宽 42，description/message/evidence 列宽 60，enum/status 列宽 20，sequence/count/bool 列宽 14，其余列宽 28；禁止按当前样例内容自动扩缩导致结构漂移。
- 可编辑 Execution Status 使用固定 data validation `NOT_STARTED,IN_PROGRESS,CONFIGURED,BLOCKED`；Verification Status 使用 `NOT_VERIFIED,PASSED,FAILED`。REUSE 的 `NOT_APPLICABLE` 不挂 data validation。状态转换约束写入 `Legend`，本批不用公式、宏或 sheet protection 动态强制。
- 所有来源于 IR、Review、规则包或用户上下文的字符串显式写为 text。以 `= + - @` 开头的外部字符串不得成为公式；回读测试断言业务单元格不存在 `data_type="f"`。
- 结构化确定性比较排除 `Generated At`，其余 sheet 名、行列顺序、值、cell data type、关键样式、data validation 和 warnings 必须一致。不比较 `.xlsx` ZIP 字节。

**各 Sheet 投影契约**

- `Overview` 使用固定 `Key | Value` 两列和以下分组顺序：Workbook format/delivery/generated metadata；interface/direction/XML encoding；SchemaIR identity/contract/hash/result summary；Standard identity/contract/hash/rule version/action/result summary；Template identity/contract/hash/rule version/result summary；UPDATE 固定提示。有效输入只生成 `DELIVERABLE`，不存在 debug 状态。
- `Interface Standard` 严格使用 `docs/design/05-configuration-workbook.md` 已定义列顺序。字段通过 `parentPath` 建树，按同父 `sequence` 进行递归前序遍历；Object/Node 在其子字段之前。不得使用 SchemaIR `level` 排序。
- Standard `CREATE/UPDATE` 行初始化为 `Execution Status=NOT_STARTED`、`Verification Status=NOT_VERIFIED`、空 Operator Note；`REUSE` 行固定为两个 `NOT_APPLICABLE` 并使用只读视觉样式。本批不启用 sheet password/protection，不用宏或公式强制状态流转。
- `Interface Template` 严格使用设计文档列顺序并保持 `fieldConfigs` 数组顺序，一条 config 一行。ASSEMBLY 只保存一个 target snapshot；PARSE 从表达式深度优先、同级按 `sequence` 的遍历结果以及 `COLLECTION_ITEM.standardSource` 收集有序唯一 Standard refs，各 Standard snapshot 列以相同顺序换行对齐。Parse target 始终单独分列。
- Template 行初始化为 `NOT_STARTED + NOT_VERIFIED`。`STRUCTURE_ONLY/COLLECTION_ITEM` 的 Value Mode 与 Value Summary 为空；空值表示不适用，不是 `EMPTY`、UNKNOWN 或 omission。
- `Value Expressions` 对每个 `VALUE` 的 FIELD_VALUE root 和每个 XML Key root 递归先父后子展开。Expression ID 由 `scope + target ref + xml key（适用时）+ child index path` 确定性生成；Parent ID 和 Sequence 可重建树。Function arguments 使用 canonical compact JSON 保存按 position 排序的 `position/kind/value-or-ref`，不是自然语言摘要。Node/Object 不产生 FIELD_VALUE 节点。
- `Warnings` 依次收集当前方向 Standard 所引用 SchemaIR path/XML Key path 上的 SchemaIR Validator issues、Standard differences、bank conditional constraints、ASSEMBLY accepted omissions、Standard/Template Validator 的剩余 issues。SchemaIR path 通过 `schemaIrFieldPath` 映射到 Standard Field，XML Key path 映射到所属 Standard Field。
- Warnings 行映射固定为：Validator-only issue 保留原 severity，`Category=VALIDATOR`，Message 前缀保留 issue code，`Review Disposition=NOT_REQUIRED`；Standard difference 使用 `WARNING + SCHEMA_STANDARD_DIFFERENCE + ACCEPTED`；结构化 bank condition 使用 `INFO + BANK_CONDITIONAL_CONSTRAINT + ACCEPTED`；accepted omission 使用 `WARNING + MISSING_TEMPLATE_FIELD + ACCEPTED`。
- 与 omission 对应的 Template `MISSING_TEMPLATE_FIELD` issue 合并到同一行并保留 `Source=Template Validator + Review`；与同一 SchemaIR path 的结构化 bank condition 对应的 SchemaIR `CONDITIONAL_FIELD` INFO 合并为一条富化 condition 行；不同 category 的同字段问题不得误合并。排序固定为 severity、category、Standard Field Ref、source/path。未配置 Parse Field 不生成 warning。
- 当前 Final/result 下，b2e0061 ASSEMBLY golden 预期 34 条方向相关 SchemaIR `CONDITIONAL_FIELD`（其中 obssid 行合并结构化 bank condition）+ 4 条合并后的 accepted omission，共 38 行；PARSE 预期 11 条方向相关 SchemaIR `CONDITIONAL_FIELD` + 4 条已批准 Standard difference，共 15 行。若 Final/result 变化导致数量变化，golden 必须失败并要求重新 Review，而不是更新为宽松断言。
- 当前 golden 的核心结构计数固定为：ASSEMBLY 36 个 Standard rows、26 个 Template rows、30 个 Value Expression nodes（27 FIELD_VALUE + 3 XML_KEY）；PARSE 19 个 Standard rows、8 个 Template rows、13 个 FIELD_VALUE nodes。Function arguments 保存在所属 expression row，不额外增加 expression node。
- `Rule References` 一行对应 `(Artifact Scope, Rule Package Version, Rule ID, Used By)`，只展开 IR 实际 `ruleReferences`；`Rule Title` 取相应 `rules_by_id[ruleId].summary`，`Source File / Section` 固定写为 `rules.yaml / rules[id=<Rule ID>]`，按四元组稳定排序。Function/Mapping catalog code 在 `Value Expressions` 展示，不伪装为 Rule ID，Mapping entries 不进入 Workbook。
- `Legend` 使用固定静态行解释列来源、枚举、六种 Value Mode、三种 binding、两种 FIXED_VALUE payload、空值、`EMPTY`、omission、状态初值、REUSE 和 secure ref；不得从样例临时生成自然语言规则。

**Workspace 与 CLI 接口**

- 新增不可变 `Phase0Selection(direction, standard_version, template_id, template_version)` 和固定 path builder；direction 的 CLI 值为小写 `assembly | parse`，version 必须匹配 `^v[1-9]\d*$`，template ID 必须为 kebab-case stable ID。加载后 selector 必须匹配 IR 的大写 direction、version 和 template identity。
- 新增不可变 `Phase0Artifacts` 保存六份 JSON，并由 `load_phase0_artifacts(workspace_path, selection) -> Phase0Artifacts` 使用既有严格 JSON I/O 加载；路径必须继续受 workspace boundary 保护，且 selector 必须与加载后的 direction/version/template identity 完全一致。
- `check --profile phase0` 必需参数：`--direction`、`--standard-version`、`--template-id`、`--template-version`、`--standard-rule-package`、`--template-rule-package`。它加载两个 RELEASED 包并执行完整输入可信链门禁，但不要求或写入 Workbook。
- 新增 `generate-workbook`，使用上述相同 selector/rule arguments，再要求 `--standard-action {CREATE,REUSE,UPDATE}`，支持 `--overwrite`；输出固定为所选 Template 目录下 `configuration-workbook.xlsx`，不接受任意输出路径。
- CLI 将 `WorkspaceError`、`RulePackageValidationError` 和 `WorkbookGenerationError` 转为 exit code 2；stdout 只输出生成路径或检查计数，stderr 不展示敏感值。

**涉及模块**

- `bank_config_compiler/configuration_workbook.py`
- `bank_config_compiler/workspace.py`、`bank_config_compiler/cli.py`
- `tests/test_configuration_workbook.py`、`tests/test_configuration_workbook_golden.py`、workspace/CLI tests
- `samples/trusted-chain/b2eboc-b2e0061/templates/{assembly,parse}/v1/configuration-workbook.xlsx`
- `pyproject.toml`、`uv.lock`：加入 `openpyxl>=3.1.5,<4`
- `README.md`、Workbook design、Golden design、Phase0 phase/status 和本计划的完成状态同步

**完成标志**

- 双方向 Workbook 均由当前 Final chain 生成并可由 openpyxl 重新打开；固定 sheet、列、行顺序与关键样式满足契约。
- Standard 快照、Template 镜像、PARSE target、三种 binding 和两端 datatype 分列可还原。
- encoding、银行 Condition、SchemaIR/Standard differences、四条 accepted omissions、Validator issues 和 Rule References 不被静默丢失或重复。
- Value Expressions 可还原标量字段值与 XML Key expression tree；Node/Object 不产生 FIELD_VALUE 节点。
- MAPPING/Replacement 受控测试只展示 rule name，不复制 entries；SECURE_INPUT_REF 只展示安全引用标识。
- 相同 Final 输入、validation results、规则版本、Standard Action 和固定 `generated_at` 生成相同结构化内容；变化只发生在显式任务上下文。
- `check --profile raw` 与现有 `ingest` 行为保持兼容；`phase0a` 继续拒绝。
- P0-T3 全部验收已通过并标记为 `Done`，P0-T4 已解锁；四类 Draft generator 不属于 P0-T3 完成条件。

**测试与验证**

- Unit：输入门禁、完整 result equality、双规则版本、Standard Action、路径/overwrite/原子失败、safe text、超长/非法字符、公式注入、日志脱敏。
- Projection：七个 sheet/列顺序、层级排序、单 config 单行、PARSE 多 source 对齐、expression ID/tree/function args、Warnings 合并、Rule References 四元组和 Legend。
- Action：CREATE/UPDATE 初始状态、REUSE `NOT_APPLICABLE`、UPDATE 固定提示；不实现真实旧版本 diff。
- Controlled fixture：使用既有 fragment 对 MAPPING 与 Replacement 的 Workbook row projector 做 UT，覆盖 redacted rule 拒绝、无 entries/target 泄漏；不通过伪造 Human Review 把 fragment 提升为 Final，并明确断言不是 b2e0061 银行事实。
- Golden：提交 ASSEMBLY/PARSE `CREATE` Workbook；用固定 `generated_at` 重新生成到临时目录，以 openpyxl 回读并比较结构化 snapshot，不比较二进制字节。
- CLI：raw compatibility、phase0 selectors 缺失/非法、两个 rule path 错配、check 只读、generate 成功、已有文件拒绝/overwrite、两个方向 smoke。
- `uv --cache-dir .uv-cache run --group dev pytest -q -p no:cacheprovider --basetemp tmp\pytest-p0t3-workbook`
- `uv lock --check`
- `uv --cache-dir .uv-cache build --out-dir tmp\build-p0t3-workbook`
- `git diff --check`、所有文本 UTF-8 no BOM、artifact/rule reference 闭合。
- 通过 openpyxl 与 ZIP 内容检查无业务 formula、宏、external link、`<REDACTED>`、Mapping entries/target 或高置信敏感固定值。
- 完成每个 coherent batch 后运行 docs-sync，强制检查根 `README.md`；人工打开两份 Golden Workbook 做最小视觉 smoke，不以视觉检查替代结构化 assertions。

## 5. P0-T4：Provider-neutral Draft generators

### 5.1 技术边界

- `DraftProvider.generate(DraftGenerationRequest) -> str` 是统一 provider contract。Request 保存 task/artifact kind、上游 `sourceHash` 和适用的 direction/version/rule selector；CLI task ID 使用 workspace 目录名。
- Provider 返回严格 UTF-8 `draft-provider-response/v1` JSON envelope，只包含 `contractVersion`、`artifactKind`、`artifactContent` 和 `reviewNotes`。未知/缺失/额外属性、BOM、非 UTF-8、重复 JSON property 或 kind mismatch 均拒绝。
- Phase0 只实现调用者显式选择的 fixture provider。`draft-stub-case/v1` 使用准确 request fingerprint 匹配 DocIR、SchemaIR、双向 Standard 和双向 Template 六个响应；不扫描、不选择最新版，也不进入 `phase0` trusted-chain selector。
- 文本上游使用 UTF-8 bytes SHA-256，JSON Final dependency 使用 canonical semantic SHA-256。`.gitattributes` 显式保留既有 Golden/Draft Markdown 的 CRLF bytes baseline，并固定 fixture JSON 的 LF；fixture root、input hash、selector 或规则版本不匹配时 fail closed。
- DocIR 只执行章节、Metadata/Fields 表和 ASSEMBLY/PARSE XML 方向的最小结构检查，不新增第四个 trusted-chain Validator。Human 必须先确认准确 DocIR bytes hash，才可冻结 `docir-final.md`。
- SchemaIR、Standard、Template provider output 必须为 `DRAFT/PENDING`；对应 Validator 必须为 0 ERROR、`finalEligible=false` 并保留 lifecycle blocking issue。任何 `FINAL/APPROVED` 输出在写盘前拒绝。
- Draft、匹配 validation result 和 review notes 全部先在内存校验，再分别使用同目录临时文件原子替换。文件系统不承诺跨文件事务；任何中断后的缺失或 result hash mismatch 必须阻止下游。
- Provider 和 stub 不得构造 Final/Human Review、调用 Workbook Generator 或硬编码银行事实到 runtime。日志只记录 task/artifact identifier、provider、contract version、direction 和 outcome，不记录银行原文、Draft、review notes、secret 或安全固定值。
- P0-T4 不实现真实 LLM/API、Prompt、网络、认证、重试或模型配置；这些最小真实调用能力属于后续 P0-T5，不扩大为通用银行推理、Review UI、自动 promotion 或 Phase1 能力。

### 5.2 完成标志

- `generate-draft docir|schemair|standard|template` 通过同一 provider contract 调用；相同 request/fixture 产生相同 Draft/result/review notes。
- 固定写入 `docir-draft.md`、`schemair-draft.json`、`standards/{direction}/{standardVersion}/standard-draft.json`、`templates/{direction}/{templateId}/{templateVersion}/template-draft.json` 及同级 review notes/result；默认拒绝覆盖。
- LLM/provider 输出无法直接形成 Final；DocIR 先经准确 bytes hash Human Review，三个 JSON Draft 人工修改后必须重新 Validator。
- Standard/Template generator 在规则版本不存在或非 RELEASED、dependency 非 Final、selector/hash 不匹配时拒绝运行。
- 完整 Phase0 回归从受控 Draft 输入开始，显式装载已审核 Final fixtures 表达 Human Review，再生成双方向 Workbook；测试和 runtime 都不得自动提升 Draft。
- P0-T4 改为 `Done` 后，P0-T5 可以开始；Phase0-PoC 还需满足 P0-T5 才能通过。

### 5.3 验证

- 六类 stub golden、provider error translation、严格 response/case、DocIR 结构、JSON lifecycle/Validator、dependency/hash/rules、overwrite/失败清理和敏感日志测试。
- 完整 pytest、双方向 Draft-to-Workbook regression、build、docs-sync、BOM/diff/secret 检查和用户命令 smoke test。

## 6. P0-T5：真实 LLM Draft-to-Workbook 验证

### 6.1 已确认边界

- 真实 provider 使用 OpenAI-compatible Chat API；实际模型由运行时显式选择，可以是 DeepSeek、Qwen 或其他兼容服务。
- 一次验收必须真实调用 DocIR、SchemaIR、ASSEMBLY/PARSE Standard 和 ASSEMBLY/PARSE Template 共六次 Draft 生成；fixture 不得充当其中任一调用。
- API key、base URL、model 和可选网络参数只存在于运行时安全配置；不得落入 artifact、日志、测试 fixture 或版本库。
- 输入可发送给用户批准的 provider，但该授权不自动授权把 raw-doc、真实 Draft、Final 或 Workbook 提交到仓库。默认只提交不含敏感业务内容的代码、测试与证据摘要。

### 6.2 实施与验证顺序

1. 新增真实 `DraftProvider` adapter 和 CLI/runtime 配置入口，将 Chat API 响应转换为严格 `draft-provider-response/v1`；保留现有 Draft/Validator/workspace publication 边界。
2. 以 mock/recorded transport 覆盖请求构造、认证缺失、超时、非 2xx、无效 JSON、response envelope 错误和日志脱敏；自动化测试不得需要真实 API key 或网络。
3. 在独立、未跟踪 workspace 中执行真实 DocIR Draft；Human 对准确 hash 单独确认后形成 Final DocIR。
4. 用该 Final DocIR 执行真实 SchemaIR Draft、Draft validation、Human Review、Final candidate 和 Final validation；然后分别执行两方向 Standard 和 Template，遵守每个上游 Final gate。
5. 对由真实 Draft 经 Review 形成的两条 Final trusted chain 执行 `check --profile phase0`，再各生成一份 Configuration Workbook；保存不含 secret 的运行证据、artifact hash、reviewer、时间、provider/model 标识和验证结果。

### 6.3 完成标志

- 六次真实 Chat API 调用均由 adapter 发起，并在同一 Draft contract 下发布 `DRAFT/PENDING` artifact；DocIR 通过最小结构检查，三个 JSON Draft 均为 0 ERROR 且 `finalEligible=false`。
- DocIR、SchemaIR、双方向 Standard 和双方向 Template 均具有独立具名 Human Review、准确内容 hash 和匹配的 Final validation result；未发生自动 promotion。
- 两个方向的真实 Final trusted chain 都通过 `check --profile phase0`，并各自生成可打开、通过结构化检查的 Workbook。
- fixture regression、完整 pytest、build、docs-sync、BOM/diff/secret 检查继续通过；真实调用失败不影响离线回归。

### 6.4 Commit Plan

#### Commit 8A：真实 OpenAI-compatible Draft provider

- Scope：新增 provider adapter、显式 CLI/runtime 配置、脱敏错误/日志、mock transport 测试和 README/设计/配置说明。
- Files：`bank_config_compiler/draft_generation.py`、`bank_config_compiler/cli.py`、新增 provider 模块与对应 tests；按实际接口更新 README、design、planning。
- Completion signal：不设置真实凭证时 fail closed；mock provider 能覆盖四类 Draft request/response contract，fixture 路径保持不变。
- Verification：专项 pytest、完整 pytest、build、静态 secret 检查和 docs-sync。
- Next starts when：用户在独立 workspace 提供已批准的 endpoint/model/credential 与可处理的验证样例。

#### Commit 8B：真实 LLM 验收证据

- Scope：执行六次真实 Draft，逐层 Human Review/Final validation，生成双方向 Workbook，并保存经过数据保留审查的最小证据摘要；不把敏感 artifact 自动加入 Git。
- Files：用户批准且可提交的 review/evidence 记录；其余真实 artifact 留在受控 workspace。
- Completion signal：满足 6.3 的全部完成标志。
- Verification：双方向 `check --profile phase0`、Workbook 结构化检查、完整 pytest、build、docs-sync、BOM/diff/secret 检查和人工 Review readback。
- Next starts when：P0-T5 状态改为 Done，Phase0-PoC 最终门禁可重新判定。

## 7. 逻辑 Commit Plan

以下 commit 同时记录已完成边界与后续实施边界。Commit 1/2 位于同一隔离分支；后续批次开始时再按当时基线建立所需开发分支，并通过 PR 合入。

### 已完成：P0-T3 文档与规则事实契约

- Evidence：PR #12 / merge commit `2de9f69`。
- Scope：requirements、design、ADR amendments、phase/planning、reference 和 `configuration-rules/v1` Draft。
- Completion signal：最新银行事实投影、Standard 镜像、结构绑定、Mapping/Replacement、processing policy、Human Review 和脱敏边界已一致记录；后续修订将 v1 收束为接口无关的 BKL 子集。

### 已完成 Commit 1：DRAFT 规则包运行时

- Suggested message：`feat: add configuration rule package validation`
- Evidence：候选 `60c3ca18665cc0e3c85bb7f1c6f2212bba1d4c4d`，机器校验与完整回归通过。
- Scope/Files：safe loader、严格 schema/semantic validator、聚合错误、日志保护、BKL 子集 scope、正式导出 function、业务确认 String、字符长度默认 `STANDARD_1`、tests、PyYAML dependency 和 docs-sync；v1 保持 DRAFT。
- Completion signal：Draft 候选的机器校验与完整回归通过，默认加载仍拒绝非 RELEASED 版本。
- Verification：规则正反向测试、完整 pytest、build、BOM、diff、敏感信息和引用闭合检查。
- Next starts when：向 maintainer 与 business reviewer 展示准确 commit、机器结果和候选 diff。

### 已完成 Commit 2：发布 `configuration-rules/v1`

- Suggested message：`chore: release configuration rules v1`
- Evidence：`deng` 与 `configuration-reviewer` 于 2026-08-06 对候选 `60c3ca18665cc0e3c85bb7f1c6f2212bba1d4c4d` 明确确认发布。
- Scope/Files：四份 YAML status、确认日期、Review/README/phase/planning 状态和 RELEASED 模式测试；不增加规则事实。
- Completion signal：双 reviewer 对准确 Draft 候选确认，v1 切换为不可变 RELEASED，默认 loader 验证通过。
- Verification：RELEASED 正反向测试、完整 pytest、build、docs-sync、BOM、diff 和敏感信息检查。
- Next starts when：RELEASED v1 可以被 Final IR 精确引用。

### 已完成 Commit 3A：SchemaIR v2 runtime 与 Draft candidate

- Suggested message：`refactor: define SchemaIR v2 validation contract`
- Scope/Files：canonical integrity helper、SchemaIR v2 Validator、严格 workspace JSON I/O、移除 `phase0a`、50-field Draft/result/review、tests 和 docs-sync。
- Completion signal：legacy runtime/profile 被替换；Draft 为 0 ERROR 且明确 `finalEligible=false`，没有被伪装为 Final。
- Verification：SchemaIR/hash/encoding/Condition/CLI/golden/strict JSON tests、完整 pytest、build、BOM、diff 和敏感信息检查。
- Next starts when：Human 对准确 Draft 和全部 blocking review item 给出结论。

### 已完成 Commit 3B：冻结 Final SchemaIR v2

- Suggested message：`chore: freeze reviewed SchemaIR v2 fixture`
- Scope/Files：只提交获批的 Final SchemaIR、匹配 validation result、review 记录、tests 和状态同步；不改变 Validator 语义。
- Completion signal：Final SchemaIR 无 uncertain/blocking issue，准确 content hash 经 Human 确认，`finalEligible=true`。
- Verification：Final golden equality、hash mismatch、完整 pytest、docs-sync、BOM、diff 和敏感信息检查。
- Next starts when：Final SchemaIR identity/version/hash 稳定；任何语义变更重新评审。

### 已完成 Commit 4A：InterfaceStandardIR Draft runtime

- Suggested message：`feat: add InterfaceStandardIR validation`
- Scope/Files：冻结 Standard contract/validator 与双向 Draft/results/review，加入正反向 UT、golden equality 和 docs-sync；不创建 Final Standard。
- Completion signal：两个 Draft 对 Final SchemaIR 与 RELEASED 规则包的绑定、字段投影、三态约束、条件、差异和 Final 门禁均可机器验证。
- Verification：Standard UT、golden equality、字段级 issues、完整 pytest、build、BOM、diff 和敏感信息检查。
- Next starts when：向 Human 展示两个准确 candidate hash、机器结果与全部 blocking review item。

### 已完成 Commit 4B：冻结 Final InterfaceStandardIR

- Suggested message：`chore: freeze reviewed interface standards`
- Scope/Files：只提交获批双向 Final/results/review 和状态同步；不改变 Standard Validator 语义。
- Completion signal：两份独立 Standard 无 `UNKNOWN`、uncertain 或未决差异，identity/version/hash 稳定。
- Verification：Final Standard golden equality、hash mismatch、完整 pytest、docs-sync、BOM、diff 和敏感信息检查。
- Next starts when：Template 可以精确绑定两份 Final Standard。

### 已完成 Commit 4C：`configuration-rules/v2` DRAFT projection amendment

- Suggested message：`feat: revise template projection rules`
- Evidence：commit `f2cf454b53541ccfa171f8f3ede59dae9e609583`；`deng` 与 `configuration-reviewer` 均确认该准确候选可发布。
- Scope/Files：新增 `configuration-rules/v2`，完整继承 v1 catalog，只修订 `TPL.BIND.STANDARD_PROJECTION`；加入 v2 DRAFT loader/catalog equality 回归、ADR-0010 和最小状态文档。不修改 v1、Final SchemaIR、Final Standard 或 Template runtime。
- Completion signal：v2 可用 `require_released=False` 安全加载，默认 loader 明确拒绝；27/207/14/5/6 与 v1 完全一致，方向性 projection 差异可精确审查。
- Review gate：展示本 commit SHA、完整验证结果以及 v1→v2 的精确语义 diff，等待 `deng` 与 `configuration-reviewer` 对同一准确候选双签。
- Next starts when：两个角色均明确确认；任何规则、catalog 或解释语义变化都会使确认失效。

### 已完成 Commit 4D：发布 `configuration-rules/v2`

- Suggested message：`chore: release configuration rules v2`
- Scope/Files：只修改 v2 四份 YAML lifecycle、confirmation date、review/README 与发布模式测试/状态文档，不增加规则或 catalog 事实。
- Completion signal：v2 四文件为 `RELEASED`，review 记录准确候选与双 reviewer，默认 loader、完整 pytest/build/docs-sync 和内容检查全部通过。
- Next starts when：发布 commit 成为当前开发基线，Template runtime 才能绑定 v2。

### 已完成 Commit 5A：InterfaceTemplateIR Draft runtime

- Suggested message：`feat: add InterfaceTemplateIR validation`
- Scope/Files：绑定 RELEASED v2，冻结方向相关 Template/expression/processing machine contract、Validator 与双向 Draft/results；不修改 Final SchemaIR、Final Standard 或规则事实。
- Completion signal：ASSEMBLY/PARSE Draft 分别为 0 ERROR、10/2 个预期 blocking Warning；候选 hash 分别为 `sha256:356b83c1aff90d83d82fa3bbc14f7fe8277c34605a3d5edb4cb99abd71c49957`、`sha256:33cd4f7ae02701d6ab19cf46628398354590dba3d612f91e43b06f78d1356621`。
- Verification：Template UT、专项 fixtures、双向 golden、完整 pytest 和 docs-sync。
- Review gate：展示本 commit SHA、两个准确候选 hash、预期 Warning 与业务事实边界，等待 reviewer `deng` 明确确认。
- Next starts when：Human Review 确认两个准确候选；任何 Template 业务内容变化都会使确认失效。

### 已完成 Commit 5B：冻结 Final InterfaceTemplateIR

- Suggested message：`chore: freeze reviewed interface templates`
- Scope/Files：只提交获批双向 Final/results/review 与状态同步；不改变 Template Validator 语义。
- Completion signal：双向 Final Template、四条 ASSEMBLY omissions、Function/processing 选择和专项 Mapping/Replacement contract evidence 经 Human Review 冻结；ASSEMBLY/PARSE Final hash 分别为 `sha256:b9966a449ddc29e08fa29c6cf7838273ce3cab91e00dbb38092767d21af2f561`、`sha256:16eb305b6ac3944f28cb1060b943fdfc2d471f69e6bf8ea52ce059c797fb22f9`，两份结果均为 0 blocking issue 且 `finalEligible=true`。
- Verification：Final Template golden equality、hash mismatch、完整 pytest、docs-sync、BOM、diff 和敏感信息检查。
- Next starts when：Workbook 所需三份 Final 与三份匹配 validation result 完整。

### 已完成 Commit 6A：Configuration Workbook 核心运行时

- Suggested message：`feat: generate configuration workbooks`
- Scope：实现 `configuration_workbook.py`、完整 Final/result/rule input gate、七个 sheet 的确定性投影、safe text/原子写入、受控 Mapping/Replacement 表达和核心 UT；不新增 CLI 命令、不提交 b2e0061 Golden Workbook。
- Files：`bank_config_compiler/configuration_workbook.py`、`tests/test_configuration_workbook.py`、`pyproject.toml`、`uv.lock`，以及 Workbook/Golden 设计和根 README 的已知同步。
- Completion signal：库 API 可从当前 ASSEMBLY/PARSE Final chain 生成并重新打开结构正确的临时 Workbook；非法链路、伪造 result、规则错配和不安全 cell 均 fail closed。
- Verification：Workbook unit/projection/controlled fixture tests、完整 pytest、build、docs-sync、BOM、diff、公式/敏感信息检查。
- Next starts when：公开生成接口、输入门禁、sheet/row/expression/warning/rule projection 已稳定，CLI 无需重新设计核心语义。

### 已完成 Commit 6B：`phase0` workspace/CLI 与完整 regression

- Suggested message：`feat: complete phase0 workbook workflow`
- Scope：实现 `Phase0Selection`、固定 artifact paths、只读 `check --profile phase0`、`generate-workbook`、双方向 CREATE Golden Workbook、openpyxl 回读 assertions、CLI smoke 和阶段状态同步；不实现 Draft generators。
- Files：`bank_config_compiler/workspace.py`、`bank_config_compiler/cli.py`、workspace/CLI/golden tests、`samples/trusted-chain/b2eboc-b2e0061/templates/{assembly,parse}/v1/configuration-workbook.xlsx`、根 README、Phase0 phase/planning 和 reference/trusted-chain 状态文档。
- Completion signal：显式选择的 ASSEMBLY/PARSE trusted chain 均能先只读检查、再生成固定路径 Workbook；结构化 golden regression 通过，P0-T3 改为 Done，P0-T4 解锁。
- Verification：双方向 CLI smoke、Workbook 回读、完整 regression、pytest、build、docs-sync、BOM、diff、ZIP/公式/外链/宏和敏感信息检查。
- Next starts when：已满足；Commit 6B 是后续开发基线，P0-T4 可开始实现四类 Draft generators。

### 已完成 Commit 7A：冻结 P0-T4 contract

- Suggested message：`docs: define P0-T4 draft generation contract`
- Scope/Files：Phase0 requirements、system overview、ADR-0003 amendment、active plan 与已知 P0-T3 状态漂移；不修改 runtime。
- Completion signal：provider/request/response、fixture case、workspace paths、Human Review gate 和验收命令 decision complete。
- Verification：内部链接、UTF-8 no BOM、`git diff --check`。
- Next starts when：文档与已确认实施计划一致。

### 已完成 Commit 7B：provider-neutral runtime 与 Draft candidate

- Suggested message：`feat: add provider-neutral IR draft generation`
- Scope/Files：provider contract、strict response/case loader、四类 orchestration、DocIR structure check、workspace publication、`generate-draft` CLI、六类 deterministic responses、tests、README/docs-sync；不冻结 Final DocIR。
- Completion signal：六个受控调用确定性输出，所有非法 provider/dependency/path/lifecycle 在写盘前 fail closed；生成准确 DocIR candidate 和 PENDING review notes。
- Verification：targeted/full pytest、CLI smoke、build、docs-sync、BOM/diff/secret 检查。
- Next starts when：向 Human 展示 DocIR candidate 准确 bytes hash、Review Golden diff、结构结果和 review notes。

### 已完成 Human Review Gate：Final DocIR

- Human 只确认准确 DocIR candidate；它可以保留忠实反映 raw doc 的冲突和不确定项，但不得把后续 SchemaIR/Standard 事实倒灌到 DocIR。
- 未获具名 reviewer 对准确 bytes hash 的明确确认前，不写入 `docir-final.md`，不启用完整 Draft-to-Workbook regression，也不把 P0-T4 标为 Done。
- Evidence：`deng` 于 `2026-08-10T10:35:51+08:00` 明确批准 `sha256:31d7fc002ccc2b840f401206f54665e36771f2bb5502d480566defdff9ac7585`；同意冲突和不确定项显式保留且不视为已确认业务事实。

### 已完成 Commit 7C：冻结 reviewed Final DocIR

- Suggested message：`chore: freeze reviewed Final DocIR fixture`
- Scope/Files：获批 `docir-final.md`、具名 reviewer/time/hash 记录、byte/hash regression 和最小状态同步；不改变 generator runtime。
- Completion signal：SchemaIR stub case 只接受获批 Final DocIR hash；任一内容变化都会使 Review 和 case 匹配失效。
- Verification：candidate/hash equality、Review 记录、完整 pytest、docs-sync、BOM/diff 检查。
- Next starts when：Final DocIR commit 成为当前开发基线。

### 已完成 Commit 7D：完整 Draft-to-Workbook closure

- Suggested message：`feat: complete phase0 draft generation workflow`
- Scope/Files：完整受控回归、双方向 CLI smoke、structured Workbook comparison、README/phase/plan/sample 状态；测试中显式装载已审核 Final fixtures，不实现自动 promotion。
- Completion signal：四类 generator 不能绕过可信边界，相同 fixture 可重复生成 Draft，双方向 Workbook 与 Golden 一致，P0-T4/Phase0 改为 Done。
- Verification：完整 pytest/build/docs-sync、BOM/diff/secret 和 Workbook 公式/宏/外链检查。
- Next starts when：P0-T4 fixture boundary 完成；P0-T5 真实 LLM 验证可开始。

## 8. 整体验收与验证要求

### 8.1 每个实现批次

- 对应模块的字段级/引用级正反向 UT。
- `uv --cache-dir .uv-cache run --group dev pytest -q -p no:cacheprovider --basetemp .pytest-p0`
- `git diff --check`
- UTF-8 no BOM 检查。
- Rule ID、内部链接和 artifact reference 检查。
- 真实/脱敏 fixture 与高置信 secret 扫描。
- code、tests 和已知文档同步在同一逻辑 commit；完成后运行 docs-sync。
- 用户可见命令、artifact、配置、验证方式或阶段状态变化时强制检查根 `README.md`。

### 8.2 P0-T3 完成门禁

**状态：PASS。以下门禁均由运行时、fixture 和自动化 regression 覆盖。**

- `configuration-rules/v1`、v2 均为 RELEASED 且不可变，Standard/Template 分别加载其实际引用版本。
- SchemaIR/Standard/Template machine contract 和 validation result contract 已冻结。
- 每条方向链的 SchemaIR/Standard/Template Final artifact 均具有 Human Review 证据和完整相等的重新计算 validation result。
- ASSEMBLY/PARSE 的 Standard、Template 和 Workbook 均有 golden regression。
- 六种 Value Mode、MAPPING/Replacement、三种 binding、Standard 镜像、银行 Condition、XML Key expression、omission 和 secure input 均被覆盖。
- `check --profile phase0` 与 `generate-workbook` 使用显式 selector 和两个规则包路径，不扫描、猜测或自动选择最新版。
- Workbook 输入错误 fail closed；输出无业务公式、宏、外链、敏感固定值、Mapping entries/target 或静默截断。
- 相同 Final chain、results、规则版本、Standard Action 和固定任务上下文可重复生成相同结构化内容。
- 完整 P0-T3 链路不依赖未确认业务默认值、历史导出 ID 或模型常识；该门禁已满足，P0-T3 为 Done，P0-T4 已解锁。

### 8.3 Phase0-PoC 最终门禁

**状态：IN PROGRESS。P0-T3 与 P0-T4 的完成标志已由实现和自动化 regression 覆盖；P0-T5 尚未实现和验证。**

- P0-T3 完成门禁全部通过。
- 四类 deterministic Draft generator 可运行，通过同一 provider contract 产生合法 Draft，且不能生成 Final 或绕过 Human Review/Validator。
- Draft-to-Workbook 完整回归可重复运行，显式装载 reviewed Final fixtures 后生成的双方向 Workbook 与 Golden 结构化一致。
- P0-T5 必须完成六次真实 OpenAI-compatible Chat API Draft、逐层独立 Human Review/Final validation 与双方向 Workbook 验证；完成前 Phase0-PoC 不得改为 Done 或进入 Phase1 planning。
