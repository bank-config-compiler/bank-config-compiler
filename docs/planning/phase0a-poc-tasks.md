# Phase0a-PoC TASK 计划

## Status

Archived bootstrap plan.

## 1. 目标与边界

Phase0a-PoC 是 `docs/phases/phase0-poc.md` 中完整 Phase0-PoC 的 bootstrap 子阶段。当前已完成范围只包括 Python CLI 骨架、`ingest`、workspace artifact 协议和 `check`。

早期 Phase0a 草案曾计划覆盖以下链路：

```text
Raw Docs
→ DocIR Draft
→ Final DocIR fixture
→ SchemaIR Draft
→ SchemaIR Validator
→ Final SchemaIR fixture
→ golden regression
```

最新结论是：Phase0a 不再继续承载完整 Phase0 的后续实现。完整 Phase0 的当前执行计划见 `docs/planning/phase0-poc-plan.md`。

Phase0a 通过不等于完整 Phase0-PoC 通过。完整 Phase0 仍必须覆盖 `Final SchemaIR -> SchemaIR Validator -> Schema Workbook -> golden regression`。

## 2. Phase0a 进度总览

| TASK | 状态 | 依赖 | 阻塞点 | 说明 |
|---|---|---|---|---|
| TASK 0：Phase0a planning 文档 | Done | 无 | 无 | 当前文档记录阶段边界、任务拆分和验证路径。 |
| TASK 1：Python 项目与 CLI 骨架 | Done | TASK 0 | 无 | 已建立最小可运行 CLI 和 raw doc 保存能力。 |
| TASK 2：Workspace 产物协议 | Done | TASK 1 | 无 | 已定义 Phase0a 文件产物命名和读写校验规则。 |
| TASK 3：DocIR Draft Generator 接口、stub 与 OpenAI-compatible adapter | Superseded | TASK 1、TASK 2 | IR 未确认 | 不再按旧顺序直接实施；trusted chain 之前需先完成 `b2e0061` IR candidate / review。 |
| TASK 4：SchemaIR Draft Generator 接口、stub 与 OpenAI-compatible adapter | Superseded | TASK 1、TASK 2、TASK 3 | IR 未确认 | 不再按旧顺序直接实施；draft generator 应在 trusted chain 后接入。 |
| TASK 5：SchemaIR Validator | Superseded | TASK 2、TASK 4 | IR 未确认 | Validator 依赖 confirmed SchemaIR，不应基于 draft IR 直接实现。 |
| TASK 6：Phase0a Stub Golden Regression | Superseded | TASK 1、TASK 2、TASK 3、TASK 4、TASK 5 | IR 未确认 | golden regression 应在 confirmed IR 和 workbook assertions 后建立。 |
| TASK 7：正式脱敏银行样例接入 | Superseded | TASK 6 | expected IR 未确认 | 改为先产出 `b2e0061` IR candidate 并人工 review。 |
| TASK 8：README 与 docs-sync | Superseded | TASK 1 到 TASK 7 的实际实现结果 | 计划已调整 | 文档同步纳入完整 Phase0 当前计划。 |

状态说明：

- `Not Started`：尚未开始。
- `In Progress`：正在执行。
- `Blocked`：存在明确外部输入或确认依赖。
- `Done`：完成标志和验证均已满足。
- `Superseded`：旧计划项已被完整 Phase0 当前执行计划替代，不作为下一步直接实施边界。

## 3. Out of Scope

- UI。
- `Workbook Generator`。
- `Schema Workbook`。
- 真实生产库导入。
- `.docx`、PDF、OCR、bbox 和原文区域高亮。
- 多用户协作、权限、审批流。
- RAG、多 Agent、自动微调、自动规则学习。
- 复杂 condition DSL。
- 多银行、多报文标准泛化。

## 4. TASK 列表

以下 TASK 0-2 是已完成的 Phase0a bootstrap 范围。TASK 3-8 保留为历史草案，不再作为可直接执行的后续计划；后续执行顺序以 `docs/planning/phase0-poc-plan.md` 为准。

### TASK 0：Phase0a planning 文档

目标：建立 Phase0a 的任务来源和执行边界。

Dependencies：

- 无。

输入：

- `docs/requirements.md`
- `docs/phases/phase0-poc.md`
- `docs/design/intermediate-representations.md`
- `docs/design/golden-sample.md`
- 已确认的 Phase0a 子阶段边界

输出：

- `docs/planning/phase0a-poc-tasks.md`

涉及文件：

- `docs/planning/README.md`
- `docs/planning/phase0a-poc-tasks.md`

完成标志：

- 已记录当时的 Phase0a 任务、依赖关系、验证路径和正式样例接入前置条件。
- 当前后续执行不再以本文档的 TASK 3-8 为准，应改以 `docs/planning/phase0-poc-plan.md` 为准。

验证命令：

- `git diff --check`

验证补充：

- 文档自检。
- 确认不修改 runtime 代码。

### TASK 1：Python 项目与 CLI 骨架

目标：建立最小可运行 Python CLI。

Dependencies：

- TASK 0。

