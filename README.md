# SpecCraft AI Agent

SpecCraft 是一个个人开发项目，用于探索本地优先、契约驱动的 AI 需求分析与研发规格编制。目标是把需求整理为经过人工确认的 `PRD.md`、`TD.md` 和机器可读的交付规格。

当前仓库仍是教学脚手架，完整领域工作流正在逐步实现。Run 从可信来源和只读仓库上下文开始，经 Fact Ledger、确定性五维完整度 Gate 与人工澄清后，构建覆盖全部权威事实的 PRD Blueprint。确定性 Fake PRD Author 按版本化模板生成草稿；用户可局部修订，再按 revision 与内容 SHA-256 审批冻结。阶段 01 的 TD/DeliverySpec 内存演示继续保留。系统不具备持久化、跨进程恢复、身份认证或真实内容质量保障。

## 当前内容

- React 19、Vite、TypeScript 与 Ant Design 前端壳；
- FastAPI 健康检查、项目状态与最小 Run/审批 API；
- Pydantic Run 请求和响应 Contract；
- Fact/Decision 证据 Contract、Completeness Analyzer、澄清 Batch 与回答 API；
- PRD Blueprint、版本化草稿、局部修订、基础文档就绪检查与绑定内容 Hash 的人工审批；
- 来源快照与只读 Repository Harness：服务端仅绑定匿名 ExportFlow 样例，支持 GUIDE_ONLY / INDEXED_READONLY；
- `speccraft` 中的单进程内存 Runner 与确定性 Fake Provider；
- `contracts`、`agent-kernel`、`speccraft` Python 包；
- CLI 和 Worker 入口；
- 匿名需求、仓库样例与 PRD/TD 编制资源；
- 前端和后端的基础验证入口。

当前 Run 演示支持内联需求或样例仓库需求文件创建、读取、澄清回答、PRD 局部修订、批准 PRD、批准 TD。来源文本以快照 Fact 入账；由于没有事实抽取模型，无法确定性归类到角色、流程、权限、失败和验收维度的自由文本会触发五个澄清问题。回答以 Decision Evidence 入账；冲突来源事实由同维度用户决定在权威视图中覆盖。PRD 仅在 Gate 通过后生成。Blueprint 引用所有权威 Fact ID，不含正文；基础检查仅判断文档结构、空内容和占位符。局部修订需要当前 revision、内容 Hash、章节和反馈；审批还需要审批人及理由，并冻结精确版本。批准后才生成 TD，TD 批准后才生成 DeliverySpec。进程重启会清空全部 Run；澄清命令在单进程内以 command ID 防重，PRD 修订和审批通过 revision 与 Hash 拒绝过期或越序操作。

## 计划中的能力

- 以共享 Contract 定义稳定输入、产物和阶段结果；
- 实现持久化 Run、Artifact、审批与恢复；
- 完整 PRD/TD Workflow 与质量闭环；
- 增加 Provider 驱动的 API 与 Workbench；
- 探索 Codex Skill 驱动的本地执行入口。

计划能力尚未在当前脚手架中实现。CodePilot、QualiFlow 和跨阶段 Supervisor 不属于当前范围。

## 项目结构

```text
apps/                 API、CLI、Web 与 Worker 入口
packages/contracts/   契约包边界
packages/agent-kernel/共享运行内核包边界
packages/speccraft/   SpecCraft 领域包边界
examples/speccraft/   匿名需求与仓库样例
learning-assets/      PRD/TD 编制资源
scripts/              本地启动脚本
```

## 启动

需要 Python 3.12 和 Node.js 20+。在仓库根目录运行：

```bash
scripts/start-scaffold.sh
```

脚本会创建 `.venv`、安装 Python 包和前端依赖，并启动 API 与 Web。端口被占用时会尝试后续可用端口。

也可以分别启动：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'packages/contracts[dev]' -e packages/agent-kernel -e packages/speccraft
npm --prefix apps/web install
.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8765
npm --prefix apps/web run dev
```

## 验证

```bash
make verify
```

也可以单独运行前端检查：

```bash
npm --prefix apps/web run test
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
```

## 设计边界

- 本地运行数据和用户凭据不应提交到版本库；
- 需求仓库作为受控上下文，规格产物由明确的审批步骤确认；
- 领域流程由后端负责，前端负责交互和结果呈现；
- 只有当前阶段明确需要时才引入数据库、模型适配器或后台执行能力。
