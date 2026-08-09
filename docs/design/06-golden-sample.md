# Golden Sample 设计

## Status

Draft. The immutable P0-T2 DocIR/SchemaIR Review Golden and the separate reviewed P0-T3 Final SchemaIR v2 fixture both exist. `configuration-rules/v1` and v2 projection semantics are released and frozen; two reviewed Final InterfaceStandardIR fixtures and two reviewed Final InterfaceTemplateIR fixtures with matching results exist. Configuration Workbook golden work remains in progress.

## 1. 目的

Golden sample 是 Prompt、四类 IR、三个 Validator、Workbook Generator 和验收判断的核心回归证据。它必须区分：

- 已由现有测试证明的 DocIR / SchemaIR 基线；
- 正在建立的目标配置和 Workbook 基线；
- 用于理解真实目标系统配置、但不直接成为 expected IR 的正式导出证据。

## 2. 完整 Golden 组成

一个完整样例至少包含：

- 真实脱敏 raw doc；
- 人工确认的 expected DocIR；
- 人工确认的 expected SchemaIR；
- expected SchemaIR validation result；
- 每个方向人工确认的 expected InterfaceStandardIR；
- expected Standard validation result；
- 至少一份绑定标准的 expected InterfaceTemplateIR；
- expected Template validation result；
- expected Configuration Workbook；
- workbook 结构化 assertions；
- Review notes 和规则来源。

`samples/golden/b2eboc-b2e0061/` 只证明 P0-T2 审查前 Review baseline，其 byte hash 固定且 legacy SchemaIR 被 v2 Validator 拒绝。`samples/trusted-chain/b2eboc-b2e0061/` 保存已评审 Final SchemaIR v2、双方向 Final Standard/Template、匹配 results 和 APPROVED reviews。SchemaIR hash 为 `sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162`；ASSEMBLY Standard hash 为 `sha256:9c77e0e92447907fa89d6ef705501dc0947d695998b80bb154476f696e9b982e`，PARSE Standard hash 为 `sha256:33efa544460ac19f216734712c1e6ae2610321ea17eb750eff35493ecca9d57e`。SchemaIR 与两份 Standard 均为 0 ERROR、0 WARNING、0 blocking issue，`finalEligible=true`。ASSEMBLY Template hash 为 `sha256:b9966a449ddc29e08fa29c6cf7838273ce3cab91e00dbb38092767d21af2f561`，保留 4 个经接受 omission 和 4 个非阻塞 Warning；PARSE Template hash 为 `sha256:16eb305b6ac3944f28cb1060b943fdfc2d471f69e6bf8ea52ce059c797fb22f9`，0 WARNING；两者均为 0 ERROR、0 blocking issue，`finalEligible=true`。

## 3. 规则来源边界

具体 Rule ID、FIELD、FUNCTION 和 `mappingRuleName` 只能来自适用的已发布规则版本。现有 Final Standard 精确引用 `configuration-rules/v1`，Final Template 精确引用 `configuration-rules/v2`。正式导出可以证明 b2e0061 实际配置和调用形态，但必须先经规则包治理和人工确认，不能被测试直接当作 expected IR。不得为满足覆盖创建占位业务标识或内联 Mapping entries。

Standard 与 Template fixture 必须分别记录实际使用的规则版本。模板必须绑定 expected Standard 的 stable ID、version 和 content hash。

## 4. Interface Standard 覆盖

Golden 至少覆盖：

- ASSEMBLY 与 PARSE 各一份独立标准；
- Parent Path 与 Full Path；
- 同级 Sequence；
- String/Boolean/Date/Number 中样例实际存在的标量类型；
- 可重复无值容器 `Node`；
- 不可重复无值容器 `Object`；
- XML attribute 转换为所属 element 的 XML Keys；
- VALUE、NO_CONSTRAINT 和 UNKNOWN 的 Review 路径；
- SchemaIR/Standard required、length、type 或其他差异；
- `transtype EQUALS "2" => obssid REQUIRED` 等银行文档条件与基础 Required 分离；
- 当前 XML 流程拒绝 JSON-only List。
- b2e0061 请求 `b2e0061-rq` 按 `1..1000`、响应 `b2e0061-rs` 按 `0..1000` 为 Node；`@security` 保留、`vamflag` 排除，observed `@lang` 只保留在来源和 Review 证据中。
- 方向级 `messages[].xmlEncoding` 冲突 Warning、Final 阻塞、Human Review 与 Workbook Overview 展示。

具体样例无法自然覆盖的类型或差异，应使用最小受控 fixture 补充，不能污染真实 golden 事实。

## 5. Interface Template 覆盖

Golden 至少覆盖：

