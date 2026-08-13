# b2e0061 Draft generation fixture

本目录是 P0-T4 唯一受控的 deterministic provider case，contract 为 `draft-stub-case/v1`。运行时只按完整 request fingerprint 精确匹配，不扫描目录、不选择最新版本，也不回退到相近 case。

候选来源均为仓库内已有的 review artifacts：DocIR 来自 Review Golden；SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR 来自对应 Human Review gate 前的历史 Draft。fixture manifest 显式绑定 task/interface、Schema identity 和 Standard identity；运行时仍会经过当前 materializer、Validator 与 lineage publication。它们用于证明 provider boundary、确定性投影和持久化路径，不新增银行业务事实。

`deng` 已批准九列 DocIR candidate hash `sha256:6e155c590aa09633106bac5193b9823ace66070d17a20c179f75eb6b8fbfe9a0`。`docir-final.md` 是 candidate 的逐字节冻结副本，`docir-final-review.md` 记录具名批准、时间、格式迁移、Object Required=N/A、保留不确定性的结论和失效边界。

## Trust boundary

- 所有 JSON provider output 必须保持 `status=DRAFT`、`review.status=PENDING`。
- Validator 必须得到 0 ERROR、`finalEligible=false` 和 lifecycle blocking issues。
- `artifacts/docir-draft.md` 始终是 provider output；只有当前获批 hash 的 byte-identical `docir-final.md` 是该 case 的 Final DocIR。`generate-draft` 不执行 promotion；只有显式 `approve-draft` 在匹配 validation 与 hash 后才能发布 workspace Final。
- 下游 fixture 已绑定当前受审 Final artifacts，不能用于绕过真实 workspace 的 Final 输入检查。
- `.gitattributes` 保留既有 Golden/Draft Markdown 的 CRLF bytes baseline，并将本目录 JSON 固定为 LF，确保 hash 不随 checkout 平台改变。

完整受控回归会生成本 case 的六份 Draft，再显式装载已审核 Final fixtures，分别完成 ASSEMBLY/PARSE `phase0` check、Workbook 生成和结构化 Golden 对比。缺少任一所需 Final 时下游调用 fail closed；测试不通过复制本次 Draft 来模拟 Human Review。
