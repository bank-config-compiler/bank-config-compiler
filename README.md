# Bank Config Compiler

## Status

Draft.

## 项目定位

Bank Config Compiler 面向银企直连实施场景，将真实脱敏的银行接口文档整理为可 Review、可校验、可追溯的银行 XML 报文模型，并依次形成目标系统接口标准、接口模板和供配置人员使用的 Configuration Workbook。

LLM / Agent 只能生成 DocIR、SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR Draft；目标配置必须按“Final SchemaIR → Final Interface Standard → Final Interface Template”顺序经过 Validator 和人工 Review。Configuration Workbook 是配置规格与执行清单，不是 Import JSON、目标系统可导入文件或 IR 的反向输入。

当前产品范围只承诺 XML 银行报文。IR 使用 JSON 序列化不等于支持 JSON 银行报文。

## 当前能力

- CLI 可以从 `.md` / `.txt` 输入创建 workspace，并保存 `raw-doc.md`。
- CLI 提供 provider-neutral `generate-draft docir|schemair|standard|template`，支持调用者显式选择 deterministic `fixture` 或真实 `openai-chat` provider。四类运行路径只写 Draft/PENDING artifact 和 review notes；三个 JSON Draft 还会写入匹配的 Draft validation result，不会生成 Final 或自动通过 Human Review。
- `openai-chat` 使用官方 OpenAI Python SDK 的最小流式 Chat Completions 子集与 JSON object response mode：API key、base URL、model 和 timeout 可由启动目录的 `.env` 或进程环境提供，非敏感项可由 CLI 显式覆盖；attempt ID 始终按调用显式传入。SDK 自动重试固定关闭。provider 在内存中聚合 SSE 分块，仅在收到 `finish_reason=stop`、最终 usage 且完整 JSON 通过边界校验后发布；流中断不会发布部分 Draft。DocIR 模型直接返回不落盘的内部 `docir-extraction/v1` 根对象，严格校验后由代码确定性生成现有 Markdown wire 和 Human Review Notes；SchemaIR/Standard/Template 的模型 envelope 不变。成功调用写入 `draft-provider-call-result/v1`；DocIR 请求、流或 extraction 失败则默认写入失败摘要，并在已收到响应内容时保存完整或部分模型响应。两类摘要均不记录 secret、endpoint 原文或银行原文。
- P0-T5 仍要求真实完成六次 Draft 调用、每层独立 Human Review/Final validation 与双方向 Workbook 验证；adapter 与离线自动化已经实现。`docir-001` 因缺少 XML metadata 被本地门禁拒绝；`draft-prompt/v2` 生成的 `docir-002` 虽通过最小门禁，但 Human Review 发现其 DocIR wire、层级和来源范围不符合冻结契约。`docir-003/004` 的长非流式请求因 `APIConnectionError` 未发布输出；严格流式聚合使 `docir-005/006` 成功完成，但 v4 直出 Markdown candidate 仍未通过 Human Review。结构化 `docir-007` 被门禁拒绝时未保留具体原因；补齐诊断后，`docir-008` 明确缺少顶层 `artifact` 与 `reviewNotes`。v5 的 envelope 要求与裸 extraction 示例冲突，v6 虽统一为 `{artifact, reviewNotes}`，`docir-009` 遇到瞬时 `APIConnectionError`，`docir-010` 则在完整流后因模型只返回 `artifact`、缺少 `reviewNotes` 被拒绝。`draft-prompt/v7` 删除了冗余 DocIR 模型 envelope；`docir-011` 返回了可解析且正常结束的直接 extraction，但只包含到不完整的 `assembly`，缺少必需的 `parse`，因此被机械门禁拒绝并留下失败摘要和完整响应。当前仍无可冻结真实 DocIR，Phase0-PoC 尚未完成。
- CLI 公开 `raw` 与只读 `phase0` profile；`phase0` 要求调用者显式选择 direction、Standard/Template 版本和两个 RELEASED 规则包，只校验一条 Final trusted chain，不扫描或猜测最新版本。
- SchemaIR v2 Validator 已作为库实现：只接受 `schemair/v2` 与 XML 节点，严格校验 artifact identity/lifecycle、字段层级、方向级 encoding evidence、最小结构化银行条件和 Final eligibility，并以 canonical JSON SHA-256 将结果绑定到完整输入内容。
- InterfaceStandardIR Validator 已作为库实现：严格绑定 Final SchemaIR identity/hash、方向与 `RELEASED` 规则包，校验字段覆盖、路径/顺序、XML Keys、三态约束、银行条件、差异 Review、Rule References 和 Final eligibility，并生成 `interface-standard-validation-result/v1`。
- InterfaceTemplateIR Validator 已作为库实现：精确绑定 Final Standard 与 `RELEASED` v2 规则包，按方向严格校验 `standardTarget`/`parseTarget`、表达式 FIELD reference、collection context、processing、omission、Mapping/Replacement、Review 和 Final eligibility，并生成 `interface-template-validation-result/v1`。
- Configuration Workbook 核心运行时已作为库实现：重新运行并完整比对三份 validation result，分别校验 Standard/Template 的 RELEASED 规则版本，以显式 Standard Action 生成固定七个 sheet，并对公式注入、脱敏占位值、非法/超长单元格和非原子覆盖 fail closed。
- workspace 库支持受 workspace 边界保护的嵌套 JSON artifact，拒绝 BOM、非 UTF-8、重复属性、非 object 根节点、NaN/Infinity 和路径逃逸。
- DocIR / SchemaIR Review Golden sample 已落地；Golden 只用于开发 fixture、历史批准样例和确定性 trusted-chain regression，不进入真实 prompt，也不对真实 DocIR 候选执行自动语义判定。`configuration-rules/v1` 与 `configuration-rules/v2` 均已发布并冻结为接口无关、非全量的 BKL configuration rules 子集。v2 保持 v1 的 27/207/14/5/6 catalog，只修订方向相关 Standard projection：ASSEMBLY 显式镜像 target，PARSE 从精确绑定的 Final Standard 解析表达式/collection source。
- 规则包 loader/validator 已作为库实现：只使用 `yaml.safe_load`，校验 UTF-8 no BOM、严格结构、生命周期、唯一性、值域、redaction 和跨文件引用。调用方显式选择 v1 或 v2 后，默认加载接受相应 `RELEASED` 版本；不会自动选择最新版本或迁移已有 Final IR。

