# Phase0-PoC 需求

## Status

Draft. Trusted-chain work is partially implemented; the rule runtime, reviewed Final SchemaIR v2 fixture, InterfaceStandardIR runtime/two reviewed Final Standards, and InterfaceTemplateIR Draft runtime/candidates are complete. Final InterfaceTemplateIR and Configuration Workbook remain P0-T3 work.

## 1. 阶段目标

Phase0-PoC 证明一条无 UI、可重复运行、可校验、可人工确认、可回归的配置辅助链路可行：

```text
Raw Docs
→ DocIR Draft / Final DocIR
→ SchemaIR Draft / Validator / Final SchemaIR
→ InterfaceStandardIR Draft / Validator / Final Standard
→ InterfaceTemplateIR Draft / Validator / Final Template
→ deterministic Configuration Workbook
→ structured golden regression
```

本阶段不验证生产集成。成功标准是使用真实脱敏 XML 银行接口样例产出四层 IR、三份校验结果和按方向模板生成的 Configuration Workbook，并以结构化 assertions 证明链路可重复。

LLM、Agent 或 workflow 可以生成 Draft，但不能替代 Validator、人工确认、确定性 Generator 和 golden regression。

## 2. 当前事实

已完成：

- Python CLI、`ingest`、严格 workspace JSON artifact I/O 和 `check --profile raw`；legacy `phase0a` 已移除。
- `b2e0061` reference raw doc。
- 经人工 Review 的 expected DocIR、expected SchemaIR 和 expected review notes。
- SchemaIR v2 XML-only Validator、canonical hash/result contract、encoding evidence、结构化条件和已冻结的 49-field b2e0061 Final fixture；准确 hash 已由 `deng` 确认，当前结果为 0 ERROR、0 WARNING、0 blocking issue，`finalEligible=true`。
- `configuration-rules/v1` 已收束为接口无关、非全量的 BKL configuration rules 子集，并具有仓库内 safe loader、严格 schema/semantic validator 和引用闭合测试；双 reviewer 已确认候选并于 2026-08-06 发布，默认 loader 可直接加载该 `RELEASED` 版本。
- `configuration-rules/v2` 继承 v1 的全部 catalog，只修订方向相关 Standard projection；maintainer 与 business reviewer 已确认准确候选，并于 2026-08-09 发布为 `RELEASED` 后冻结。
- `interface-standard/v1` 与 `interface-standard-validation-result/v1`、Standard Validator 及双方向 b2e0061 Final fixture；两个 Standard 均经 `deng` 确认准确 hash，结果为 0 ERROR、0 WARNING、0 blocking issue，`finalEligible=true`。
- `interface-template/v1` 与 `interface-template-validation-result/v1`、Template Validator 及双方向 b2e0061 Draft fixture；ASSEMBLY/PARSE 候选 hash 分别为 `sha256:356b83c1aff90d83d82fa3bbc14f7fe8277c34605a3d5edb4cb99abd71c49957`、`sha256:33cd4f7ae02701d6ab19cf46628398354590dba3d612f91e43b06f78d1356621`，仍等待 Human Review。

尚未完成：

- 四类 IR Draft generator。
- 人工确认并冻结双方向 Final InterfaceTemplateIR fixture/result。
- Configuration Workbook Generator、expected workbook 和结构化 assertions。
- 覆盖完整可信链路的 golden regression。

`configuration-rules/v1` 与 v2 均已发布并冻结；v2 不改变其 27/207/14/5/6 catalog、Function String、Mapping/Replacement、字符长度默认 `STANDARD_1` 或业务 Condition 边界，只修订 Template Standard projection。现有 Final Standard 继续绑定 v1；当前 InterfaceTemplateIR Draft 精确绑定 v2。详细任务状态见 `docs/planning/00-phase0-poc-plan.md`。

## 3. In Scope

- 使用一份真实脱敏 XML 银行接口文档作为验证样例。
- `.md`、`.txt` 和粘贴文本输入。
- Raw Docs 到 DocIR Draft，人工确认 Final DocIR fixture。
- Final DocIR 到 SchemaIR Draft，SchemaIR Validator，人工确认 Final SchemaIR fixture。
- 整理并由业务负责人确认不可变 `configuration-rules/v1`。
- Final SchemaIR 到 InterfaceStandardIR Draft、Standard Validator 和人工确认 Final Standard。
- Final Standard 到 InterfaceTemplateIR Draft、Template Validator 和人工确认 Final Template。
- 一个标准关联多份同方向模板，模板精确绑定不可变标准版本。
- ASSEMBLY 模板字段子集/omission 与 PARSE Standard source 到 Parse Field target。
- 方向级 `messages[].xmlEncoding`、显式 evidence/conflict disposition Review，并在 Workbook Overview 展示。
- ASSEMBLY Template 显式镜像 Standard target 的 required/length/dataType；PARSE 从表达式或 collection source 的 Standard reference 派生。
- `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM` 结构绑定；b2e0061 重复响应 Node 创建 `paymentLineList` 元素。
- 银行文档明确条件与基础 Required 分离，并在 Standard/Workbook 中可追溯。
- 标量字段值和 XML Key 使用同一递归 Value Expression 模型；Node/Object 无字段值表达式。
- MAPPING/Replacement 通过全局唯一 `mappingRuleName` 引用预设 catalog，并使用各自的 unmatched 语义。
- Workbook Generator 基于三份 Final 模型、三份校验结果、规则版本和 Standard Action 生成一份方向模板工作簿。
- 保存关键中间产物和结构化 golden regression。

