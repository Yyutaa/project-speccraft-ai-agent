# 阶段 02 Handoff：可信输入与 Engineering Harness

## 目标与非目标

已实现以来源、内容 SHA-256、读取状态与权限信息描述 Run 输入，并从匿名 ExportFlow 样例构造有界、可审计的只读工程上下文。目标仓库不接受写操作。

本阶段不实现 Fact Ledger、知识检索、澄清问题、数据库、真实模型 Provider、全仓索引、跨进程恢复或任意本机仓库授权。

## 选型理由

- Pydantic v2 已是共享 Contract 依赖；Path、文件描述符、UTF-8、JSON 稳定序列化和 SHA-256 使用 Python 标准库。
- 服务端只绑定匿名样例仓库，避免让请求体自行授权本机根目录。
- 显式静态文件集合确保 Context Slice 可复现且不会把全仓文本装入上下文。
- 读取使用目录文件描述符逐段打开并禁止跟随符号链接；不通过路径字符串检查后再无保护地打开文件。
- 不新增运行时依赖。

## 模块边界

- `packages/contracts/.../context.py`：Source、Snapshot、RepositoryBinding、ContextEntry、HarnessContextSlice 和模式/状态；校验来源内容 Hash、相对规范路径及切片 Hash。
- `packages/speccraft/.../repository_context.py`：只读路径校验、大小/文本过滤、需求快照、模式选择、来源理由与 Context Slice Hash。
- `packages/speccraft/.../runner.py`：先构造输入上下文，再以需求正文调用 Fake Provider；存入 Run 的来源快照与 Harness 投影。
- `apps/api/main.py`：将服务端样例根目录绑定给 Harness，并把读取拒绝映射为结构化 HTTP 错误。
- `apps/web/src/api.ts` 与 `App.tsx`：按 API 返回内容显示来源、权限、模式、选择理由和 Hash，不自行推导或修改。

## 状态与数据流

1. `POST /api/runs` 接收且只接收一种需求来源：原始内联 `requirement` 或样例仓库相对路径 `requirement_path`。
2. 文件需求限定在 `requirements/**/*.md`（含 `requirements/` 直属文件）。原始 UTF-8 字节被读取、Hash 并保存；PRD 生成时才对正文 `strip()`。
3. 服务端固定绑定 `examples/speccraft/repositories/exportflow-sample`，权限为 `read_only`。
4. `GUIDE_ONLY` 选择 `AGENTS.md`、`README.md`；`INDEXED_READONLY` 在此基础上选择 `.deliveryflow/repository.yaml`、`package.json`、`pyproject.toml`。列表和顺序固定。
5. Harness 逐文件读取并生成有来源 Hash 和选择理由的 Context Slice。切片 SHA-256 对按固定顺序排列的 `{path, sha256, selection_reason, content}` JSON（UTF-8、无空格、非 ASCII 原样输出）计算。
6. 任一读取失败时，Run 不保存。成功后 Run 同时保存需求来源快照、仓库绑定、Context Slice 与阶段 01 状态。

仓库规则仅作为工程上下文，不传入 Fake Provider 的 PRD 需求参数，也不升级为产品 Fact。

## 公开 Contract

- `CreateRunRequest`: `requirement` 与 `requirement_path` 必须且只能提供一个；`context_mode` 为 `guide_only` 或 `indexed_readonly`。
- `SourceSnapshot`: 来源类型、来源路径、规范化根内相对路径、成功读取状态、原始文本、与文本一致的 64 位小写 SHA-256。
- `RepositoryBinding`: 仓库 ID、服务端绑定根目录、固定 `read_only` 权限和上下文模式。
- `HarnessContextSlice`: 有序 ContextEntry 列表，每项包含 Snapshot 和选择理由；Contract 会校验切片 SHA-256。
- `HarnessErrorCode`: 稳定的路径、读取、文本类型和大小拒绝码；API 只映射 HTTP 状态，不改变错误码。
- `RunResponse`: 原阶段 01 Run 投影，加上 `source_snapshot`、`repository_binding`、`harness_context`。

## 失败与恢复策略

拒绝码包括 `invalid_source_path`、`path_outside_root`、`path_not_allowed`、`symlink_not_allowed`、`source_not_found`、`source_unreadable`、`unsupported_file`、`file_too_large`、`context_too_large`、`empty_requirement` 和 `repository_not_allowed`。API 分别映射到 403、404、413、415 或 422；路径安全检查和单文件大小检查在正文读取前完成，总上下文大小则在有限的固定文件集读取后校验。Run 创建失败时不写入半成品，调用方可修正来源后重新创建；无持久化恢复语义。

读取边界包含：根内相对 POSIX 路径与穿越校验、逐段拒绝符号链接及基于目录描述符的 no-follow 打开、敏感/缓存目录与敏感文件拒绝、固定文本扩展名与 UTF-8/NUL 校验、每文件 64 KiB 和 Context Slice 128 KiB 上限。

## 测试与验收证据

最终执行结果：

| 命令 | 退出码 | 结果 |
| --- | ---: | --- |
| `make verify` | 0 | Python 45 项通过；Ruff 通过；mypy 14 个源码文件无问题；Web 2 项通过；Vite 构建成功 |
| `.venv/bin/python` + FastAPI `TestClient` 正常/穿越路径手工请求 | 0 | 正常 201 返回来源与 5 条索引切片；穿越请求 403 `path_outside_root` |
| `.venv/bin/python` + 临时仓库符号链接手工探测 | 0 | 拒绝码 `symlink_not_allowed`，未返回快照 |

`make verify` 的 Vite 构建提示 bundle 大于 500 kB；这是既有依赖 bundle 警告，不影响退出码。Python TestClient 依赖发出 httpx deprecation warning。

自动化覆盖稳定文件 Hash、稳定切片 Hash、两种模式、PRD 与工程约束隔离、路径穿越、绝对路径、符号链接（文件和父目录）、敏感/缓存目录、超大文件、非 UTF-8/NUL 文本及总上下文上限。API 测试验证正常来源投影和根外拒绝码。前端测试验证页面只显示 API 提供的模式、路径、选择理由及 Hash。

## 已知限制与当前系统快照

- 唯一可绑定目标仓库是匿名 ExportFlow 夹具；API 不接受任意根路径或仓库 ID。
- 夹具目前只有指南、需求和项目清单，没有业务源码；索引结果不代表对真实实现代码的理解。
- Run 和快照仍只存在于 API 单进程内存中；进程重启会丢失。
- 来源 Hash 只冻结读取到的文件文本，不是仓库整体原子快照，也不验证需求内容真假。
- 没有真实 Provider 或内容质量评估。
- 课程导航第 04 章本轮未能从课程页面读取，实施者未将其作为已读或测试证据。

## 下一阶段冻结契约

- 客户端输入路径永远不能授权或扩大服务器允许根目录；根目录绑定必须由服务端信任配置提供。
- 目标业务仓库只读；Harness 不修改产品需求，也不把工程规则提升为已确认 Fact。
- `SourceSnapshot` 的 SHA-256 对读取的原始 UTF-8 内容计算；需求整理不能改写快照。
- `HarnessContextSlice` 只包含显式选择、有限大小、有来源 Hash 与选择理由的文本；切片 Hash 保持有序规范序列化语义。
- `GUIDE_ONLY` 和 `INDEXED_READONLY` 是显式模式；过滤、拒绝码和上限不得静默放宽。
