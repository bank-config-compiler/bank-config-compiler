# Bank Config Compiler

## Status

Draft.

## 项目定位

Bank Config Compiler 面向银企直连实施场景，将真实脱敏的银行接口文档整理为可 Review、可校验、可追溯的银行 XML 报文模型，并依次形成目标系统接口标准、接口模板和供配置人员使用的 Configuration Workbook。

LLM / Agent 只能生成 DocIR、SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR Draft；目标配置必须按“Final SchemaIR → Final Interface Standard → Final Interface Template”顺序经过 Validator 和人工 Review。Configuration Workbook 是配置规格与执行清单，不是 Import JSON、目标系统可导入文件或 IR 的反向输入。

当前产品范围只承诺 XML 银行报文。IR 使用 JSON 序列化不等于支持 JSON 银行报文。

## 当前能力

- CLI 可以从 `.md` / `.txt` 输入创建 workspace，并保存 `raw-doc.md`。
- CLI 提供 provider-neutral `generate-draft docir|schemair|standard|template`，并以 `validate-draft`、`approve-draft` 实现六份 Draft 共用的 Human Gate。生成阶段只发布 `DRAFT/PENDING`；可物化但含 ERROR 的 Draft 明确返回 `3`，结构或外部调用 hard failure 不发布 Draft并返回 `2`。只有具名 Human 对当前准确 hash 批准后才发布 Final。
- `openai-chat` 使用官方 OpenAI Python SDK 的最小流式 Chat Completions 子集与 JSON object response mode。DocIR 的 `draft-prompt/v13` 只让模型提出有序 XML semantic tree 和按代码 selector 匹配的语义详情；代码校验唯一根、父子结构、顺序和 detail coverage，再以 `docir-semantic-materializer/v1` 分配 index 并渲染固定 Markdown wire。SchemaIR、Standard、Template 的 `draft-prompt/v8` 同样只请求语义 candidate，稳定身份和可从 Final 上游唯一推导的结构字段由 materializer 锁定或重算。原始 response/candidate 仅保存在 Git-ignored attempt evidence 中，不是公开 IR 或下游输入。
- ADR-0015 已接受六类 Draft 的统一可信链：LLM 提出内部 semantic candidate，代码确定性物化身份、层级与固定 wire，可物化但校验失败的内容发布为明确 Invalid Draft，再由 Human 修改、重校验和批准准确 hash。P0-T5/P0-T6 所需 runtime 与离线回归已经实现；真实 DocIR attempt、逐层 Human approval 和双方向 Workbook 验收尚未执行，因此 Phase0-PoC 仍为 `In Progress`。
- CLI 公开 `raw` 与只读 `phase0` profile；`phase0` 要求调用者显式选择 direction、Standard/Template 版本和两个 RELEASED 规则包，只校验一条 Final trusted chain，不扫描或猜测最新版本。
- SchemaIR v2 Validator 已作为库实现：只接受 `schemair/v2` 与 XML 节点，严格校验 artifact identity/lifecycle、字段层级、方向级 encoding evidence、最小结构化银行条件和 Final eligibility，并以 canonical JSON SHA-256 将结果绑定到完整输入内容。
- InterfaceStandardIR Validator 已作为库实现：严格绑定 Final SchemaIR identity/hash、方向与 `RELEASED` 规则包，校验字段覆盖、路径/顺序、XML Keys、三态约束、银行条件、差异 Review、Rule References 和 Final eligibility，并生成 `interface-standard-validation-result/v1`。
- InterfaceTemplateIR Validator 已作为库实现：精确绑定 Final Standard 与 `RELEASED` v2 规则包，按方向严格校验 `standardTarget`/`parseTarget`、表达式 FIELD reference、collection context、processing、omission、Mapping/Replacement、Review 和 Final eligibility，并生成 `interface-template-validation-result/v1`。
- Configuration Workbook 核心运行时已作为库实现：重新运行并完整比对三份 validation result，分别校验 Standard/Template 的 RELEASED 规则版本，以显式 Standard Action 生成固定七个 sheet，并对公式注入、脱敏占位值、非法/超长单元格和非原子覆盖 fail closed。
- workspace 库支持受 workspace 边界保护的嵌套 JSON artifact，拒绝 BOM、非 UTF-8、重复属性、非 object 根节点、NaN/Infinity 和路径逃逸。
- DocIR / SchemaIR Review Golden sample 已落地；Golden 只用于开发 fixture、历史批准样例和确定性 trusted-chain regression，不进入真实 prompt，也不对真实 DocIR 候选执行自动语义判定。`configuration-rules/v1` 与 `configuration-rules/v2` 均已发布并冻结为接口无关、非全量的 BKL configuration rules 子集。v2 保持 v1 的 27/207/14/5/6 catalog，只修订方向相关 Standard projection：ASSEMBLY 显式镜像 target，PARSE 从精确绑定的 Final Standard 解析表达式/collection source。
- 规则包 loader/validator 已作为库实现：只使用 `yaml.safe_load`，校验 UTF-8 no BOM、严格结构、生命周期、唯一性、值域、redaction 和跨文件引用。调用方显式选择 v1 或 v2 后，默认加载接受相应 `RELEASED` 版本；不会自动选择最新版本或迁移已有 Final IR。

