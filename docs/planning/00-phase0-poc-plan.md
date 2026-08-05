# Phase0-PoC 执行计划

## Status

Active. P0-T3 is In Progress; the source-material blocker is resolved and `configuration-rules/v1` Draft is available.

## 1. 目标与边界

Phase0-PoC 证明一条无 UI、可重复运行、可回归的可信链路：

```text
Raw Docs
→ Final DocIR
→ SchemaIR Draft / Validator / Final SchemaIR
→ InterfaceStandardIR Draft / Validator / Final Standard
→ InterfaceTemplateIR Draft / Validator / Final Template
→ Configuration Workbook
→ golden regression
```

LLM 只生成 Draft。Template 必须基于精确绑定的 Final Standard。Workbook Generator 只消费三份 Final 模型、三份通过校验结果、精确规则版本和调用者显式指定的 Standard Action。

Phase0a 不再作为独立 active phase。已完成 CLI、`ingest`、workspace artifact 协议和 `check` 统一记录为 Phase0 bootstrap。

## 2. 当前状态

| TASK | 状态 | 依赖 | 阻塞点 | 完成标志 |
|---|---|---|---|---|
| P0-T0：Bootstrap | Done | 无 | 无 | CLI 可导入 raw doc，workspace artifact 协议和 `check --profile raw\|phase0a` 可用。 |
| P0-T1：`b2e0061` IR candidate / Review | Done | P0-T0 | 无 | Candidate DocIR / SchemaIR 经 Human Review 更新，正式 IR 设计和 reference 边界清晰。 |
| P0-T2：Review Golden sample boundary | Done | P0-T1 | 无 | Expected DocIR、expected SchemaIR 和 expected review notes 已冻结。 |
| P0-T3：Trusted chain | In Progress | P0-T2、`configuration-rules/v1` Draft | 无启动 blocker；规则包仍需提交 loader/validator 并发布，两个配置 IR/Validator/Workbook 尚未实现 | 保留已完成 SchemaIR Validator；发布规则包，完成两个配置 IR contract/fixture/Validator、Workbook 和完整 regression。 |
| P0-T4：Draft generators | Blocked | P0-T3 | trusted chain 未完成 | DocIR、SchemaIR、Standard、Template 四个 stub 与 LLM Draft generator 可运行，且 LLM 不进入可信边界。 |

状态定义：

- `Done`：完成标志与验证均已满足。
- `In Progress`：已有可验证子产物，但完整完成标志未满足。
- `Next`：依赖已满足，应优先执行。
- `Blocked`：存在明确前置条件，不能开始或继续关键工作。

## 3. 已完成证据

- `samples/golden/b2eboc-b2e0061/docir.expected.md`
- `samples/golden/b2eboc-b2e0061/schemair.expected.json`
- `samples/golden/b2eboc-b2e0061/review-notes.expected.md`
- `samples/golden/b2eboc-b2e0061/schemair-validation.expected.json`
- SchemaIR Validator v1 及自动化测试

这些证据只证明 DocIR / SchemaIR Review boundary 和 SchemaIR Validator，不证明规则包、InterfaceStandardIR、InterfaceTemplateIR、Configuration Workbook 或完整可信链路已实现。

SchemaIR Validator 当前仍接受 legacy JSON 枚举。这是待修实现差距，不是 JSON 银行报文支持证据。

## 4. P0-T3：Trusted chain

### 4.1 已解除的资料 blocker 与剩余边界

以下输入已经提供并形成 `configuration-rules/v1` Draft：

- `bkl.md` 的 Value Mode、function 声明和数据类型；
- ASSEMBLY/PARSE 方向字段清单；
- b2e0061 正式 Standard/Template 双向导出；
- 银行文档及 `obssid` 等明确条件约束；
- 维护人 `deng` 与业务 reviewer `configuration-reviewer`；
- PARSE 固定对象、Condition、MAPPING、Replacement、完整 processing policy 和脱敏边界的业务确认；
- `mapping.txt` 预设规则样例子集与 `others.json` MAPPING Template 行。

因此 P0-T3 可以开始实现。以下未知项不阻止 P0，但不得被实现者推断：

- 相近 function code 的 alias 关系；
- processing policy 的系统默认值；P0 必须显式保存选择；
- 目标系统全量 Mapping catalog；v1 只覆盖已提供样例子集。

