# Configuration Rules v1

## Status

Draft.

## Scope

本版本是可追溯但非全量的 BKL configuration rules 子集，不绑定任何具体银行接口：

- XML Interface Standard 的字段、路径、顺序、XML Keys、类型和约束映射规则。
- ASSEMBLY 与 PARSE 的方向性 Template 绑定。
- 六种 Value Mode 的能力边界。
- Empty/Overlength、Row Limit 和六种字符长度 processing policy。
- `assemblyFields.txt` 与 `parseFields.txt` 提供的方向性 FIELD catalog。
- 正式 Template 导出中实际观察到的 function；参数和返回值的 String 契约来自业务确认。
- 预设 Mapping catalog 子集，以及 MAPPING/Replacement 的引用与执行契约。
- 银行文档明确条件约束的最小结构化表达。
- raw-doc/Final SchemaIR 到 Standard 的事实优先级、缺失约束语义与差异保留。
- Template Required/Length/Data Type 镜像、容器 coverage 和 `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM` 绑定。
- `FIXED_VALUE` 的 `LITERAL | SECURE_INPUT_REF` payload 边界。

本版本不覆盖：

- 全量目标系统字段、function、processing policy 或 Condition catalog。
- 目的系统业务 Condition 的推断、通用 AST 或运行时执行。
- JSON 银行报文、目标系统导入 JSON 或 API。

## Governance

| 属性 | 值 |
|---|---|
| Package | `configuration-rules` |
| Version | `v1` |
| Status | `DRAFT` |
| Maintainer | `deng` |
| Business reviewer | `configuration-reviewer` |
| Confirmation date | Pending reviewer sign-off |
| Target | BKL configuration rules subset |

`DRAFT` 表示内容已经可以作为实现输入，但尚不能被 Final IR 引用。只有 `review.md` 中的发布检查全部关闭、YAML 机器校验通过后，才能切换为 `RELEASED` 并冻结。

仓库内 loader/validator 已可使用 `require_released=False` 对本 Draft 候选执行安全加载、严格 schema/semantic 校验和引用闭合检查。默认加载继续拒绝本版本，直至 maintainer 与 business reviewer 完成发布确认。

## Files

- [`rules.yaml`](rules.yaml)：Rule ID、值域和能力状态。
- [`fields.yaml`](fields.yaml)：ASSEMBLY/PARSE FIELD catalog。
- [`functions.yaml`](functions.yaml)：正式导出中已观察到的 function 契约。
- [`mappings.yaml`](mappings.yaml)：预设 Mapping catalog 样例子集。
- [`rules.md`](rules.md)：Standard、Template、Condition、MAPPING 和 processing policy 解释。
- [`review.md`](review.md)：证据、确认、脱敏和未决项。

## Sources

| 来源 | 权威范围 |
|---|---|
| `docs/reference/samples/bkl.md` | 六种 Value Mode 和基本数据类型；不作为 v1 function catalog 来源。 |
| `docs/reference/samples/b2eboc/assemblyFields.txt` | ASSEMBLY 方向可引用的扁平系统请求字段名。 |
| `docs/reference/samples/b2eboc/parseFields.txt` | PARSE 方向固定输出对象字段名、path 和 datatype。 |
| `docs/reference/samples/mapping.txt` | 五个预设 Mapping rule 样例及其 source-target entries。 |
| `docs/reference/samples/b2eboc/others.json` | MAPPING Template 行、`mappingRuleName` 引用和一个已脱敏预设规则快照。 |
| `b2e0061-*-standard.json` | BKL Interface Standard 形态的正式导出证据。 |
| `b2e0061-*-template.json` | BKL Interface Template 形态、实际策略代码和 function 的正式导出证据。 |

正式导出用于理解并设计 IR/Workbook，不是项目目标输出，也不直接进入 Generator。`mappings.yaml` 只收录当前有证据的样例子集，不代表目标系统全量 catalog。银行事实与导出配置冲突时，两侧都必须保留并 Review，不允许静默覆盖。

来源路径可以包含提供证据的接口标识，但只承担 provenance 作用，不表示规则适用于该接口或将接口事实提升为 BKL 规则。银行结构、字段条件和方向级 XML encoding 属于对应 SchemaIR/Human Review，不进入本规则包。

## Reference Contract

IR 中的规则引用必须同时保存：

```yaml
rulePackageVersion: v1
ruleId: STD.FIELD.PARENT_PATH
```

仅保存 Rule ID、仅保存版本或引用不存在的标识均为无效引用。
