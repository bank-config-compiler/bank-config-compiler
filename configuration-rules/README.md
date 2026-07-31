# Configuration Rules

## Status

Contract only. No rule package version has been published.

## Purpose

`configuration-rules/` 是 ConfigIR 的正式、版本化规则来源，保存目标系统字段取值与处理策略，以及字段、function、mapping catalog。

本目录不保存银行报文结构。银行原始结构和约束属于 SchemaIR。`docs/reference/` 中的候选材料和历史导出 JSON 也不是规则资产，不能被 ConfigIR 当作权威来源。

## Planned Structure

```text
configuration-rules/
├── README.md
└── v1/
    ├── README.md
    ├── rules.md
    ├── fields.md
    ├── functions.md
    └── mappings.md
```

当前只提交本维护契约。`v1/` 必须在真实目标系统资料整理并经业务负责人确认后创建；不得添加占位业务标识或猜测内容。

## Versioning

- 版本目录一旦发布不可原地覆盖。
- 任何会改变 ConfigIR 解释或生成结果的规则/catalog 变化必须发布新版本。
- 已发布目录中的拼写或说明修订也不得原地修改；需要变更时发布新版本并记录差异。
- ConfigIR、Validator result 和 Configuration Workbook 必须记录精确规则版本。
- 规则版本变化不会自动迁移已有 Final ConfigIR；必须显式评估影响、重新校验并人工 Review。

## Rule IDs

- 每条可被 ConfigIR 引用的规则必须具有稳定且唯一的 Rule ID。
- Rule ID 在已发布版本内不可重新分配、改变含义或删除后复用。
- ConfigIR 中的 `Rule Reference` 必须能解析到指定版本内的规则。
- 多条规则共同支撑一个配置决定时，必须保留全部引用。

Rule ID 的命名格式将在整理首个真实规则包时确定；当前不得预先制造格式或编号。

## Package Files

### `v1/README.md`

记录：

- 规则包状态、发布日期和维护人；
- 原始资料来源与脱敏说明；
- 业务负责人 Review 结论；
- 适用目标系统及明确边界；
- 与前后版本的关系。

### `v1/rules.md`

记录：

- `FIXED_VALUE`、`EMPTY`、`FIELD`、`FUNCTION`、`MAPPING`、`CONCATENATE` 的选择原则；
- configured required；
- empty handling；
- overlength handling；
- configured length、row limit、中文字符长度；
- 非法字符和有序替换；
- 其他可被 ConfigIR 引用的字段处理规则。

### `v1/fields.md`

保存目标系统业务字段的原始标识、显示名称和资料中明确给出的适用说明。

### `v1/functions.md`

保存目标系统 function 的原始标识、显示名称、参数和资料中明确给出的适用说明。

### `v1/mappings.md`

保存目标系统 mapping 的原始标识、显示名称和资料中明确给出的业务对应关系。

## Source Requirements

允许来源：

- 用户提供并确认的目标系统正式资料；
- 由业务负责人确认的补充说明；
- 能追溯到上述资料的整理结果。

禁止来源：

- `docs/reference/` 中未确认的候选草案；
- 历史导出 JSON 中反推的字段、function 或 mapping；
- LLM 常识或模型补全；
- 相近系统、相似名称或不完整线索；
- 为满足测试覆盖而创建的占位业务标识。

资料缺失或相互冲突时必须记录 blocker 并停止对应 ConfigIR 工作，不能默默选择一种解释。

## Publication Checklist

发布首个版本前必须满足：

- 所有规则和 catalog 项均可追溯到真实资料。
- Rule ID 唯一且引用有效。
- 原始标识和显示名称经业务 Review。
- 六种 Value Mode 与字段处理策略有明确适用规则。
- 缺失、冲突和不适用项被显式记录。
- 规则包由业务负责人确认。
- 内部链接、编码和唯一 ID 检查通过。

## Current Blocker

目标系统 catalog 尚未提供，因此 `v1/` 尚不存在。Phase0 的 ConfigIR contract、ConfigIR Validator、golden fixture 和 Configuration Workbook 实现保持 Blocked。
