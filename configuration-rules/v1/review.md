# Configuration Rules v1 Review Record

## Status

Draft Review Record.

## Governance

- Maintainer：`deng`
- Business reviewer：`configuration-reviewer`
- Confirmation date：待 maintainer 与 business reviewer 对修订后的准确候选完成发布确认后填写。
- Release disposition：`DRAFT`；完成机器校验和下述 release checks 后才能改为 `RELEASED`。

## Confirmed Decisions

- v1 是可追溯但非全量的 BKL configuration rules 子集，不绑定任何具体银行接口。
- 来源路径可以包含提供证据的接口标识，但只承担 provenance 作用，不表示规则适用于该接口。
- `FILED` 是参考资料笔误，正式枚举为 `FIELD`。
- FIELD 是方向内全局唯一的扁平标识。
- ASSEMBLY 使用 `assemblyFields.txt`；PARSE 使用固定输出对象 `parseFields.txt`。
- PARSE 未配置字段默认不产生 omission 或 warning，也不推断其由代码赋值。
- raw-doc/Final SchemaIR 决定银行字段、path、出现次数、条件和 encoding；正式导出只证明目标系统形态与已观察配置。
- raw-doc 在人工确认范围内没有写约束时使用 `NO_CONSTRAINT`；证据冲突或无法判定时使用 `UNKNOWN`。
- Template field config 显式镜像 Standard Required、Length 和 Data Type，Validator 必须要求完全相等。
- Node/Object 不参加 ASSEMBLY omission coverage；PARSE 重复 Standard Node 可使用 `COLLECTION_ITEM` 绑定一个 Parse List 元素。
- `FIXED_VALUE` payload 只允许 `LITERAL | SECURE_INPUT_REF`，后者不保存或展示真实值。
- Function catalog 只使用正式 Template 导出中实际观察到的 `SystemDateFormat`、`SeqNoGenerate`、`TotalAmountWithDecimalPlace`、`DateFormat` 和 `SinglePaymentGetPaymentNo`；不使用 `bkl.md` 的 function 内容。
- Function 的 FIELD reference、literal、参数和返回值均为 String；该数据类型契约来自业务确认。
- Function 参数只允许 FIELD reference 或 literal；仅 CONCATENATE children 允许递归表达式。
- 字符长度 policy 默认值为 `STANDARD_1`；其他未确认 processing policy 默认值保持 `UNKNOWN`。
- Mapping 使用预设 catalog；Template 以全局唯一 `mappingRuleName` 引用一个规则，entries 不进入 IR。
- MAPPING 对完整 FIELD String 精确匹配，未匹配时报错。
- Replacement 在 Value Expression 后使用一个 `mappingRuleName` 替换片段；空 target 表示删除，未命中内容保留。
- 正式 Standard/Template 导出用于理解真实目标系统配置和设计 IR/Workbook，不是项目输出。
- 目标系统业务 Condition 只记录通用能力边界，不从接口导出反推通用条件。
- 银行文档明确的简单条件可以形成 Standard 条件约束；具体接口条件只属于对应 SchemaIR/Human Review。

## Evidence Matrix

| 事实 | 证据 | Review 结论 |
|---|---|---|
| 六种 Value Mode 与基本数据类型 | `docs/reference/samples/bkl.md` | 接受；`FILED` 规范化为 `FIELD`，但该文档不作为 v1 function catalog 来源。 |
| ASSEMBLY FIELD catalog | `assemblyFields.txt` | 接受；207 个名称，方向内唯一。 |
| PARSE FIELD catalog | `parseFields.txt` | 接受；14 个字段，包含 path/datatype；缺失 description 原样保留，不推断。 |
| Function code、名称和参数位置 | `docs/reference/samples/b2eboc/b2e0061-assembly-template.json`、`b2e0061-parse-template.json` | 接受 5 个正式导出中实际观察到的 function；路径中的接口标识只用于 provenance。 |
| Function String 类型 | 业务确认 | FIELD reference、literal、参数和输出统一为 String。 |
| Processing policy 值域和字符长度默认值 | 业务确认 | Empty、Overlength、Row Limit、`STANDARD_1..6` 进入 v1；字符长度默认 `STANDARD_1`。 |
| Standard/Template 形态 | 正式 Standard/Template 导出 | 接受为 BKL 形态和已观察配置证据，不提升其中的接口事实。 |
| MAPPING Template 行 | `others.json` | 接受 `FIELD_REF + mappingRuleName` 形态；敏感 target 已脱敏。 |
| 预设 Mapping catalog | `mapping.txt`、`others.json` | 接受为 v1 样例子集；共 6 个全局唯一规则。 |
| Standard/Template 镜像 | 正式 Template 导出、业务确认 | Template 显式保存 Required/Length/Data Type，并与 Standard/Final SchemaIR 完全一致。 |
| 安全固定值 | 已脱敏 Template 导出、业务确认 | 使用 `FIXED_VALUE + SECURE_INPUT_REF`，占位符不得进入 Final fixture。 |
| 目标系统 Condition 能力 | 正式 Template 导出 | 只证明通用能力存在，不保存或推断接口专属条件。 |

## Redaction

正式 Template 导出中的客户或环境固定值属于敏感配置，参考样例使用 `<REDACTED>` 替换。字段名、Value Mode、结构标识和非敏感协议常量保留。

`others.json` 中的公司名称 Mapping target 同样使用 `<REDACTED>`；`mappings.yaml` 只保留相同占位符和结构证据。

这些占位值不能进入 fixture、规则包或 Workbook Generator 输入，也不能被解释为业务默认值。

## Observed but Not Generalized

- 正式导出只观察到部分 processing policy code；完整允许值及字符长度默认值来自业务确认。
- 当前 Function catalog 是正式导出中实际观察到的子集，不代表 BKL 全量 function catalog，也不推断 alias。
- `mapping.txt` 只是目标系统预设 Mapping 的样例子集，不能据此声称覆盖全量 catalog。
- 正式导出存在多行业务 Condition，但不把接口配置提升为通用生成规则。

## Open Items

- `functions.yaml` 和 `mappings.yaml` 都是有证据的 BKL 子集，不是全量 catalog。
- Empty、Overlength、Row Limit 和 Replacement 的系统默认值仍未知，调用方必须显式配置或保持 `UNKNOWN`。
- Function alias 关系未确认；相近 function code 不能自动合并。

## Release Checks

- [x] 所有 YAML 可由 `yaml.safe_load` 安全加载。
- [x] Rule ID 唯一且所有引用闭合。
- [x] FIELD catalog 与来源文件一致且方向内唯一。
- [x] 正式导出中观察到的 5 个 function code 与参数位置可解析。
- [x] Function String 类型、Mapping/Replacement 和 processing policy 契约已确认。
- [x] 字符长度默认值为 `STANDARD_1`，其他未知默认值没有被补猜。
- [x] Standard 镜像、结构绑定、容器 coverage 和 secure fixed value 边界已确认。
- [x] v1 只包含接口无关的 BKL 规则事实；接口标识只存在于 provenance 路径。
- [x] Standard/Template/Workbook 文档与本规则包无冲突。
- [ ] Maintainer 与 business reviewer 对修订后的准确候选确认发布。
