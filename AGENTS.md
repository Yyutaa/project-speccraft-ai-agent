# SpecCraft AI Agent 协作约定

## 项目定位

本仓库是个人开发的 SpecCraft AI Agent 项目，目前处于工程脚手架阶段。Contract、Kernel、Workflow、Provider、数据库、Worker、质量闭环和 Codex 插件尚未实现。

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

- `apps/api/`：只提供健康检查和静态项目状态。
- `apps/web/`：只展示项目状态和八阶段路线。
- `apps/cli/`：只显示项目状态。
- `apps/worker/`：只说明 Worker 尚未实现。
- `packages/contracts/`：只保留包边界。
- `packages/agent-kernel/`：只保留包边界。
- `packages/speccraft/`：只保留包边界。
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

## 验证

基础验证：

```bash
make verify
```

涉及前端时额外关注浏览器中的真实状态和网络请求。
