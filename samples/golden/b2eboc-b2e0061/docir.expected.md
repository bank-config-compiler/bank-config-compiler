# Interface

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Interface Code | b2e0061 | 直接来自交易标题。 |
| Interface Name | 公对私转账汇款 | 直接来自交易标题。 |
| Message Format | XML | 直接来自 BOCB2E 文件格式说明。 |
| Version | 120 | 推测值；协议说明推荐 `120`，但示例也出现 `version="100"`，不确定性在 SchemaIR envelope 字段中标记。 |
| Source Document | samples/golden/b2eboc-b2e0061/raw-doc.md | 本 Review Golden sample 使用人工修正后的 raw-doc 作为样例 source。 |
| Review Golden Status | REVIEW_GOLDEN | 用于冻结 expected DocIR / SchemaIR / review notes；不是 final business answer，也不是 runtime final contract。 |

---

# Source Context / 来源上下文

BOCB2E 使用 HTTP POST 和 `application/xml` 内容。XML payload 包含一个 `<bocb2e>` block，并包含 `<head>` 与 `<trans>` 子节点。本 Review Golden DocIR 保留通用 envelope/head 上下文，同时只抽取 b2e0061 的 `ASSEMBLY` / `PARSE` 交易消息。

从 raw-doc 保留的通用规则：

- XML declaration 建议使用 UTF-8，但 raw-doc 示例也出现 GB2312。
- `<bocb2e>` 可包含 `version`、`security`、`locale` 属性；示例中还观察到 `lang="chs"`。
- 一个 HTTP 请求或响应只能且必须包含一个 BOCB2E XML block。
- `head` 包含前置机、客户、操作员、交易代码和 token 等通用字段。
- `trans` 下的交易 wrapper 命名为 `trn-xxx-rq` 和 `trn-xxx-rs`。
- 按通用消息章节，响应状态使用 `rspcod` 和 `rspmsg`；示例响应出现 `errmsg`，需人工确认正式 tag。

# Envelope

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Envelope Name | BOCB2E XML block | 覆盖 b2e0061 请求/响应共享 envelope。 |
| Root Path | Root.bocb2e | path 由 XML 层级推导，完整 path 在 SchemaIR 中表达。 |
| Applies To | ASSEMBLY, PARSE | Workbook 展示时并入两个方向 sheet。 |
| Evidence Scope | raw-doc BOCB2E 文件格式、顶层、消息章节和报文示例 | 历史导出 JSON 不作为字段来源。 |

## Fields

| Index | Or | Message Item | Mult. | Type | Required | 说明 | 校验点 | Review |
|---|---|---|---|---|---|---|---|---|
| 1 |  | `bocb2e` | [1..1] | Object |  | BOCB2E XML 顶层块 | 一个 HTTP 请求或响应只能且必须包含一个 BOCB2E XML block |  |
| 1.1 |  | 　`@version` | [0..1] | String | N | BOCB2E 协议版本号 | BOCNET 3.0 表示为 `120`；使用数字型货币码时用 `100` | 版本口径需确认。 |
| 1.2 |  | 　`@security` | [0..1] | Boolean | N | 是否启用 BOCB2E 协议层安全模式 | 目前应选择 `true` |  |
| 1.3 |  | 　`@locale` | [0..1] | String | N | 客户端区域和响应语言类型 | 例如 `zh_CN`、`en_US` | 协议说明使用 `locale`。 |
| 1.4 |  | 　`@lang` | [0..1] | String | N | 示例中观察到的历史语言属性 | 示例使用 `lang="chs"` | 是否兼容 `locale` 需确认。 |
| 1.5 |  | 　`head` | [1..1] | Object |  | 数据头 | 包含前端信息、企业 ID、企业操作员等信息 |  |
| 1.5.1 |  | 　　`termid` | [1..1] | String | Y | 代表一台企业前置机 | E 开头 + 前置机 IP 地址，各段补零，无小数点 12 位<br>检查终端号是否维护 |  |
| 1.5.2 |  | 　　`trnid` | [1..1] | String | Y | 客户端产生的报文编号 | 字母数字串 0-12 位 |  |
| 1.5.3 |  | 　　`custid` | [1..1] | String | Y | 企业在中行网银系统的客户编码 | 数码 1-10 位 |  |
| 1.5.4 |  | 　　`cusopr` | [1..1] | String | Y | 企业操作员代码 | 字母数字标点串 1-20 位<br>检查操作员是否存在 |  |
| 1.5.5 |  | 　　`trncod` | [1..1] | String | Y | 交易代码 | b2e 开头加 4 位数字<br>检查交易是否存在，与报文体是否一致 |  |
| 1.5.6 |  | 　　`token` | [0..1] | String | N | 交易验证标识，签到时生成、签退时注销 | Base64 字符串 0-64 位<br>检查令牌是否正确 | 请求示例可缺省，响应示例出现；方向差异需确认。 |
| 1.6 |  | 　`trans` | [1..1] | Object |  | 交易数据块 | b2e0061 交易 wrapper 挂载于该节点下 |  |

