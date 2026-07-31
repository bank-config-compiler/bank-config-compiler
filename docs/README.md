# 文档中心

## Status

Active.

## 职责与受众

根目录 `README.md` 面向首次访问仓库或使用 Python 包的用户，负责项目定位摘要、当前能力快照、快速开始命令和现有 workspace artifact 协议。

本文件面向需要理解、评审或维护正式产品契约的工程人员，负责 source-of-truth 层级、阅读路径、文件命名和文档治理。它不复制运行命令或实时任务状态：

- 快速开始和当前可运行命令以 [`../README.md`](../README.md) 为入口。
- Phase0 详细任务状态只在 [`planning/00-phase0-poc-plan.md`](planning/00-phase0-poc-plan.md) 维护。

根 README 中的产品说明是入口摘要，不构成详细产品契约。摘要与正式文档不一致时，按下述 source-of-truth 层级解释。

## Source of Truth

正式文档按以下优先级解释：

1. [`01-requirements.md`](01-requirements.md) 定义项目级产品契约、范围和成功标准。
2. [`../configuration-rules/`](../configuration-rules/README.md) 保存 ConfigIR 可引用的正式、版本化目标系统规则资产。
3. [`adr/`](adr/README.md) 记录已经接受且约束后续实现的工程决策。
4. [`design/`](design/README.md) 细化系统、数据模型和交付物设计。
5. [`phases/`](phases/00-phase0-poc.md) 定义各阶段目标和验收边界。
6. [`planning/`](planning/README.md) 记录当前阶段的任务状态、依赖和验证路径。
7. [`reference/`](reference/README.md) 只保存候选草案和参考输入，不构成正式承诺。

同一层级出现不一致时，应停止实施并先修正文档；低优先级文档不得覆盖高优先级契约。

## 按目的阅读

| 目的 | 阅读入口 |
|---|---|
| 了解项目定位、范围和验收标准 | `01-requirements.md` |
| 理解已接受的关键决策 | `adr/README.md` |
| 理解三层 IR、系统边界和 Configuration Workbook | `design/README.md` |
| 查看阶段目标和进入条件 | `phases/00-phase0-poc.md`，再按阶段编号继续 |
| 查看 Phase0 当前任务、blocker 和验证路径 | `planning/00-phase0-poc-plan.md` |
| 查看正式目标系统规则资产 | `../configuration-rules/README.md` |
| 查阅候选草案和参考输入 | `reference/README.md` |
| 运行当前 CLI 或检查 workspace artifact | `../README.md` |

## 文档维护边界

- 根 `README.md` 只维护首次使用者需要的项目摘要、真实可运行命令、当前能力快照和 artifact 协议。
- `01-requirements.md` 维护产品级范围、术语、可信流程和跨阶段成功标准。
- `adr/` 维护已经接受且需要长期解释的决策，不重写历史。
- `design/` 维护模型、模块和交付物设计，不记录实时任务状态。
- `phases/` 维护阶段目标与验收边界；`planning/` 维护 active task 状态和 blocker。
- `configuration-rules/` 是正式规则资产；`reference/` 不是权威规则或 catalog 来源。
- 用户可见命令、artifact、配置或当前已实现能力变化时，必须同步检查根 README。
- 本文件不复制根 README 中的命令，也不复制 planning 中的任务明细。

## Naming and Status Rules

- 每个目录内的正式 Markdown 文档使用 `NN-kebab-case.md`，其中 `NN` 为两位排序编号。
- `README.md`、`ADR-XXXX-*`、原始样例和 JSON fixture 不加排序编号。
- `00-09` 用于入口、总览或最早阶段；常规主题使用 `10-89` 范围内的既定顺序。
- `90-99` 用于 superseded 或历史设计；编号不替代状态声明。
- 正式 Markdown 文档必须显式声明 `Status`；Draft、Placeholder、Reference 或 Superseded 内容不得伪装成当前承诺。
- 重命名文档时必须同步全部 Markdown 链接、路径示例和目录索引。
