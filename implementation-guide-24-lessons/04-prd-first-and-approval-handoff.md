# 阶段 04 Handoff：PRD-first 与审批冻结

## 目标与非目标

已实现从 Fact Ledger 权威视图构建 PRD Blueprint、读取版本化 PRD 编制包、生成确定性 PRD 草稿、基础结构检查、单章节修订，以及绑定 revision 和内容 SHA-256 的人工审批冻结。阶段 01 的 TD/DeliverySpec 内存演示仍在 PRD 批准后继续执行。

本阶段没有新增 TD 设计、Design Authority、Issue Ledger、自动 PRD 修复、LangGraph、真实模型、数据库、持久化 Kernel 或身份认证。PRD 内容是否符合业务仍由人判断。

## 选型理由

- 共享 Pydantic Contract 已在仓库中；Hash、章节替换、时间戳和锁使用 Python 标准库，无新增依赖。
- Blueprint 用确定性代码规划章节和 Fact ID 引用，确保每条权威事实至少被一个章节覆盖；它不写正文，也不增加独立 Gate。
- PRD Author 是最小 Protocol，当前 Fake 实现只把被引用的权威 claim 放进模板。模板、指南和自检均从 `learning-assets/authoring-pack/v1/prd/` 读取；没有把规则另抄成运行时代码中的 Prompt。
- 就绪检查只校验可复现的结构问题，不对正确性作伪判断；用户负责审批。当前同步内存 Runner 已足够承载这条路径，因此未引入 LangGraph。

## 模块边界

- `packages/contracts/src/deliveryflow_contracts/prd.py`：PRD 章节、Blueprint、Revision、Readiness、修订请求和审批 receipt 的公开数据约束。
- `packages/contracts/src/deliveryflow_contracts/runs.py`：Run 中 PRD 规划、修订历史、当前草稿、就绪结果和审批证据的状态不变量；只有未批准 PRD 可修订。
- `packages/speccraft/src/deliveryflow_speccraft/prd.py`：从 Ledger 权威 Fact 构建 Blueprint；结构就绪检查；精确替换一个 H2 章节正文。
- `packages/speccraft/src/deliveryflow_speccraft/prd_authoring.py`：编制包读取、最小 Author Port 和确定性 Fake PRD Author。
- `packages/speccraft/src/deliveryflow_speccraft/runner.py`：同步内存编排；在锁内完成修订和审批的版本校验、全量 Run 校验，再原子替换内存快照。
- `apps/api/main.py`：公开 PRD 修订与审批端点，映射稳定错误码。
- `apps/web/src/api.ts`、`App.tsx`：展示服务端章节、当前版本/Hash、就绪结果和审批证据；发送用户选择的章节、正文、反馈、审批人和理由。

## 状态与数据流

```text
来源快照 + 只读仓库上下文
  → Ledger 权威视图 + 五维 Completeness Gate
  → 用户回答解除 blocking Gap
  → Blueprint（章节、适用性、全部权威 Fact ID 引用；无正文）
  → Authoring Pack + Fake PRD Author → PRD r1 + SHA-256
  → 基础结构检查 → prd_awaiting_approval
  → 用户指定章节与反馈 + 当前 revision/hash → PRD r2 + 新 Hash + 重检
  → 用户提交 actor/rationale + 当前 revision/hash → 审批 receipt，PRD 冻结
  → 沿用阶段 01 的 TD 内存演示
```

Run 只持有一份当前可写 PRD 草稿；旧 revision 保存在内存修订历史中，不能用于审批。Ledger 是需求事实源，Blueprint 是结构投影，PRD Revision 是文档内容事实，Readiness 是确定性检查结果，receipt 是用户审批事实。前端没有计算 Hash、就绪状态或状态转换。

## 公开 Contract

- `PrdBlueprint` 固定为编制包的八个 H2 章节顺序，包含 `ledger_revision`、权威 Fact ID 集合和各章节的适用性/引用；所有权威 Fact ID 必须被覆盖，不能引用非权威 ID。
- `PrdRevision` 包含连续 revision、完整内容、精确 UTF-8 SHA-256、可选的变更章节和用户反馈。Run 的 `prd_revisions[-1]` 必须等于当前 `prd_draft`。
- `PrdReadiness` 绑定同一个 revision/hash，问题码覆盖缺标题、缺章、重复章、额外章、顺序错误、空章和占位符。仅在无问题时提供 `approve_prd` 命令；`revise_prd` 始终是待批准 PRD 的可用命令。
- `POST /api/runs/{run_id}/prd/revisions` 接收 `expected_revision`、`expected_content_hash`、`section_id`、`replacement_body`、`feedback`；只允许替换指定章节正文，拒绝正文中新增 Markdown 标题。
- `POST /api/runs/{run_id}/approvals/prd` 接收 `revision`、`content_hash`、`actor`、`rationale`；成功 receipt 增加 `approved_at` 并与当前草稿版本和 Hash 一致。批准后无 PRD 修订命令，后续修订返回 409。
- 缺失 Run 为 404；旧 revision、错误 Hash、非法阶段或就绪检查未通过为 409；非法局部修订为 422。请求模型字段缺失或格式不合法由 FastAPI 返回 422。

## 失败与恢复策略

Runner 在同一锁内比较当前 revision/hash、执行单章替换、重新计算 Hash/就绪结果并完整验证 Run，然后才替换内存状态。旧 revision、错误 Hash、跨章节修改、未就绪审批和批准后修改都不能留下部分状态。用户可读取当前 Run 后，以最新 revision/hash 重新提交合法命令。进程重启后内存 Run 和修订历史丢失，没有跨进程恢复或持久化幂等保证。

