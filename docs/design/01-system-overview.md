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
    E --> F["SchemaIR Validator"]
    F -->|"校验失败：修正后重新校验"| E
    F -->|"校验通过"| SV["SchemaIR Validation Result"]
    SV --> G["人工 Review SchemaIR"]
    G -->|"修正后重新校验"| E
    G -->|"确认"| H["Final SchemaIR"]

    H --> I["LLM 生成 InterfaceStandardIR Draft"]
    RS["Standard 使用的 configuration-rules 版本"] --> I
    I --> J["Standard Validator"]
    J -->|"校验失败：修正后重新校验"| I
    J -->|"校验通过"| STV["Standard Validation Result"]
    STV --> K["人工 Review Interface Standard"]
    K -->|"修正后重新校验"| I
    K -->|"确认"| L["Final InterfaceStandardIR"]

    L --> M["LLM 生成 InterfaceTemplateIR Draft"]
    RT["Template 使用的 configuration-rules 版本"] --> M
    M --> N["Template Validator"]
    N -->|"校验失败：修正后重新校验"| M
    N -->|"校验通过"| TV["Template Validation Result"]
    TV --> O["人工 Review Interface Template / Omissions"]
    O -->|"修正后重新校验"| M
    O -->|"确认"| P["Final InterfaceTemplateIR"]

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

- Final SchemaIR：银行 XML 报文结构与银行原始约束。
- Final InterfaceStandardIR：一个 `interfaceCode + direction` 的目标系统接口标准。
- Final InterfaceTemplateIR：一份模板对所绑定标准字段的取值、处理和 omission 决策。

Configuration Workbook 是派生交付物，不是事实源，也不是可导入文件。

## 2. 模块边界

### 2.1 Input / Workspace

职责：

- 接收 `.md`、`.txt` 或粘贴文本。
- 保存 raw doc 和任务上下文。
- 为 Draft、Final、Validator result 和 workbook 提供可追溯 artifact 边界。

不负责解释银行字段或目标系统规则。

### 2.2 LLM Draft Generators

职责：

- 从 Raw Docs 生成 DocIR Draft。
- 从 Final DocIR 生成 SchemaIR Draft。
- 从 Final SchemaIR 与指定规则版本生成 InterfaceStandardIR Draft。
- 从 Final InterfaceStandardIR 与指定规则版本生成 InterfaceTemplateIR Draft。

约束：

- 只能输出 Draft。
- Template generator 必须精确绑定已确认的标准版本。
- 不得在缺少 catalog 时推断字段、function 或 mapping。
- 输出必须经过结构校验和人工 Review。
- 不生成最终工作簿。

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

Template Validator 负责：

- Template 精确引用 Final Standard 的 ID、version 和 content hash；
- 每个 `standardFieldRef` 存在且在同一模板中不重复；
- Value Expression 树、递归关系和顺序合法；
- String/Boolean/Date/Number 标量模板行必须有字段值表达式，Node/Object 模板行不得有字段值表达式；
- FIELD、FUNCTION、MAPPING 与 Rule ID 引用属于指定 catalog/规则版本；
- 存在模板行时，每个标准 XML Key 恰好具有一个表达式；
- 缺失标准字段均有 omission Warning；未确认 omission 不能成为 Final；
- 已确认 omission 与 `EMPTY` 保持不同语义。

Validator 不判断某个 function、mapping 或字段省略是否符合业务语义；该判断必须由人工 Review 完成。

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
- 将标量字段值与 XML Key 的递归表达式展开到 `Value Expressions`；
- 汇总差异、omissions、规则冲突、不确定项和 Validator issue；
- 生成执行与验证清单。

禁止：

- 补业务字段或临时推断 Value Mode；
- 替换缺失的 Rule ID 或 catalog 引用；
- 连接目标系统推断 Standard Action；
- 把 omission 转换为 `EMPTY`；
- 反向读取 Excel 更新任何 Final IR；
- 输出或承诺目标系统 Import JSON。

## 3. 规则资产边界

正式规则资产位于仓库顶层 `configuration-rules/`。`docs/reference/` 不是规则来源。

规则版本一旦发布不可原地覆盖。InterfaceStandardIR、InterfaceTemplateIR、Validator result 和 Configuration Workbook 必须记录实际使用的精确规则版本及 Rule ID。标准和后续模板可以使用不同规则版本，但模板对标准 artifact 的绑定不因此改变。

当前 catalog 未提供，因而两个目标配置 IR 的 wire contract、Validator、golden fixture 和 Workbook Generator 仍受阻，不得以历史导出 JSON 代替。

## 4. 候选任务状态

以下状态表达核心产物边界，wire name 可在实现 spec 中细化：

```text
RAW_DOC_CREATED
DOCIR_DRAFT_GENERATED
DOCIR_CONFIRMED
SCHEMAIR_DRAFT_GENERATED
SCHEMAIR_VALIDATED
SCHEMAIR_CONFIRMED
STANDARD_DRAFT_GENERATED
STANDARD_VALIDATED
STANDARD_CONFIRMED
TEMPLATE_DRAFT_GENERATED
TEMPLATE_VALIDATED
TEMPLATE_CONFIRMED
CONFIGURATION_WORKBOOK_GENERATED
```

任何 Draft 被修改后，对应 validation 状态必须失效并重新计算。标准版本变化不会自动迁移或重新解释已有模板。

## 5. 候选 Workspace 结构

```text
workspace/{taskId}/
├── raw-doc.md
├── docir-draft.md
├── docir-final.md
├── schemair-draft.json
├── schemair-validation-result.json
├── schemair-final.json
├── standards/{direction}/{standardVersion}/
│   ├── standard-draft.json
│   ├── standard-validation-result.json
│   └── standard-final.json
└── templates/{direction}/{templateId}/{templateVersion}/
    ├── template-draft.json
    ├── template-validation-result.json
    ├── template-final.json
    └── configuration-workbook.xlsx
```

这是候选 artifact 结构，不是已经实现的完整协议。当前 bootstrap 只实现根 README 中列出的 artifact；具体 wire 和命名在 catalog 确认后的代码实施 spec 中冻结。

## 6. 分阶段交付

- Phase0-PoC：文件 workspace、受控 fixture、三个 Validator、确定性 Workbook Generator 和结构化 golden regression。
- Phase1-MVP：增加四类 IR Review、omission Review 与工作簿预览/下载。
- Phase2-Pilot：验证标准复用、模板接受率、omission 质量、规则版本影响和人工返工量。
- Phase3-Production：暂不定义。
