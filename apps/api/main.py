from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class StageSummary(BaseModel):
    id: str
    title: str
    description: str
    implemented: bool = False


class ScaffoldResponse(BaseModel):
    project: str
    mode: Literal["project-scaffold"]
    implemented_capabilities: list[str]
    deferred_capabilities: list[str]
    stages: list[StageSummary]


STAGES = [
    StageSummary(
        id="requirement_context",
        title="需求上下文构建",
        description="建立可信来源、仓库绑定与只读工程上下文。",
    ),
    StageSummary(
        id="requirement_clarification",
        title="需求澄清与决策",
        description="发现缺口，由用户确认关键产品事实。",
    ),
    StageSummary(
        id="product_specification",
        title="产品规格设计",
        description="基于已确认事实生成 PRD。",
    ),
    StageSummary(
        id="product_approval",
        title="产品规格验收",
        description="人工修订并批准冻结 PRD。",
    ),
    StageSummary(
        id="technical_design",
        title="技术方案设计",
        description="从批准 PRD 派生技术权威并生成统一 TD。",
    ),
    StageSummary(
        id="technical_validation",
        title="技术方案验证",
        description="发现、修复并收敛技术质量问题。",
    ),
    StageSummary(
        id="technical_approval",
        title="技术方案验收",
        description="人工批准绑定确定版本的 TD。",
    ),
    StageSummary(
        id="artifact_publication",
        title="交付物发布",
        description="发布 PRD、TD 与机器可读 DeliverySpec。",
    ),
]


app = FastAPI(title="SpecCraft Project API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(status="ok", service="speccraft-project-scaffold")


@app.get("/api/scaffold", response_model=ScaffoldResponse)
def read_scaffold() -> ScaffoldResponse:
    return ScaffoldResponse(
        project="SpecCraft AI Agent",
        mode="project-scaffold",
        implemented_capabilities=[
            "React 与 FastAPI 最小链路",
            "Python 多包边界",
            "匿名需求与目标仓库样例",
        ],
        deferred_capabilities=[
            "LLM Provider 与模型调用",
            "Run、Artifact 与持久化",
            "PRD/TD Workflow 与质量闭环",
            "Provider-driven Worker 与 Workbench",
            "Codex Native Skills 与 Host Runtime",
        ],
        stages=STAGES,
    )
