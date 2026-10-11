# 阶段 01 Handoff：跑通内存版 Happy Path

## 目标与非目标

阶段 01 已交付最小可观察流程：一句话需求创建 Run，确定性 Fake Provider 生成 PRD；用户单独批准 PRD 后生成 TD；用户批准 TD 后创建 DeliverySpec。Web 页面通过 FastAPI 命令与查询接口展示服务端响应。

本阶段没有实现 SQLite、迁移、LangGraph、真实 Provider、Worker、SSE、自动质量循环、Codex 插件、正式文件导出或多用户身份认证。DeliverySpec 当前是内存响应对象，不是已发布文件。

## 选型理由

- Pydantic v2 已是后端依赖，直接用于公开请求/响应模型和不变量校验；没有增加 Python 或 npm 依赖。
- FastAPI 是现有 API 框架，直接暴露最小 Run 命令和查询。
- 单个进程内字典足以演示本阶段状态转换；`threading.Lock` 保护每次读取/更新，API 同步执行。该存储明确不提供跨进程恢复。
- Fake Provider 直接格式化固定文本。相同需求产生相同 PRD/TD 草稿，不访问模型或网络。
- Web 使用现有 React、TypeScript 和 Ant Design；页面从 Run 响应读取状态、草稿、批准记录、DeliverySpec 和 `available_commands`，不乐观推进状态。

## 模块边界

```text
apps/web (输入与响应投影)
   │ HTTP
apps/api (FastAPI DTO 路由、错误映射、进程组合根)
   │
packages/speccraft (FakeProvider + InMemoryRunner + PRD-first 转换)
   │
packages/contracts (Pydantic 请求、状态、审批、产物响应)
```

`agent-kernel`、CLI、Worker、匿名样例与领域资源没有承担 Run 状态职责。阶段路线 `/api/scaffold` 仍为静态产品契约。

## 状态与数据流

```text
POST /api/runs
  → prd_awaiting_approval (PRD 草稿、approve_prd)
POST /api/runs/{id}/approvals/prd {revision}
  → td_awaiting_approval (PRD Approval、TD 草稿、approve_td)
POST /api/runs/{id}/approvals/td {revision}
  → completed (TD Approval、DeliverySpec、无后续命令)
```

TD 只在 PRD 批准成功后创建。DeliverySpec 只在 TD 批准成功后创建，绑定同一 Run 的 PRD/TD revision 和内容。失败命令在状态校验及 revision 校验通过前不会写入更新。

## 公开 Contract

Pydantic 类型位于 `packages/contracts/src/deliveryflow_contracts/runs.py`。

- `CreateRunRequest`: `{ "requirement": string }`，修剪首尾空白，空白需求返回 422。
- `ApprovalRequest`: `{ "revision": integer >= 1 }`。
- `RunResponse`: `run_id`、`requirement`、三态之一的 `status`、版本化 PRD/TD 草稿、审批记录、可空 DeliverySpec 和 `available_commands`。模型校验状态、Gate、版本与 DeliverySpec 关联。
- `POST /api/runs` 返回 201；`GET /api/runs/{run_id}` 返回 200。
- `POST /api/runs/{run_id}/approvals/prd` 与 `/approvals/td` 返回更新后的 Run。
- Run 不存在返回 404 `run_not_found`；非法顺序返回 409 `invalid_run_transition`；revision 不匹配返回 409 `revision_conflict`；请求格式错误返回 422。

创建命令没有幂等键：重试创建可能产生第二个 Run。审批命令不是幂等操作；已完成相同审批再次提交会因状态不匹配返回 409。GET 可重复读取当前进程内快照。

## 失败与恢复策略

阶段 01 的恢复能力只有同一进程内对 Run 的再次 GET。启动新 API 进程会清空存储，不提供恢复或持久化承诺。提前批准 TD、重复批准、未知 Run 和错误 revision 均明确拒绝；测试检查拒绝前后快照相等。Web 请求失败时展示错误并保留最后一次成功 Run 响应。

