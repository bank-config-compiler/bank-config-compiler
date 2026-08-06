# Configuration Rules

## Status

Active. `v1` is an interface-independent BKL rules subset in Draft and is not yet an immutable released package.

## Purpose

`configuration-rules/` 保存 InterfaceStandardIR 与 InterfaceTemplateIR 可引用的、版本化的目标系统规则事实。银行文档事实仍属于 SchemaIR；参考导出、字段清单和 `bkl.md` 只提供可追溯证据，不直接成为 Final IR 输入。

每个 IR 通过 `<rulePackageVersion, ruleId>` 引用规则。Rule ID 在不同版本间保持可读且不携带版本后缀，例如 `STD.FIELD.PARENT_PATH`；版本由 `rulePackageVersion` 单独表达。

## Version Lifecycle

规则包使用以下生命周期：

- `DRAFT`：允许补充和修正；只能用于设计、实现和 Draft fixture，不得支撑 Final IR。
- `RELEASED`：维护人和业务 reviewer 已确认，机器校验通过；目录内容冻结。
- `SUPERSEDED`：由新版本替代，但旧内容继续保留以验证历史 IR。

已发布版本不得原地修改。规则、字段或 function 发生语义变化时必须创建新版本；拼写修复若影响内容哈希也按新版本处理。

每个 Final Standard、Final Template、对应 Validator result 和 Workbook 必须记录实际使用的精确规则版本。Standard 与后续 Template 可以使用不同规则版本，但 Template 仍精确绑定 Standard artifact ID、version 和 content hash。规则升级不会自动迁移已有 Final artifact；必须显式评估影响、重新校验并人工 Review。

## Package Layout

每个版本至少包含：

- `README.md`：范围、来源、治理和使用边界。
- `rules.yaml`：Rule ID、值域和可机器读取的规则事实。
- `fields.yaml`：按方向区分的 FIELD catalog。
- `functions.yaml`：function 标识和已确认调用契约。
- `mappings.yaml`：全局唯一 `mappingRuleName`、String source-target entries 和来源。
- `rules.md`：规则解释、取舍和实现边界。
- `review.md`：来源、脱敏、确认记录和未决项。

目标系统具有预设 Mapping catalog。Template 的 MAPPING 与 Replacement 只保存 `mappingRuleName`，entries 由对应版本的 `mappings.yaml` 提供；不创建独立 `mappings.md`，使用语义统一记录在 `rules.yaml` 与 `rules.md`。

规则包同时定义 Template 对绑定 Standard 的 Required/Length/Data Type 镜像、Node/Object coverage、PARSE collection item binding，以及 `FIXED_VALUE` 的安全引用 payload。银行事实仍以 Final SchemaIR 为准；正式导出与 raw-doc 冲突时必须记录差异，不能反向覆盖银行事实。

## Governance

- Maintainer：`deng`
- Business reviewer：`configuration-reviewer`
- YAML loader 必须使用 `yaml.safe_load`，只接受标准 YAML 类型，再执行项目自己的结构、唯一性和引用校验。
- 参考资料缺失时必须保留 `UNKNOWN` 或维持功能未支持状态，禁止从相近名称、历史经验或模型常识补齐。

## Runtime Validation

`bank_config_compiler.configuration_rules.load_rule_package(package_dir)` 读取显式指定的版本目录。它固定加载四份 YAML，聚合返回可定位到 file/path 的结构、类型、唯一性、值域、redaction 与引用错误；不读取银行 raw-doc、正式导出或隐式默认路径。

默认调用只接受 `RELEASED` 规则包。发布前的 Draft 候选检查必须显式调用 `load_rule_package(package_dir, require_released=False)`；该参数只允许验证候选，不允许 Draft 支撑 Final IR。

## Source Requirements

允许来源：

- 用户提供并确认的目标系统正式资料或正式导出；
- 银行原始文档；
- 业务负责人确认的补充说明；
- 能追溯到上述材料的字段清单和整理结果。

禁止来源：

- 未确认的候选草案；
- LLM 常识或相近系统经验；
- 仅凭相似 function/field 名称推断 alias 或配置；
- 为满足测试覆盖创建的占位业务标识或默认行为。

资料缺失或相互冲突时，规则包必须保存来源差异、`UNKNOWN` 或 documented-only 状态；不得默默选择一种解释。

## Available Versions

- [`v1/`](v1/README.md)：接口无关、非全量的 BKL configuration rules 子集，当前为 Draft。