输入：

- `.md` 或 `.txt` 原始文本输入。
- CLI 参数：输入文件路径、workspace 输出目录。

输出：

- 可运行 CLI。
- 保存原始输入的 workspace。

涉及范围：

- Python 项目配置。
- CLI 入口。
- 基础目录结构。
- 最小 smoke test。

不包含：

- LLM。
- DocIR 生成。
- SchemaIR 生成。
- Validator。

完成标志：

- CLI 能稳定读取 `.md` / `.txt` 输入。
- CLI 能创建 workspace。
- CLI 能保存 raw doc。

验证命令：

- `uv run --group dev pytest`
- `uv run bank-config-compiler ingest --input docs/reference/samples/b2eboc/b2e0061.md --workspace workspace/phase0a-smoke --overwrite`

验证补充：

- CLI smoke test 已覆盖。
- unit test 已覆盖 `.md` / `.txt` 输入、缺失输入、非法后缀和 overwrite 行为。

### TASK 2：Workspace 产物协议

目标：定义 Phase0a 文件产物命名和读写规则。

Dependencies：

- TASK 1。

输入：

- TASK 1 创建的 workspace。
- 原始输入文档。

输出：

- `raw-doc.md`
- `docir-draft.md`
- `docir-final.md`
- `schemair-draft.json`
- `schemair-validation-result.json`
- `schemair-final.json`

涉及范围：

- workspace I/O。
- 路径校验。
- UTF-8 with no BOM 读写规则。
- 文件缺失与格式错误信息。

不包含：

- 具体 IR 生成逻辑。
- Validator 规则实现。

完成标志：

- CLI 能创建、读取并校验 Phase0a 必要文件。
- 文件命名与 `docs/design/golden-sample.md` 的 golden sample 方向兼容。

验证命令：

- `uv run --group dev pytest`
- `uv run bank-config-compiler check --workspace workspace/phase0a-smoke --profile raw`
- `uv run bank-config-compiler check --workspace workspace/phase0a-smoke --profile phase0a`

验证补充：

- unit test 已覆盖 artifact 缺失、UTF-8 BOM、非法 JSON、未知 artifact 名称。
- smoke test 已覆盖 `ingest` 后的 raw profile 校验。
- `phase0a` profile 要求全部 Phase0a artifact 存在；当前不会生成 DocIR / SchemaIR 内容。

### TASK 3：DocIR Draft Generator 接口、stub 与 OpenAI-compatible adapter

目标：同时支持真实 LLM 和 stub 生成 DocIR Draft。

Dependencies：

- TASK 1。
- TASK 2。

输入：

- `raw-doc.md`
- generator provider 配置。
- OpenAI-compatible 环境变量配置。

输出：

- `docir-draft.md`

涉及范围：

- DocIR generator 接口。
- stub generator。
- OpenAI-compatible adapter。
- 环境变量配置。
- LLM 调用边界。
- 错误处理。
- 敏感日志约束。

不包含：

- SchemaIR 生成。
- Validator。
- Human Review UI。

完成标志：

- CLI 可从 raw doc 生成 `docir-draft.md`。
- stub 输出稳定。
- 默认真实 LLM 配置缺失时返回明确错误。
- 日志不输出完整银行原文。

验证命令：

- 待 TASK 3 实现时确定。

验证补充：

- stub unit test。
- 无密钥时真实 LLM 路径错误信息测试。

### TASK 4：SchemaIR Draft Generator 接口、stub 与 OpenAI-compatible adapter

目标：基于 `docir-final.md` 生成 `schemair-draft.json`。

Dependencies：

- TASK 1。
- TASK 2。
- TASK 3。

输入：

- `docir-final.md`
- generator provider 配置。
- OpenAI-compatible 环境变量配置。

输出：

- `schemair-draft.json`

涉及范围：

- SchemaIR generator 接口。
- stub generator。
- OpenAI-compatible adapter。
- SchemaIR JSON 输出。
- 字段最小结构。
- `uncertain` / `sourceText` 保留策略。

不包含：

- Validator 规则实现。
- Schema Workbook。
- Workbook Generator。

完成标志：

- CLI 可从 final DocIR 生成 draft SchemaIR。
- stub 输出稳定。
- draft SchemaIR 字段最小结构符合 Phase0a 要求。

验证命令：

- 待 TASK 4 实现时确定。

验证补充：

- stub unit test。
- JSON 结构测试。

### TASK 5：SchemaIR Validator

目标：实现字段级 SchemaIR Validator。

Dependencies：

- TASK 2。
- TASK 4。

输入：

- `schemair-draft.json`

输出：

- `schemair-validation-result.json`

校验范围：

- `path` 非空。
- `fieldName` 非空。
- `dataType` 属于允许枚举。
- `required` 是 boolean。
- `multiple` 是 boolean。
- `hasChildren` 是 boolean。
- `confidence` 在 0 到 1 之间。
- `sourceText` 非空。
- `path` 不重复。
- 父子路径关系可解释。
- `hasChildren`、`multiple` 和 `dataType` 不存在明显冲突。

不包含：

