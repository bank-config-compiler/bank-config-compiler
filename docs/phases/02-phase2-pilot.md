# Phase2-Pilot 需求

## Status

Draft.

## 1. 阶段目标

Phase2-Pilot 在受控真实项目或准真实项目中验证实施提效、标准复用、模板配置质量和工作簿有效性。

本阶段范围必须依据 Phase1-MVP 的验收证据重新确认，不提前锁定具体实现。是否进一步系统化，应基于真实样例、三类 Validator 缺口、规则/标准版本影响、模板 omission 质量、Generator 稳定性和 Workbook 对人工配置的指导效果判断。

## 2. 候选范围

- 多个真实脱敏样例的回归集。
- 更完整的任务、版本和 Review 审计记录。
- Prompt 与规则版本管理。
- SchemaIR 字段覆盖率与人工修改率。
- Interface Standard 自动生成接受率、人工修改率和类型/path 修正原因。
- 同一 Standard 的 Template 复用数量与标准版本迁移成本。
- Template 字段映射接受率、人工修改率和未映射项。
- Omission 接受率、拒绝率、错误省略率和人工修正原因。
- FUNCTION/MAPPING 选择质量和修正原因。
- 规则版本变化对 Standard、Template、Warnings 和人工返工量的影响。
- Configuration Workbook 对配置人员人工配置与验证的有效性。
- 试点部署、日志检索、故障定位和版本演进机制。

## 3. 进入条件

- Phase1 golden regression 稳定。
- 已明确试点银行文档样例、目标系统 catalog 和 Workbook 最小验收标准。
- 已定义试点成功指标、数据保留策略和人工 Review 职责边界。
- 标准复用、模板版本和 omission Review 已有可审计实现。

## 4. 待确认问题

- 试点样例数量和覆盖范围。
- 试点成功指标。
- 试点数据保留与脱敏要求。
- Standard/Template 人工修改点统计口径。
- Omission 质量与漏配率的判断方式。
- 映射接受率和 FUNCTION/MAPPING 质量的统计口径。
- 规则/标准版本影响的基线和比较方式。
- Validator 和 Workbook Generator 缺口的处理流程。
