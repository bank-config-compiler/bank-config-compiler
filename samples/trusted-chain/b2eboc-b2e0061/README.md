# b2e0061 P0-T3 Trusted-chain Fixture

该目录与 `samples/golden/b2eboc-b2e0061/` 的 P0-T2 Review Golden 分离。P0-T2 文件保持 byte-identical，用于证明历史审查边界；这里承载当前 machine contract 的已冻结 Final 链路。b2e0061 只是通用银行接口解析配置辅助产品的 P0 fixture，不定义 runtime 专用规则。

当前包含：

- `schemair-final.json`：`schemair/v2`、`b2eboc-b2e0061-schema@v1`，49 个 fields；
- `schemair-validation-result.json`：与 Final canonical content hash 精确匹配的 v2 结果；
- `schemair-review.md`：Human 事实结论与准确 hash 确认记录。
- `standards/assembly/v1/`：ASSEMBLY Final InterfaceStandardIR 与匹配 validation result；
- `standards/parse/v1/`：PARSE Final InterfaceStandardIR 与匹配 validation result；
- `standards/standard-review.md`：双方向 Standard 的准确 hash 确认与 Human Review 记录。
- `templates/assembly/v1/`：ASSEMBLY Final InterfaceTemplateIR 与匹配 validation result；
- `templates/parse/v1/`：PARSE Final InterfaceTemplateIR 与匹配 validation result；
- `templates/template-review.md`：双方向 Template 的 Draft candidate 确认、Final hash 和 Human Review 记录。
- `templates/{assembly,parse}/v1/configuration-workbook.xlsx`：固定任务上下文生成的 CREATE Golden Workbook；分别包含 36/19 条 Standard、26/8 条 Template、30/13 个 Expression node 和 38/15 条 Warning。

Final hash 为 `sha256:4729131ad59fd29899895b1149a476c1f95b71f304cb43bd17749985f19e7162`。当前结果为 0 ERROR、0 WARNING、34 INFO、0 blocking issue、`finalEligible=true`；两方向 XML encoding 均保存 Human 与银行线下确认的 `UTF-8` evidence。

`deng` 已确认该准确 hash。任何 SchemaIR JSON 语义值变化都会使 Review 和 validation result 同时失效，必须重新复验和确认。

两份 Final Standard 均为 0 ERROR、0 WARNING、0 blocking issue、`finalEligible=true`。ASSEMBLY hash 为 `sha256:9c77e0e92447907fa89d6ef705501dc0947d695998b80bb154476f696e9b982e`；PARSE hash 为 `sha256:33efa544460ac19f216734712c1e6ae2610321ea17eb750eff35493ecca9d57e`。`deng` 已确认两个准确 hash，可供后续 Template 精确绑定。

两份 Final Template 均精确绑定对应 Final Standard 与 `configuration-rules/v2`。ASSEMBLY hash 为 `sha256:b9966a449ddc29e08fa29c6cf7838273ce3cab91e00dbb38092767d21af2f561`，保留 4 个经接受的 omission 和 4 个非阻塞 Warning；PARSE hash 为 `sha256:16eb305b6ac3944f28cb1060b943fdfc2d471f69e6bf8ea52ce059c797fb22f9`，结果为 0 WARNING。两者均为 0 ERROR、0 blocking issue、`finalEligible=true`，并经 `deng` 对准确 Draft 候选确认后冻结。

两份 Golden Workbook 只由上述 Final chain、匹配 validation results、RELEASED v1/v2 和显式 `Standard Action=CREATE` 派生；不复制 Mapping entries/target，不包含宏、外链、业务公式、`<REDACTED>` 或安全输入真实值。它们是结构化 regression fixture，不是目标系统导入文件，也不作为 CLI workspace manifest。
