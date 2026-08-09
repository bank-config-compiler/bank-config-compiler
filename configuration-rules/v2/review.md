# Configuration Rules v2 Review Record

## Status

Released Review Record.

## Governance

- Maintainer：`deng`
- Business reviewer：`configuration-reviewer`
- Confirmation date：`2026-08-09`（Asia/Shanghai）。
- Release disposition：`RELEASED`；v2 内容冻结。

## Release Confirmation

- Candidate：`f2cf454b53541ccfa171f8f3ede59dae9e609583`
- Maintainer `deng`：确认该准确候选可以发布为 `configuration-rules/v2 RELEASED`。
- Business reviewer `configuration-reviewer`：确认该准确候选可以发布为 `configuration-rules/v2 RELEASED`。
- 发布转换只修改生命周期 metadata、发布记录、发布模式测试和状态文档，不增加或修改规则、FIELD、Function 或 Mapping 事实。

## Candidate Boundary

v2 完整继承 v1 已发布的 Rule ID、FIELD、Function、Mapping 与 processing-policy catalog；不新增或删除 catalog 事实。唯一语义修订是 `TPL.BIND.STANDARD_PROJECTION` 的方向相关投影规则：

- ASSEMBLY 在 `standardTarget` 中显式保存 Standard projection。
- PARSE 的 FIELD_REF 和 collection `standardSource` 只保存 `standardFieldRef`，projection 从精确绑定的 Final Standard 确定性解析。
- PARSE 复合表达式允许零个、一个或多个 Standard source，不声明顶层“主” Standard source。
- `bindingKind`、Value Expression `mode` 及其既有值域保持不变。

`configuration-rules/v1` 保持 byte-identical、`RELEASED` 且可继续验证历史 IR。现有 Final SchemaIR 和 Final InterfaceStandardIR 继续引用 v1；后续 InterfaceTemplateIR 可以独立引用 RELEASED v2，并继续精确绑定既有 Final Standard identity/version/content hash。

## Evidence and Decision

- 复合 PARSE 配置需要同时读取 `rspcod` 与 `rspmsg`，单一顶层 Standard source 无法表达真实数据流。
- `standardFieldRef` 是稳定外键，用于存在性、方向、path/type、影响分析和 Workbook join。
- PARSE projection 可由不可变 Final Standard 的 identity/version/content hash 确定性解析；重复保存会制造同一事实的漂移面。
- 用户确认保留现有 `bindingKind` 与 Value Expression `mode` 命名，不进行无关 wire rename。
- 用户确认不修改已发布 v1，采用 v2 重新双签。

## Unchanged v1 Facts

- v2 仍是接口无关、非全量的 BKL configuration rules 子集。
- FIELD catalog 仍为 207 个 ASSEMBLY 与 14 个 PARSE code。
- Function catalog 仍只包含正式导出观察到的 5 个 String function，不使用 `bkl.md` 的 function 内容。
- Mapping catalog 仍为 6 个样例规则；redaction、MAPPING 与 Replacement 语义不变。
- 字符长度默认值仍为 `STANDARD_1`；其他未确认默认值仍保持 `UNKNOWN`。
- 目标系统业务 Condition 仍不从具体接口导出推断。

## Release Checks

- [x] 四份 YAML 可由 `yaml.safe_load` 安全加载并通过现有严格 loader。
- [x] v2 目录名、package version、四文件 status、confirmation date 与 RELEASED lifecycle 一致。
- [x] Rule ID、FIELD、Function、Mapping 和 processing-policy catalog 与 v1 完全一致。
- [x] 只有方向相关 Standard projection 规则及其解释发生语义变化。
- [x] Standard 与 Template 可以引用不同规则版本的边界已记录。
- [x] README、ADR、Phase0 状态与候选行为一致。
- [x] Maintainer `deng` 对准确候选 `f2cf454b53541ccfa171f8f3ede59dae9e609583` 明确确认。
- [x] Business reviewer `configuration-reviewer` 对同一准确候选明确确认。

任何规则事实、catalog 或文档语义修改都会使已有确认失效，必须重新验证并重新双签。
