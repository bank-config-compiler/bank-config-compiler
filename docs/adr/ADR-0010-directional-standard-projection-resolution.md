# ADR-0010: 按 Template 方向保存或解析 Standard projection

## Status

Accepted. Amends ADR-0008. Implemented by the released `configuration-rules/v2`.

## Date

2026-08-09

## Context

ADR-0008 要求每个 Template field config 保存单一 `standardFieldRef + standardProjection`。该模型适合 ASSEMBLY，因为每行只有一个银行 Standard target；但不能准确表达 PARSE：

- PARSE 的 target 是 Parse Field，Standard Field 是 Value Expression 的 source。
- `failReason` 等表达式会同时使用 `rspcod` 和 `rspmsg`，不存在可被确定选择的单一“主” Standard source。
- literal 或 EMPTY 表达式可能没有 Standard source。
- Template 已精确绑定不可变 Final Standard 的 `standardId + standardVersion + contentHash`，因此 PARSE source 的 required、length 和 dataType 可以由 `standardFieldRef` 确定性解析。

强制保存顶层单一 Standard source 会丢失真实依赖；同时保存表达式引用、顶层 source list 和 projection 会重复同一事实并增加漂移面。

`configuration-rules/v1` 已发布且不可变，不能原地改变其 `TPL.BIND.STANDARD_PROJECTION` 语义。

## Decision

- 保留现有 field config `bindingKind` 与 Value Expression `mode` 名称和值域。
- ASSEMBLY field config 使用 `standardTarget`：
  - `standardFieldRef` 指向唯一 Standard target；
  - `standardProjection.required/length/dataType` 显式镜像该 Final Standard 字段，并由 Validator 强制完全相等。
- PARSE VALUE field config 只声明 `parseTarget`；每个 FIELD_REF 在表达式节点保存自己的 `standardFieldRef`。
- PARSE function 的 FIELD_REF 参数和 MAPPING source 使用同一方向明确的 `standardFieldRef`，不使用通用、可混淆的 `fieldRef`。
- PARSE `COLLECTION_ITEM` 使用 `standardSource.standardFieldRef` 标识集合结构来源。
- PARSE 不保存顶层 `standardFieldRef`、`standardSources` 或重复的 `standardProjection`。Validator 从 Template 精确绑定的 Final Standard 解析每个引用的 projection。
- PARSE 表达式允许零个、一个或多个 Standard source；Validator 不得选择某个引用作为“主” source。
- `xmlKeyExpressions` 明确只属于 ASSEMBLY field config。
- 创建 `configuration-rules/v2` 承载修订后的 `TPL.BIND.STANDARD_PROJECTION`；v1 保持不变。现有 Final SchemaIR/Standard 继续引用 v1，后续 Template 可以独立引用 RELEASED v2。

## Alternatives Considered

### 原地修改并重新双签 v1

Pros:

- 不增加规则版本。

Cons:

- 同一个 `rulePackageVersion: v1` 会在不同 Git revision 表示不同语义。
- 历史 IR 没有规则包内容 hash，无法区分修改前后的 v1。
- 违反已发布版本不可变的治理约束。

Why not chosen:

- 破坏历史验证和可复现性；重新双签不能修复版本身份复用。

### PARSE 顶层保存 `standardSources[]` 及 projection

Pros:

- 可集中展示所有 source。

Cons:

- 与表达式树中的 FIELD_REF 重复。
- source list、projection 与表达式可能相互漂移。
- 纯 literal/EMPTY 表达式仍需要特殊规则。

Why not chosen:

- 精确绑定的 Final Standard 已能提供确定性解析，不需要第二份事实清单。

### 为复合表达式选择一个主 Standard source

Pros:

- 延续单一顶层 projection wire。

Cons:

- 主 source 没有业务语义。
- 会隐藏其他真实依赖，并使影响分析和 Workbook 展示不完整。

Why not chosen:

- 该选择不可由规则或银行事实确定，违反 fail-closed 原则。

## Consequences

- InterfaceTemplateIR Validator 必须使用方向相关的 field config 属性集合，并递归校验 PARSE 表达式中的全部 Standard 引用。
- ASSEMBLY coverage 和 target 唯一性基于 `standardTarget.standardFieldRef`；PARSE target 唯一性基于 `parseTarget.parseFieldRef`。
- PARSE collection context 必须验证表达式中的每个 Standard source 都位于对应 `standardSource` 集合节点下；零 source 表达式只依赖已建立的 collection iteration context。
- Workbook 对 ASSEMBLY 展示显式 Template projection；对 PARSE 从绑定 Final Standard 展开所有 source projection，并与 Parse target 分列展示。
- `configuration-rules/v2` 已经双 reviewer 对准确候选确认并发布；Final Template 必须精确引用该 `RELEASED` 版本。
