# 系统设计总览

## Status

Draft.

## 1. 设计目标

系统由输入与 artifact workspace、LLM Draft Generators、Human Review Boundary、Validators、版本化规则资产和确定性 Workbook Generator 协作完成配置辅助链路。

目标系统的操作顺序是先配置接口标准，再配置引用该标准的接口模板。系统设计必须保留这一依赖，不能把银行报文事实、目标结构配置和转换配置压缩成一个模型。

```mermaid
flowchart TD
    A["Raw Docs"] --> B["LLM 生成 DocIR Draft"]
    B --> C["人工 Review DocIR"]
    C -->|"修正后重新 Review"| B
    C -->|"确认"| D["Final DocIR"]

    D --> E["LLM 生成 SchemaIR Draft"]
    E --> F["SchemaIR Validator / Draft Result"]
    F -->|"结构错误：修正后重新校验"| E
    F --> G["人工 Review SchemaIR"]
    G -->|"修改事实"| E
    G -->|"完成 Final metadata"| HC["完整 Final SchemaIR Candidate"]
    HC --> FV["SchemaIR Validator 复验"]
    FV -->|"失败：返回 Review"| G
    FV -->|"通过且 hash 匹配"| SV["Final SchemaIR Validation Result"]
    SV --> H["Eligible Final SchemaIR"]

    H --> I["LLM 生成 InterfaceStandardIR Draft"]
    RS["Standard 使用的 configuration-rules 版本"] --> I
    I --> J["Standard Validator / Draft Result"]
    J -->|"结构错误：修正后重新校验"| I
    J --> K["人工 Review Interface Standard"]
    K -->|"修改事实"| I
    K -->|"完成 Final metadata"| LC["完整 Final Standard Candidate"]
    LC --> JV["Standard Validator 复验"]
    JV -->|"失败：返回 Review"| K
    JV -->|"通过且 hash 匹配"| STV["Final Standard Validation Result"]
    STV --> L["Eligible Final InterfaceStandardIR"]

    L --> M["LLM 生成 InterfaceTemplateIR Draft"]
    RT["Template 使用的 configuration-rules 版本"] --> M
    M --> N["Template Validator / Draft Result"]
    N -->|"结构错误：修正后重新校验"| M
    N --> O["人工 Review Interface Template / Omissions"]
    O -->|"修改事实"| M
    O -->|"完成 Final metadata"| PC["完整 Final Template Candidate"]
    PC --> NV["Template Validator 复验"]
    NV -->|"失败：返回 Review"| O
    NV -->|"通过且 hash 匹配"| TV["Final Template Validation Result"]
    TV --> P["Eligible Final InterfaceTemplateIR"]

    H --> Q["确定性 Workbook Generator"]
    L --> Q
    P --> Q
    SV -->|"匹配 Final SchemaIR"| Q
    STV -->|"匹配 Final Standard"| Q
    TV -->|"匹配 Final Template"| Q
    RS -->|"Standard 精确规则版本"| Q
    RT -->|"Template 精确规则版本"| Q
    X["人工指定 Standard Action"] --> Q
    Q --> W["Configuration Workbook"]
```

上图表达组件职责和数据流；`docs/01-requirements.md` 中的可信流程是唯一规范性生命周期图。关键顺序为：

```text
Final SchemaIR
→ InterfaceStandardIR Draft / Validator / Review / Final
→ InterfaceTemplateIR Draft / Validator / Review / Final
→ Configuration Workbook
```

系统采用三个顺序关联的配置事实源：

- Final SchemaIR：银行 XML 报文结构、方向级 `messages[].xmlEncoding` 与银行原始约束。
- Final InterfaceStandardIR：一个 `interfaceCode + direction` 的目标系统接口标准，包括银行文档明确条件约束。
- Final InterfaceTemplateIR：一份模板的方向性 source/target、取值、处理和适用的 ASSEMBLY omission 决策。

Configuration Workbook 是派生交付物，不是事实源，也不是可导入文件。

## 2. 模块边界

### 2.1 Input / Workspace

职责：

- 接收 UTF-8 no BOM 的 `.md` 与 `.txt` 文件。
- 保存 raw doc 和任务上下文。
- 为 Draft、Final、Validator result 和 workbook 提供可追溯 artifact 边界。

不负责解释银行字段或目标系统规则。

### 2.2 Provider-neutral Draft Generators

职责：

- 从 Raw Docs 生成 DocIR Draft。
- 从 Final DocIR 生成 SchemaIR Draft。
- 从 Final SchemaIR 与指定规则版本生成 InterfaceStandardIR Draft。
- 从 Final InterfaceStandardIR、方向性 FIELD catalog 与指定规则版本生成 InterfaceTemplateIR Draft。

