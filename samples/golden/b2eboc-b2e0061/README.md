# b2e0061 Review Golden Sample

## Status

Review Golden.

## Purpose

This sample freezes the expected DocIR, SchemaIR, and review notes for the `b2e0061` raw document. It is not a final business answer and is not a runtime final contract.

The unresolved questions in `review-notes.expected.md` are intentional. They define the review output that later generators must preserve, including uncertainty, confidence, evidence, and human confirmation points.

## Artifacts

| Artifact | Purpose |
|---|---|
| `raw-doc.md` | Controlled raw document source for this sample. |
| `docir.expected.md` | Expected DocIR structure generated from the raw document. |
| `schemair.expected.json` | Expected SchemaIR generated from the expected DocIR. |
| `review-notes.expected.md` | Expected human review notes, including unresolved confirmation points. |

## Boundary

- Historical exported JSON may be used only as human review reference.
- Historical exported JSON must not be used to fill fields, enter expected SchemaIR, or act as regression input.
- `schemair-validation.expected.json` and `workbook-assertions.expected.json` are intentionally deferred until Validator and Workbook assertion boundaries are implemented.
