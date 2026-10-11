# SpecCraft 匿名公开 Fixture

这组材料用于 P2 快速 Contract、Workflow 与 Eval 验证。它们以 ExportFlow 的“超大 Excel
订单异步导入与导出闭环”为示例背景，但不依赖该仓库，也不含任何 SBS 业务数据。

- `complete.md`：完整需求，直接进入候选规格与人工批准 Gate；
- `missing-role-permission-failure.md`：缺少角色、权限和失败语义，必须澄清；
- `knowledge-conflict.md`：PRD 与知识引用冲突，不能由 RAG 覆盖 PRD；
- `knowledge-required-unavailable.md`：关键术语依赖授权知识源，Provider 不可用时必须显式停下。

`catalog.yaml` 是 gold expectation；模型评审不能覆盖这些确定性预期。

`repositories/exportflow-sample/` 是 P2.10 的匿名全栈仓库 Fixture。它同时提供 Repository Guide、
标准 `.deliveryflow/` Harness、前后端依赖清单和一条不完整需求，用于从 CLI 真实演示仓库发现、
澄清、修订、批准和七类文档导出；它不是 DeliveryFlow 的业务依赖。