P0-T3 与 P0-T4 均为 `Done`。P0-T5 的公共 lineage、DocIR semantic materialization、validation/approval runtime 已完成离线实现，等待获准的真实 DocIR attempt 与 Human Gate；P0-T6 的下游五类 IR materializer/Human Gate 也已完成离线实现，但真实执行受 Final DocIR 阻塞。Phase0-PoC 当前仍为 `In Progress`。详细状态见 [Phase0-PoC 执行计划](docs/planning/00-phase0-poc-plan.md)。

## 快速开始

安装依赖并运行测试：

```powershell
uv run --group dev pytest
```

为运行下面的受控 b2e0061 fixture，导入其精确绑定的 raw doc 到 workspace：

```powershell
uv run bank-config-compiler ingest `
  --input samples/golden/b2eboc-b2e0061/raw-doc.md `
  --workspace workspace/phase0-smoke `
  --task-id phase0-smoke `
  --interface-code b2e0061 `
  --overwrite
```

`ingest` 原子保存 `raw-doc.md` 与 `phase0-task/v1` 的 `task.json`；manifest 绑定显式 task/interface、XML scope 和 raw bytes hash，不生成 DocIR、SchemaIR 或 Validator 结果。fixture 按 `raw-doc.md` 的准确 UTF-8 bytes hash 匹配；manifest 缺失、身份不符或源文件被改写时，后续 Draft 命令 fail closed。

使用受控 b2e0061 fixture 生成 DocIR Draft：

```powershell
uv run bank-config-compiler generate-draft docir `
  --workspace workspace/phase0-smoke `
  --provider fixture `
  --fixture-root samples/draft-generation/b2eboc-b2e0061
```

根工作集固定输出 `docir-draft.md`、`docir-review-notes.md` 和 `docir-generation-result.json`。fixture 使用完整 input hash 精确匹配；内容不匹配时命令 fail closed。生成结果不是 Final，必须先对准确 bytes hash 完成 Human Review，才能另行冻结 `docir-final.md`。受控 b2e0061 case 已保存 byte-identical 的获批 Final DocIR 与独立 APPROVED Review 记录；runtime 仍不会自动执行该 freeze。

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

配置优先级为：CLI 参数 > 已存在的进程环境变量 > 当前启动目录的 `.env` > timeout 默认值 600 秒。该 timeout 既是 SDK 逐次 I/O timeout，也是每个物理 subcall 的绝对墙钟期限；它不是整个多段 attempt 的共享预算。API key 不提供 CLI 参数，避免进入 shell history。`--chat-base-url` 只接受不含 credential、query 或 fragment 的 HTTPS URL；`--chat-model` 没有内置模型默认值。attempt ID 在整个 workspace 内不可复用，`--overwrite` 也只能替换根工作 Draft，不能覆盖历史 attempt。成功或失败 evidence 位于 `provider-attempts/{artifactKind}/{attemptId}/`；v2 摘要按顺序记录 subcall 的 segment、outcome、hash、模型/响应 ID、token usage、时间和 contract，不记录 API key、endpoint 原文或输入内容。原始 response/candidate 是被 Git 忽略的临时诊断，不属于 Human Review、Final 或 trusted chain。

下游命令分别是 `generate-draft schemair`、`generate-draft standard` 和 `generate-draft template`。SchemaIR 固定读取 `docir-final.md`，并要求显式 `--schema-id`、`--schema-version`；Standard 还要求 direction、`--standard-id`、Standard version 和 RELEASED 规则包；Template 要求匹配的 Final Standard、Template identity 和 RELEASED 规则包。模型不得生成这些稳定身份。完整参数以 `--help` 为准。可物化但 Validator 含 ERROR 的 JSON Draft 仍会连同结果发布，命令返回 `3`；reviewable 返回 `0`；未形成 Draft 的硬失败返回 `2`。

Human 修改当前工作 Draft 后，用同一组 selector 重新校验。例如 DocIR：

```powershell
uv run bank-config-compiler validate-draft docir `
  --workspace workspace/phase0-real
