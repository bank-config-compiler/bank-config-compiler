# Phase0-PoC 执行计划

## Status

Active. P0-T3 is blocked by the unavailable target-system catalog.

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
| P0-T3：Trusted chain | Blocked | P0-T2、真实 catalog | 不能形成 `configuration-rules/v1`、Final Standard/Template 或 Workbook assertions | 保留已完成 SchemaIR Validator；完成规则包、两个配置 IR contract/fixture/Validator、Workbook 和完整 regression。 |
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

### 4.1 当前 blocker

需要用户后续整理并提供目标系统资料：

- 接口标准路径、类型、约束和 XML Keys 的实际配置规则；
- 字段原始标识和显示名称；
- function 原始标识、显示名称、参数和适用规则；
- mapping 原始标识、显示名称和业务含义；
- 六种 Value Mode 的选择规则；
- Node/Object 无字段值表达式时处理策略与 XML Key 表达式的适用规则；
- empty、overlength、row limit、中文字符长度和替换规则。

资料提供并经业务 Review 前：

- 不创建带占位内容的 `configuration-rules/v1`；
- 不从 `docs/reference/` 历史 JSON 提取 catalog 或目标配置事实；
- 不让 LLM 或实现者猜测字段、function、mapping 或 Rule ID；
- Standard/Template schema、fixture、Validator 和 Workbook Generator 保持 Blocked。

### 4.2 规则包 v1

输入条件：真实资料已提供。

```text
configuration-rules/v1/
├── README.md
├── rules.md
├── fields.md
├── functions.md
└── mappings.md
```

完成标志：

- Standard 结构映射、Template 表达式和处理规则均有来源。
- 每条可引用规则具有稳定唯一 Rule ID。
- catalog 只包含真实原始标识和显示名称。
- v1 经业务负责人确认，发布后不可原地覆盖。

### 4.3 SchemaIR Validator XML-only 对齐

后续实现批次必须：

- 将 `messageFormat` 产品值收紧为 XML；
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

完成标志：所有配置与 Rule ID 可追溯；UNKNOWN 和未确认差异保持显式；fixture 经业务负责人确认。

### 4.5 Standard Validator

涉及范围：

- identity/version/source hash；
- field/path/sequence/hierarchy；
- XML type 和 List 拒绝；
- XML Keys 与 SchemaIR attributes；
- constraint states 和 difference Review；
- Final 条件。

完成标志：返回可定位到 direction、fieldId、path 和 Rule ID 的错误，不以程序判断替代业务 Review。

### 4.6 InterfaceTemplateIR contract 与 fixture

输入条件：Final Standard fixtures 与 v1 catalog 已确认。

涉及范围：

- 冻结 machine JSON contract；
- 精确 Standard ID/version/content hash 绑定；
- 模板字段是标准字段子集；
- fieldConfigs 与 omissions 分离；
- 六种 Value Mode 和递归 CONCATENATE；
- 标量字段值与 XML Key expressions，Node/Object 不包含字段值表达式；
- empty/overlength、row limit、中文字符长度和 replacements；
- omission reason 与 Review disposition。

完成标志：未确认 omission 阻止 Final；确认 omission 可 Final 且仍生成 Warning；omission、EMPTY、Empty Handling 不混淆。

### 4.7 Template Validator

涉及范围：

- Standard 版本和 hash 精确匹配；
- standardFieldRef 存在且不重复；
- 标量字段值/XML Key expression tree 和 catalog/Rule ID 引用；
- 标量字段必须有字段值表达式，Node/Object 不得有字段值表达式；
- XML Key expression 完整性；
- omission coverage 与人工结论；
- Final 条件。

完成标志：返回可定位到 templateId、fieldRef、expression/XML Key 和 Rule ID 的错误，不代替 function/mapping/omission 业务 Review。

### 4.8 Configuration Workbook 与 regression

涉及范围：

- 固定七个 sheet；
- 一份方向标准 + 一份绑定模板；
- Standard Action CREATE/REUSE/UPDATE；
- Standard 完整快照与 Template 字段子集；
- 标量字段/XML Key Value Expressions 展开，Node/Object 不生成 FIELD_VALUE 节点；
- omissions、差异、Warnings 与 Rule References；
- `workbook-assertions.expected.json`；
- 完整 trusted-chain golden regression。

完成标志：

- 相同三份 Final、三份校验结果、规则版本和 Standard Action 可重复生成相同结构化内容。
- 模板 omission 不制造虚假行，已确认 omission 在 Warnings 可追溯。
- 六种 Value Mode、递归 CONCATENATE、Node/Object 无字段值表达式、XML Key expression 和 REUSE 状态均有断言。

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
- requirements/system-overview Mermaid 一致性与渲染检查
- README、phase、planning、design、ADR 和规则资产交叉核对

后续实现批次：

- `uv run --group dev pytest`
- SchemaIR / Standard / Template Validator 字段级错误测试
- Workbook 结构化 assertions
- 完整 golden regression
- 代码变更后的 docs-sync

只要用户可见命令、artifact、配置、验证方式或阶段状态变化，必须检查根 `README.md`。
