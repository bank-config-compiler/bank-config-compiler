# Interface

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Interface Code | b2e0061 | 直接来自交易标题。 |
| Interface Name | 公对私转账汇款 | 直接来自交易标题。 |
| Message Format | XML | 直接来自 BOCB2E 文件格式说明。 |
| Version | 120 | 推测值；协议说明推荐 `120`，但示例也出现 `version="100"`，不确定性在 SchemaIR envelope 字段中标记。 |
| Source Document | samples/candidates/b2eboc-b2e0061/raw-doc.md | 本 candidate 使用人工修正后的 raw-doc 作为样例 source。 |
| Candidate Status | REVIEW_ONLY | 仅用于 human review，不是 golden sample，也不是 runtime contract。 |

---

# Source Context / 来源上下文

BOCB2E 使用 HTTP POST 和 `application/xml` 内容。XML payload 包含一个 `<bocb2e>` block，并包含 `<head>` 与 `<trans>` 子节点。本 candidate DocIR 保留通用 envelope/head 上下文，同时只抽取 b2e0061 的 `ASSEMBLY` / `PARSE` 交易消息。

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
| Root Path | Root.bocb2e | path 由 XML 层级推导。 |
| Applies To | ASSEMBLY, PARSE | Workbook 展示时并入两个方向 sheet。 |
| Evidence Scope | raw-doc BOCB2E 文件格式、顶层、消息章节和报文示例 | 历史导出 JSON 不作为字段来源。 |

## Fields

| Field Name | Path | Type | Occurs | Required | Description | 条件 / 备注 |
|---|---|---|---|---|---|---|
| bocb2e | Root.bocb2e | Object | 1..1 | Y | BOCB2E XML 顶层块 | 一个 HTTP 请求或响应只能且必须包含一个 BOCB2E XML block。 |
| @version | Root.bocb2e.@version | String | 0..1 | N | BOCB2E 协议版本号 | 推测默认 `120`；示例出现 `100`，需确认实际配置口径。 |
| @security | Root.bocb2e.@security | Boolean | 0..1 | N | 是否启用 BOCB2E 协议层安全模式 | 原文说明目前应选择 `true`。 |
| @locale | Root.bocb2e.@locale | String | 0..1 | N | 客户端区域和响应语言类型 | 协议说明使用 `locale`，示例未出现。 |
| @lang | Root.bocb2e.@lang | String | 0..1 | N | 示例中观察到的历史语言属性 | 示例使用 `lang="chs"`；是否兼容 `locale` 需确认。 |
| head | Root.bocb2e.head | Object | 1..1 | Y | 消息头 | 包含前端信息、企业 ID、企业操作员等信息。 |
| termid | Root.bocb2e.head.termid | String | 1..1 | Y | 代表一台企业前置机 | E 开头 + 前置机 IP 地址，各段补零，无小数点 12 位。 |
| trnid | Root.bocb2e.head.trnid | String | 1..1 | Y | 客户端产生的报文编号 | 字母数字串 0-12 位。 |
| custid | Root.bocb2e.head.custid | String | 1..1 | Y | 企业在中行网银系统的客户编码 | 数码 1-10 位。 |
| cusopr | Root.bocb2e.head.cusopr | String | 1..1 | Y | 企业操作员代码 | 字母数字标点串 1-20 位。 |
| trncod | Root.bocb2e.head.trncod | String | 1..1 | Y | 交易代码 | b2e 开头加 4 位数字；需与报文体一致。 |
| token | Root.bocb2e.head.token | String | 0..1 | N | 交易验证标识 | 签到时生成、签退时注销；请求示例可缺省，响应示例出现。 |
| trans | Root.bocb2e.trans | Object | 1..1 | Y | 交易数据块 | b2e0061 交易 wrapper 挂载于该节点下。 |

# Message: ASSEMBLY

## Metadata

| Key | Value | Review Note |
|---|---|---|
| Message Name | b2e0061-rq | 直接来自请求表。 |
| Function Type | ASSEMBLY | 企业端组装请求报文。 |
| Root Path | Root.bocb2e.trans.trn-b2e0061-rq | path 由 BOCB2E envelope 和交易 wrapper 推导。 |
| Description | 公对私转账汇款请求报文 | 企业端发起划账时银行只检查付款账号，不校验收款账号。 |

## Fields

