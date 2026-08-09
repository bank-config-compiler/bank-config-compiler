# b2e0061 SchemaIR v2 Candidate Review

Status: `PENDING`

Candidate content hash: `sha256:9fda4beb7ff03f51fe2511cb2257845957d62ed41becc47b55ac133867b72d21`

该记录只汇总 Commit 3A 的 Human Review 门禁。事实结论必须写回完整 Final candidate，设置 `status=FINAL` 与 `review=APPROVED` 后重新运行 Validator；本文件不能单独把 Draft 提升为 Final。

## 机器结果

- Contract：`schemair/v2` / `schemair-validation-result/v2`
- Identity：`b2eboc-b2e0061-schema@v1`
- Coverage：13 个 envelope field、27 个 ASSEMBLY field、10 个 PARSE field，共 50 个 field
- Result：0 ERROR、38 WARNING、35 INFO、21 个 blocking issue，`finalEligible=false`
- 两个方向均保存已确认的 `xmlEncoding=UTF-8` 和 `HUMAN_BANK_CONFIRMATION` evidence；当前没有 encoding conflict

## Human 必须确认并关闭

1. `Root.bocb2e.@version`：协议候选 `120` 与示例 `100` 冲突，最终 `protocolVersion`、attribute 值及 evidence 如何确定。
2. `Root.bocb2e.@locale` / `Root.bocb2e.@lang`：是否保留 observed `@lang`，以及它与协议 `@locale` 的关系。
3. `Root.bocb2e.head.token`：请求与响应下的基础必填性。
4. 请求 `b2e0061-rq` 重复节点：`0..1000` 与 `required=true` 冲突，最小出现次数是否为 0 或 1。
5. 请求容器 `fractn`、`toactn`：基础必填性是否可由子字段推导。
6. `fractn.fribkn`：5 位与 12 位联行号约束如何作为银行事实保存。
7. `fractn.actacn`：前置机 1–35 与平台 1–20 的冲突。
8. `trnamt`：前置机 `(22,2)` 与平台 `(15,2)` 的冲突。
9. `trftime`：`HH0000（000000-230000）` 是否只允许整点。
10. `comacn`：前置机 0–35 与平台非空 1–20 的冲突。
11. 响应顶层 `status.rspcod` / `status.rspmsg`：缺失约束以及 `rspmsg` / `errmsg` 正式 tag。
12. 响应明细 `status.rspcod` / `status.rspmsg`：缺失长度与格式。
13. 响应 `insid`：缺失约束以及与请求 `insid` 的关联。
14. 响应 `obssid`：基础必填、长度和格式。
15. 结构化条件：是否确认 `transtype EQUALS "2" => obssid REQUIRED`；确认后必须把 condition review 改为 `APPROVED`。

`ceitinfo` 是否可由配置人员编辑，以及目标系统面对多组银行/平台约束时的采用方式，属于后续 Standard/Template Review，不写入 SchemaIR 事实层。

## Final 候选要求

- 所有 `uncertain=true`、`UNKNOWN` 或 blocking Warning 均已关闭。
- `review.reviewer` 与 `review.reviewedAt` 使用实际具名 reviewer 和带时区 RFC 3339 时间。
- 向 reviewer 展示修改后的完整 canonical content hash；任何 JSON 语义值变化都使确认失效。
- 通过 v2 Validator 后提交匹配的 validation result，不能复用本 Draft 的结果。
