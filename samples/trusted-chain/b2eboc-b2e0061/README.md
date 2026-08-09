# b2e0061 P0-T3 Trusted-chain Fixture

该目录与 `samples/golden/b2eboc-b2e0061/` 的 P0-T2 Review Golden 分离。P0-T2 文件保持 byte-identical，用于证明历史审查边界；这里承载当前 machine contract 的已冻结 Final 链路。b2e0061 只是通用银行接口解析配置辅助产品的 P0 fixture，不定义 runtime 专用规则。

当前包含：

- `schemair-final.json`：`schemair/v2`、`b2eboc-b2e0061-schema@v1`，49 个 fields；
- `schemair-validation-result.json`：与 Final canonical content hash 精确匹配的 v2 结果；
- `schemair-review.md`：Human 事实结论与准确 hash 确认记录。
- `standards/assembly/v1/`：ASSEMBLY InterfaceStandardIR Draft 与匹配 validation result；
- `standards/parse/v1/`：PARSE InterfaceStandardIR Draft 与匹配 validation result；
- `standards/standard-review.md`：双方向 Standard 的准确候选 hash 与 Human Review 门禁。

Final hash 为 `sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162`。当前结果为 0 ERROR、0 WARNING、34 INFO、0 blocking issue、`finalEligible=true`；两方向 XML encoding 均保存 Human 与银行线下确认的 `UTF-8` evidence。

`deng` 已确认该准确 hash。任何 SchemaIR JSON 语义值变化都会使 Review 和 validation result 同时失效，必须重新复验和确认。

Standard Draft 当前均为 0 ERROR，但仍包含 lifecycle、email Regex 和 PARSE length difference 的 blocking Review 项，不能作为 Final Standard 进入 Template 阶段。
