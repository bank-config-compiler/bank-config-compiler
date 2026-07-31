# Phase2-Pilot 需求

## Status

Draft.

## 1. 阶段目标

Phase2-Pilot 目标是在受控真实项目或准真实项目中验证实施提效和稳定性。

本阶段应基于 Phase1-MVP 的验收证据重新确认范围，不应在 Phase1 验收前提前锁定具体实现。

交付形态应是受控内部试点工具或小型内部系统。是否进一步系统化，应基于真实样例、人工修改点、双 Validator 缺口、规则版本影响、Workbook Generator 稳定性和 Configuration Workbook 对人工配置的指导效果判断。

## 2. 候选范围

以下范围仅作为 Phase2 规划输入，需在 Phase1 验收后确认：

- 多个真实脱敏样例的回归集。
- 更完整的任务审计记录。
- Prompt 与规则版本管理。
- SchemaIR 字段覆盖率与人工修改率。
- ConfigIR 映射接受率、人工修改率和未映射项统计。
- FUNCTION / MAPPING 选择质量和修正原因统计。
- 规则版本变化对 ConfigIR、Warnings 和人工返工量的影响。
- Configuration Workbook 对配置人员人工配置与验证的有效性。
- 试点环境部署、日志检索和故障定位。
- 试点运行问题复盘和版本演进机制。

## 3. 进入条件

- Phase1 的 golden sample 回归稳定。
- 已明确试点银行文档样例、目标系统 catalog 和 Configuration Workbook 最小验收标准。
- 已定义试点成功指标、数据保留策略和人工 Review 职责边界。

## 4. 待确认问题

- 试点样例数量和覆盖范围。
- 试点成功指标。
- 试点数据保留与脱敏要求。
- 人工修改点和不确定字段的统计方式。
- 映射接受率、未映射项和 FUNCTION / MAPPING 选择质量的统计口径。
- 规则版本影响的基线和比较方式。
- Validator 覆盖缺口和 Workbook Generator 规则缺口的处理流程。
