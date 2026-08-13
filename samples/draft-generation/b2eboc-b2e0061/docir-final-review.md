# b2e0061 Final DocIR Review

Status: `APPROVED`

该记录只批准受控 b2e0061 raw doc 的 DocIR 表达，不把候选中保留的冲突或不确定项转化为已确认银行业务事实，也不倒灌后续 SchemaIR、Standard 或 Template 结论。

## Candidate confirmation

- Reviewed commit：`6a936d5b0d1b515c09840ceb6d1881485cd23baf`
- Reviewer：`deng`
- Reviewed at：`2026-08-10T10:35:51+08:00`
- Approved Draft bytes hash：`sha256:6e155c590aa09633106bac5193b9823ace66070d17a20c179f75eb6b8fbfe9a0`
- Approved Draft size：`11963` bytes
- Candidate：`artifacts/docir-draft.md`
- Final：`docir-final.md`

`deng` 明确确认该 DocIR candidate 忠实反映受控 raw doc；同意候选中的冲突和不确定项继续显式保留，不将其视为已确认业务事实，并批准上述准确 bytes hash 冻结为 Final DocIR。

## Review conclusions

1. Final DocIR 必须与获批 Draft candidate 逐字节一致，不在 freeze 时修订内容或格式。
2. DocIR 使用通用九列 Fields contract；原两列校验内容按原顺序无损合并为 `校验点`；Object Required 固定为空（N/A），不从必填叶子反推容器出现性；`obssid` 按“通常可空、交易类型为 2 时非空”确认为 `C`。
3. `version=120` 与示例 `100`、`@locale` 与 observed `@lang`、请求重复节点出现次数、两组约束及 `rspmsg`/`errmsg` 等冲突继续作为原文事实和不确定性保留。
4. `ceitinfo` 是否可配置、目标系统采用哪组约束以及正式配置策略属于后续 SchemaIR/Standard/Template Review，不在 DocIR 中提前决定。
5. 本次批准确认的是 raw doc 表达的忠实性，不等于批准上述未决业务结论。

## Freeze boundary

- `docir-final.md` 是 `docir-draft.md` 的 byte-identical freeze；任一字节变化都会改变 hash 并使本 Review 失效。
- SchemaIR deterministic case 只接受上述获批 Final DocIR hash，不允许相近内容、换行变化或自动回退。
- Provider、Validator 或 workflow 仍不得自动创建新的 Final DocIR 或伪造 Human Review。