P0-T3 与 P0-T4 均为 `Done`：SchemaIR v2、InterfaceStandardIR、InterfaceTemplateIR、Configuration Workbook、显式 `phase0` workspace/CLI 与双方向 Golden regression 已闭合；provider-neutral runtime、六个受控 b2e0061 responses、四类 Draft CLI 和准确 hash `sha256:31d7fc002ccc2b840f401206f54665e36771f2bb5502d480566defdff9ac7585` 的 reviewed Final DocIR 已冻结。完整受控回归会依次生成六份 fixture Draft，显式装载已审核 Final fixtures 表达 Human Review，执行 ASSEMBLY/PARSE `check --profile phase0` 并生成两个 Workbook；结构化内容均与 Golden 一致，测试和 runtime 都不会自动把 Draft 提升为 Final。P0-T5 的 adapter/配置/离线测试候选已经实现，但六次真实 LLM 调用和后续 Human Review-to-Workbook 证据尚未完成，故 Phase0-PoC 当前为 `In Progress`。详细状态见 [Phase0-PoC 执行计划](docs/planning/00-phase0-poc-plan.md)。

## 快速开始

安装依赖并运行测试：

```powershell
uv run --group dev pytest
```

为运行下面的受控 b2e0061 fixture，导入其精确绑定的 raw doc 到 workspace：

```powershell
uv run bank-config-compiler ingest --input samples/golden/b2eboc-b2e0061/raw-doc.md --workspace workspace/phase0-smoke --overwrite
```

`ingest` 只把外部 `.md` / `.txt` 输入保存为 workspace 内的 `raw-doc.md`，不生成 DocIR、SchemaIR 或 Validator 结果。fixture 按 `raw-doc.md` 的准确 UTF-8 bytes hash 匹配；若改用其他文档，后续 fixture 命令会 fail closed。

使用受控 b2e0061 fixture 生成 DocIR Draft：

```powershell
uv run bank-config-compiler generate-draft docir `
  --workspace workspace/phase0-smoke `
  --provider fixture `
  --fixture-root samples/draft-generation/b2eboc-b2e0061
