
## 取值方式
取值方式列：报文字段的值怎么获取处理

- FIXED_VALUE（固定值）
- EMPTY（空值）
- FIELD（取系统请求数据的字段）
- FUNCTION（系统提供的特定功能的function）
- MAPPING（映射能力，配置映射关系，常用于银行自约定的statusCode映射为我们系统约定的statusCode）
- CONCATENATE(拼接，可以将多个值拼接起来，被拼接值可以是任意取值方式）

## function

所有 function 输入、参数和输出的数据类型均为 String。

functions:
  TotalNum:
    code: TotalNum
    name: 计算总条数
    description: 计算上游传递的支付指令里的支付条数
    params: []
    example: "TotalNum()"

  CurrentDate:
    code: CurrentDate
    name: 获取当前日期
    description: 获取系统当前日期
    params:
      - name: format
        description: 日期格式
        default: "yyyyMMdd"
    example: "CurrentDate(yyyyMMdd)"

  CurrentDateTime:
    code: CurrentDateTime
    name: 获取当前日期时间
    description: 获取系统当前日期时间
    params:
      - name: format
        description: 日期时间格式
        default: "yyyyMMddHHmmss"
    example: "CurrentDateTime(yyyyMMddHHmmss)"

  SequenceNumber:
    code: SequenceNumber
    name: 生成序列号
    description: 生成不重复的序列号
    params:
      - name: digits
        description: 序列号位数
        default: 4
    example: "SequenceNumber(4)"

  FormatDate:
    code: FormatDate
    name: 日期格式转换
    description: 将日期字段从源格式转换为目标格式
    params:
      - name: source
        description: 源日期字段
      - name: from_format
        description: 源格式
      - name: to_format
        description: 目标格式
    example: "FormatDate(FIELD:transactionDate, yyyy-MM-dd, yyyyMMdd)"

## mapping

mapping 使用系统预设规则。模板配置 MAPPING 时选择一个全局唯一 `mappingRuleName`，并提供一个 FIELD 输入；完整值未匹配时校验失败。预设规则样例见 `mapping.txt`。

replacement 与 mapping 引用同一套预设规则，但在 Value Expression 完成后对结果字符串执行片段替换；空 target 表示删除命中片段，未命中的内容原样保留。每个栏位最多选择一个 replacement `mappingRuleName`。

## 数据类型

- String
- Boolean
- Date
- Number
- Node
- Object
- List
- Node：XML中的可重复出现的无值节点
- Object：XML中的无值节点
- List：仅用于JSON，同json中的List

数据类型参考：
<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns:xsi="">
  <pain.001.001.02>
    <GrpHdr>
      <MsgId>null</MsgId>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>null</PmtInfId>
      <Dbtr>
        <Nm>null</Nm>
      </Dbtr>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>null</InstrId>
          <EndToEndId>null</EndToEndId>
        </PmtId>
      </CdtTrfTxInf>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>null</InstrId>
          <EndToEndId>null</EndToEndId>
        </PmtId>
      </CdtTrfTxInf>
    </PmtInf>
    <PmtInf>
      <PmtInfId>null</PmtInfId>
      <Dbtr>
        <Nm>null</Nm>
      </Dbtr>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>null</InstrId>
          <EndToEndId>null</EndToEndId>
        </PmtId>
      </CdtTrfTxInf>
    </PmtInf>
  </pain.001.001.02>
</Document>

配置：
Document：
数据类型：Object，路径：Root

pain.001.001.02：
数据类型：Object，路径：Root.Document

MsgId：
数据类型：String，路径：Root.Document.pain.001.001.02.GrpHdr

PmtInf：
数据类型：NODE，路径：Root.Document.pain.001.001.02