- 六种 Value Mode；MAPPING 覆盖单一 FIELD input、预设规则引用和 unmatched error；
- Replacement 覆盖单一预设规则、片段替换、空 target 删除和未命中内容保留；
- ASSEMBLY 与 PARSE 使用同一表达结构，但 ASSEMBLY target 为 Standard Field、PARSE target 为 Parse Field；
- ASSEMBLY 配置行在 `standardTarget.standardProjection` 显式镜像 Standard required/length/dataType，任一不一致校验失败；PARSE 从表达式/collection source 的 Standard reference 派生；
- `VALUE`、`STRUCTURE_ONLY`、`COLLECTION_ITEM`，包括 `b2e0061-rs(Node) -> paymentLineList(List)`；
- String/Boolean/Date/Number 标量字段必须有字段值表达式，Node/Object 不得有字段值表达式；
- ASSEMBLY 模板 target 是标准字段子集；
- 缺失 ASSEMBLY 标量 Standard Field 生成 MISSING_TEMPLATE_FIELD Warning；Node/Object 不参加 omission coverage；
- PARSE 只校验实际配置的 Parse Field，未配置字段不生成 omission/warning；
- 未确认 omission 阻止 Final；
- 已确认 omission 带原因进入 Final，并继续出现在 Workbook Warnings；
- omission、EMPTY 与 Empty Handling 三者不同；
- 同一 ASSEMBLY `standardTarget.standardFieldRef` 或 PARSE `parseTarget.parseFieldRef` 重复时校验失败；
- 存在模板行时，每个标准 XML Key 有独立表达式；
- 未知或缺失 XML Key expression 校验失败；
- FIXED_VALUE 同时覆盖 `LITERAL` 与只保存引用标识的 `SECURE_INPUT_REF`；
- 标准 ID、version 或 content hash 不匹配时校验失败。

目的系统业务 Condition 和同目标多行是 future candidate，不属于当前 golden 成功路径。银行文档明确条件属于 Standard golden，并在 Workbook 中展示但不执行。

## 6. Workbook Assertions

Expected Workbook 固定包含：

```text
Overview
Interface Standard
Interface Template
Value Expressions
Warnings
Rule References
Legend
```

结构化 assertions 至少验证：

- 一份 workbook 只包含一个方向标准和一份绑定模板；
- Standard / Template identity、version、content hash 和规则版本准确；
- Overview 的方向级 XML encoding 来自 Final SchemaIR；
- Standard Action 为 CREATE、REUSE 或 UPDATE；
- REUSE 标准行不进入执行完成率；
- Standard Sheet 包含完整标准字段；
- Template Sheet 只包含实际配置的方向性绑定；
- Standard 快照、Template required/length/dataType 镜像、Parse target 与 Value Expression 分列，且镜像完全一致；
- `b2e0061-rs(Node) -> paymentLineList(List)` 的 COLLECTION_ITEM 及两端类型可还原；
- 已确认 ASSEMBLY omissions 只进入 Warnings，不制造空模板行；未配置 Parse Field 不制造 omission；
- Value Expressions 能按 Expression Scope 还原标量字段值和 XML Key 表达式树，并且不为 Node/Object 生成 FIELD_VALUE 节点；
- 递归 CONCATENATE 和 function 参数可结构化还原；
- MAPPING/Replacement 的 `mappingRuleName` 可还原且 Workbook 不复制 entries；
- SECURE_INPUT_REF 仅展示安全引用标识，不泄露真实值；
- 银行条件、evidence 和 Review disposition 可结构化还原；
- SchemaIR/Standard 差异、规则冲突、不确定项和 Validator warning 不被静默忽略；
- 相同 Final 输入、三份校验结果、规则版本和 Standard Action 可重复生成相同结构化业务内容。

不以二进制 `.xlsx` 字节完全相同作为唯一门禁；应解析 workbook 后断言业务结构、单元格值、顺序和关键样式语义。

## 7. Reference Sample 边界

`docs/reference/samples/b2eboc/` 包含真实语境 raw doc、字段目录与正式 ASSEMBLY/PARSE Standard/Template 导出。正式导出用于理解目标系统真实配置和人工对照：

- 不能作为 SchemaIR 的银行事实来源，也不能直接成为 StandardIR、TemplateIR 或 Generator 输入；
- 可以作为 b2e0061 目标配置和调用形态证据，但必须先进入规则包或人工确认的 expected fixture；
- Rule ID 只能由正式规则包定义；
- 不引入历史 database ID、parent ID、approval status 或 import contract；
- 与 raw doc/SchemaIR 冲突时，银行报文事实以人工确认的 SchemaIR 为准；
- 目标配置事实必须来自正式规则包和人工确认的 Final IR。

## 8. 当前执行边界

`configuration-rules/v1`、`configuration-rules/v2`、Standard/Template runtime、双方向 Final Standard/Template 与匹配 validation results 已冻结。P0-T3 当前继续 expected Configuration Workbook 和相关 assertions。

这些资产必须按 Final SchemaIR → Standard → RELEASED Template rules → Template → Workbook 顺序补齐。P0-T2 expected artifacts 不改写；SchemaIR v2 Final fixture 已落实两个方向的 `UTF-8` Human/银行 evidence，并按已确认 canonical content hash 冻结。ASSEMBLY Final Standard 为 36 fields、3 XML Keys、1 condition，hash 为 `sha256:9c77e0e92447907fa89d6ef705501dc0947d695998b80bb154476f696e9b982e`；PARSE Final Standard 为 19 fields、3 XML Keys、4 approved differences，hash 为 `sha256:33efa544460ac19f216734712c1e6ae2610321ea17eb750eff35493ecca9d57e`。规则包 v1/v2 均保持冻结；v2 仍使用正式导出观察到的 5 个 Function、String 类型、字符长度默认 `STANDARD_1`、MAPPING 和 Replacement 契约，不得把 Function 或 Mapping 子集扩张成全量 catalog。
