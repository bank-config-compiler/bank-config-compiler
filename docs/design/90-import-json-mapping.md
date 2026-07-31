# Import JSON Mapping 设计

## Status

Superseded by `docs/adr/ADR-0004-schemair-and-workbook-artifacts.md`; the current dual-model boundary is defined by `docs/adr/ADR-0006-configir-and-configuration-workbook.md`.

## 1. 历史背景

早期设计曾考虑由确定性 Rule Engine 基于 `Final SchemaIR` 生成目标系统 Import JSON Draft。

在接入 `docs/reference/samples/b2eboc/` 后，真实或接近真实的导出 JSON 暴露出较高目标系统适配成本：同一接口存在 `ASSEMBLY` / `PARSE` 两个方向，导出 JSON 中还包含历史 ID、目标系统状态字段、父子引用和导入模板字段。这些字段并不完全来自银行 raw doc。

继续以 Import JSON 作为目标产物会把项目重心从“配置人员可审计的字段整理”推向“目标系统导入适配器维护”，与当前阶段目标不匹配。

## 2. 当前决策

项目不再以 Import JSON 作为最终目标产物。

当前目标是：

```text
Raw Docs
→ DocIR
→ Final SchemaIR
→ Final ConfigIR
→ Configuration Workbook
```

`Final SchemaIR` 是银行 XML 报文事实源，`Final ConfigIR` 是目标系统字段配置事实源。Configuration Workbook 是面向配置人员的人工配置交付物。

ConfigIR 中目标系统感知的字段取值、function、mapping 和处理策略，以及工作簿中面向人的配置指导，不等于恢复 Import JSON。它们不包含历史 ID、导入状态、父子 ID、导入模板兼容层或目标系统写入行为。

## 3. 历史样例处理

`docs/reference/samples/b2eboc/b2e0061-assembly.json` 和 `docs/reference/samples/b2eboc/b2e0061-parse.json` 保留为历史参考输入，用于理解目标系统曾经的导出形态。

这些 JSON 不再作为：

- 项目最终目标产物。
- MVP 验收标准。
- Rule Engine 输出兼容性标准。
- SchemaIR 字段模型或 ConfigIR 规则/catalog 的权威来源。

它们可以作为：

- 理解 `ASSEMBLY` / `PARSE` 方向的参考。
- 识别目标系统人工配置时可能关注的字段的辅助材料。
- 后续如果重新启动导入自动化时的参考样例。

## 4. 不再适用的候选规则

以下早期候选内容已不再适用：

- `fieldConfigs` 扁平数组格式。
- 从 SchemaIR 生成目标系统 Import JSON。
- `controlType` 映射。
- `ImportTargetProfile` / `ImportAdapter` / 接口级导入例外清单。
- 用 Import JSON 兼容性作为阶段成功条件。

后续若重新决定支持目标系统导入，应新建 ADR，明确恢复目标、兼容范围、ID 策略、导入校验方式和维护成本边界。