Phase0 中四类 generator 通过同一个 `DraftProvider` contract 调用。编排层显式传入 request 与只包含当前上游内容、media type 和适用 RELEASED 规则包的 `DraftGenerationContext`；provider 不读取 workspace、不扫描 Final/Golden，也不选择规则版本。provider 返回严格 UTF-8 的 `draft-provider-response/v1` JSON envelope 和非敏感调用 metadata；编排层负责 input hash/rule version 一致性、严格解析、dependency 校验、Validator 调用和 workspace 发布。deterministic fixture provider 只加载调用者显式指定的 `draft-stub-case/v1`。真实 `openai-chat` provider 使用运行时显式选择的 OpenAI-compatible Chat API，只把外部响应转换为同一公开 envelope，不能改变核心 trusted-chain 语义或自动产生 Final。SchemaIR/Standard/Template 各执行一个 `complete-artifact` 调用；DocIR 在一个 attempt 内依次提取完整 Interface/Envelope、联合 ASSEMBLY/PARSE messages outline 和有界字段详情，最终合并成内部 `docir-extraction/v1`，再由确定性 renderer 生成现有 Markdown 和 Human Review Notes。segment、outline 与 extraction 都不持久化，不成为公开 IR 或下游事实源。

真实 provider 只读取四个白名单配置：`BANK_CONFIG_COMPILER_LLM_API_KEY`、`BANK_CONFIG_COMPILER_LLM_BASE_URL`、`BANK_CONFIG_COMPILER_LLM_MODEL` 和 `BANK_CONFIG_COMPILER_LLM_TIMEOUT_SECONDS`。它们可来自启动目录中被 Git 忽略的 `.env` 或进程环境，进程环境优先；base URL、model、timeout 可再由 CLI 覆盖。API key 不提供 CLI 参数，attempt ID 始终按调用显式传入。Chat API 固定使用流式响应并在内存中聚合；每个 subcall 只有收到 `finish_reason=stop`、最终 usage 且完整 JSON 通过 segment 校验才可进入下一步。同一个 timeout 同时配置 SDK 逐次 I/O timeout 与从 stream create 到聚合完成的物理 subcall 绝对墙钟期限；后者触发时关闭当前资源并以稳定错误类型 fail closed。DocIR field detail 默认每批最多 16 个字段，可通过仅适用于 DocIR `openai-chat` 的正整数 CLI 参数覆盖；联合 outline 的 `{index,item}` selector 必须准确覆盖并保持顺序，最终合并再次执行完整 extraction 与 renderer 机械校验。开发验证期间，本项目 provider 门禁的具体校验原因会进入 CLI 和结构化日志，deadline 额外记录非敏感 elapsed/chunk count，SDK/第三方异常仍只记录类型。SDK 自动重试固定为 0；attempt 顺序 fail-fast，不 resume，所有重跑都必须由操作者以新 attempt ID 从第一段发起。成功调用增加 `draft-provider-call-result/v2`；DocIR 失败则由编排层保存 `draft-provider-failure-result/v2`，并把已有内容的 subcall 响应按 sequence/segment 分文件保存。v2 摘要记录有序 calls、provider/model/response ID、token usage、时间、Prompt/segment contract 与 endpoint fingerprint，不记录 secret、endpoint 原文或 source；失败文件不是 trusted-chain artifact。

约束：

- 只能输出 Draft。
- Template generator 必须精确绑定已确认的标准版本。
- 不得在缺少 catalog 事实时根据相近名称推断字段、function、mapping 或业务 Condition。
- 输出必须经过结构校验和人工 Review。
- 不生成最终工作簿。
- 不得返回或写入 `FINAL/APPROVED` artifact；DocIR 必须先由 Human 对准确 bytes hash 确认，三个 JSON Draft 则必须保存匹配 result 且保持 `finalEligible=false`。
- Provider response、原始银行文档、Draft 内容、review notes 和敏感固定值不得进入日志。

### 2.3 Validators

SchemaIR Validator 负责 SchemaIR 结构、枚举、完整 path、父子关系和确定性 invariant。

Standard Validator 负责：

