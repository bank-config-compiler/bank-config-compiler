3.1 Group Header

The group header contains common information for the payment message.

| Field Name | Type | Length | Mandatory | Description |
|------------|------|--------|-----------|-------------|
| MsgId | String | 35 | M | Message Identification |
| CreDtTm | DateTime | ISO8601 | M | Creation Date Time |
| NbOfTxs | Numeric | 15 | M | Number Of Transactions |

XML Example:
<GrpHdr>
  <MsgId>MSG202605270001</MsgId>
  <CreDtTm>2026-05-27T10:00:00</CreDtTm>
  <NbOfTxs>1</NbOfTxs>
</GrpHdr>

3.2 Payment Information

| Field Name | Type | Occurs | Mandatory | Description |
|------------|------|--------|-----------|-------------|
| PmtInfId | String | 1..1 | M | Payment Information Identification |
| ReqdExctnDt | Date | 1..1 | M | Requested Execution Date |
| CdtTrfTxInf | Group | 1..n | M | Credit Transfer Transaction Information |

Condition:
ReqdExctnDt must not be earlier than current business date.

XML Example:
<PmtInf>
  <PmtInfId>PMT001</PmtInfId>
  <ReqdExctnDt>2026-05-28</ReqdExctnDt>
  <CdtTrfTxInf>
    <Amt>100.00</Amt>
  </CdtTrfTxInf>
</PmtInf>

