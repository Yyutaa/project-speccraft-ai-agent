# 阶段 03 Handoff：事实账本与澄清 Gate

## 目标与非目标

已实现来源事实与用户决定分开入账、五维确定性完整度检查、澄清问题覆盖校验和显式回答 Gate。缺少角色、流程、权限、失败或验收信息时，Run 暂停且不生成 PRD；用户提交答案后写入 Decision Evidence，Gate 通过才从 Ledger 权威视图生成 PRD。

本阶段不实现 PRD Blueprint、真实模型 Provider、自动补答、数据库、跨进程恢复、RAG、身份认证或生成后重新打开澄清并使下游 Artifact 级联失效。

## 选型理由

- Pydantic v2 已是现有共享 Contract 依赖；领域分析、revision、防重和时间戳使用现有 Python 标准库，无新增运行时依赖。
- 在现有单进程内存 Runner 中保存 Ledger、Gap、Batch、Decision Evidence 与已消费 command ID，直接暴露 V0 的真实恢复和幂等边界。
- CompletenessAnalyzer 只检查结构化维度事实/决定；它不调用模型，也不根据自由文本关键词猜测语义完整度。
- 澄清 Provider 只把 GapSignal 转成确定性问题、选项和推荐。推荐仅保留在 Proposal 中；服务端只根据显式答案命令创建 Decision。
- Gate 放在 PRD 生成之前，因此澄清期间无需模拟 Artifact 失效或保留半成品。

## 模块边界

- `packages/contracts/src/deliveryflow_contracts/facts.py`：FactKind、FactDimension、SourceEvidence、DecisionEvidence、RequirementFact、FactLedger、GapSignal、CompletenessResult、ClarificationProposal/Batch/Answer 和提交请求；约束证据、推荐选项、revision 与问题覆盖。
- `packages/contracts/src/deliveryflow_contracts/runs.py`：新增 `awaiting_clarification` Run 状态、提交澄清命令、Ledger/Completeness/Batch 投影及跨对象状态不变量；校验 FACT 引用当前 Run 捕获的 SourceSnapshot。
- `packages/speccraft/src/deliveryflow_speccraft/completeness.py`：无 Provider 依赖的五维确定性完整度分析。相同 Ledger revision 和事实顺序得到相同 Gap。
- `packages/speccraft/src/deliveryflow_speccraft/runner.py`：创建来源 FACT，生成 Gap/Batch；校验回答、expected revision 与重复 command ID；形成决定后重新分析，只有 Gate 完整才调用 PRD Fake Provider。
- `apps/api/main.py`：公开澄清答案 POST 路由，映射 404/409/422 错误码；CORS 允许现有页面使用 GET/POST。
- `apps/web/src/api.ts`、`App.tsx`：投影 Ledger 和待回答问题；显示推荐但不预选；只提交用户选择/自定义答案并渲染后端 Run 响应。

## 状态与数据流

```text
POST /api/runs
  → SourceSnapshot + RepositoryBinding + HarnessContextSlice
  → FactLedger r1（带来源的未分类需求文本）
  → CompletenessAnalyzer
  → 五维存在任一缺口：awaiting_clarification（无 PRD）
  → 显式用户答案 + DecisionEvidence，Ledger revision + 1
  → Gate 通过：从 Ledger.authoritative_view 生成 PRD
  → PRD/TD 人工审批及 DeliverySpec 继续沿用阶段 01 流程
```

同维度 Decision 在 `authoritative_view` 中覆盖来源 FACT；来源 FACT 仍留在 Ledger 历史中。下游 Fake Provider 接收权威视图中的 claim 列表，不直接读取 SourceSnapshot 或 Harness 原文集合。

目前输入界面只有自由文本，且本阶段没有事实抽取模型。因此初始文本作为 dimension 为 `null` 的来源 FACT 入账，不会自动覆盖五个维度；新 Run 会保守地产生五个阻塞问题。系统不会因自然语言看起来完整或模型建议而跳过 Gate。

## 公开 Contract