## 测试与验收证据

| 步骤与命令 | 退出码 | 关键结果 |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q tests/test_prd_contracts.py` | 0 | 5 项通过；此前先见到导入失败，随后建立公开 Contract |
| `.venv/bin/python -m pytest -q tests/test_prd_blueprint.py tests/test_prd_contracts.py` | 0 | 6 项通过；Blueprint 覆盖与 Contract 约束 |
| `.venv/bin/python -m pytest -q tests/test_prd_authoring.py` | 0 | 3 项通过；编制包读取、模板章节及 Fake Author |
| `.venv/bin/python -m pytest -q tests/test_prd_readiness.py` | 0 | 3 项通过；结构就绪检查正反例 |
| `.venv/bin/python -m pytest -q tests/test_prd_revision_runner.py` | 0 | 3 项通过；局部修订、审批冻结、旧版本/错误 Hash/未就绪负例 |
| `.venv/bin/python -m pytest -q tests/test_run_api.py` | 0 | 11 项通过；新端点正常、Hash 冲突、跨章节标题注入和冻结后修改均有断言 |
| `.venv/bin/python -m pytest -q tests/test_in_memory_runner.py` | 0 | 7 项通过；旧调用方迁移至双绑定审批 |
| `.venv/bin/python -m pytest -q tests/test_run_contracts.py` | 0 | 7 项通过；Run 投影与审批版本约束 |
| `npm --prefix apps/web test -- --run -t 'submits one PRD'` | 0 | 局部修订页面测试通过；先前失败用于定位章节选择交互，改为原生 select |
| `make verify` | 0 | Python 93 项通过；Ruff 通过；mypy 19 文件通过；前端 5 项通过；Vite 构建通过 |
| 独立 FastAPI TestClient 操作序列 | 0 | Run `956aa454-a82f-4077-9df2-ea8407c50ef4`：等待澄清 → PRD r1 → 局部修订 r2 → 人工批准；receipt Hash `7fc46e15891bb741b3b9f57af05f925b48fc3d1efe54174a513c2f42773546ad`；旧 r1 审批 409、批准后修改 409，失败前后 GET 快照完全相同 |
| 本地 Uvicorn `127.0.0.1:8766` + 标准库 HTTP 请求脚本 | 0 | Run `ccd1af54-f696-4cc7-9225-23767bfbdb3d`：201 创建 → 200 澄清 → 200 PRD r2 → 旧 r1 审批 409 → 当前 r2 审批 200 → 冻结后修订 409；GET 快照与批准响应一致。receipt Hash `e673a5820084d07ec6f7af60ab6d3d0103ec3efdeef0b5eb139dce7e1b427243` |

自动化还覆盖 Blueprint 缺引用/错误引用、模板章节不匹配、占位符/缺章、错误 Hash、旧 revision、重复审批及越序审批。`make verify` 中 TestClient 发出既有 httpx/Starlette deprecation warning；Vite 对单一 bundle 大于 500 kB 发出 warning，退出码均为 0。

首次实际 HTTP 验收脚本使用环境默认 `urllib` opener，读取响应时出现 `JSONDecodeError`（退出码 1）；紧接着 `curl` 对同一端点确认 201 和完整 JSON。归因于验收脚本的本地 HTTP 适配层；改为 `ProxyHandler({})` 的直接本地请求后整条正反路径通过，没有修改产品实现。浏览器手工操作 **NOT RUN**：计算机 UI 工具在获取标签状态时超时；前端行为由 5 项组件测试、类型检查与构建验证，不能据此声称已完成浏览器人工验收。

## 已知限制与当前系统快照

- Run、PRD 修订历史和审批都只在单个 API 进程内；服务重启清空。没有身份认证，`actor` 是用户提交的文本，不是强身份凭证。
- Fake Author 只把 Ledger claim 填入模板，不保证 PRD 业务质量；没有相关 Fact 的章节会明确写“本节没有额外的已确认事实”。基础检查通过不等于业务正确。
- 局部修订正文来自用户且记录反馈；本阶段未把修订内容反向抽取成 Ledger Fact，也没有自动判断其与权威事实是否语义冲突。人工审批承担内容判断。
- 当前前端只展示最新 PRD 正文和审批证据，Run 响应保留全部内存修订历史；无持久化或历史版本对比 UI。
- 第 07–10 章课程路径在当前仓库中不存在；用户明确指示无需继续查找必读资料，按确认步骤执行。本 Handoff 不将课程原文记为已读。
- 阶段 01 旧 TD Fake 演示仍存在，但本阶段没有实现新的 TD 设计、验证或质量循环。

## 下一阶段冻结契约

- Blueprint 固定章节顺序、权威 Fact ID 全覆盖、不含正文或独立 Gate；PRD 只从 Completeness Gate 通过后的 Ledger 权威视图派生。
- Author Port 与版本化编制资源分离；基础检查限于结构、空内容、顺序与占位符，不自动修改文档或判断业务正确性。
- PRD 局部修订只改一个章节，每次成功形成新 revision 和精确内容 SHA-256，并使旧 revision/hash 失效。
- PRD 审批必须由独立人工命令形成绑定 revision、Hash、actor、rationale、时间的 receipt；批准后 PRD 不可变，TD 不得回写它。
- 当前状态的唯一权威是后端 Run；前端只渲染服务端投影和 `available_commands`，错误命令不留下部分更新。
