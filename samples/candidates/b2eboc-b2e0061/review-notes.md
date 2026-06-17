# b2e0061 IR Candidate Review Notes / 人工评审说明

Status: 仅用于 human review，不是 golden sample，也不是 runtime contract。

Review input: 本文件吸收 `human-review-result.md` 中的人工评审结论；`human-review-result.md` 保留原文，不在本轮重写。

## 必须确认

1. `Root.bocb2e.@version` 的配置口径。SchemaIR 顶层 `version` 暂保留推测值 `120`；但 raw-doc 示例出现 `version="100"`，因此 envelope 字段将 `uncertain=true`、`evidence.kind=DERIVED`。
2. `Root.bocb2e.@locale` 与观察到的 `Root.bocb2e.@lang` 是否需要同时支持。协议说明使用 `locale`，示例使用 `lang="chs"`。
3. 请求报文 `<b2e0061-rq>` 原文只写“不超过1000笔”。当前 candidate 保留 `occurs: "0..1000"`、`multiple: true`，同时将 `required=true` 标为待确认；需要确认请求最小出现次数是否应为 `1`。
4. `ceitinfo` 是否进入配置人员可编辑范围。字段存在于请求表，但原文说明“该标签由前置机自动添加，企业无需上送”。
5. 多个字段同时存在前置机约束和接口平台约束，后续 Validator 应采用更严格约束、更宽松约束，还是同时展示两组约束，仍需明确。
6. 响应状态字段正式 tag。b2e0061 响应表使用 `rspmsg`，通用示例出现 `errmsg`；当前 SchemaIR 使用 `rspmsg` 并保留 review note。

## 建议关注

1. `fractn`、`toactn`、响应内 `status` 等容器字段的必填性来自子字段或消息结构推导，不是字段行直接给出的显式约束。
2. `fribkn`、付款账号 `actacn`、`trnamt`、`comacn` 等字段存在前置机和平台约束不一致，已降低 confidence 或标记 `uncertain=true`。
3. `trftime` 已按用户修正后的 raw-doc 使用 `HH0000（000000-230000）`，但仍需要确认是否只允许整点时间。
4. `status`、`rspcod`、`rspmsg`、`actacn` 等重复 tag name 需要依赖完整 `path` 区分；Workbook review 时应优先展示 path。
5. Workbook 不新增独立 `ENVELOPE` sheet；`ASSEMBLY` 与 `PARSE` sheet 都会先展示 envelope/head 字段，再展示对应方向交易字段。这种重复是有意设计，便于单方向 review。

## 低风险说明

1. 本 candidate 使用 `samples/candidates/b2eboc-b2e0061/raw-doc.md` 作为受控样例 source。若源文档本身错误，应先修正 raw-doc，再进入 DocIR / SchemaIR 转换。
2. DocIR 允许写推导出的完整 path，但不确定项必须通过 review 信息标记；SchemaIR 字段通过 `confidence`、`uncertain` 和 `evidence` 表达推导风险。
3. XML 文本值采用保守类型策略：账号、联行号、币种、枚举和流水号即使原文写数码/数字，也优先保留为 `string`。
4. 条件规则仍以文本保留，P0-T2 不把条件转换为正式 DSL。
5. 每次 DocIR / SchemaIR draft 生成都应产出类似本文件的 `review-notes.md`，用于 human review，而不是只给机器可读字段。

## 历史导出 JSON 对照

1. 历史导出 JSON 只能作为人工 review 对照材料，用来发现遗漏、命名差异或配置展示问题。
2. 历史导出 JSON 不参与字段补全，不进入 expected SchemaIR，不作为回归输入，也不作为字段 `sourceText` / `evidence` 来源。
3. 如果未来 review 中发现历史导出 JSON 与 raw-doc 冲突，应回到 raw-doc 或受控样例 source 修正，不在 SchemaIR 中静默吸收历史导出字段。