| Field Name | Path | Type | Length | Occurs | Required | Description | 条件 / 备注 |
|---|---|---|---|---|---|---|---|
| trn-b2e0061-rq | Root.bocb2e.trans.trn-b2e0061-rq | Object |  | 1..1 | Y | 转账交易请求 | 交易包装节点。 |
| ceitinfo | Root.bocb2e.trans.trn-b2e0061-rq.ceitinfo | String |  | 0..1 | N | 数字签名 | 该标签由前置机自动添加，企业无需上送；Workbook 是否展示为可配置字段需确认。 |
| transtype | Root.bocb2e.trans.trn-b2e0061-rq.transtype | String | 0-1 | 0..1 | N | 交易类型 | 可空；非空时只能为 1 或 2。1=委托待授权，2=授权退回修改。 |
| b2e0061-rq | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq | Object |  | 0..1000 | Y | 转账请求内容 | 原文写“不超过1000笔”；最小出现次数需人工确认。 |
| insid | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.insid | String | 1-32 | 1..1 | Y | 指令ID；本转账指令在客户端的唯一标识，建议企业按时间顺序生成且不超过12位 | 平台校验：操作员所属客户号下不能重复，不支持中文。 |
| obssid | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.obssid | String | 0-30 | 0..1 | N | 网银交易流水号 | 交易类型为 2 时有效且非空；流水对应交易必须存在且为该客户下退回类公转私交易。 |
| fractn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn | Object |  | 1..1 | Y | 付款人账户 | 分组节点，必填性由必填子字段推导。 |
| fribkn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn.fribkn | String | 0,5,12 | 0..1 | N | 付款行联行号 | 可空；前置机写 5 位或 12 位，平台说明含 5 位省行联行号。 |
| actacn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn.actacn | String | 1-35 | 1..1 | Y | 付款账号 | 平台校验为 1-20 位且账户已维护；与前置机长度 1-35 存在差异。 |
| actnam | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn.actnam | String | 0-70 | 0..1 | N | 付款人名称 | 虚拟账号时上送主账号名称。 |
| toactn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn | Object |  | 1..1 | Y | 收款人账户信息 | 分组节点，必填性由必填子字段推导。 |
| toibkn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.toibkn | String | 0-12 | 0..1 | N | 收款行联行号 | 可空；5 位或 12 位数字。 |
| acttyp | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.acttyp | String | 0-3 | 0..1 | N | 收款账户类型 | 可空，默认借记卡；119=借记卡，101=普活活期，188=活一本，103=信用卡；上送但无业务校验。 |
| actacn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.actacn | String | 1-35 | 1..1 | Y | 收款账号 | 如果中行账户且长度 18 位，必须上送收款行联行号；不支持中文。 |
| toname | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.toname | String | 1-70 | 1..1 | Y | 收款人名称 | 一个汉字等于一个字符。 |
| tobknm | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.tobknm | String | 0-70 | 0..1 | C | 收款人开户行名称 | 当收款行联行号为空时必填；系统可根据联行号或 CNAPS 号补全。 |
| toaddr | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.toaddr | String | 0-70 | 0..1 | N | 收款人地址 | 一个汉字占 2 个字符。 |
| email | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn.email | String | 3-80 | 0..1 | N | 收款人电子邮件地址 | 可空；非空时包含 @。 |
| trnamt | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.trnamt | Decimal | 15,2 / 22,2 | 1..1 | Y | 转账金额 | 前置机写长度(22,2)，平台写 15,2 位；不得超过转账限额。 |
| trncur | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.trncur | String | 3 | 1..1 | Y | 转账货币 | 只支持 001 或 CNY。 |
| priolv | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.priolv | String | 1-2 | 1..1 | Y | 银行处理优先级 | 枚举：0=普通，1=加急。 |
| cuspriolv | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.cuspriolv | String | 1-2 | 1..1 | Y | 客户处理优先级 | 枚举：0=普通，1=快速。 |
| furinfo | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.furinfo | String | 0-200 | 0..1 | N | 用途 | 不支持竖线字符；一个汉字占 2 个字符。 |
| trfdate | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.trfdate | Date | YYYYMMDD | 1..1 | Y | 要求的转账日期 | 系统当前日期含当日之后的一个月内。 |
| trftime | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.trftime | String | HHMMSS | 0..1 | N | 要求的转账时间 | 整点时间；raw-doc 已修正为 `HH0000（000000-230000）`，仍需确认是否只允许整点。 |
| comacn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.comacn | String | 0-35 | 0..1 | N | 支付费用账号 | 非空则平台按 1-20 位校验；为空使用付款账户代替。 |
| bocflag | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.bocflag | String | 1-2 | 1..1 | Y | 收款人是否中行账号 | 枚举：1=中行，0=他行。 |

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
| Root Path | Root.bocb2e.trans.trn-b2e0061-rs | path 由 BOCB2E envelope 和交易 wrapper 推导。 |
| Description | 公对私转账汇款响应报文 | 包含报文级处理状态和每条转账指令处理状态。 |

## Fields

| Field Name | Path | Type | Length | Occurs | Required | Description | 条件 / 备注 |
|---|---|---|---|---|---|---|---|
| trn-b2e0061-rs | Root.bocb2e.trans.trn-b2e0061-rs | Object |  | 1..1 | Y | 对应请求的响应 | 交易包装节点。 |
| status | Root.bocb2e.trans.trn-b2e0061-rs.status | Object |  | 1..1 | Y | 报文处理状态 | 通用响应状态结构。 |
| rspcod | Root.bocb2e.trans.trn-b2e0061-rs.status.rspcod | String |  | 1..1 | Y | 报文处理状态码 | 原字段表未给出 b2e0061 专属长度。 |
| rspmsg | Root.bocb2e.trans.trn-b2e0061-rs.status.rspmsg | String |  | 1..1 | Y | 报文处理状态说明 | 通用示例曾写 `errmsg`，需确认正式 tag。 |
| b2e0061-rs | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs | Object |  | 0..1000 | N | 每条转账指令响应内容 | 原文明确 `(0..1000)`。 |
| status | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.status | Object |  | 1..1 | Y | 每条划账指令处理状态 | 每条响应内状态。 |
| rspcod | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.status.rspcod | String |  | 1..1 | Y | 每条划账指令处理状态码 | 原字段表未给出长度。 |
| rspmsg | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.status.rspmsg | String |  | 1..1 | Y | 每条划账指令处理状态说明 | 原字段表未给出长度。 |
| insid | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.insid | String |  | 1..1 | Y | 指令ID，请求时给出的ID | 响应字段表未给出格式。 |
| obssid | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.obssid | String |  | 0..1 | N | 每条划账指令的网银划账流水号 | 响应字段表未给出必填性，候选按可空处理。 |

## Conditions

- 报文级 `status` 与每条响应内 `status` 是两个不同路径下的重复 tag，必须通过 path 区分。
- 响应字段表未给出大部分字段长度和必填性，本 candidate 需人工确认。
