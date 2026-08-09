# Configuration Rules v2

## Status

Released.

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
- ASSEMBLY 显式 Standard projection、PARSE 从精确绑定的 Final Standard 派生 projection、容器 coverage 和 `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM` 绑定。
- `FIXED_VALUE` 的 `LITERAL | SECURE_INPUT_REF` payload 边界。

本版本不覆盖：

- 全量目标系统字段、function、processing policy 或 Condition catalog。
- 目的系统业务 Condition 的推断、通用 AST 或运行时执行。
- JSON 银行报文、目标系统导入 JSON 或 API。

## Governance

| 属性 | 值 |
|---|---|
| Package | `configuration-rules` |
| Version | `v2` |
| Status | `RELEASED` |
| Maintainer | `deng` |
| Business reviewer | `configuration-reviewer` |
| Confirmation date | `2026-08-09` |
| Target | BKL configuration rules subset |

本版本从不可变 v1 创建，只修订 `TPL.BIND.STANDARD_PROJECTION` 的方向相关语义，不修改已发布 v1。`review.md` 已记录两个角色对准确候选 `f2cf454b53541ccfa171f8f3ede59dae9e609583` 的明确确认；本目录自发布起冻结。

仓库内 loader/validator 默认接受本 `RELEASED` 版本，并执行安全加载、严格 schema/semantic 校验和引用闭合检查。历史 v1 继续可独立加载；调用方必须显式选择规则版本，不自动迁移已有 Final IR。

v1 的 Rule ID、FIELD、Function、Mapping 与 processing-policy catalog 在 v2 中保持不变。ASSEMBLY 使用 `standardTarget.standardProjection` 显式镜像 Final Standard；PARSE 的 FIELD_REF 或 collection `standardSource` 保存 `standardFieldRef`，Validator 根据 Template 精确绑定的 Final Standard identity/version/content hash 派生 required、length 和 dataType。PARSE 不保存顶层单一 Standard source，也不重复保存 projection。

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
| `docs/reference/samples/bkl.md` | 六种 Value Mode 和基本数据类型；不作为 v2 function catalog 来源。 |
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
rulePackageVersion: v2
ruleId: STD.FIELD.PARENT_PATH
```

仅保存 Rule ID、仅保存版本或引用不存在的标识均为无效引用。
