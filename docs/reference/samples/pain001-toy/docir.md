# Message

Message Name: Customer Credit Transfer Initiation
Message Type: pain.001
Format: ISO20022
Version:

---

# Section: Group Header

## Description

The group header contains common information for the payment message.

## Fields

| Field Name | XML Path | Type | Length | Occurs | Required | Description |
|---|---|---|---|---|---|---|
| MsgId | GrpHdr.MsgId | String | 35 | 1..1 | M | Message Identification |
| CreDtTm | GrpHdr.CreDtTm | DateTime | ISO8601 | 1..1 | M | Creation Date Time |
| NbOfTxs | GrpHdr.NbOfTxs | Numeric | 15 | 1..1 | M | Number Of Transactions |

## XML Example

```xml
<GrpHdr>
  <MsgId>MSG202605270001</MsgId>
  <CreDtTm>2026-05-27T10:00:00</CreDtTm>
  <NbOfTxs>1</NbOfTxs>
</GrpHdr>
```

---

# Section: Payment Information

## Fields

| Field Name | XML Path | Type | Length | Occurs | Required | Description |
|---|---|---|---|---|---|---|
| PmtInfId | PmtInf.PmtInfId | String |  | 1..1 | M | Payment Information Identification |
| ReqdExctnDt | PmtInf.ReqdExctnDt | Date |  | 1..1 | M | Requested Execution Date |
| CdtTrfTxInf | PmtInf.CdtTrfTxInf | Group |  | 1..n | M | Credit Transfer Transaction Information |

## Conditions

- ReqdExctnDt must not be earlier than current business date.

## XML Example

```xml
<PmtInf>
  <PmtInfId>PMT001</PmtInfId>
  <ReqdExctnDt>2026-05-28</ReqdExctnDt>
  <CdtTrfTxInf>
    <Amt>100.00</Amt>
  </CdtTrfTxInf>
</PmtInf>
```

