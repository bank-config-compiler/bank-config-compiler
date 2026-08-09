# b2e0061 InterfaceStandardIR v1 Final Candidate Review

Status: `APPROVED`

该记录只评审通用 InterfaceStandardIR runtime 的 b2e0061 P0 fixture，不把接口字段、正则或默认长度硬编码为 runtime 规则。两个 Standard 均精确绑定已冻结的 Final SchemaIR v2 与 `configuration-rules/v1`。

## Final candidate 机器预检

| Direction | Standard identity | Candidate content hash | Coverage | Machine result |
|---|---|---|---|---|
| ASSEMBLY | `b2e0061-assembly-standard@v1` | `sha256:9c77e0e92447907fa89d6ef705501dc0947d695998b80bb154476f696e9b982e` | 36 fields：29 scalar、7 container、3 XML Keys、1 condition | 0 ERROR、0 WARNING、0 blocking，`finalEligible=true` |
| PARSE | `b2e0061-parse-standard@v1` | `sha256:33efa544460ac19f216734712c1e6ae2610321ea17eb750eff35493ecca9d57e` | 19 fields：12 scalar、7 container、3 XML Keys、4 differences | 0 ERROR、0 WARNING、0 blocking，`finalEligible=true` |

- Contract：`interface-standard/v1` / `interface-standard-validation-result/v1`
- Reviewer：`deng`
- Reviewed at：`2026-08-09T16:18:27+08:00`
- 两个 candidate 均为 `status=FINAL`、`review.status=APPROVED`。
- `deng` 于 `2026-08-09T16:26:36+08:00` 明确确认上表两个准确 canonical hash 可以冻结为 Final InterfaceStandardIR v1。

## Human Review conclusions

1. `email` 保留 Final SchemaIR 已确认的 email 格式语义和长度 3–80；目标 Standard 不配置未经来源确认的精确 Regex，因此使用 `regex.state=NO_CONSTRAINT`。
2. PARSE 顶层和明细两组 `rspcod/rspmsg` 均为 optional String；四条 SchemaIR-to-Standard difference 已确认，`rspcod` 使用 0–50，`rspmsg` 使用 0–500。
3. 两方向完整覆盖 Final SchemaIR 中适用的 XML element；XML attribute 只投影为所属 element 的 XML Keys。
4. `Root.bocb2e` 的 XML Keys 严格为 `@version`、`@security`、`@locale`；不包含 observed `@lang`，也不包含正式导出独有的 `vamflag`。
5. 请求 `b2e0061-rq` 为 required `Node`，响应 `b2e0061-rs` 为 optional `Node`。
6. ASSEMBLY 保存已批准的 `transtype EQUALS "2" => obssid REQUIRED`，不把它压成基础 required。

## Hash confirmation gate

- reviewer 已分别确认上表两个完整 candidate hash。
- 任一 Standard JSON 语义变化都会改变对应 hash，并使 Review 与 validation result 失效。
- 本文件已记录确认时间，并与两个 Final Standard 和匹配 validation result 一起提交。
- `ceitinfo` 是否在具体模板中由配置人员赋值属于后续 Template Review，不改变它作为银行 Standard element 的存在。
- b2e0061 只是通用银行接口解析配置辅助链路的 P0 fixture；runtime 只校验 machine contract、依赖与规则引用。
