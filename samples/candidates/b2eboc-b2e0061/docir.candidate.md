# Interface

Interface Code: b2e0061
Interface Name: 公对私转账汇款
Message Format: XML
Version: 120
Source Document: docs/reference/samples/b2eboc/b2e0061.md
Candidate Status: 仅用于 review，不是 golden sample，也不是 runtime contract

---

# Source Context / 来源上下文

BOCB2E 使用 HTTP POST 和 `application/xml` 内容。XML payload 包含一个 `<bocb2e>` 块，并包含 `<head>` 与 `<trans>` 子节点。本 candidate DocIR 保留通用 envelope 作为上下文，但 SchemaIR 只抽取 b2e0061 交易消息。

从 raw-doc 保留的通用规则：

- XML declaration 建议使用 UTF-8，但 raw-doc 示例也出现 GB2312。
- `<bocb2e>` 可包含 `version`、`security`、`locale` 属性。
- 一个 HTTP 请求或响应只能且必须包含一个 BOCB2E XML block。
- 交易 wrapper 命名为 `trn-xxx-rq` 和 `trn-xxx-rs`。
- 按通用消息章节，响应状态使用 `rspcod` 和 `rspmsg`。

# Message: ASSEMBLY

Message Name: b2e0061-rq
Function Type: ASSEMBLY
Root Path: Root.bocb2e.trans.trn-b2e0061-rq
Description: 公对私转账汇款请求报文。企业端发起划账时银行只检查付款账号，不校验收款账号。

## Fields

| Field Name | Path | Type | Length | Occurs | Required | Description | 条件 / 备注 |
|---|---|---|---|---|---|---|---|
| trn-b2e0061-rq | Root.bocb2e.trans.trn-b2e0061-rq | Object |  | 1..1 | Y | 转账交易请求 | 交易包装节点。 |
| ceitinfo | Root.bocb2e.trans.trn-b2e0061-rq.ceitinfo | String |  | 0..1 | N | 数字签名 | 该标签由前置机自动添加，企业无需上送。 |
| transtype | Root.bocb2e.trans.trn-b2e0061-rq.transtype | String | 0-1 | 0..1 | N | 交易类型 | 可空；非空时只能为 1 或 2。1=委托待授权，2=授权退回修改。 |
| b2e0061-rq | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq | Object |  | 0..1000 | Y | 转账请求内容 | 原文写“不超过1000笔”；最小出现次数需人工确认。 |
| insid | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.insid | String | 1-32 | 1..1 | Y | 指令ID；本转账指令在客户端的唯一标识，建议企业按时间顺序生成且不超过12位 | 平台校验：操作员所属客户号下不能重复，不支持中文。 |
| obssid | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.obssid | String | 0-30 | 0..1 | N | 网银交易流水号 | 交易类型为 2 时有效且非空；流水对应交易必须存在且为该客户下退回类公转私交易。 |
| fractn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn | Object |  | 1..1 | Y | 付款人账户 | 分组节点，原文未显式给出必填性。 |
| fribkn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn.fribkn | String | 0,5,12 | 0..1 | N | 付款行联行号 | 可空；前置机写 5 位或 12 位，平台说明含 5 位省行联行号。 |
| actacn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn.actacn | String | 1-35 | 1..1 | Y | 付款账号 | 平台校验为 1-20 位且账户已维护；与前置机长度 1-35 存在差异。 |
| actnam | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.fractn.actnam | String | 0-70 | 0..1 | N | 付款人名称 | 虚拟账号时上送主账号名称。 |
| toactn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.toactn | Object |  | 1..1 | Y | 收款人账户信息 | 分组节点，原文未显式给出必填性。 |
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
| trftime | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.trftime | String | HHMMSS | 0..1 | N | 要求的转账时间 | 当日时为当前时间后整点；当日后一个月内为整点；HH1000 描述需确认。 |
| comacn | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.comacn | String | 0-35 | 0..1 | N | 支付费用账号 | 非空则平台按 1-20 位校验；为空使用付款账户代替。 |
| bocflag | Root.bocb2e.trans.trn-b2e0061-rq.b2e0061-rq.bocflag | String | 1-2 | 1..1 | Y | 收款人是否中行账号 | 枚举：1=中行，0=他行。 |

## Conditions

- `transtype` 为空表示普通转账；非空只能为 `1` 或 `2`。
- `obssid` 在 `transtype=2` 时有效且非空。
- `tobknm` 在 `toibkn` 为空时必填。
- `trftime` 受 `trfdate` 是否为当日影响。
- `comacn` 为空时使用付款账户代替。

# Message: PARSE

Message Name: b2e0061-rs
Function Type: PARSE
Root Path: Root.bocb2e.trans.trn-b2e0061-rs
Description: 公对私转账汇款响应报文，包含报文级处理状态和每条转账指令处理状态。

## Fields

| Field Name | Path | Type | Length | Occurs | Required | Description | 条件 / 备注 |
|---|---|---|---|---|---|---|---|
| trn-b2e0061-rs | Root.bocb2e.trans.trn-b2e0061-rs | Object |  | 1..1 | Y | 对应请求的响应 | 交易包装节点。 |
| status | Root.bocb2e.trans.trn-b2e0061-rs.status | Object |  | 1..1 | Y | 报文处理状态 | 通用响应状态结构。 |
| rspcod | Root.bocb2e.trans.trn-b2e0061-rs.status.rspcod | String |  | 1..1 | Y | 报文处理状态码 | 原字段表未给出 b2e0061 专属长度。 |
| rspmsg | Root.bocb2e.trans.trn-b2e0061-rs.status.rspmsg | String |  | 1..1 | Y | 报文处理状态说明 | 通用章节示例曾写 `Rspmsg` / `errmsg`，需确认正式 tag。 |
| b2e0061-rs | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs | Object |  | 0..1000 | N | 每条转账指令响应内容 | 原文明确 `(0..1000)`。 |
| status | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.status | Object |  | 1..1 | Y | 每条划账指令处理状态 | 每条响应内状态。 |
| rspcod | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.status.rspcod | String |  | 1..1 | Y | 每条划账指令处理状态码 | 原字段表未给出长度。 |
| rspmsg | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.status.rspmsg | String |  | 1..1 | Y | 每条划账指令处理状态说明 | 原字段表未给出长度。 |
| insid | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.insid | String |  | 1..1 | Y | 指令ID，请求时给出的ID | 响应字段表未给出格式。 |
| obssid | Root.bocb2e.trans.trn-b2e0061-rs.b2e0061-rs.obssid | String |  | 0..1 | N | 每条划账指令的网银划账流水号 | 响应字段表未给出必填性，候选按可空处理。 |

## Conditions

- 报文级 `status` 与每条响应内 `status` 是两个不同路径下的重复 tag，必须通过 path 区分。
- 响应字段表未给出大部分字段长度和必填性，本 candidate 需人工确认。