- `FactKind` 仅有 `fact` 和 `decision`。`FACT` 必须有 SourceEvidence；Run 校验其 Hash 和摘录匹配该 Run 捕获的需求或 Harness 快照。`DECISION` 必须有 DecisionEvidence、维度、批次/问题 ID、command ID 和 expected revision，且不能伪装成来源证据。
- `FactDimension` 固定为 `role`、`workflow`、`permission`、`failure`、`acceptance`。缺失或来源事实互相冲突时产生 blocking Gap；同维度用户决定解决该缺口。当前 Analyzer 只产生这五类阻塞 Gap，不推断可选细节。
- `ClarificationProposal` 的推荐 ID 必须对应其选项并附理由。Proposal 不是 Fact，推荐不会自动成为决定。
- `ClarificationBatch` 持有当前 Ledger revision、所有 Gap ID、阻塞 Gap ID 和 Proposal；每个阻塞 Gap 必须有唯一问题，提案不能引用未知 Gap。
- `SubmitClarificationRequest` 要求非空答案、每问题最多回答一次、expected revision 和 command ID。Runner 要求本批次所有阻塞问题恰好各答一次，选项必须属于问题，或提供非空自定义答案。
- 创建 Run 返回 `awaiting_clarification`、无 PRD、仅有 `submit_clarification` 命令；答案提交成功且 Gate 通过才返回 `prd_awaiting_approval` 和 PRD 草稿。
- 答案端点：`POST /api/runs/{run_id}/clarifications/answers`。旧 revision/越序/重复命令返回 409；答案不完整或选项无效返回 422；错误响应不会改变 Run。

## 失败与恢复策略

- 部分答案、未知问题/选项、旧 revision、重复 command ID、等待澄清时审批 PRD 均拒绝且保留原 Run 快照。
- 决策对象、完整新 Ledger、分析结果与新 Run 投影在锁内校验；全部构造成功后才替换内存状态并登记 command ID。
- 防重记录与 Run 同属单进程内存；服务重启后都丢失，不承诺持久化幂等。
- 用户身份未认证。Decision Evidence 能追溯本地 Run 中的显式答案命令和 revision，但不构成强身份或不可抵赖审计。
- 当前不支持 Gate 通过后修改决定；此时 PRD/TD/DeliverySpec 尚不存在下游失效问题。后续如允许改动已确认决定，必须引入 revision 绑定和派生产物失效语义，不能复用旧 Artifact。

## 测试与验收证据

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q`（`make verify` 中） | 0 | 75 项通过；TestClient 发出一条现有 httpx/Starlette deprecation warning |
| `.venv/bin/ruff check apps packages tests` | 0 | All checks passed |
| `.venv/bin/mypy apps packages/contracts/src packages/agent-kernel/src packages/speccraft/src` | 0 | 16 个源码文件无问题 |
| `npm --prefix apps/web run test` | 0 | 2 项通过 |
| `npm --prefix apps/web run build` | 0 | TypeScript 检查及 Vite 构建成功；bundle 大于 500 kB 有警告 |
| 独立 FastAPI TestClient 正常/失败路径脚本 | 0 | 正常：201 等待澄清 → 200 PRD 等待审批，Ledger 新增 5 条 Decision；失败：部分答案 422、旧 revision 409、重复命令 409、越序 PRD 审批 409；每次拒绝后 GET 与原响应完全相同 |

自动化负例还覆盖无来源 FACT、无 Decision Evidence、覆盖遗漏、未知 Gap、错误推荐 ID、空/重复答案、用户决定覆盖冲突事实及伪造快照来源证据。

## 已知限制与当前系统快照

- 使用阶段 02 的匿名 ExportFlow 样例和本地 Harness；Run、Ledger 和防重记录均是单进程内存数据。
- 用户自由文本不会被语义抽取到五个维度；当前策略对所有五维缺失提问。Fake Provider 的选项和推荐是固定示例，不代表真实模型或产品建议。
- 冲突检测只对同维度 claim 做 `strip().casefold()` 后精确比较，不能识别语义等价或复杂矛盾。
- API 没有用户认证；权限来自显式请求流程约束。
- `implementation-guide-24-lessons/03-fact-ledger-and-clarification.md` 导航所指的第 03、05、06 章课程原文未包含在本仓库或 `learning-assets/`，本阶段没有将其记为已读或验收证据。
- 完整检查 `make verify` 通过。Vite bundle 尺寸警告和 TestClient deprecation warning 未影响退出码。

## 下一阶段冻结契约

- `FactKind`、五个 `FactDimension`、SourceEvidence/DecisionEvidence 准入条件及 `FactLedger.authoritative_view` 的决定优先语义。
- CompletenessAnalyzer 的确定性与五维阻塞规则；它不调用模型，不通过推荐或自由文本推断解除 Gate。
- `ClarificationBatch` 对当前 blocking Gap 的完整问题覆盖；Proposal 推荐不得预选或自动成为 Decision。
- 澄清答案必须显式提交、完整覆盖阻塞问题、匹配 expected revision；内存内重复 command ID 拒绝且失败不产生部分状态变化。
- PRD 只可从 Gate 通过后的 Ledger 权威视图生成。澄清前不得生成 PRD；PRD/TD/DeliverySpec 的后续批准顺序仍遵循阶段 01 契约。