- `interfaceCode`、direction、standard identity 和版本绑定；
- `fieldId`、parentPath、fullPath、sequence 和层级关系；
- `Node`、`Object` 与标量类型和 SchemaIR 结构一致；
- 当前 XML 标准不使用 JSON-only `List`；
- XML Keys 能追溯到 SchemaIR attribute；
- 约束状态不是未确认的 `UNKNOWN`；
- SchemaIR/Standard 差异具有原因、Rule ID 和 Review 结论。
- 银行条件引用、operator/effect、literal 和 evidence 合法，但 Validator 不执行条件。
- raw-doc 未写的约束在已审查范围内投影为 `NO_CONSTRAINT`；证据冲突或无法判定时保持 `UNKNOWN` 并阻止 Final。

Template Validator 负责：

- Template 精确引用 Final Standard 的 ID、version 和 content hash；
- ASSEMBLY `standardTarget.standardProjection` 与绑定 Standard 完全一致；PARSE 从精确绑定的 Final Standard 解析表达式/collection 中全部 `standardFieldRef` 的 projection；
- `VALUE | STRUCTURE_ONLY | COLLECTION_ITEM` 的结构绑定与方向、Standard 类型和 Parse target 相容；
- ASSEMBLY `standardTarget` 引用存在且不重复；
- PARSE target Parse Field 引用存在、path/datatype 与 catalog 相容，表达式/collection 内 Standard FIELD_REF 存在且方向正确；
- Value Expression 树、递归关系和顺序合法；
- String/Boolean/Date/Number 标量模板行必须有字段值表达式，Node/Object 模板行不得有字段值表达式；
- FIELD、FUNCTION、`mappingRuleName` 与 Rule ID 引用属于指定 catalog/规则版本；Function/MAPPING/Replacement 输入输出满足 String 和单规则约束；
- 存在模板行时，每个标准 XML Key 恰好具有一个表达式；
- 缺失 ASSEMBLY 标量 Standard Field 均有 omission Warning；未确认 omission 不能成为 Final；Node/Object 不参加 omission coverage，未配置 Parse Field 不自动产生 omission；
- 有 XML Key 或结构绑定需求的 Node/Object 必须有适用结构行：普通容器使用 `STRUCTURE_ONLY`，Parse collection source 使用 `COLLECTION_ITEM`；缺失 XML Key 配置直接报错，不伪装成 omission；
- `FIXED_VALUE` payload 必须在 `LITERAL` 与 `SECURE_INPUT_REF` 中二选一，安全输入只保存引用标识；
- 已确认 omission 与 `EMPTY` 保持不同语义。

Validator 不判断某个 function、mapping、目的系统业务 Condition 或字段省略是否符合业务语义；该判断必须由人工 Review 完成。

### 2.4 Review Workbench

候选职责：

- 展示、编辑和确认 DocIR。
- 展示 SchemaIR Validator 结果，修改并重新校验 SchemaIR。
- Review Interface Standard 的路径、类型、XML Keys、约束状态、差异和 Validator 结果。
- Review Interface Template 的字段表达式、XML Key 表达式、规则依据、处理策略和 omissions。
- 对每个 omission 保存原因与接受/拒绝结论。
- 预览和下载 Configuration Workbook。

Phase0 可以用受控 fixture 或命令流程表达人工确认；Phase1 才提供 UI。任何 Draft 被修改后，都必须重新进入对应 Validator。

### 2.5 Workbook Generator

输入：

- Final SchemaIR；
- Final InterfaceStandardIR；
- 选定的 Final InterfaceTemplateIR；
- 与三份 Final 内容匹配的通过校验结果；
- Standard 与 Template 实际使用的精确规则版本；
- 调用者显式指定的 `Standard Action = CREATE | REUSE | UPDATE`；
- 生成时间等非业务任务上下文。

职责：

- 为一个方向模板生成一份 `.xlsx`；
- 输出绑定标准的完整快照和模板实际字段子集；
- 在 `Overview` 展示 Final SchemaIR 的方向级 XML encoding，不生成伪 Standard 字段；
- 在 Template sheet 分列展示 Standard 快照、Template 镜像、Parse target 和 Value Expression，避免混合两端类型；
- 将标量字段值与 XML Key 的递归表达式展开到 `Value Expressions`；
- 汇总差异、银行条件、ASSEMBLY omissions、规则冲突、不确定项和 Validator issue；
- 生成执行与验证清单。

禁止：

- 补业务字段或临时推断 Value Mode；
- 替换缺失的 Rule ID 或 catalog 引用；
- 连接目标系统推断 Standard Action；
- 把 omission 转换为 `EMPTY`；
- 反向读取 Excel 更新任何 Final IR；
- 输出或承诺目标系统 Import JSON。

## 3. 规则资产边界

正式规则资产位于仓库顶层 `configuration-rules/`。`docs/reference/` 可以提供 raw-doc、正式导出和 catalog 样例等 Review 证据，但未经规则治理不能成为 Final IR 的规则来源。

