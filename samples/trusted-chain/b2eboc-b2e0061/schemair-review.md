# b2e0061 SchemaIR v2 Candidate Review

Status: `APPROVED`

Candidate content hash: `sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162`

该记录只评审作为 P0 trusted-chain fixture 的 b2e0061 SchemaIR，不把样例字段或约束固化为通用产品规则。SchemaIR runtime、Validator 与后续 Standard/Template contract 必须保持银行接口无关。

## Final candidate 机器预检

- Contract：`schemair/v2`
- Identity：`b2eboc-b2e0061-schema@v1`
- Reviewer：`deng`
- Reviewed at：`2026-08-09T12:48:17+08:00`
- Coverage：12 个 envelope field、27 个 ASSEMBLY field、10 个 PARSE field，共 49 个 field
- Preflight：0 ERROR、0 WARNING、34 INFO、0 blocking issue，`finalEligible=true`
- 两个方向均保存已确认的 `xmlEncoding=UTF-8` 和 `HUMAN_BANK_CONFIRMATION` evidence；当前没有 encoding conflict

`deng` 于 `2026-08-09T12:59:49+08:00` 明确确认上述准确 candidate hash 可以冻结为 b2e0061 Final SchemaIR v2。正式 `schemair-validation-result.json` 已由 v2 Validator 重新生成并与该 hash 匹配。

## Human Review 结论

1. `protocolVersion` 与 `Root.bocb2e.@version` 使用 `100`。
2. 只保留 `@locale` 字段；删除 observed `@lang` 字段。
3. 共享 envelope 中的 `token` 对请求和响应均必填。
4. 请求 `b2e0061-rq` 为 `1..1000`。
5. `fractn`、`toactn` 是非必填 Object 容器，本身不取值。
6. `fractn.fribkn` 可空，非空时为 5 位数字。
7. `fractn.actacn` 长度为 1–35。
8. `trnamt` 使用 `(22,2)`。
9. `trftime` 只允许 `HH0000`，范围 `000000–230000`。
10. `comacn` 可空，最大 35 位。
11. 响应顶层 `rspcod` / `rspmsg` 为非必填 String，正式 tag 为 `rspmsg`；银行 SchemaIR 不保存目标系统默认长度。
12. 响应明细 `rspcod` / `rspmsg` 同上。
13. 响应 `insid` 为必填 String、长度 1–32。请求值由本系统生成，银行在响应中原样返回，供系统关联原支付请求；该保证不形成配置校验。
14. 响应 `obssid` 非必填，非空时为 1–30 位纯数字 String。
15. 确认 `transtype EQUALS "2" => obssid REQUIRED`，结构化 Condition review 为 `APPROVED`。

`rspcod=50`、`rspmsg=500` 是后续 Standard 默认值，不回写为银行 SchemaIR 事实。`ceitinfo` 是否可由配置人员编辑以及目标系统采用哪些约束，也属于后续 Standard/Template Review。

## 冻结结果

- Final SchemaIR、validation result 与本 Review 记录必须在同一 commit 中提交。
- 任何 SchemaIR JSON 语义值变化都会改变 hash，并使本次确认和 validation result 同时失效。
- b2e0061 只是通用银行接口解析配置链路的 P0 fixture，不得将其字段或约束硬编码到 runtime。