当前 API 不做用户身份认证；“人工审批”表示必须由独立 API 命令触发，不构成多用户审计或身份归属保证。

## 测试与验收证据

| 检查 | 命令 | 退出码与结果 |
| --- | --- | --- |
| Contract | `.venv/bin/python -m pytest tests/test_run_contracts.py -q` | 0；4 passed |
| Runner | `.venv/bin/python -m pytest tests/test_run_contracts.py tests/test_in_memory_runner.py -q` | 0；11 passed |
| API | `.venv/bin/python -m pytest tests/test_run_api.py tests/test_run_contracts.py tests/test_in_memory_runner.py -q` | 0；18 passed，1 Starlette/httpx deprecation warning |
| Scaffold projection | `.venv/bin/python -m pytest tests/test_scaffold_api.py -q` | 0；3 passed |
| Web projection | `npm --prefix apps/web run test -- src/App.test.tsx` | 0；2 passed（创建/完整审批；409 后保持旧状态） |
| 全自动化关 | `make verify` | 0；后端 22 passed，Ruff、Mypy、Web 2 passed、TypeScript 与 Vite build 成功 |
| 启动脚本 | `scripts/start-scaffold.sh` | API 8765、Web 5174 成功监听；手工验收后 Ctrl+C 停止，shell session 退出码 130（预期中断） |

基线 `make verify` 在实现前运行并通过（退出码 0）。基线脚手架的 `scripts/start-scaffold.sh` 未在修改前单独启动；只验证了本阶段实现后的启动结果。该初始启动检查为 NOT RUN。

浏览器手工验收（Codex in-app browser，`http://127.0.0.1:5174/`）：输入“浏览器验收：问候页面”，点击“创建 Run”后可见 Run ID、`等待 PRD 人工审批` 和 PRD；点击“批准 PRD”后可见 `等待 TD 人工审批` 与 TD；点击“批准 TD”后可见 `已完成`、两条批准记录和含 PRD/TD revision 的 DeliverySpec。

API 失败/冲突手验使用本机 `127.0.0.1:8765`：先创建后立即批准 TD，返回 409 `invalid_run_transition`，随后 GET 等于创建快照，状态仍为 `prd_awaiting_approval`；批准 PRD 后以 revision 99 批准 TD，返回 409 `revision_conflict`，GET 等于批准 PRD 响应，状态仍为 `td_awaiting_approval`。再以当前 TD revision 批准返回 200 `completed`。第一次手验脚本因本机代理对 `urllib` loopback 请求返回 502 失败；客户端用标准库 `ProxyHandler({})` 禁用代理后重跑通过。API 本身另经 `curl` 健康检查 200、创建 Run 201 确认。

`make verify` 的 Vite build 提示打包 JS chunk 超过 500 kB；构建退出码仍为 0。后端测试有一条现有 Starlette/httpx deprecation warning，未为此引入依赖。

## 已知限制与当前系统快照

- Run、草稿、Approval 和 DeliverySpec 仅在一个 API 进程内存中；重启丢失。
- 请求在 API 进程同步执行；没有 Worker、排队或进度事件。
- Fake Provider 的草稿仅用于流程教学，内容质量未经验证。
- CreateRun 重试会创建新 Run；没有身份认证或审批人身份审计。
- 当前公开状态为 `prd_awaiting_approval`、`td_awaiting_approval`、`completed`；版本从 1 开始。审批要求精确 revision。
- 阶段路线 API 与页面继续显示产品定义的八阶段静态路线；本阶段 Run Happy Path 不代表其他六个阶段已实现。

## 下一阶段冻结契约

后续工作必须保持 `CreateRunRequest`、`ApprovalRequest`、`RunResponse`、当前三个状态值、四个 API 路径和错误语义兼容。PRD 先批准，TD 只能从获批 PRD 派生；DeliverySpec 只能在 TD 批准后出现。审批必须继续是显式用户命令并绑定 revision；Web 状态与命令继续来自后端响应。阶段 01 没有承诺创建操作幂等、持久化格式、自动恢复、真实 Provider 或内容质量门槛。