规则版本一旦发布不可原地覆盖。InterfaceStandardIR、InterfaceTemplateIR、Validator result 和 Configuration Workbook 必须记录实际使用的精确规则版本及 Rule ID。标准和后续模板可以使用不同规则版本，但模板对标准 artifact 的绑定不因此改变。

`configuration-rules/v1` 与只修订方向相关 Standard projection 的 v2 均已发布并冻结。SchemaIR v2、InterfaceStandardIR、InterfaceTemplateIR、Configuration Workbook、双方向 Golden 与匹配 validation results 均已实现并冻结；P0-T3 已完成。P0-T4 的 provider-neutral runtime、六个受控 response、四类 CLI 和准确 hash 的 reviewed Final DocIR 已冻结；完整受控回归显式装载已审核 Final fixtures，双方向 Workbook 结构化内容均与 Golden 一致。P0-T5 的真实 provider adapter、显式配置、Prompt/context 边界与离线测试候选已经实现。`docir-012` 至 `docir-016` 逐步收口 shape、职责、空值 Review 与 index/name 问题。v12 的 `docir-017` Interface/Envelope 已通过全部机械门禁；联合 outline 随后在无可校验响应的情况下发生 `ReadTimeout`。离线调查确认原 timeout 缺少物理 subcall 绝对墙钟期限，现已补齐 watchdog、稳定失败分类与诊断计数；再次真实调用仍须另获授权并以新 attempt ID 从第一段开始。Golden 不参与真实候选自动语义判定。其余真实 Draft、逐层 Final validation 与双方向 Workbook 证据仍未完成，Phase0-PoC 为 In Progress。Final IR 必须精确引用适用的 `RELEASED` 规则版本。

## 4. 候选任务状态

以下状态表达核心产物边界，wire name 可在实现 spec 中细化：

```text
RAW_DOC_CREATED
DOCIR_DRAFT_GENERATED
DOCIR_CONFIRMED
SCHEMAIR_DRAFT_GENERATED
SCHEMAIR_DRAFT_VALIDATED
SCHEMAIR_CONFIRMED
SCHEMAIR_FINAL_VALIDATED
STANDARD_DRAFT_GENERATED
STANDARD_DRAFT_VALIDATED
STANDARD_CONFIRMED
STANDARD_FINAL_VALIDATED
TEMPLATE_DRAFT_GENERATED
TEMPLATE_DRAFT_VALIDATED
TEMPLATE_CONFIRMED
TEMPLATE_FINAL_VALIDATED
CONFIGURATION_WORKBOOK_GENERATED
```

任何 Draft 或完整 Final candidate 被修改后，对应 validation 状态必须失效并重新计算。只有 Final 内容的 identity/version/contract/hash 与复验结果全部匹配且 `finalEligible=true`，才能进入下游；标准版本变化不会自动迁移或重新解释已有模板。

## 5. 候选 Workspace 结构

```text
workspace/{taskId}/
├── raw-doc.md
├── docir-draft.md
├── docir-review-notes.md
├── docir-final.md
├── schemair-draft.json
├── schemair-review-notes.md
├── schemair-validation-result.json
├── schemair-final.json
├── standards/{direction}/{standardVersion}/
│   ├── standard-draft.json
│   ├── standard-review-notes.md
│   ├── standard-validation-result.json
│   └── standard-final.json
└── templates/{direction}/{templateId}/{templateVersion}/
    ├── template-draft.json
    ├── template-review-notes.md
    ├── template-validation-result.json
    ├── template-final.json
    └── configuration-workbook.xlsx
```

根级 SchemaIR artifact、library JSON I/O、通用 workspace selector/path contract 与完整 `phase0` CLI profile 均已实现。`phase0` 不扫描目录或自动选择最新版，只接受显式 direction/version/template selector，并分别加载 Standard 与 Template 实际引用的规则包。Draft 与 validation result 分别使用同目录临时文件原子替换；普通文件系统不提供跨文件事务，任何中断后的缺失或 canonical hash 不匹配都必须阻止下游。

## 6. 分阶段交付

- Phase0-PoC：文件 workspace、受控 fixture、真实 OpenAI-compatible Chat API Draft 验证、三个 Validator、逐层 Human Review、确定性 Workbook Generator 和结构化 golden regression。
- Phase1-MVP：增加四类 IR Review、omission Review 与工作簿预览/下载。
- Phase2-Pilot：验证标准复用、模板接受率、omission 质量、规则版本影响和人工返工量。
- Phase3-Production：暂不定义。
