# b2e0061 P0-T3 Trusted-chain Fixture

该目录与 `samples/golden/b2eboc-b2e0061/` 的 P0-T2 Review Golden 分离。P0-T2 文件保持 byte-identical，用于证明历史审查边界；这里承载当前 machine contract 的候选与后续 Final 链路。

当前包含：

- `schemair-draft.json`：`schemair/v2`、`b2eboc-b2e0061-schema@v1`，50 个 fields；
- `schemair-validation-result.json`：与 Draft canonical content hash 匹配的 v2 结果；
- `schemair-review.md`：21 个 blocking issue 的 Human Review 入口。

当前结果为 0 ERROR、38 WARNING、35 INFO、`finalEligible=false`。两方向 XML encoding 已保存 Human 与银行线下确认的 `UTF-8` evidence，但其余不确定事实和结构化 Condition 未全部确认，因此本目录不存在 `schemair-final.json`。

Human 完成 Review 后必须先形成包含最终 lifecycle/review metadata 的完整 Final candidate，再重新运行 Validator。不得复制或改名 Draft result 冒充 Final evidence。