```

固定输出为 `docir-draft.md` 和 `docir-review-notes.md`。fixture 使用完整 input hash 精确匹配；内容不匹配时命令 fail closed。真实 provider 内部的结构化 extraction 不会成为额外 workspace 文件。生成结果不是 Final，必须先对准确 bytes hash 完成 Human Review，才能另行冻结 `docir-final.md`。受控 b2e0061 case 已保存 byte-identical 的获批 Final DocIR 与独立 APPROVED Review 记录；runtime 仍不会自动执行该 freeze。

使用真实 OpenAI-compatible Chat API 前，在仓库/worktree 根目录复制配置模板：

```powershell
Copy-Item .env.example .env
```

然后只在本机编辑 `.env`，填写获批的 API key、HTTPS endpoint、精确模型 ID 和 timeout。`.env` 已被 Git 忽略，`.env.example` 只包含占位值。CLI 只读取以下四个白名单变量，不加载 `.env` 中的其他设置：

```dotenv
BANK_CONFIG_COMPILER_LLM_API_KEY=<runtime-secret>
BANK_CONFIG_COMPILER_LLM_BASE_URL=https://approved-provider.example/v1
BANK_CONFIG_COMPILER_LLM_MODEL=approved-model-snapshot
BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS=600
```

在包含该 `.env` 的目录启动命令：

```powershell
uv run bank-config-compiler generate-draft docir `
  --workspace workspace/phase0-real `
  --provider openai-chat `
  --attempt-id docir-001
```

配置优先级为：CLI 参数 > 已存在的进程环境变量 > 当前启动目录的 `.env` > timeout 默认值 600 秒。API key 不提供 CLI 参数，避免进入 shell history。`--chat-base-url` 只接受不含 credential、query 或 fragment 的 HTTPS URL；`--chat-model` 没有内置模型默认值；`--attempt-id` 用于区分人工发起的独立尝试。运行时不自动重试，失败后必须由操作者以新的 attempt ID 明确重跑。开发验证期间，本项目 provider 自身产生的流、JSON 或 extraction 门禁错误会输出具体校验原因；任意 SDK/第三方异常仍只输出异常类型。DocIR 失败不发布部分 Draft，但默认保存 `docir-provider-failure-result.json`，若已收到模型内容还会保存 `docir-provider-failure-response.txt`，CLI 输出证据路径和响应 hash。成功后除 Draft/review notes 外，还会写入同级 `*-provider-call-result.json`。成功/失败摘要记录 source/artifact 或 response hash、模型/响应 ID、token usage、时间和 endpoint SHA-256 fingerprint，不记录 API key、endpoint 原文或输入内容；失败响应文件是被 Git 忽略的开发诊断，不属于 Human Review、Final 或 trusted chain。真实 Draft 仍必须按层完成 Human Review 和 Final validation。

下游命令分别是 `generate-draft schemair`、`generate-draft standard` 和 `generate-draft template`。SchemaIR 固定读取 `docir-final.md`；Standard 还必须显式提供 direction、Standard version 和 RELEASED 规则包；Template 还必须显式提供匹配的 Final Standard、Template identity 和 RELEASED 规则包。完整参数以 `--help` 为准。默认拒绝覆盖任一 Draft 输出或 DocIR 失败证据；`--overwrite` 会替换对应输出组。

检查只包含 raw doc 的 workspace：

```powershell
uv run bank-config-compiler check --workspace workspace/phase0-smoke --profile raw
```

`phase0a` 已移除且不提供兼容别名。检查一条已准备好的 ASSEMBLY trusted chain：

```powershell
uv run bank-config-compiler check `
  --workspace workspace/phase0-b2e0061 `
  --profile phase0 `
  --direction assembly `
  --standard-version v1 `
  --template-id b2e0061-assembly-common `
  --template-version v1 `
  --standard-rule-package configuration-rules/v1 `
  --template-rule-package configuration-rules/v2
```

生成配置工作簿时必须显式提供 Standard Action；默认拒绝覆盖：

