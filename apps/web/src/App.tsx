import { CheckCircleOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { Alert, Button, Card, ConfigProvider, Input, Spin, Tag } from "antd";
import { useEffect, useState } from "react";

import { api, Run, Scaffold } from "./api";

const statusLabels: Record<Run["status"], string> = {
  prd_awaiting_approval: "等待 PRD 人工审批",
  td_awaiting_approval: "等待 TD 人工审批",
  completed: "已完成",
};


export default function App() {
  const [scaffold, setScaffold] = useState<Scaffold | null>(null);
  const [requirement, setRequirement] = useState("");
  const [run, setRun] = useState<Run | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([api.health(), api.scaffold()])
      .then(([, scaffoldResponse]) => setScaffold(scaffoldResponse))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "无法连接脚手架 API");
      });
  }, []);

  async function perform(action: () => Promise<Run>) {
    setBusy(true);
    setRunError(null);
    try {
      setRun(await action());
    } catch (reason) {
      setRunError(reason instanceof Error ? reason.message : "请求失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#073d35",
          borderRadius: 4,
          colorText: "#1f2423",
        },
      }}
    >
      <header className="site-header">
        <strong>SpecCraft</strong>
        <Tag>Project scaffold</Tag>
      </header>
      <main>
        <section className="hero">
          <p className="eyebrow">个人开发项目</p>
          <h1>构建本地优先的 AI 规格编制工具</h1>
          <p className="hero-copy">
            从确定性内存演示开始：先审阅并批准 PRD，再审阅 TD，最后生成 DeliverySpec。持久化、真实模型和完整工作流仍未实现。
          </p>
          {error ? (
            <Alert type="error" showIcon message="API 未连接" description={error} />
          ) : scaffold ? (
            <div className="connection-status">
              <CheckCircleOutlined /> API 已连接
            </div>
          ) : (
            <div className="connection-status pending"><Spin size="small" /> 正在连接 API</div>
          )}
        </section>

        {scaffold && (
          <>
            <section aria-labelledby="run-title" className="run-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">In-memory demonstration</p>
                  <h2 id="run-title">跑通规格审批</h2>
                </div>
                <p>草稿由确定性 Fake Provider 生成；审批由你明确提交。</p>
              </div>
              <Card>
                <label htmlFor="requirement">一句话需求</label>
                <Input.TextArea
                  id="requirement"
                  aria-label="一句话需求"
                  value={requirement}
                  onChange={(event) => setRequirement(event.target.value)}
                  placeholder="描述你希望构建的产品"
                  rows={3}
                  disabled={busy || run !== null}
                />
                {!run && (
                  <Button
                    type="primary"
                    className="run-action"
                    disabled={!requirement.trim()}
                    loading={busy}
                    onClick={() => void perform(() => api.createRun(requirement))}
                  >创建 Run</Button>
                )}
                {runError && <Alert className="run-error" type="error" showIcon title={runError} />}
                {run && (
                  <div className="run-result" aria-live="polite">
                    <div className="run-status">
                      <span>Run {run.run_id}</span>
                      <Tag>{statusLabels[run.status]}</Tag>
                    </div>
                    <article aria-label="来源与只读工程上下文">
                      <h3>来源与只读工程上下文</h3>
                      <p>需求来源：{run.source_snapshot.normalized_path ?? "用户内联输入"}</p>
                      <code>需求 SHA-256 {run.source_snapshot.sha256}</code>
                      <p>仓库：{run.repository_binding.repository_id} · {run.repository_binding.permission}</p>
                      <p>只读工程上下文 · {run.repository_binding.context_mode}</p>
                      <code>上下文 SHA-256 {run.harness_context.sha256}</code>
                      <ul>
                        {run.harness_context.entries.map((entry) => (
                          <li key={entry.snapshot.normalized_path}>
                            <strong>{entry.snapshot.normalized_path}</strong>: {entry.selection_reason}
                            <br />
                            <code>SHA-256 {entry.snapshot.sha256}</code>
                          </li>
                        ))}
                      </ul>
                    </article>
                    <article>
                      <h3>PRD 草稿 · r{run.prd_draft.revision}</h3>
                      <pre>{run.prd_draft.content}</pre>
                      {run.prd_approval && <p>PRD 已批准 · r{run.prd_approval.revision}</p>}
                    </article>
                    {run.td_draft && (
                      <article>
                        <h3>TD 草稿 · r{run.td_draft.revision}</h3>
                        <pre>{run.td_draft.content}</pre>
                        {run.td_approval && <p>TD 已批准 · r{run.td_approval.revision}</p>}
                      </article>
                    )}
                    {run.delivery_spec && (
                      <article>
                        <h3>DeliverySpec</h3>
                        <pre>{JSON.stringify(run.delivery_spec, null, 2)}</pre>
                      </article>
                    )}
                    {run.available_commands.includes("approve_prd") && (
                      <Button className="run-action" loading={busy} onClick={() => void perform(() => api.approvePrd(run))}>
                        批准 PRD
                      </Button>
                    )}
                    {run.available_commands.includes("approve_td") && (
                      <Button className="run-action" loading={busy} onClick={() => void perform(() => api.approveTd(run))}>
                        批准 TD
                      </Button>
                    )}
                  </div>
                )}
              </Card>
            </section>
            <section aria-labelledby="stage-title">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Product contract</p>
                  <h2 id="stage-title">八阶段产品路线</h2>
                </div>
                <p>这些阶段是最终产品形状，不代表脚手架已经实现。</p>
              </div>
              <ol className="stage-grid">
                {scaffold.stages.map((stage, index) => (
                  <li key={stage.id}>
                    <Card className="stage-card">
                      <div className="stage-meta">
                        <span>{String(index + 1).padStart(2, "0")}</span>
                        <Tag icon={<ClockCircleOutlined />}>待实现</Tag>
                      </div>
                      <h3>{stage.title}</h3>
                      <p>{stage.description}</p>
                      <code>{stage.id}</code>
                    </Card>
                  </li>
                ))}
              </ol>
            </section>

            <section className="boundary-grid" aria-label="脚手架边界">
              <Card title="已经保留">
                <ul>{scaffold.implemented_capabilities.map((item) => <li key={item}>{item}</li>)}</ul>
              </Card>
              <Card title="计划实现">
                <ul>{scaffold.deferred_capabilities.map((item) => <li key={item}>{item}</li>)}</ul>
              </Card>
            </section>
          </>
        )}
      </main>
      <footer>
        当前能力与启动方式见项目 README。
      </footer>
    </ConfigProvider>
  );
}
