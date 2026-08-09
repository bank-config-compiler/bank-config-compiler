# b2e0061 InterfaceTemplateIR v1 Final Review

Status: `APPROVED`

该记录只评审通用 InterfaceTemplateIR runtime 的 b2e0061 P0 fixture，不把接口字段、Function、Mapping 或 processing policy 硬编码为 runtime 规则。两个 Template 均精确绑定对应 Final InterfaceStandardIR v1 与 `configuration-rules/v2`。

## Candidate confirmation

- Reviewed commit：`39213672666b529f4ce669c57a9717fa61ccadc8`
- Reviewer：`deng`
- Reviewed at：`2026-08-09T18:56:17+08:00`
- ASSEMBLY Draft candidate：`sha256:356b83c1aff90d83d82fa3bbc14f7fe8277c34605a3d5edb4cb99abd71c49957`
- PARSE Draft candidate：`sha256:33cd4f7ae02701d6ab19cf46628398354590dba3d612f91e43b06f78d1356621`
- `deng` 明确确认两个准确候选可以冻结为 Final InterfaceTemplateIR v1，同时确认四条 ASSEMBLY omission，且受控 Mapping/Replacement fixture 不是 b2e0061 银行事实。

## Final machine verification

| Direction | Template identity | Final content hash | Coverage | Machine result |
|---|---|---|---|---|
| ASSEMBLY | `b2e0061-assembly-common@v1` | `sha256:b9966a449ddc29e08fa29c6cf7838273ce3cab91e00dbb38092767d21af2f561` | 26 configs：25 VALUE、1 STRUCTURE_ONLY、3 XML Key expressions、4 accepted omissions | 0 ERROR、4 non-blocking WARNING、0 blocking，`finalEligible=true` |
| PARSE | `b2e0061-parse-common@v1` | `sha256:16eb305b6ac3944f28cb1060b943fdfc2d471f69e6bf8ea52ce059c797fb22f9` | 8 configs：7 VALUE、1 COLLECTION_ITEM | 0 ERROR、0 WARNING、0 blocking，`finalEligible=true` |

Final hash 相对获批 Draft hash 的变化只来自 `status=FINAL`、APPROVED Review metadata 和四条 omission 的 ACCEPTED Review metadata；字段配置、表达式、processing policy、依赖引用和规则引用未改变。

## Human Review conclusions

1. ASSEMBLY 使用 `standardTarget` 与 `assemblyFieldRef`；PARSE 使用 `parseTarget`、表达式内 `standardFieldRef` 和 collection-only `standardSource`。
2. `xmlKeyExpressions` 只属于 ASSEMBLY；根节点只配置 `@version`、`@security`、`@locale`。
3. ASSEMBLY 的 `fractn.actnam`、`toactn.toname`、`toactn.tobknm` 和 `bocflag` 保持 omission；P0 不擅自选择正式导出的同目标业务 Condition 分支。
4. PARSE 的 `b2e0061-rs(Node) -> paymentLineList(List)` 使用 `COLLECTION_ITEM`；响应 `insid` 只用于定位对应请求，不增加配置一致性校验。
5. b2e0061 两份 Template 实际未使用 MAPPING 或 Replacement。`tests/fixtures/interface-template-v1/mapping-replacement.json` 只验证通用 contract，不是银行事实。
6. 任一 Final Template JSON 语义变化都会改变对应 canonical hash，并使本 Review 与 validation result 失效。