```

Validator 原子替换当前 validation result 与 review notes，不改 Draft，也不证明其语义忠实于 raw doc。非交互 approval 必须绑定准确 hash，不提供通用 `--yes`：

```powershell
uv run bank-config-compiler approve-draft docir `
  --workspace workspace/phase0-real `
  --reviewer deng `
  --review-note "已逐项对照 raw-doc 完成审查" `
  --expected-content-hash sha256:<64-hex>
```

交互模式省略 `--expected-content-hash`，CLI 会重新校验并展示 task/interface/artifact 身份、Validator 摘要、reviewer、note 和完整 hash，只接受明确确认。Standard/Template 的 validate/approve 还必须提供与其路径和依赖一致的 direction/version/template/rule-package selectors。

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
uv run python -m bank_config_compiler ingest --input samples/golden/b2eboc-b2e0061/raw-doc.md --workspace workspace/phase0-smoke --task-id phase0-smoke --interface-code b2e0061 --overwrite
```

## Workspace Artifacts

`raw` profile 要求 `task.json` 与 hash 匹配的 `raw-doc.md`。`phase0` profile 使用以下固定路径：

| Artifact | 格式 | 当前用途 |
|---|---|---|
| `task.json` | JSON | `phase0-task/v1` workspace 身份锚点，绑定 task/interface/XML scope/raw hash。 |
| `raw-doc.md` | Markdown / text | 由 `ingest` 从外部输入导入，作为后续生成命令的输入。 |
| `docir-draft.md` / `docir-review-notes.md` / `docir-generation-result.json` | Markdown / JSON | Human-editable DocIR、当前 Review 入口和不随 Human 编辑改写的初始 generation lineage。 |
| `provider-attempts/{artifactKind}/{attemptId}/` | JSON / text | 不可复用的真实调用 evidence、provider response/candidate、生成快照或失败 subcall 响应；物化 hard failure 也消费 attempt ID，但这些文件不是 trusted-chain artifact。 |
| `docir-validation-result.json` / `docir-approval-result.json` / `docir-final.md` | JSON / Markdown | 当前准确 Draft hash 的聚合结果、批准映射和 byte-identical Final；approval result 最后发布。 |
| `schemair-draft.json` / `schemair-review-notes.md` / `schemair-generation-result.json` | JSON / Markdown | SchemaIR 工作 Draft、当前 notes 和初始 generation lineage；Invalid Draft 不得进入下游。 |
| `schemair-validation-result.json` / `schemair-approval-result.json` / `schemair-final.json` | JSON | 当前 Draft 或 Final 的匹配结果、`approvedDraftHash → finalHash` 映射和 Final SchemaIR v2。 |
| `standards/{direction}/{standardVersion}/standard-draft.json` / `standard-review-notes.md` / `standard-generation-result.json` | JSON / Markdown | Standard 工作 Draft、当前 notes 和初始 lineage。 |
| `standards/{direction}/{standardVersion}/standard-validation-result.json` / `standard-approval-result.json` / `standard-final.json` | JSON | 当前 Draft 或 Final 的匹配结果、批准映射和显式方向/版本的 Final Standard。 |
| `templates/{direction}/{templateId}/{templateVersion}/template-draft.json` / `template-review-notes.md` / `template-generation-result.json` | JSON / Markdown | Template 工作 Draft、当前 notes 和初始 lineage。 |
| `templates/{direction}/{templateId}/{templateVersion}/template-validation-result.json` / `template-approval-result.json` / `template-final.json` | JSON | 当前 Draft 或 Final 的匹配结果、批准映射和显式选择的 Final Template。 |
| `templates/{direction}/{templateId}/{templateVersion}/configuration-workbook.xlsx` | XLSX | `generate-workbook` 的固定输出；不作为 IR 反向输入。 |

库级 JSON artifact I/O 可以安全读写 workspace 内的相对嵌套路径。P0-T3 Final SchemaIR、双方向 Final Standard/Template、机器结果、Review 记录和 Golden Workbook 位于 `samples/trusted-chain/b2eboc-b2e0061/`；它们是开发 fixture，不是 CLI workspace manifest。P0-T4 deterministic provider case 位于 `samples/draft-generation/b2eboc-b2e0061/`，只用于精确匹配的 PoC 验证。Draft result 与 Final result 使用同一固定路径，因此应在独立 Draft workspace 中运行；若显式覆盖 Final result，后续 trusted-chain check 会因 hash/lifecycle 不匹配而拒绝。所有文本与 JSON artifact 必须使用 UTF-8 with no BOM。

## 详细文档

正式产品契约、设计决策、阶段计划、规则资产和文档维护规范统一从 [文档中心](docs/README.md) 进入。