MAPPING 与 Replacement 已纳入 P0 IR/Validator/Workbook/专项 golden；目的系统业务 Condition 仍明确排除，不得为关闭测试覆盖而补猜。

### 4.2 规则包 v1

输入条件：已满足；真实资料和治理身份已提供。

```text
configuration-rules/v1/
├── README.md
├── rules.md
├── rules.yaml
├── fields.yaml
├── functions.yaml
├── mappings.yaml
└── review.md
```

完成标志：

- Standard 结构映射、方向性 Template 表达式和已观察 processing policy 均有来源。
- 每条可引用规则具有稳定唯一 Rule ID。
- FIELD/function catalog 区分 BKL 声明与正式导出观察，不合并相似标识；Function 类型统一为 String。
- Mapping catalog 名称全局唯一，String entries、MAPPING unmatched error 与 Replacement 片段语义可校验。
- YAML 可安全加载，引用闭合，review checks 完成。
- v1 由 `deng` 和 `configuration-reviewer` 确认，切换到 RELEASED 后不可原地覆盖。

### 4.3 SchemaIR Validator XML-only 对齐

后续实现批次必须：

- 将 `messageFormat` 产品值收紧为 XML；
- 在 `messages[].xmlEncoding` 保存方向级 Final encoding，冲突证据必须 Review；
- 移除当前产品路径中的 JSON_OBJECT / JSON_ARRAY；
- 增加拒绝 legacy JSON 枚举的测试；
- 保持现有 XML golden validation 通过。

### 4.4 InterfaceStandardIR contract 与 fixture

输入条件：`configuration-rules/v1` 已确认。

涉及范围：

- 冻结 machine JSON contract；
- 为 b2e0061 的 ASSEMBLY/PARSE 形成经人工确认的 expected Standard；
- 覆盖 stable identity、version、SchemaIR content hash；
- 覆盖 fieldId、sequence、parentPath/fullPath；
- 覆盖 Node/Object/标量和 XML Keys；
- 覆盖 VALUE、NO_CONSTRAINT、UNKNOWN；
- 覆盖 SchemaIR/Standard 差异、原因、Rule ID 和人工结论。
- 覆盖基础 Required 与银行文档条件 Required 分离，包括 `transtype=2 => obssid required`。
- 以 raw-doc/Final SchemaIR 为银行事实权威：b2e0061 保留 `@security`、排除 `vamflag`，`@lang` 仅作 observed evidence/difference Warning。
- `b2e0061-rq`、`b2e0061-rs` 按 `0..1000` 为 Node；raw-doc 未写约束时为 `NO_CONSTRAINT`，冲突或无法判定时为 `UNKNOWN`。

完成标志：所有配置与 Rule ID 可追溯；UNKNOWN 和未确认差异保持显式；fixture 经业务负责人确认。

### 4.5 Standard Validator

涉及范围：

- identity/version/source hash；
- field/path/sequence/hierarchy；
- XML type 和 List 拒绝；
- XML Keys 与 SchemaIR attributes；
- constraint states 和 difference Review；
- 银行条件的 field reference、operator/effect、literal、evidence 与 Review；
- Final 条件。

完成标志：返回可定位到 direction、fieldId、path 和 Rule ID 的错误，不以程序判断替代业务 Review。

### 4.6 InterfaceTemplateIR contract 与 fixture

输入条件：Final Standard fixtures 与 v1 catalog 已确认。

涉及范围：

- 冻结 machine JSON contract；
- 精确 Standard ID/version/content hash 绑定；
- 每个 field config 显式保存 `standardProjection.required/length/dataType`；
- `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM`，包括 `b2e0061-rs(Node) -> paymentLineList(List)`；
- ASSEMBLY target Standard Field；PARSE target Parse Field，表达式内 FIELD_REF 引用绑定 Standard；
- ASSEMBLY 标量 fieldConfigs 与 omissions 分离，Node/Object 不参加 coverage；PARSE 未配置 field 不生成 omission；
- 六种 Value Mode；MAPPING 使用一个 String FIELD_REF 和一个 `mappingRuleName`；
- 标量字段值与 XML Key expressions，Node/Object 不包含字段值表达式；
- 完整 empty/overlength、正整数 row limit、`STANDARD_1..6` 和单一 Replacement rule；
- omission reason 与 Review disposition。
- FIXED_VALUE 的 `LITERAL | SECURE_INPUT_REF` payload；安全输入只保存引用标识。

