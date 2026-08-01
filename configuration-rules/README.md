# Configuration Rules

## Status

Contract only. No rule package version has been published.

## Purpose

`configuration-rules/` 是 InterfaceStandardIR 与 InterfaceTemplateIR 的正式、版本化规则来源：

- Standard 规则定义如何将 Final SchemaIR 映射为目标系统接口标准。
- Template 规则定义取值表达式、处理策略，以及 fields/functions/mappings catalog。

本目录不保存银行报文事实。银行原始结构和约束属于 SchemaIR。`docs/reference/` 中的候选材料和历史导出 JSON 不是权威规则资产，不能用于补猜 Standard 或 Template 配置。

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

当前只提交维护契约。`v1/` 必须在真实目标系统资料整理并经业务负责人确认后创建；不得添加占位业务标识或猜测内容。

## Versioning

- 版本目录一旦发布不可原地覆盖。
- 任何改变 Standard 或 Template 解释和生成结果的规则/catalog 变化必须发布新版本。
- 已发布目录中的拼写或说明修订也通过新版本记录，不原地修改。
- 每个 Final Standard、Final Template、Validator result 和 Workbook 必须记录实际使用的精确规则版本。
- Standard 与后续 Template 可以使用不同规则版本；Template 仍必须精确绑定 Standard artifact ID、version 和 content hash。
- 规则变化不会自动迁移已有 Final artifact；必须显式评估影响、重新校验并人工 Review。

## Rule IDs

- 每条可被 StandardIR 或 TemplateIR 引用的规则必须具有稳定唯一 Rule ID。
- Rule ID 在已发布版本内不可重新分配、改变含义或删除后复用。
- IR 中的 Rule Reference 必须能解析到该 artifact 指定的规则版本。
- 多条规则共同支撑一个决定时，必须保留全部引用。

Rule ID 命名格式在整理首个真实规则包时确定，当前不得预先制造格式或编号。

## Package Files

### `v1/README.md`

记录规则包状态、发布日期、维护人、原始资料来源、脱敏说明、业务 Review 结论、适用目标系统和版本关系。

### `v1/rules.md`

至少记录两组规则。

Interface Standard：

- parentPath/fullPath 形成方式；
- sibling sequence；
- String/Boolean/Date/Number/Node/Object 映射；
- XML Keys 表达；
- required、length、illegal characters 和 regex；
- VALUE、NO_CONSTRAINT、UNKNOWN 的使用与 Review；
- SchemaIR/Standard 差异处理。

Interface Template：

- FIXED_VALUE、EMPTY、FIELD、FUNCTION、MAPPING、CONCATENATE 的选择原则；
- String/Boolean/Date/Number 标量字段值和 XML Key Value Expressions；
- Node/Object 无字段值表达式，以及容器处理策略和 XML Key 表达式的适用边界；
- empty handling、overlength handling、row limit、中文字符长度和有序替换；
- 模板字段 omission 与 EMPTY 的区别；
- 其他可被 TemplateIR 引用的处理规则。

### `v1/fields.md`

保存目标系统业务字段的原始标识、显示名称和资料中明确给出的适用说明，供 Template FIELD 引用。

### `v1/functions.md`

保存目标系统 function 的原始标识、显示名称、参数和适用说明，供 Template FUNCTION 引用。

### `v1/mappings.md`

保存目标系统 mapping 的原始标识、显示名称和业务对应关系，供 Template MAPPING 引用。

## Source Requirements

允许来源：

- 用户提供并确认的目标系统正式资料；
- 业务负责人确认的补充说明；
- 能追溯到上述资料的整理结果。

禁止来源：

- `docs/reference/` 中未确认的候选草案；
- 历史导出 JSON 中反推的字段、function、mapping 或配置规则；
- LLM 常识或模型补全；
- 相近系统、相似名称或不完整线索；
- 为满足测试覆盖而创建的占位业务标识。

资料缺失或相互冲突时必须记录 blocker 并停止对应 Standard/Template 工作，不能默默选择一种解释。

## Publication Checklist

发布首个版本前必须满足：

- 所有规则和 catalog 项均可追溯到真实资料。
- Standard 与 Template 规则职责边界明确。
- Rule ID 唯一且引用有效。
- 原始标识和显示名称经业务 Review。
- 六种 Value Mode 与处理策略有明确适用规则。
- 缺失、冲突和不适用项被显式记录。
- 规则包由业务负责人确认。
- 内部链接、编码和唯一 ID 检查通过。

## Current Blocker

目标系统 catalog 和完整规则资料尚未提供，因此 `v1/` 尚不存在。Phase0 的 InterfaceStandardIR / InterfaceTemplateIR wire contract、Validator、golden fixture 和 Configuration Workbook 实现保持 Blocked。
