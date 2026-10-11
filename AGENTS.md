# SpecCraft AI Agent 协作约定

## 项目定位

本仓库是个人开发的 SpecCraft AI Agent 教学项目，目前处于分阶段实现阶段。当前包含共享 Run Contract、同步单进程内存 Runner、确定性 Fake Provider 与最小 PRD-first 审批 API；持久化、真实 Provider、完整 Workflow、Worker、质量闭环和 Codex 插件尚未实现。

按当前能力边界逐步开发，完成验收并记录可复现的证据。

## 开工前读取

1. 本文件；
2. `README.md`；
3. 涉及 Web 时读取 `DESIGN.md`；
4. 涉及 FastAPI 时读取 `.agents/skills/fastapi/SKILL.md`。

开始修改前运行 `git status --short --branch`，不要覆盖已有改动。

## 固定产品边界

目标能力是 P0 Contract、P1 Shared Kernel、P2 Provider-driven SpecCraft 与 P2.5 Codex Native。正式产物为：

```text
PRD.md
TD.md
DeliverySpec.json
```

面向用户的八阶段流程固定为：

```text
需求上下文构建
→ 需求澄清与决策
→ 产品规格设计
→ 产品规格验收
→ 技术方案设计
→ 技术方案验证
→ 技术方案验收
→ 交付物发布
```

PRD 必须先批准冻结，TD 不得回写已批准 PRD。模型不得代替用户批准 PRD、TD 或发布结果。

## 当前代码边界

- `apps/api/`：提供健康检查、静态项目状态以及内存 Run 的创建/读取/PRD 与 TD 审批 API。
- `apps/web/`：展示静态八阶段路线，并通过 API 创建、审批和观察一个 Run；状态与可用命令来自服务端响应。
- `apps/cli/`：只显示项目状态。
- `apps/worker/`：只说明 Worker 尚未实现。
- `packages/contracts/`：定义共享 Pydantic 请求、响应、Run 状态和产物契约。
- `packages/agent-kernel/`：只保留包边界。
- `packages/speccraft/`：包含最小内存 Runner 与确定性 Fake Provider，不实现持久化或完整 Workflow。
- `examples/speccraft/`：匿名输入样例，不是预期输出。
- `learning-assets/`：领域编制资源种子，不是运行时实现。

## 实现规则

- Python 3.12；生产代码使用类型注解。
- 后端按 `domain → application → ports/adapters → composition root` 单向依赖。
- 前端不复制 Workflow、Policy 或质量决策，只展示后端投影。
- 输入路径必须规范化并限制在允许根目录内。
- 优先使用标准库和已有依赖；新依赖必须对应明确需求。
- 不提交 `.venv/`、`node_modules/`、缓存、构建产物、数据库、`.env` 或模型凭据。
- 不提交真实业务 PRD、未脱敏日志、完整对话或模型推理过程。
- 非平凡状态转换、Gate、路径安全和 Artifact 行为必须有正例与负例测试。
- Agent 的完成声明不是证据；报告实际执行命令、退出码和结果。

## 契约、事实源与控制权

- 分层依赖保持单向：Execution Host → SpecCraft Domain → Shared Kernel → Contract；SpecCraft Domain 可直接依赖 Contract。Contract 定义共享数据协议，Kernel 提供通用生命周期机制，SpecCraft Domain 持有产品阶段规则，Host 负责组合入口和适配器。
- 后端领域/内核状态是 Run、Decision、Approval 与 Artifact 的权威事实源。前端只展示服务端投影；Snapshot 是读取投影，Checkpoint 是恢复材料，两者都不能取代或覆盖事实源。
- Source 只表明证据出处，不自动成为已确认 Fact。Fact 必须保留来源和确认状态；Decision 与 Approval 必须能追溯责任主体及其对象版本。
- 模型只提供语义候选、草稿或建议；确定性代码负责结构校验、Gate 和合法状态转换；用户负责产品/技术决策以及 PRD、TD 和发布批准。模型不得批准、发布或将候选直接升级为事实。
- PRD 获批后冻结；TD 只能基于获批 PRD 派生，不得回写 PRD。阶段越界、非法状态和版本冲突必须明确拒绝且不得留下部分状态变化，并由正例与失败用例覆盖。
- 阶段 01 冻结的流程顺序是先批准 PRD，再生成/批准 TD，最后发布 DeliverySpec；阶段 01 可采用内存实现，但不得声称内存状态可跨进程恢复。
- 阶段 01 的 Runner 只保存在单个 API 进程内并同步执行；API 写操作不承诺幂等，Approval 必须绑定正在批准的草稿 revision，重复或越序审批应拒绝且不得改变 Run。
- Fake Provider 只生成可重复的示例草稿，不代表模型能力或内容质量验证；页面不得乐观修改 Run 状态，只能渲染 API 返回值及其 `available_commands`。

## 验证

基础验证：

```bash
make verify
```

涉及前端时额外关注浏览器中的真实状态和网络请求。