完成标志：未确认 ASSEMBLY omission 阻止 Final；确认 omission 可 Final 且仍生成 Warning；PARSE 只校验实际配置目标；omission、EMPTY、Empty Handling 不混淆。

### 4.7 Template Validator

涉及范围：

- Standard 版本和 hash 精确匹配；
- `standardProjection.required/length/dataType` 与 Standard 完全一致；
- binding kind 与方向、Standard 类型和 Parse target 相容；
- ASSEMBLY target standardFieldRef 存在且不重复；
- PARSE target parseFieldRef 存在、path/datatype 相容，表达式内 standardFieldRef 存在；
- 标量字段值/XML Key expression tree 和 catalog/Rule ID 引用；
- Function String 类型、MAPPING 完整值匹配/未匹配 error、Replacement 片段替换/删除/保留；
- 标量字段必须有字段值表达式，Node/Object 不得有字段值表达式；
- XML Key expression 完整性；
- ASSEMBLY 标量 omission coverage 与人工结论；Node/Object 不参加 coverage，有 XML Key/结构需求时必须使用适用结构绑定；PARSE 不做 catalog coverage 推断；
- SECURE_INPUT_REF 不携带真实值；
- Final 条件。

完成标志：返回可定位到 templateId、source/target fieldRef、expression/XML Key 和 Rule ID 的错误，不代替 function、mapping、目的系统业务 Condition 或 omission 业务 Review。

### 4.8 Configuration Workbook 与 regression

涉及范围：

- 固定七个 sheet；
- 一份方向标准 + 一份绑定模板；
- Standard Action CREATE/REUSE/UPDATE；
- Standard 完整快照与 Template 方向性 source/target 绑定；
- Overview 展示方向级 XML encoding；Template 将 Standard 快照、Template 镜像、Parse target 和 Value Expression 分列；
- `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM`，包括 Node 到 Parse List 元素的结构绑定；
- 标量字段/XML Key Value Expressions 展开，Node/Object 不生成 FIELD_VALUE 节点；
- MAPPING/Replacement `mappingRuleName` 展示且不复制 entries；
- 银行条件、ASSEMBLY omissions、差异、Warnings 与 Rule References；
- `workbook-assertions.expected.json`；
- 完整 trusted-chain golden regression。

完成标志：

- 相同三份 Final、三份校验结果、规则版本和 Standard Action 可重复生成相同结构化内容。
- ASSEMBLY 标量 omission 不制造虚假行，已确认 omission 在 Warnings 可追溯；Node/Object 不制造 omission，未配置 Parse Field 不制造 Warning。
- 六种 Value Mode、Replacement、Node/Object 无字段值表达式、XML Key expression、银行条件和 REUSE 状态均有断言。
- Standard 镜像、两端 datatype、SECURE_INPUT_REF 不泄露真实值和 direction-level encoding 均有断言。

### 4.9 Implementation commit plan

#### Commit 1：冻结 P0-T3 文档契约

- 建议提交信息：`docs: finalize P0-T3 configuration contract`。
- 边界：只同步 requirements、active design、ADR amendment、phase/planning、各级 README、reference 说明和 `configuration-rules/v1` Draft 事实；不实现代码，不修改正式导出或 P0-T2 expected artifacts。
- 涉及文件：`README.md`、`docs/01-requirements.md`、`docs/{adr,design,phases,planning,reference}/**/*.md`、`configuration-rules/{README.md,v1/*}` 和 `samples/golden/b2eboc-b2e0061/README.md`。
- 完成标志：银行事实投影、direction-level encoding、Standard 镜像、三种 binding kind、容器 coverage、PARSE 两端列和 SECURE_INPUT_REF 在所有 active contract 中一致；规则包仍为 `DRAFT`，P0-T3 仍为 `In Progress`。
- 下次开始条件：文档 diff 经确认；maintainer/business reviewer 未正式发布前不得把 v1 改为 `RELEASED`。

#### Commit 2：发布规则包并实现 loader/validator

