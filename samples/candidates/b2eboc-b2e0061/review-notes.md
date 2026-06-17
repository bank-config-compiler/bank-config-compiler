# b2e0061 IR Candidate Review Notes / 评审记录

Status: 仅用于 review，不是 golden sample，也不是 runtime contract。

## 已确认的 Candidate 决定

- SchemaIR 范围是 b2e0061 交易消息，不包含可复用的 BOCB2E `head` / 完整 envelope 模型。
- 当 `标记1-4` 层级清晰时，DocIR 填入推导出的完整 path。
- SchemaIR 包含 XML 容器节点，便于 workbook 缩进和父子关系 review。
- `sourceText` 使用字段行级 Markdown 证据。
- XML 文本值采用保守类型策略：账号、联行号、币种、枚举和流水号即使原文写数码/数字，也保留为 `string`。
- 保留 `confidence`，但主要 review 信号由 `uncertain`、`uncertainReason` 和 `reviewNote` 承载。

## 需要人工确认的问题

1. `version` is set to `120` from the BOCB2E protocol description, but raw examples also use `version="100"`. Confirm whether SchemaIR top-level `version` should mean protocol version, candidate default, or per-sample observed value.
2. Request payload `<b2e0061-rq>` says `不超过1000笔`; this candidate maps it to `occurs: "0..1000"` and `multiple: true`, with `uncertain=true`. Confirm whether minimum should be `1` for actual requests.
3. Response payload `<b2e0061-rs>` explicitly says `(0..1000)` and is mapped to `0..1000`.
4. `ceitinfo` is included because it appears in the request table, but the raw doc says it is automatically added by the front-end and enterprises do not upload it. Confirm whether it remains in SchemaIR with config guidance or is excluded from user-configurable workbook rows.
5. Several fields have different front-end and platform constraints. The candidate preserves both in `description` / `conditionText`; confirm whether validator should later prefer stricter, looser, or dual constraints.
6. `fribkn` platform text first says nullable 5 digits, while the front-end format allows nullable 5 or 12 digits. Candidate uses `0,5,12` in `length.raw` and `reviewNote`.
7. `fractn` and `toactn` are treated as required containers because their children contain required fields, but the raw doc does not explicitly state container requiredness.
8. `tobknm` is mapped as `required=false` with `conditionText` because it is required when `toibkn` is empty.
9. `trftime` raw text contains `HH1000（00000-230000）默认为000000`, which appears inconsistent with `HHMMSS`. Candidate keeps `dataType: "string"`, `format: "HHMMSS"`, and marks the row uncertain.
10. Response `rspmsg` is used from the b2e0061 table, while the common response example uses `<errmsg>OK</errmsg>`. Confirm whether `rspmsg` is the correct formal tag for SchemaIR.
11. Response fields `rspcod`, `rspmsg`, `insid`, and `obssid` have no dedicated length/format constraints in the b2e0061 response table. Candidate keeps length values null and marks lower confidence where needed.
12. Duplicate tag names such as `status`, `rspcod`, `rspmsg`, and `actacn` are resolved by full `path`; confirm this is enough for workbook reviewers.
13. Historical export JSON files were not used to add fields. Confirm whether P0-T2 expected SchemaIR may compare against those exports for review only.

## Candidate 质量检查

- 请求和响应方向均已覆盖。
- 每个 SchemaIR 字段都有行级 `sourceText`。
- 纯关闭 tag 行未进入 SchemaIR 字段。
- 未引入目标系统 import ID、parent ID、approval status 等历史导出专有字段。
- 条件以文本保留，P0-T1 不转换为正式 DSL。
