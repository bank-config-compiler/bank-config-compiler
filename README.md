# Bank Config Compiler

## Status

Draft.

## 项目定位

Bank Config Compiler 面向银企直连实施场景，将真实脱敏的银行接口文档整理为可 Review、可校验、可追溯的银行 XML 报文模型，并依次形成目标系统接口标准、接口模板和供配置人员使用的 Configuration Workbook。

LLM / Agent 只能生成 DocIR、SchemaIR、InterfaceStandardIR 和 InterfaceTemplateIR Draft；目标配置必须按“Final SchemaIR → Final Interface Standard → Final Interface Template”顺序经过 Validator 和人工 Review。Configuration Workbook 是配置规格与执行清单，不是 Import JSON、目标系统可导入文件或 IR 的反向输入。

当前产品范围只承诺 XML 银行报文。IR 使用 JSON 序列化不等于支持 JSON 银行报文。

## 当前能力

- CLI 可以从 `.md` / `.txt` 输入创建 workspace，并保存 `raw-doc.md`。
- CLI 当前只公开 `raw` profile，检查 `raw-doc.md` 的 UTF-8 no BOM 文件协议；完整 `phase0` profile 将在 Workbook trusted chain 完成时启用。
- SchemaIR v2 Validator 已作为库实现：只接受 `schemair/v2` 与 XML 节点，严格校验 artifact identity/lifecycle、字段层级、方向级 encoding evidence、最小结构化银行条件和 Final eligibility，并以 canonical JSON SHA-256 将结果绑定到完整输入内容。
- InterfaceStandardIR Validator 已作为库实现：严格绑定 Final SchemaIR identity/hash、方向与 `RELEASED` 规则包，校验字段覆盖、路径/顺序、XML Keys、三态约束、银行条件、差异 Review、Rule References 和 Final eligibility，并生成 `interface-standard-validation-result/v1`。
- InterfaceTemplateIR Validator 已作为库实现：精确绑定 Final Standard 与 `RELEASED` v2 规则包，按方向严格校验 `standardTarget`/`parseTarget`、表达式 FIELD reference、collection context、processing、omission、Mapping/Replacement、Review 和 Final eligibility，并生成 `interface-template-validation-result/v1`。
- workspace 库支持受 workspace 边界保护的嵌套 JSON artifact，拒绝 BOM、非 UTF-8、重复属性、非 object 根节点、NaN/Infinity 和路径逃逸。
- DocIR / SchemaIR Review Golden sample 已落地；`configuration-rules/v1` 与 `configuration-rules/v2` 均已发布并冻结为接口无关、非全量的 BKL configuration rules 子集。v2 保持 v1 的 27/207/14/5/6 catalog，只修订方向相关 Standard projection：ASSEMBLY 显式镜像 target，PARSE 从精确绑定的 Final Standard 解析表达式/collection source。
- 规则包 loader/validator 已作为库实现：只使用 `yaml.safe_load`，校验 UTF-8 no BOM、严格结构、生命周期、唯一性、值域、redaction 和跨文件引用。调用方显式选择 v1 或 v2 后，默认加载接受相应 `RELEASED` 版本；不会自动选择最新版本或迁移已有 Final IR。

P0-T3 为 `In Progress`：SchemaIR v2、InterfaceStandardIR runtime/Final fixtures 和 InterfaceTemplateIR Draft runtime 已完成。b2e0061 的 ASSEMBLY/PARSE Template Draft 候选 hash 分别为 `sha256:356b83c1aff90d83d82fa3bbc14f7fe8277c34605a3d5edb4cb99abd71c49957`、`sha256:33cd4f7ae02701d6ab19cf46628398354590dba3d612f91e43b06f78d1356621`，当前仍是 `DRAFT/PENDING`，需 Human Review 后才能冻结为 Final；Workbook 和完整 trusted chain 尚未实现。详细状态见 [Phase0-PoC 执行计划](docs/planning/00-phase0-poc-plan.md)。

## 快速开始

安装依赖并运行测试：

```powershell
uv run --group dev pytest
```

导入原始输入到 workspace：

```powershell
uv run bank-config-compiler ingest --input docs/reference/samples/b2eboc/b2e0061.md --workspace workspace/phase0-smoke --overwrite
```

`ingest` 只把外部 `.md` / `.txt` 输入保存为 workspace 内的 `raw-doc.md`，不生成 DocIR、SchemaIR 或 Validator 结果。

检查只包含 raw doc 的 workspace：

```powershell
uv run bank-config-compiler check --workspace workspace/phase0-smoke --profile raw
```

`phase0a` 已移除且不提供兼容别名。当前 `check` 不运行 SchemaIR Validator；完整 `phase0` profile 将要求调用者显式选择 direction、Standard/Template 版本和规则包，并在 Workbook 批次实现。

等价模块入口：

```powershell
uv run python -m bank_config_compiler ingest --input docs/reference/samples/b2eboc/b2e0061.md --workspace workspace/phase0-smoke --overwrite
```

## Workspace Artifacts

当前 CLI profile 只要求以下文件：

| Artifact | 格式 | 当前用途 |
|---|---|---|
| `raw-doc.md` | Markdown / text | 由 `ingest` 从外部输入导入，作为后续生成命令的输入。 |

库级 JSON artifact I/O 可以安全读写 workspace 内的相对嵌套路径。P0-T3 Final SchemaIR、双方向 Final Standard、机器结果和 Review 记录位于 `samples/trusted-chain/b2eboc-b2e0061/`；它们是通用链路的开发 fixture，不是 CLI 自动生成的 artifact。所有 artifact 必须使用 UTF-8 with no BOM。

## 详细文档

正式产品契约、设计决策、阶段计划、规则资产和文档维护规范统一从 [文档中心](docs/README.md) 进入。
