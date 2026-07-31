# 文档索引

## Status

Active.

## Source of Truth

正式文档按以下优先级解释：

1. `docs/01-requirements.md` 定义项目级产品契约、范围和成功标准。
2. `configuration-rules/` 保存 ConfigIR 可引用的正式、版本化目标系统规则资产。
3. `docs/adr/` 记录已经接受且约束后续实现的工程决策。
4. `docs/design/` 细化系统、数据模型和交付物设计。
5. `docs/phases/` 定义各阶段目标和验收边界。
6. `docs/planning/` 记录当前阶段的任务状态、依赖和验证路径。
7. `docs/reference/` 只保存候选草案和参考输入，不构成正式承诺。

同一层级出现不一致时，应停止实施并先修正文档；低优先级文档不得覆盖高优先级契约。

## Recommended Reading Order

1. `01-requirements.md`
2. `../configuration-rules/README.md`
3. `adr/README.md`
4. `design/README.md`
5. `phases/00-phase0-poc.md`
6. `planning/00-phase0-poc-plan.md`

## Naming Rules

- 每个目录内的正式 Markdown 文档使用 `NN-kebab-case.md`，其中 `NN` 为两位排序编号。
- `README.md`、`ADR-XXXX-*`、原始样例和 JSON fixture 不加排序编号。
- `00-09` 用于入口、总览或最早阶段；常规主题使用 `10-89` 范围内的既定顺序。
- `90-99` 用于 superseded 或历史设计；编号不替代状态声明，文档仍必须显式标记状态。
- 重命名文档时必须同步全部 Markdown 链接、路径示例和目录索引。
