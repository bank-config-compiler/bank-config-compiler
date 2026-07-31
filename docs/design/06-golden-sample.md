# Golden Sample 设计

## Status

Draft. DocIR / SchemaIR golden baseline exists; InterfaceStandardIR / InterfaceTemplateIR and Configuration Workbook golden assets remain blocked by the unavailable target-system catalog.

## 1. 目的

Golden sample 是 Prompt、四类 IR、三个 Validator、Workbook Generator 和验收判断的核心回归证据。它必须区分：

- 已由现有测试证明的 DocIR / SchemaIR 基线；
- catalog 提供后才能建立的目标配置和 Workbook 基线；
- 仅用于理解历史系统形态、不能作为正确答案的 reference JSON。

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

当前 `samples/golden/b2eboc-b2e0061/` 只证明 DocIR/SchemaIR Review baseline 与 SchemaIR Validator，不证明后续目标配置链路已经实现。

## 3. 规则来源边界

具体 Rule ID、FIELD、FUNCTION 和 MAPPING 标识只能来自已确认的 `configuration-rules/v1`。不得为满足测试覆盖创建占位业务标识，也不得从历史导出 JSON 反推 catalog。

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
- 当前 XML 流程拒绝 JSON-only List。

具体样例无法自然覆盖的类型或差异，应使用最小受控 fixture 补充，不能污染真实 golden 事实。

## 5. Interface Template 覆盖

Golden 至少覆盖：

- FIELD、FIXED_VALUE、EMPTY、FUNCTION、MAPPING 和递归 CONCATENATE；
- ASSEMBLY 与 PARSE 使用同一表达结构；
- 模板字段是标准字段子集；
- 缺失字段生成 MISSING_TEMPLATE_FIELD Warning；
- 未确认 omission 阻止 Final；
- 已确认 omission 带原因进入 Final，并继续出现在 Workbook Warnings；
- omission、EMPTY 与 Empty Handling 三者不同；
- 同一 standardFieldRef 重复时校验失败；
- 存在模板行时，每个标准 XML Key 有独立表达式；
- 未知或缺失 XML Key expression 校验失败；
- 标准 ID、version 或 content hash 不匹配时校验失败。

同字段多行 condition 是 future candidate，不属于当前 golden 成功路径。

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
- Standard Action 为 CREATE、REUSE 或 UPDATE；
- REUSE 标准行不进入执行完成率；
- Standard Sheet 包含完整标准字段；
- Template Sheet 只包含实际配置的标准字段子集；
- 已确认 omissions 只进入 Warnings，不制造空模板行；
- Value Expressions 能按 Expression Scope 还原字段值和 XML Key 表达式树；
- 递归 CONCATENATE、function 参数和 mapping 引用可结构化还原；
- SchemaIR/Standard 差异、规则冲突、不确定项和 Validator warning 不被静默忽略；
- 相同 Final 输入、三份校验结果、规则版本和 Standard Action 可重复生成相同结构化业务内容。

不以二进制 `.xlsx` 字节完全相同作为唯一门禁；应解析 workbook 后断言业务结构、单元格值、顺序和关键样式语义。

## 7. Reference Sample 边界

`docs/reference/samples/b2eboc/` 包含真实语境 raw doc 与历史 ASSEMBLY/PARSE 导出 JSON。历史 JSON 只用于理解目标系统概念和人工对照：

- 不能作为 SchemaIR、StandardIR 或 TemplateIR 的权威输入；
- 不能提供 Rule ID、catalog 标识或 expected 配置值；
- 不引入历史 database ID、parent ID、approval status 或 import contract；
- 与 raw doc/SchemaIR 冲突时，银行报文事实以人工确认的 SchemaIR 为准；
- 目标配置事实必须来自正式规则包和人工确认的 Final IR。

## 8. 当前 Blocker

目标系统 catalog 和完整规则资料尚未提供，因此当前不得创建：

- `configuration-rules/v1`；
- Final InterfaceStandardIR / InterfaceTemplateIR fixture；
- Standard / Template Validator expected result；
- expected Configuration Workbook 和相关 assertions。

资料确认后，先建立不可变规则包，再按 Standard → Template → Workbook 的顺序补齐 golden 资产。
