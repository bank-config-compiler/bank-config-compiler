# Configuration Rules v1 Review Record

## Status

Draft Review Record.

## Governance

- Maintainer：`deng`
- Business reviewer：`configuration-reviewer`
- Confirmation date：待 maintainer 与 business reviewer 完成发布确认后填写。
- Release disposition：`DRAFT`；完成机器校验和下述 release checks 后才能改为 `RELEASED`。

## Confirmed Decisions

- `FILED` 是参考资料笔误，正式枚举为 `FIELD`。
- FIELD 是方向内全局唯一的扁平标识。
- ASSEMBLY 使用 `assemblyFields.txt`；PARSE 使用固定输出对象 `parseFields.txt`。
- PARSE 未配置字段默认不产生 omission 或 warning，也不推断其由代码赋值。
- raw-doc/Final SchemaIR 决定银行字段、path、出现次数和约束；正式导出只证明目标系统形态与已观察配置。
- raw-doc 在当前已确认范围内没有写约束时使用 `NO_CONSTRAINT`；证据冲突或无法判定时使用 `UNKNOWN`。
- Template field config 显式镜像 Standard Required、Length 和 Data Type，Validator 必须要求完全相等。
- Node/Object 不参加 ASSEMBLY omission coverage；PARSE 重复 Standard Node 可使用 `COLLECTION_ITEM` 绑定一个 Parse List 元素。
- `b2e0061-rq`、`b2e0061-rs` 依据 raw-doc `0..1000` 均为 Node；`b2e0061-rs` 的每次出现对应 `paymentLineList` 的一个元素。
- `FIXED_VALUE` payload 只允许 `LITERAL | SECURE_INPUT_REF`，后者不保存或展示真实值。
- 方向级 XML encoding 保存于 SchemaIR message 并经 Review 后展示在 Workbook Overview，不形成 Standard 字段。
- b2e0061 Standard 保留 `@security`、排除 `vamflag`；`@lang` 只作为 SchemaIR observed evidence 和差异 Warning。
- Function 输入、参数和返回值都是 String；参数只允许 FIELD reference 或 literal；仅 CONCATENATE children 允许递归表达式。
- Mapping 使用预设 catalog；Template 以全局唯一 `mappingRuleName` 引用一个规则，entries 不进入 IR。
- MAPPING 对完整 FIELD String 精确匹配，未匹配时报错。
- Replacement 在 Value Expression 后使用一个 `mappingRuleName` 替换片段；空 target 表示删除，未命中内容保留。
- 正式 Standard/Template 导出用于理解真实目标系统配置和设计 IR/Workbook，不是项目输出。
- 目的系统业务 Condition 本期只记录能力，不推断、不建模、不执行。
- 银行文档明确的简单条件可以形成 Standard 条件约束并进入 IR/Workbook。
- b2e0061 `obssid` 条件为 `transtype == "2"` 时必填。
- MAPPING 和 Replacement 纳入 P0 IR、Validator、Workbook 和专项 golden 覆盖。

## Evidence Matrix