## 4. Out of Scope

- UI。
- JSON 银行报文；Parse Field Catalog 中固定输出对象的 `List` 不表示支持 JSON 银行报文。
- `.docx`、PDF、OCR、bbox 和原文区域高亮。
- Import JSON、目标系统 API 写入、自动导入和生产库直连。
- Excel 反向导入或更新任一 IR。
- 连接、认证、证书、部署或全量系统配置。
- 目的系统业务 Condition、同一目标字段多条模板行和运行时选择逻辑。
- 多用户、权限和审批流。
- RAG、多 Agent、自动微调、自动规则学习。
- 多银行和多报文标准泛化。

## 5. 功能需求

### 5.1 DocIR 与 SchemaIR

DocIR Draft 至少保留接口编码、XML 格式、ASSEMBLY/PARSE、字段表、章节、XML 示例、条件、来源证据、冲突和不确定项。人工确认后形成 Final DocIR。

SchemaIR Draft 保存银行 XML element、attribute、完整 path、父子层级、类型、required、length、occurs、condition、方向级 `xmlEncoding` 和 evidence。SchemaIR Validator 必须提供字段级错误。Human 先完成包括 Final lifecycle/Review metadata 在内的完整 candidate，再重新运行 Validator；只有 identity/version/contract/canonical hash 匹配且 `finalEligible=true` 的结果可以进入下游。b2e0061 两个方向已由 Human 与银行线下确认为 `UTF-8`；显式文档 evidence 冲突产生 blocking Warning，直到 Human Review 处置。Final encoding 不生成 Standard 字段。

### 5.2 规则包

Phase0 必须使用业务负责人确认的版本化规则包；`configuration-rules/v1` 与 v2 都是接口无关、非全量且不可变的 BKL configuration rules 子集。Final IR 只能精确引用适用的 `RELEASED` 版本，不能自动选择最新版本。规则包包含：

- Interface Standard 的路径、类型和约束映射规则；
- 六种 Value Mode 和模板处理策略；
- 稳定 Rule ID；
- 方向性 FIELD、String function 与预设 Mapping catalog 样例子集。

未确认事实保持 `UNKNOWN`，不得制造占位业务标识。Template 只保存全局唯一 `mappingRuleName`，不内联 entries；当前 catalog 是样例子集，不声称全量覆盖。

### 5.3 InterfaceStandardIR

LLM 结合 Final SchemaIR 和规则版本生成 Standard Draft，至少覆盖：

- `interfaceCode + direction`、稳定 ID 和不可变版本；
- fieldId、sequence、field name/description；
- parentPath 与 fullPath；
- required、length、illegal characters、regex；
- XML Keys；
- String/Boolean/Date/Number/Node/Object；
- VALUE、NO_CONSTRAINT、UNKNOWN；
- SchemaIR/Standard 差异、规则依据和人工结论。
- 银行文档明确条件与基础 Required 分离，例如 `transtype=2 => obssid required`。

银行字段、路径、出现次数和约束以 raw-doc/Final SchemaIR 为准；正式导出只证明目标系统形态。raw-doc 在已审查范围内未写约束时使用 `NO_CONSTRAINT`，证据冲突或无法判定时使用 `UNKNOWN`。b2e0061 Standard 保留 `@security`、排除 `vamflag`；observed `@lang` 只保留在来源和 Review 证据中，不作为 Final SchemaIR 或 Standard 字段。请求 `b2e0061-rq` 按 `1..1000`、响应 `b2e0061-rs` 按 `0..1000` 建模，二者均为 `Node`。

Standard Validator 只校验结构、来源引用和确定性 invariant。人工确认后形成 Final Standard。

### 5.4 InterfaceTemplateIR

LLM 基于 Final Standard 和规则版本生成 Template Draft，至少覆盖：

