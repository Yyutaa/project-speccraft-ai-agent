# 阶段 00 技术方案与 Handoff

## 目标与非目标

阶段 00 仅冻结 SpecCraft 的四层责任、八阶段产品契约、核心对象语义、人工控制权和阶段 01 最小接口语义。唯一产品交付是文档。

不实现 Run、Artifact、审批服务、Workflow、数据库、LangGraph、Provider、Artifact Store、Worker、插件或新的 API；不改变首页交互或增加依赖。

## 选型理由

使用 Markdown 表格和 Mermaid-free 文本责任图，直接与现有指南、`AGENTS.md` 和证据模板协作。当前任务没有运行时行为，不需要新框架、Schema 包或文档生成依赖。阶段 01 接口是冻结语义草案，字段细节由阶段 01 的公开 Contract 和正反例测试确定。

## 模块边界

责任图及职责详见[阶段 00 契约设计结果](00-agent-contract-and-scaffold.md#契约设计结果)。冻结的单向依赖为：

```text
Execution Host → SpecCraft Domain → Shared Kernel → Contract
                         └────────────────────────→ Contract
```

Contract 定义共享协议；Kernel 承担通用生命周期机制；SpecCraft Domain 负责产品阶段语义；Execution Host 组合入口和适配器。当前仅存在静态 FastAPI 与 React 外壳，以上业务分层是目标契约，不是现存实现。

本阶段新增的 `00-agent-contract-and-scaffold.md` 与 Handoff 已通过 `.gitignore` 精确例外纳入变更；课程目录其余本地资料仍保持忽略，不扩大为整目录公开。

## 状态与数据流

目标产品流程为八阶段契约表中的顺序：来源和上下文形成证据，用户确认的事实/决策支撑 PRD 草稿；用户批准具体 PRD 版本后才允许设计 TD；技术验证产生与版本关联的证据；用户批准 TD 后才允许发布正式交付物。

Source 提供出处；Fact 保留确认状态与来源；Decision/Approval 记录人的选择和批准；Run 承载一次流程状态；Artifact 承载有版本身份的内容；Snapshot 是读取投影；Checkpoint 仅用于恢复。快照与恢复状态都不能替代事实源。当前均无相应运行时状态或持久化。

## 公开 Contract

当前唯一 HTTP Contract 仍为：

- `GET /api/health`：返回服务健康状态。
- `GET /api/scaffold`：返回静态项目能力说明和八阶段列表。

没有 Run API。阶段 01 的接口草案见阶段指南，覆盖创建/读取 Run、独立批准 PRD/TD、服务端状态投影及无效输入、不存在资源、非法状态和版本冲突的拒绝语义。批准权归用户；模型不能批准；失败命令不得产生部分状态推进。

## 失败与恢复策略

阶段 00 只定义契约，不存在业务状态转换可供运行。阶段 01 应把非法 Gate、错误资源和版本冲突作为负例，验证操作被拒绝且状态不变。阶段 01 明确采用进程内存和同步执行，不承诺进程重启恢复；不得假称 Checkpoint、Snapshot 或模型自然语言能恢复真实 Run。

若后续验收失败，应保留失败命令、退出码和最小错误信息，定位 Contract、状态转换、控制权、序列化、适配器、持久化、前端投影或测试夹具根因，再针对根因增加回归用例。此策略来自阶段提示词，本阶段没有实现对应自动化工具。

## 测试及验收证据

### 基线验证

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| 初次 `make verify` | 2 | 因 `.venv/bin/python` 不存在，在 pytest 前退出；没有测试运行 |
| `scripts/start-scaffold.sh` | 130（收到 Ctrl+C 后正常清理并退出） | 创建 `.venv`，安装仓库 Python 包及 Web 依赖；API 使用 `8765`，Web 因默认端口占用使用 `5174`；日志确认 API shutdown 完成 |
| `curl http://127.0.0.1:8765/api/health` | 0 / HTTP 200 | 返回 `status=ok` 和 `speccraft-project-scaffold` |
| `curl http://127.0.0.1:8765/api/scaffold` | 0 / HTTP 200 | 返回 8 个阶段，均为 `implemented=false` |
| `curl http://127.0.0.1:5174/` | 0 / HTTP 200 | Web 首页服务可用 |
| `curl http://127.0.0.1:5174/api/health` | 0 / HTTP 200 | Vite 代理可达健康 API |
| 环境就绪后 `make verify` | 0 | 3 个 Python 测试和 1 个 Web 测试通过；Ruff、Mypy、TypeScript 与 Vite build 通过 |

验证期间安装工具提示 npm 当前依赖树有 4 个 audit 漏洞（1 moderate、1 high、2 critical）；本阶段未运行 `npm audit` 深入分析或升级依赖，以遵守不改依赖边界。Python TestClient 输出一条 Starlette/httpx 弃用警告。

契约文档最小结构检查通过：包含四层责任、八对象、八阶段、阶段 01 成功与错误语义。自动化总验证仅证明当前脚手架能运行，不证明文档契约已有运行时实现。

### 手工验收

- **正常路径**：API 实际返回八阶段且全部标记未实现；首页服务和 API 代理返回 200。Chrome 浏览器实际渲染首页，显示“API 已连接”、八个阶段名称和顺序、全部“待实现”，并显示当前已保留/计划实现能力；页面没有创建/审批/发布按钮。与 API 返回逐项一致。
- **控制权失败路径**：契约表将 PRD 批准者限定为用户，并规定模型自动批准应被拒绝。当前没有审批 API，因此这是对规范的审查验证，不是运行时请求测试；模型自动批准的 HTTP 拒绝验收 **NOT RUN**（当前无审批 API），阶段 01 才能增加相应可执行正反例。

## 当前系统快照

- FastAPI 仅有 `GET /api/health` 和 `GET /api/scaffold`。
- React 读取健康状态与静态脚手架说明，显示八阶段，不提供业务按钮。
- `contracts`、`agent-kernel`、`speccraft` 仅保留包边界；没有 Run、Artifact、模型或数据库。
- 脚手架启动后，本地生成了被忽略的 `.venv/` 和 `apps/web/node_modules/`；没有运行时依赖文件被阶段 00 文档变更修改。
- `/api/scaffold` 和页面的八阶段为静态路线，不是工作流状态。

## 已知限制

- 第 25 章术语附录文件在仓库中不存在；本阶段依靠第 01、02 章及指南语境定义对象。
- 阶段 01 草案冻结最少行为和失败语义，不冻结最终字段级 JSON Schema；后续应由 Contract 正例/负例验证字段。
- 当前没有业务接口，所以“模型自动批准被拒绝”不能做 HTTP 运行时验收。
- 验证工具安装报告了 npm audit 漏洞和 Starlette/httpx 弃用提示；未改依赖或做安全升级。

## 下一阶段冻结契约

阶段 01 必须保持八阶段名称/顺序、四层依赖方向、PRD-first、人工审批权和正式产物名称 `PRD.md`、`TD.md`、`DeliverySpec.json`。CreateRun 的最小输入是用户需求文本；服务端是 Run 状态权威；审批为独立用户命令并绑定具体草稿版本；PRD 未批准不得产生 TD，TD 未批准不得发布 DeliverySpec；拒绝的命令不得改变状态。阶段 01 限定为单进程内存、同步执行、确定性 Fake Provider，不引入持久化、Worker、真实 Provider、SSE、质量循环或插件。
