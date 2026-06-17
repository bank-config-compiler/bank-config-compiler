## docir.candidata.md

1. `Interface` 章节结构不正确：`Interface Code` 和 `Interface Name` 写在同一行，不便阅读。`Message: ASSEMBLY`、`Message: PARSE` 章节也有同样问题。



## schemaIR

1. `SchemaIR` 范围应覆盖 `b2e0061` 交易消息以及可复用的 `BOCB2E head`，形成完整的 `envelope` 模型；否则无法完整指导配置。


## review-notes

1. `interface` 中的 `version` 不正确；对于不确定的内容，可以写推测值120，但需要标注不确定，参考schemair的confidence。
2. review-notes 的定位是什么？是否每次生成docir或schemaIR都会生成一个review-notes给human，如果是，文本书写应该更加适合人来review

## others

1. 需要有一个文档讲解 `docir` 和 `schemir` 的字段含义，例如 `confidence` 低于多少时需要重点关注。