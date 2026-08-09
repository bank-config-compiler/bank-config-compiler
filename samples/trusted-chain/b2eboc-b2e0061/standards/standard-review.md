# b2e0061 InterfaceStandardIR v1 Draft Review

Status: `PENDING`

该记录只评审通用 InterfaceStandardIR runtime 的 b2e0061 P0 fixture，不把接口字段、正则或默认长度硬编码为 runtime 规则。两个 Standard 均精确绑定已冻结的 Final SchemaIR v2 与 `configuration-rules/v1`。

## 准确候选

| Direction | Standard identity | Candidate content hash | Coverage | Machine result |
|---|---|---|---|---|
| ASSEMBLY | `b2e0061-assembly-standard@v1` | `sha256:34691505230a063e7b0c92798f6bd81b7fc41c5a988b0476195fcc23ec778af4` | 36 fields：29 scalar、7 container、3 XML Keys、1 condition | 0 ERROR、4 WARNING、4 blocking，`finalEligible=false` |
| PARSE | `b2e0061-parse-standard@v1` | `sha256:28dfde20c7190d5eccc93558d0726e7675656c4e6029b77f3018e76807fcacb2` | 19 fields：12 scalar、7 container、3 XML Keys、4 differences | 0 ERROR、6 WARNING、6 blocking，`finalEligible=false` |

Draft lifecycle 与顶层 `PENDING` Review 各产生一个预期 blocking Warning。未经准确 hash 确认，不得改为 `FINAL/APPROVED`。

## 已确定的投影

- 两方向完整覆盖 Final SchemaIR 中适用的 XML element；XML attribute 不生成字段行。
- `Root.bocb2e` 的 XML Keys 严格为 `@version`、`@security`、`@locale`；不包含 observed `@lang`，也不包含正式导出独有的 `vamflag`。
- 请求 `b2e0061-rq` 为 required `Node`，响应 `b2e0061-rs` 为 optional `Node`。
- `required`、length、data type 和不能稳定结构化的 `conditionText` 默认逐值保留 Final SchemaIR；正式导出的 database ID、状态和冲突配置不进入 IR。
- ASSEMBLY 保存已批准的 `transtype EQUALS "2" => obssid REQUIRED`，不把它压成基础 required。
- `digits`、`YYYYMMDD` 与 `HH0000` 分别投影为可审查 Regex；所有字段的 Illegal Characters 保持 `NO_CONSTRAINT`。
- PARSE 顶层和明细两组 `rspcod/rspmsg` 均为 optional String；Standard length 分别采用此前 Human 确认的 50/500，并以四条待候选确认的 SchemaIR-to-Standard difference 保存。

## Human 必须关闭

1. `email`：Final SchemaIR 只确认 email 格式语义与长度 3–80，尚未确认目标系统采用的精确 Regex。当前为 `regex.state=UNKNOWN`、`uncertain=true`。Human 需要明确选择 `NO_CONSTRAINT`，或提供准确 Regex `VALUE`。
2. 确认 PARSE 四条 `rspcod=50`、`rspmsg=500` length difference 的准确投影；值来自此前 Human 结论，但必须随本次候选 hash 一并确认。
3. 对两个完整候选 hash 分别确认后，才可填入实际 reviewer/timestamp、关闭 difference/field uncertainty 并重新运行 Validator。

## 冻结边界

- 本批只提交 DRAFT candidate、匹配 validation result 和 Review 入口，不创建 Final Standard。
- 任一 Standard JSON 语义变化都会改变对应 hash，并使 Review 与 validation result 失效。
- `ceitinfo` 是否在具体模板中由配置人员赋值属于后续 Template Review，不改变它作为银行 Standard element 的存在。
- b2e0061 只是通用银行接口解析配置辅助链路的 P0 fixture；runtime 只校验 machine contract、依赖与规则引用。