- Schema Workbook。
- Workbook Generator。
- 复杂 condition DSL。

完成标志：

- Validator 结果可定位到字段和规则。
- Validator 失败时返回字段级错误列表，不能只返回通用失败信息。

验证命令：

- 待 TASK 5 实现时确定。

验证补充：

- valid SchemaIR 单元测试。
- missing field 单元测试。
- duplicate path 单元测试。
- invalid type 单元测试。
- confidence 越界单元测试。
- sourceText 缺失单元测试。

### TASK 6：Phase0a Stub Golden Regression

目标：建立不依赖真实 LLM 的稳定回归命令。

Dependencies：

- TASK 1。
- TASK 2。
- TASK 3。
- TASK 4。
- TASK 5。

输入：

- stub raw doc fixture。
- stub expected DocIR。
- stub expected SchemaIR。
- expected validation result。

输出：

- stub fixture。
- expected 文件。
- 回归脚本或测试命令。
- 回归命令文档。

涉及范围：

- 测试样例。
- expected diff。
- 回归命令。
- 回归结果输出。

不包含：

- 正式银行样例。
- 真实 LLM 质量门禁。
- Schema Workbook。
- Workbook Generator。

完成标志：

- 本地一条命令可跑通 `Raw Docs -> DocIR Draft -> SchemaIR Draft -> Validator`。
- stub golden regression 作为 Phase0a 自动化硬门禁。

验证命令：

- 待 TASK 6 实现时确定。

验证补充：

- golden regression 通过。

### TASK 7：正式脱敏银行样例接入

目标：接入用户提供的正式 `raw-doc` 和 expected IR。

Dependencies：

- TASK 6。
- 用户已提供正式 raw doc：`docs/reference/samples/b2eboc/b2e0061.md`。
- 用户确认 `docir.expected.md`。
- 用户确认 `schemair.expected.json`。

输入：

- 已入库的正式 raw doc：`docs/reference/samples/b2eboc/b2e0061.md`。
- 人工确认后的 `docir.expected.md`。
- 人工确认后的 `schemair.expected.json`。

输出：

```text
samples/golden/<message-code>-real-masked/
├── raw-doc.md
├── docir.expected.md
├── schemair.expected.json
├── schemair-validation.expected.json
└── README.md
```

涉及范围：

- 样例 README。
- 脱敏说明。
- expected fixtures。
- 正式样例回归接入。

完成标志：

- 正式样例进入 golden regression。
- 文档说明该样例可作为 Phase0a 验收资产。
- 正式样例仍使用 stub / fixture 做硬门禁，不依赖真实 LLM 输出稳定性。

验证命令：

- 待 TASK 7 实现时确定。

验证补充：

- 正式样例回归通过。

### TASK 8：README 与 docs-sync

目标：同步用户可见命令、配置和阶段状态。

Dependencies：

- TASK 1 到 TASK 7 的实际实现结果。

输入：

- TASK 1 到 TASK 7 的实际实现结果。
- 当前 README。
- Phase0a planning 文档。

输出：

- 更新后的 `README.md`。
- 必要时更新的 `docs/planning/phase0a-poc-tasks.md`。
- 必要时更新的 `docs/design/*`。

涉及文件：

- `README.md`
- `docs/planning/phase0a-poc-tasks.md`
- 必要时涉及 `docs/design/*`

完成标志：

- README 说明当前可运行命令、LLM 配置、stub 回归、正式样例接入状态。
- planning 文档与实际实现状态一致。

验证命令：

- 待 TASK 8 执行时确定。

验证补充：

- docs-sync 检查通过。

## 5. 待用户提供资产

本节保留 Phase0a 旧计划中的资产状态。当前完整 Phase0 的下一步不是直接进入旧 TASK 7，而是先基于已提供的 raw doc 产出 IR candidate 并人工 review。

已提供：

- `docs/reference/samples/b2eboc/b2e0061.md`

仍需用户确认或补充：

- 人工确认后的 `docir.expected.md`。
- 人工确认后的 `schemair.expected.json`。

可先由后续执行者基于 `b2e0061.md` 生成 DocIR / SchemaIR candidate，再与用户逐字段确认。确认后的版本才能整理为 expected artifacts 并作为 golden fixture 入库。

脱敏要求：

- 不包含真实客户名。
- 不包含真实账号。
- 不包含证书编号。
- 不包含机构号。
- 不包含真实 URL。
- 不包含密钥、token 或密码。
- 不包含联系人、手机号、邮箱。
- 不包含生产环境地址。
- 不包含内部系统名。

建议使用稳定占位符：

```text
<MASKED_COMPANY_NAME>
<MASKED_ACCOUNT_NO>
<MASKED_BANK_ENDPOINT>
```

## 6. 验证总览

当前 TASK 0 验证：

- 文档自检。
- `git diff --check`

后续完整 Phase0 实现的最低验证要求：

- CLI smoke test。
- unit test。
- stub golden regression。
- docs-sync 检查。

只要用户可见命令、配置、验证方式、阶段状态或公开产物格式发生变化，必须检查 `README.md`。
