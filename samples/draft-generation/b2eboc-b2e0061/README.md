# b2e0061 Draft generation fixture

本目录是 P0-T4 唯一受控的 deterministic provider case，contract 为 `draft-stub-case/v1`。运行时只按完整 request fingerprint 精确匹配，不扫描目录、不选择最新版本，也不回退到相近 case。

候选来源均为仓库内已有的 review artifacts：DocIR 来自 Review Golden；SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR 来自对应 Human Review gate 前的历史 Draft。它们用于证明 provider boundary、Validator 和持久化路径，不新增银行业务事实。

## Trust boundary

- 所有 JSON provider output 必须保持 `status=DRAFT`、`review.status=PENDING`。
- Validator 必须得到 0 ERROR、`finalEligible=false` 和 lifecycle blocking issues。
- `docir-draft.md` 不是 `docir-final.md`。Human 必须确认准确 content hash 后，才能在后续独立 commit 冻结 Final DocIR。
- 下游 fixture 已绑定当前受审 Final artifacts，不能用于绕过真实 workspace 的 Final 输入检查。
- `.gitattributes` 保留既有 Golden/Draft Markdown 的 CRLF bytes baseline，并将本目录 JSON 固定为 LF，确保 hash 不随 checkout 平台改变。
