# Bank Config Compiler

## Status

Draft.

## 项目定位

Bank Config Compiler 面向银企直连实施场景，将真实脱敏的银行接口文档整理为可 Review、可校验、可追溯的银行 XML 报文模型，并依次形成目标系统接口标准、接口模板和供配置人员使用的 Configuration Workbook。

LLM / Agent 只能生成 DocIR、SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR Draft；目标配置必须按“Final SchemaIR → Final Interface Standard → Final Interface Template”顺序经过 Validator 和人工 Review。Configuration Workbook 是配置规格与执行清单，不是 Import JSON、目标系统可导入文件或 IR 的反向输入。

当前产品范围只承诺 XML 银行报文。IR 使用 JSON 序列化不等于支持 JSON 银行报文。

## 当前能力

- CLI 可以从 `.md` / `.txt` 输入创建 workspace，并保存 `raw-doc.md`。
- CLI 可以检查固定 artifact 名称、UTF-8 no BOM 编码和 JSON 可解析性。
- SchemaIR Validator v1 已作为库和自动化测试实现，并具有 b2e0061 expected validation result。现有实现仍接受 legacy JSON 枚举；这不代表产品支持 JSON 银行报文。
- DocIR / SchemaIR Review Golden sample 已落地；`configuration-rules/v1` 已发布为接口无关、非全量且不可变的 BKL configuration rules 子集，包含方向字段、正式导出观察到的 5 个 String Function、预设 Mapping catalog 样例、MAPPING/Replacement、processing policy、Standard 镜像、结构绑定和安全固定值契约；字符长度默认值为 `STANDARD_1`。
- 规则包 loader/validator 已作为库实现：只使用 `yaml.safe_load`，校验 UTF-8 no BOM、严格结构、生命周期、唯一性、值域、redaction 和跨文件引用。默认加载已接受 `RELEASED` v1；未来 Draft 候选检查必须显式使用 `require_released=False`。

P0-T3 的资料缺失 blocker 已解除并为 `In Progress`；规则包运行时已经完成，`configuration-rules/v1` 经 maintainer 与 business reviewer 对候选 `60c3ca18665cc0e3c85bb7f1c6f2212bba1d4c4d` 双签，于 2026-08-06 发布为 `RELEASED`。b2e0061 两个方向的 XML encoding 已由 Human 与银行线下确认为 `UTF-8`；对应 SchemaIR v2 wire contract、Validator、Standard/Template、Workbook 和完整 trusted chain 尚未实现。详细状态和后续执行边界见 [Phase0-PoC 执行计划](docs/planning/00-phase0-poc-plan.md)。

## 快速开始

安装依赖并运行测试：

```powershell
uv run --group dev pytest
```

导入原始输入到 workspace：

```powershell
uv run bank-config-compiler ingest --input docs/reference/samples/b2eboc/b2e0061.md --workspace workspace/phase0a-smoke --overwrite
```

`ingest` 只把外部 `.md` / `.txt` 输入保存为 workspace 内的 `raw-doc.md`，不生成 DocIR、SchemaIR 或 Validator 结果。

检查只包含 raw doc 的 workspace：

```powershell
uv run bank-config-compiler check --workspace workspace/phase0a-smoke --profile raw
```

检查完整 workspace artifact 协议：

```powershell
uv run bank-config-compiler check --workspace workspace/phase0a-protocol-smoke --profile phase0a
```

`phase0a` profile 要求全部当前 artifact 已存在；CLI `check` 只检查文件协议和可解析性，不生成 SchemaIR，也不运行 SchemaIR Validator。

等价模块入口：

```powershell
uv run python -m bank_config_compiler ingest --input docs/reference/samples/b2eboc/b2e0061.md --workspace workspace/phase0a-smoke --overwrite
```

## Workspace Artifacts

当前 bootstrap 固定以下文件名：

| Artifact | 格式 | 当前用途 |
|---|---|---|
| `raw-doc.md` | Markdown / text | 由 `ingest` 从外部输入导入，作为后续生成命令的输入。 |
| `docir-draft.md` | Markdown | 仅定义文件协议，生成逻辑尚未实现。 |
| `docir-final.md` | Markdown | 仅定义文件协议，人工确认流程尚未实现。 |
| `schemair-draft.json` | JSON | 仅定义文件协议，生成逻辑尚未实现。 |
| `schemair-validation-result.json` | JSON | SchemaIR Validator 输出协议；当前 CLI `check` 只校验该文件可解析。 |
| `schemair-final.json` | JSON | 仅定义文件协议，人工确认流程尚未实现。 |

所有 artifact 必须使用 UTF-8 with no BOM。

## 详细文档

正式产品契约、设计决策、阶段计划、规则资产和文档维护规范统一从 [文档中心](docs/README.md) 进入。