# Message: ASSEMBLY

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Message Name | b2e0061-rq | 直接来自请求表。 |
| Function Type | ASSEMBLY | 企业端组装请求报文。 |
| Root Path | Root.bocb2e.trans.trn-b2e0061-rq | path 由 BOCB2E envelope 和交易 wrapper 推导，完整 path 在 SchemaIR 中表达。 |
| Description | 公对私转账汇款请求报文 | 企业端发起划账时银行只检查付款账号，不校验收款账号。 |

## Fields

| Index | Or | Message Item | Mult. | Type | Required | 说明 | 校验点 | Review |
|---|---|---|---|---|---|---|---|---|
| 2 |  | `trn-b2e0061-rq` | [1..1] | Object |  | 转账交易请求 |  | 交易包装节点。 |
| 2.1 |  | 　`ceitinfo` | [0..1] | String | N | 数字签名 | 该标签由前置机自动添加，企业无需上送 | 是否进入可配置字段需确认。 |
| 2.2 |  | 　`transtype` | [0..1] | String | N | 交易类型 | 不超过1位数字；可空<br>1 委托待授权；2 授权退回修改；该项可空，表示普通转账交易，非空时只能为1或2 |  |
| 2.3 |  | 　`b2e0061-rq` | [0..1000] | Object |  | 转账请求内容 | 不超过1000笔 | 最小出现次数需确认。 |
| 2.3.1 |  | 　　`insid` | [1..1] | String | Y | 指令ID；本转账指令在客户端的唯一标识，建议企业按时间顺序生成且不超过12位 | 非空字符串；长度1-32<br>客户号下不能重复；不支持中文 |  |
| 2.3.2 |  | 　　`obssid` | [0..1] | String | C | 网银交易流水号 | 可空，若不为空只为数字且长度1-30位<br>交易类型为2时有效且非空；流水对应交易必须存在且为该客户下退回类公转私交易 |  |
| 2.3.3 |  | 　　`fractn` | [1..1] | Object |  | 付款人账户 |  |  |
| 2.3.3.1 |  | 　　　`fribkn` | [0..1] | String | N | 付款行联行号 | 可空数码5位或12位<br>可空，数码5位；联行号有对应的省行联行号 | 前置机和平台长度口径不一致。 |
| 2.3.3.2 |  | 　　　`actacn` | [1..1] | String | Y | 付款账号 | 非空字符串；1-35位<br>非空字符1-20位；账户已维护，操作员有权限；不支持中文 | 前置机和平台长度口径不一致。 |
| 2.3.3.3 |  | 　　　`actnam` | [0..1] | String | N | 付款人名称 | 可空字符串；长度0-70<br>虚拟账号时上送主账号名称 |  |
| 2.3.4 |  | 　　`toactn` | [1..1] | Object |  | 收款人账户信息 |  |  |
| 2.3.4.1 |  | 　　　`toibkn` | [0..1] | String | N | 收款行联行号 | 数码；长度0-12<br>可空；5位或12位数字；中行账户支持上送12位 CNAPS 号 |  |
| 2.3.4.2 |  | 　　　`acttyp` | [0..1] | String | N | 收款账户类型 | 数码；长度0-3<br>可空，默认借记卡；119=借记卡，101=普活活期，188=活一本，103=信用卡；上送但无业务校验 |  |
| 2.3.4.3 |  | 　　　`actacn` | [1..1] | String | Y | 收款账号 | 非空字符串；长度1-35<br>中行账户且长度18位时必须上送收款行联行号；不支持中文 |  |
| 2.3.4.4 |  | 　　　`toname` | [1..1] | String | Y | 收款人名称 | 非空字符串；长度1-70<br>一个汉字等于一个字符 |  |
| 2.3.4.5 |  | 　　　`tobknm` | [0..1] | String | C | 收款人开户行名称 | 可空字符串；0-70位<br>当收款行联行号为空时必填；系统可根据联行号或 CNAPS 号补全 | 条件必填。 |
| 2.3.4.6 |  | 　　　`toaddr` | [0..1] | String | N | 收款人地址 | 可空字符串；0-70位<br>一个汉字占2个字符 |  |
| 2.3.4.7 |  | 　　　`email` | [0..1] | String | N | 收款人电子邮件地址 | 可空；非空时包含 @，3-80 位 |  |
| 2.3.5 |  | 　　`trnamt` | [1..1] | Decimal | Y | 转账金额 | 非空正数字；长度(22,2)<br>非空正数15,2位；根据交易币种辅币位数检查金额格式；不超过转账限额 | 前置机和平台长度口径不一致。 |
| 2.3.6 |  | 　　`trncur` | [1..1] | String | Y | 转账货币 | 非空3位大写字母、数字<br>只支持001或者CNY，仅人民币 |  |
| 2.3.7 |  | 　　`priolv` | [1..1] | String | Y | 银行处理优先级 | 非空字母数字字符串1-2位<br>枚举：0=普通，1=加急 |  |
| 2.3.8 |  | 　　`cuspriolv` | [1..1] | String | Y | 客户处理优先级 | 非空字母数字字符串1-2位<br>枚举：0=普通，1=快速 |  |
| 2.3.9 |  | 　　`furinfo` | [0..1] | String | N | 用途 | 字符串，长度0-200，不支持 `\|`<br>可空；一个汉字占2个字符 |  |
| 2.3.10 |  | 　　`trfdate` | [1..1] | Date | Y | 要求的转账日期；YYYYMMDD | 日期；YYYYMMDD<br>系统当前日期含当日之后的一个月内 |  |
| 2.3.11 |  | 　　`trftime` | [0..1] | String | N | 要求的转账时间；HHMMSS | 可空，时间 HHMMSS<br>当日时为当前时间后整点；当日后一个月内为整点；HH0000（000000-230000）默认为000000 | 是否只允许整点需确认。 |
| 2.3.12 |  | 　　`comacn` | [0..1] | String | N | 支付费用账号 | 可空字符串；0-35位<br>非空则1-20位且账户已维护；为空使用付款账户代替 | 前置机和平台长度口径不一致。 |
| 2.3.13 |  | 　　`bocflag` | [1..1] | String | Y | 收款人是否中行账号 | 非空字母数字1-2位<br>枚举：1=中行，0=他行 |  |