```powershell
uv run bank-config-compiler generate-workbook `
  --workspace workspace/phase0-b2e0061 `
  --direction assembly `
  --standard-version v1 `
  --template-id b2e0061-assembly-common `
  --template-version v1 `
  --standard-rule-package configuration-rules/v1 `
  --template-rule-package configuration-rules/v2 `
  --standard-action CREATE
```

输出固定为 `templates/assembly/b2e0061-assembly-common/v1/configuration-workbook.xlsx`。只有显式传入 `--overwrite` 才会原子替换已有文件；`check --profile phase0` 不读取、生成或修改 Workbook。

等价模块入口：

```powershell
uv run python -m bank_config_compiler ingest --input samples/golden/b2eboc-b2e0061/raw-doc.md --workspace workspace/phase0-smoke --overwrite
```

## Workspace Artifacts

`raw` profile 只要求 `raw-doc.md`。`phase0` profile 使用以下固定路径：

| Artifact | 格式 | 当前用途 |
|---|---|---|
| `raw-doc.md` | Markdown / text | 由 `ingest` 从外部输入导入，作为后续生成命令的输入。 |
| `docir-draft.md` / `docir-review-notes.md` / `docir-provider-call-result.json` | Markdown / JSON | DocIR provider candidate、绑定准确 bytes hash 的 Review 入口，以及真实调用时生成的脱敏审计摘要。 |
| `docir-provider-failure-result.json` / `docir-provider-failure-response.txt` | JSON / text | 真实 DocIR 失败调用的诊断摘要，以及存在时的完整/部分模型响应；不是 Draft 或 trusted-chain artifact。 |
| `docir-final.md` | Markdown | 仅由独立 Human Review/freeze 批次创建；SchemaIR generator 的输入。 |
| `schemair-draft.json` / `schemair-review-notes.md` / `schemair-validation-result.json` / `schemair-provider-call-result.json` | JSON / Markdown | SchemaIR Draft 输出组；真实调用时另含脱敏审计摘要；validation result 必须 0 ERROR 且 `finalEligible=false`。 |
| `schemair-final.json` | JSON | Final SchemaIR v2。 |
| `schemair-validation-result.json` | JSON | 与完整 Final SchemaIR 内容精确匹配的结果。 |
| `standards/{direction}/{standardVersion}/standard-final.json` | JSON | 显式选择方向和版本的 Final Standard。 |
| `standards/{direction}/{standardVersion}/standard-draft.json` / `standard-review-notes.md` / `standard-validation-result.json` / `standard-provider-call-result.json` | JSON / Markdown | Standard Draft 输出组；真实调用时另含脱敏审计摘要。 |
| `standards/{direction}/{standardVersion}/standard-validation-result.json` | JSON | 与 Final Standard 精确匹配的结果。 |
| `templates/{direction}/{templateId}/{templateVersion}/template-final.json` | JSON | 显式选择的 Final Template。 |
| `templates/{direction}/{templateId}/{templateVersion}/template-draft.json` / `template-review-notes.md` / `template-validation-result.json` / `template-provider-call-result.json` | JSON / Markdown | Template Draft 输出组；真实调用时另含脱敏审计摘要。 |
| `templates/{direction}/{templateId}/{templateVersion}/template-validation-result.json` | JSON | 与 Final Template 精确匹配的结果。 |
| `templates/{direction}/{templateId}/{templateVersion}/configuration-workbook.xlsx` | XLSX | `generate-workbook` 的固定输出；不作为 IR 反向输入。 |

库级 JSON artifact I/O 可以安全读写 workspace 内的相对嵌套路径。P0-T3 Final SchemaIR、双方向 Final Standard/Template、机器结果、Review 记录和 Golden Workbook 位于 `samples/trusted-chain/b2eboc-b2e0061/`；它们是开发 fixture，不是 CLI workspace manifest。P0-T4 deterministic provider case 位于 `samples/draft-generation/b2eboc-b2e0061/`，只用于精确匹配的 PoC 验证。Draft result 与 Final result 使用同一固定路径，因此应在独立 Draft workspace 中运行；若显式覆盖 Final result，后续 trusted-chain check 会因 hash/lifecycle 不匹配而拒绝。所有文本与 JSON artifact 必须使用 UTF-8 with no BOM。

## 详细文档

正式产品契约、设计决策、阶段计划、规则资产和文档维护规范统一从 [文档中心](docs/README.md) 进入。
