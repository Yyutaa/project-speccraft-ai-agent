import { CheckCircleOutlined, ClockCircleOutlined } from "@ant-design/icons";
import { Alert, Card, ConfigProvider, Spin, Tag } from "antd";
import { useEffect, useState } from "react";

import { api, Scaffold } from "./api";


export default function App() {
  const [scaffold, setScaffold] = useState<Scaffold | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([api.health(), api.scaffold()])
      .then(([, scaffoldResponse]) => setScaffold(scaffoldResponse))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "无法连接脚手架 API");
      });
  }, []);

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
            React、FastAPI 与 Python 包边界已经就绪。领域契约、持久化、工作流、质量闭环和双宿主能力仍在规划中。
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