## Conditions

- `transtype` 为空表示普通转账；非空只能为 `1` 或 `2`。
- `obssid` 在 `transtype=2` 时有效且非空。
- `tobknm` 在 `toibkn` 为空时必填。
- `trftime` 受 `trfdate` 是否为当日影响，并且看起来只允许整点。
- `comacn` 为空时使用付款账户代替。

# Message: PARSE

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Message Name | b2e0061-rs | 直接来自响应表。 |
| Function Type | PARSE | 银行返回响应报文，系统解析。 |
| Root Path | Root.bocb2e.trans.trn-b2e0061-rs | path 由 BOCB2E envelope 和交易 wrapper 推导，完整 path 在 SchemaIR 中表达。 |
| Description | 公对私转账汇款响应报文 | 包含报文级处理状态和每条转账指令处理状态。 |

## Fields

| Index | Or | Message Item | Mult. | Type | Required | 说明 | 校验点 | Review |
|---|---|---|---|---|---|---|---|---|
| 3 |  | `trn-b2e0061-rs` | [1..1] | Object |  | 对应请求的响应 |  | 交易包装节点。 |
| 3.1 |  | 　`status` | [1..1] | Object |  | 报文处理状态 |  | 通用响应状态结构。 |
| 3.1.1 |  | 　　`rspcod` | [1..1] | String | Y | 报文处理状态码 |  | 原字段表未给出 b2e0061 专属长度。 |
| 3.1.2 |  | 　　`rspmsg` | [1..1] | String | Y | 报文处理状态说明 |  | 通用示例曾写 `errmsg`，需确认正式 tag。 |
| 3.2 |  | 　`b2e0061-rs` | [0..1000] | Object |  | 每条转账指令响应内容 |  | 原文明确 `(0..1000)`。 |
| 3.2.1 |  | 　　`status` | [1..1] | Object |  | 每条划账指令处理状态 |  | 每条响应内状态。 |
| 3.2.1.1 |  | 　　　`rspcod` | [1..1] | String | Y | 每条划账指令处理状态码 |  | 原字段表未给出长度。 |
| 3.2.1.2 |  | 　　　`rspmsg` | [1..1] | String | Y | 每条划账指令处理状态说明 |  | 原字段表未给出长度。 |
| 3.2.2 |  | 　　`insid` | [1..1] | String | Y | 指令ID，请求时给出的ID |  | 响应字段表未给出格式。 |
| 3.2.3 |  | 　　`obssid` | [0..1] | String | N | 每条划账指令的网银划账流水号 |  | 响应字段表未给出必填性，候选按可空处理。 |

## Conditions

- 报文级 `status` 与每条响应内 `status` 是两个不同层级下的重复 tag，必须由 SchemaIR path 区分。
- 响应字段表未给出大部分字段长度和必填性，本 Review Golden sample 期望保留人工确认项。