- 边界：加入 PyYAML safe loader、规则包 schema/validator、Rule ID/字段/function/Mapping 引用测试；不实现 Standard/Template IR。
- 涉及文件：`configuration-rules/v1/*`、规则 loader/validator 模块、对应 tests、`pyproject.toml`、`uv.lock` 和必要文档同步。
- 完成标志：YAML 安全加载、Rule ID 唯一且引用闭合、b2e0061 所需 catalog 可解析，v1 Review checks 经 `deng` 与 `configuration-reviewer` 正式确认并切换到 `RELEASED`。
- 下次开始条件：规则版本冻结，样例必需值不存在实现者猜测。

#### Commit 3：完成 XML-only SchemaIR 与 InterfaceStandardIR 链路

- 边界：收紧 SchemaIR XML 枚举并增加 `messages[].xmlEncoding`；实现 Standard contract/validator、银行条件最小结构和双向 expected Standard。
- 涉及文件：SchemaIR/Standard contract 与 validator 模块、b2e0061 Standard fixtures/tests、对应设计文档。
- 完成标志：identity/hash、path/sequence、类型、XML Keys、三态约束、银行条件、encoding、`@security`/`vamflag`/`@lang` 差异和 Rule References 通过校验并经人工确认。
- 下次开始条件：两份 Final Standard fixture 冻结，修改会产生新 version/hash。

#### Commit 4：完成 InterfaceTemplateIR 链路

- 边界：实现 Standard 镜像、三种 binding kind、方向性 source/target、FIELD/function 参数、递归 CONCATENATE、MAPPING、Replacement、processing policy、XML Key expressions、SECURE_INPUT_REF 和 ASSEMBLY 标量 omissions；Template Condition 继续 fail closed。
- 涉及文件：Template contract/validator、双向 expected Template、validation results、tests 和对应设计文档。
- 完成标志：ASSEMBLY 标量配置或 omission 完整，Node/Object coverage 正确，PARSE collection/target 引用合法，MAPPING/Replacement catalog 和执行约束通过，未知引用和越界能力 fail closed。
- 下次开始条件：两份 Final Template fixture 及 validation result 冻结。

#### Commit 5：生成 Configuration Workbook 并闭合 golden regression

- 边界：使用 openpyxl 生成固定七个 sheet，扩展 workspace artifact/CLI，加入来源矩阵、结构化 workbook assertions 和完整 trusted-chain regression。
- 涉及文件：Workbook generator、workspace/CLI 边界、golden workbook assertions、tests、README 和相关文档。
- 完成标志：相同 Final 输入、校验结果、规则版本和 Standard Action 产生相同结构化内容；encoding、Standard 镜像、两端 datatype、三种 binding、银行条件、SECURE_INPUT_REF、MAPPING/Replacement、Warnings、Rule References 和 REUSE 状态可回读断言。
- 下次开始条件：全部 P0-T3 验收通过后改为 Done，P0-T4 才解除依赖。

## 5. P0-T4：Draft generators

P0-T3 完成后接入四个 Draft generator：

- Raw Docs → DocIR Draft；
- Final DocIR → SchemaIR Draft；
- Final SchemaIR + 指定规则版本 → InterfaceStandardIR Draft；
- Final Standard + 指定规则版本 → InterfaceTemplateIR Draft。

涉及范围：确定性 stub、OpenAI-compatible adapter、输出结构校验、缺配置错误和敏感日志约束。

完成标志：

- LLM 只能生成 Draft，不能直接写 Final。
- Stub 输出稳定并可用于测试。
- Template generator 拒绝非 Final 或版本/hash 不匹配的 Standard。
- 缺 catalog 时 Standard/Template Draft generation fail closed。
- 日志不输出完整银行原文、规则敏感内容或 secret。

## 6. 验证要求

当前文档批次：

- `git diff --check`
- UTF-8 no BOM 检查
- 活动文档旧产品术语搜索
- Markdown 本地路径存在性检查
- `yaml.safe_load` 和 Rule ID/引用闭合检查
- README、phase、planning、design、ADR 和规则资产交叉核对
- `uv --cache-dir .uv-cache run --group dev pytest -q -p no:cacheprovider --basetemp .pytest-docs`

后续实现批次：

- `uv --cache-dir .uv-cache run --group dev pytest -q -p no:cacheprovider --basetemp .pytest-p0t3`
- SchemaIR / Standard / Template Validator 字段级错误测试
- Workbook 结构化 assertions
- 完整 golden regression
- 代码变更后的 docs-sync

只要用户可见命令、artifact、配置、验证方式或阶段状态变化，必须检查根 `README.md`。