- 精确 Standard ID/version/content hash 绑定；
- ASSEMBLY 显式保存并严格校验 `standardTarget.standardProjection`；PARSE 从精确绑定的 Final Standard 解析表达式/collection source projection；
- `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM`，其中 `b2e0061-rs(Node) -> paymentLineList(List)` 为集合元素绑定；
- ASSEMBLY target Standard Field；PARSE target Parse Field，表达式内 FIELD_REF 引用绑定 Standard；
- ASSEMBLY 标量 Standard Field 子集和 omissions，Node/Object 不参加 coverage；PARSE configured-targets-only；
- 六种 Value Mode；MAPPING 使用 String FIELD input、单一预设规则并在未匹配时报错；
- 标量字段值与每个 XML Key 的独立表达式，Node/Object 不配置字段值表达式；
- 完整 empty/overlength、正整数 row limit、`STANDARD_1..6` 和单一 Replacement rule；
- Rule ID、confidence、不确定原因和人工结论；
- ASSEMBLY 缺失字段的 Warning、omission reason 与 Review disposition。
- FIXED_VALUE payload 使用 `LITERAL | SECURE_INPUT_REF`；安全输入只保存引用标识。

未确认 ASSEMBLY 标量 omission 阻止 Final Template；确认有意省略后允许 Final 并继续进入 Workbook Warnings。Node/Object 不产生 omission；有 XML Key 或结构绑定需求时必须有适用结构行，缺失配置直接报错。未配置 Parse Field 不产生 omission/warning。Template Validator 不能代替人工判断 function、mapping、目的系统业务 Condition 或 omission 的业务语义。

### 5.5 Configuration Workbook

Generator 只读取 Final SchemaIR、Final Standard、选定的 Final Template、三份匹配的校验结果、精确规则版本和显式 Standard Action。

工作簿固定包含 `Overview`、`Interface Standard`、`Interface Template`、`Value Expressions`、`Warnings`、`Rule References`、`Legend`。

`Overview` 展示方向级 XML encoding。`Interface Template` 将 Standard 快照、Template required/length/dataType 镜像、Parse target 和 Value Expression 分列，不能把 `b2e0061-rs(Node)` 与 `paymentLineList(List)` 合并为一种类型。`Value Expressions` 按树展开标量字段值和 XML Key 表达式，是 Final Template 的派生明细，不是额外事实源。Node/Object 不生成 FIELD_VALUE 节点；已确认 ASSEMBLY omission 和银行条件进入 Warnings，不在 Template Sheet 生成虚假行；未配置 Parse Field 不制造 Warning。

工作簿不直接导入目标系统，也不反向更新任一 IR。

## 6. Golden Regression

Phase0 golden regression 至少覆盖：

- ASSEMBLY 与 PARSE 独立标准和模板；
- parentPath/fullPath、sequence、Node/Object、XML Keys；
- direction-level XML encoding、`@security`/`vamflag`/`@lang` 投影决定；
- VALUE、NO_CONSTRAINT、UNKNOWN；
- P0 支持的 FIXED_VALUE、EMPTY、FIELD、FUNCTION 和递归 CONCATENATE；
- MAPPING/Replacement 的 catalog reference、匹配/替换行为与错误路径；
- 标量字段必须有字段值表达式，Node/Object 不得有字段值表达式；
- ASSEMBLY 标量字段子集、未确认/已确认 omission 和 EMPTY 的区别；Node/Object 不产生 omission；
- PARSE Standard source 到 Parse Field target 及 configured-targets-only 校验；
- Standard 镜像一致性、三种 binding kind 和 `b2e0061-rs(Node) -> paymentLineList(List)`；
- FIXED_VALUE 的 `LITERAL`/`SECURE_INPUT_REF` 与安全值不落盘；
- 银行条件与基础 Required 分离；
- 标量字段值与 XML Key expression tree；
- Standard version/hash mismatch；
- SchemaIR/Standard 差异、规则冲突和 warnings；
- 七个固定 workbook sheet、Standard Action 和状态列。

具体业务字段、function、`mappingRuleName` 和 Rule ID 只能来自 IR 精确引用的已发布 catalog。MAPPING/Replacement 属于 P0 专项 golden；目的系统业务 Condition 不属于 P0 golden 成功路径。

## 7. 通过条件

- 四类 IR 逻辑契约与机器格式均已冻结。
- `configuration-rules/v1` 与 v2 内容可追溯且经业务负责人确认。
- 三个 Validator 都能返回可定位的错误。
- 四个 Draft generator 可运行，且不会绕过人工确认形成 Final。
- Template 只能基于精确绑定的 Final Standard 生成。
- ASSEMBLY 标量字段子集/omission、容器结构绑定和 PARSE configured targets 可回归验证。
- 三份 Final 模型可以稳定生成一个方向模板的 Configuration Workbook。
- 完整链路可重复运行并通过测试。

规则包未 RELEASED、Final Standard/Template fixture 未冻结或完整 regression 未通过时，Phase0 不满足通过条件。