| 事实 | 证据 | Review 结论 |
|---|---|---|
| 六种 Value Mode | `docs/reference/samples/bkl.md` | 接受；`FILED` 规范化为 `FIELD`。 |
| ASSEMBLY FIELD catalog | `assemblyFields.txt` | 接受；207 个名称，方向内唯一。 |
| PARSE FIELD catalog | `parseFields.txt` | 接受；14 个字段，包含 path/datatype；`instructionId`、`sourceCode` 的缺失 description 原样保留，不推断。 |
| Standard 字段与层级 | 两份 `*-standard.json` | 接受为 b2e0061 目标系统配置证据。 |
| Template 取值和 processing policy | 两份 `*-template.json` | 接受为 b2e0061 目标系统配置证据。 |
| MAPPING Template 行 | `others.json` | 接受 `FIELD_REF + mappingRuleName` 形态；公司名称 target 已脱敏。 |
| 预设 Mapping catalog | `mapping.txt`、`others.json` | 接受为 v1 样例子集；共 6 个全局唯一规则。 |
| Function String 类型 | 业务确认 | 输入、参数和输出统一为 String。 |
| Processing policy 完整值域 | 业务确认 | Empty、Overlength、Row Limit、STANDARD_1..6 进入 v1。 |
| 银行报文条件 | `b2e0061.md` | 银行明确条件可结构化；复杂说明保留原文。 |
| 银行事实投影与缺失约束 | `b2e0061.md`、业务确认 | raw-doc/Final SchemaIR 优先；已确认范围内未写即 `NO_CONSTRAINT`，冲突才为 `UNKNOWN`。 |
| Standard/Template 镜像 | 正式 Template 导出、业务确认 | Template 显式保存 Required/Length/Data Type，并与 Standard/raw-doc 完全一致。 |
| 重复容器与 Parse List | `b2e0061.md`、`parseFields.txt`、业务确认 | 两方向 payload 为 Node；每个 `b2e0061-rs` 对应 `paymentLineList` 一个元素。 |
| XML encoding 与 observed attribute | `b2e0061.md`、业务确认 | encoding 为 SchemaIR message metadata；raw-doc 同时包含 UTF-8 建议与 GB2312 示例，方向 Final 值留给 SchemaIR fixture Review；`@lang` 不进入 Final Standard。 |
| 安全固定值 | 已脱敏 Template 导出、业务确认 | 使用 `FIXED_VALUE + SECURE_INPUT_REF`，占位符不得进入 Final fixture。 |
| 目的系统业务 Condition | 正式 Template 导出 | 只证明能力存在；P0 不实现。 |

## Redaction

正式 ASSEMBLY Template 导出中的 `termid`、`trnid`、`custid`、`cusopr` 固定值属于客户/环境配置，参考样例使用 `<REDACTED>` 替换。字段名、Value Mode、结构标识和非敏感协议常量保留。

`others.json` 中的公司名称 Mapping target 同样使用 `<REDACTED>`；`mappings.yaml` 只保留相同占位符和结构证据。

这些占位值不能进入 fixture、规则包或 Workbook Generator 输入，也不能被解释为业务默认值。

## Observed but Not Generalized

- b2e0061 导出只实际使用 `BLANK`、`INTERCEPT`、`TRUNCATE_FRONT`、`STANDARD_1`、`STANDARD_4` 和 Row Limit `1`；完整允许值来自业务确认。
- 导出实际 function code 与 `bkl.md` 的通用 function 名称存在语义相近项，但未确认 alias 关系，因此分别保存，不合并标识。
- `mapping.txt` 只是目标系统预设 Mapping 的样例子集，不能据此声称覆盖全量 catalog。
- 导出存在多行业务 Condition，但 P0 不把这些配置提升为通用生成规则。
- 正式 Standard 导出的 `vamflag` 和容器 `Object` 形态与 raw-doc 不一致，仅作为差异证据，不进入 b2e0061 Final Standard 事实。

## Open Items

以下项目不阻止 P0 规则 loader、IR contract 和 Workbook 实现：

- b2e0061 两个方向的 Final `xmlEncoding` 尚需在 SchemaIR fixture Review 中从 UTF-8/GB2312 冲突证据中确认；规则包不提供默认值。
- Function 的语义 alias 仍未确认；相近函数代码继续作为不同标识。
- processing policy 的系统默认值仍未知；P0 必须显式配置，不使用隐式默认。
- `mappings.yaml` 是已确认样例子集，不是全量目标系统 catalog。

## Release Checks

- [x] 所有 YAML 可由 `yaml.safe_load` 安全加载。
- [x] Rule ID 唯一且所有引用闭合。
- [x] FIELD catalog 与来源文件一致且方向内唯一。
- [x] b2e0061 所需 function code 与参数位置可解析。
- [x] Function String 类型、Mapping/Replacement 和 processing policy 契约已确认。
- [x] Standard 镜像、结构绑定、容器 coverage、secure fixed value 和 encoding 边界已确认。
- [x] Standard/Template/Workbook 文档与本规则包无冲突。
- [x] 所有 P0 必需未知项已经关闭或被明确排除出 P0。
- [ ] Maintainer 与 business reviewer 确认发布。
