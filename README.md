# Bank Config Compiler

## Status

Draft.

## 项目定位

本项目面向银企直连实施场景，用于将真实脱敏的银行接口文档转换为可 Review、可校验、可追溯、可回归的 SchemaIR，并生成面向配置人员的 Schema Workbook。

本项目不是全自动生产配置生成器，也不以目标系统 Import JSON 作为当前交付目标。LLM / Agent 能力可以生成草稿，但可信链路必须包含人工 Review、SchemaIR 校验、确定性 Workbook Generator 和回归证据。

`Final SchemaIR` 是系统内部事实源。Schema Workbook 是由 `Final SchemaIR` 确定性生成的 Excel 交付物，用于指导配置人员人工配置目标系统。

## 交付形态

项目按阶段演进：

| Phase | 交付形态 |
|---|---|
| Phase0-PoC | 可重复运行的链路验证工具，例如 CLI、script 或 lightweight workflow runner，加文件 workspace、fixtures、Validator、Workbook Generator 和 golden sample regression。 |
| Phase1-MVP | 轻量 Review Tool，支持 Review、校验、确认、Schema Workbook 预览和下载。 |
| Phase2-Pilot | 受控内部试点工具或小型内部系统，用于真实或准真实项目验证。 |
| Phase3-Production | 暂不定义。 |

Skill、Agent 或 Dify-style workflow 可以作为辅助组件，但不是完整交付物，也不是可信边界。

## 文档结构

当前 source of truth 位于 `docs/`：

- `docs/requirements.md`：项目级需求、原则、交付形态和跨阶段约束。
- `docs/phases/`：各阶段需求。
- `docs/design/`：系统设计、IR 设计、Schema Workbook 策略和 golden sample 策略。
- `docs/adr/`：已接受的架构决策。
- `docs/reference/`：参考草案和样例，不是正式承诺。

建议阅读顺序：

1. `docs/requirements.md`
2. `docs/adr/README.md`
3. `docs/design/README.md`
4. `docs/phases/phase0-poc.md`
5. `docs/phases/phase1-mvp.md`

## 当前实现状态

当前仓库已开始实现 Phase0a-PoC 的无 UI CLI 链路。

已完成：

- Phase0a TASK 1：Python 项目与 CLI 骨架。
- CLI 支持从 `.md` / `.txt` 输入文件创建 workspace，并保存 `raw-doc.md`。
- Phase0a TASK 2：Workspace 产物协议。
- CLI 支持校验 Phase0a workspace 的固定 artifact 名称、UTF-8 no BOM 编码和 JSON 可解析性。
- Phase0 当前 reference raw doc 已提供：`docs/reference/samples/b2eboc/b2e0061.md`。

尚未完成：

- DocIR / SchemaIR 生成。
- SchemaIR Validator。
- Workbook Generator、Schema Workbook 和 golden regression。
- 基于 `b2e0061.md` 的 expected DocIR / expected SchemaIR / Validator result。

后续 Phase0-PoC 仍需确认：

- 基于 `b2e0061.md` 的 expected DocIR 和 expected SchemaIR。
- DocIR 最小格式和质量标准。
- SchemaIR 最小字段、类型枚举和校验规则。
- Schema Workbook 的 sheet、列、样式和结构化断言。
- Golden sample 目录结构和回归方式。
- 技术栈和无 UI 验证形态。

## 本地命令

安装与测试通过 `uv` 执行：

```powershell
uv run --group dev pytest
```

导入原始输入到 workspace：

```powershell
uv run bank-config-compiler ingest --input docs/reference/samples/b2eboc/b2e0061.md --workspace workspace/phase0a-smoke --overwrite
```

`ingest` 只是 Phase0a 链路的第一步：把外部 `.md` / `.txt` 输入标准化保存为 workspace 内的 `raw-doc.md`。它不生成 DocIR、SchemaIR 或 Validator 结果；后续转换应由独立生成、校验或编排命令负责。

校验只包含 raw doc 的 workspace：

```powershell
uv run bank-config-compiler check --workspace workspace/phase0a-smoke --profile raw
```

校验完整 Phase0a artifact 协议。该命令要求 workspace 中已经存在全部 Phase0a artifact；当前 Task1/2 不生成 DocIR / SchemaIR 内容：

```powershell
uv run bank-config-compiler check --workspace workspace/phase0a-protocol-smoke --profile phase0a
```

等价模块入口：

```powershell
uv run python -m bank_config_compiler ingest --input docs/reference/samples/b2eboc/b2e0061.md --workspace workspace/phase0a-smoke --overwrite
```

`docs/reference/samples/b2eboc/` 是当前 reference sample。它用于设计和 smoke 验证，不等同于已确认的 golden sample。

## Phase0a workspace artifacts

Task1/2 固定以下文件名：

| Artifact | 格式 | 当前用途 |
|---|---|---|
| `raw-doc.md` | Markdown / text | 由 `ingest` 从外部输入导入，作为后续生成命令的输入。 |
| `docir-draft.md` | Markdown | 仅定义文件协议，生成逻辑属于后续 Task。 |
| `docir-final.md` | Markdown | 仅定义文件协议，人工确认流程属于后续 Task。 |
| `schemair-draft.json` | JSON | 仅定义文件协议，生成逻辑属于后续 Task。 |
| `schemair-validation-result.json` | JSON | 仅定义文件协议，Validator 规则属于后续 Task。 |
| `schemair-final.json` | JSON | 仅定义文件协议，人工确认流程属于后续 Task。 |

所有 artifact 必须使用 UTF-8 with no BOM。
