"""项目管理 HTTP Schema。"""

from pydantic import BaseModel, ConfigDict, Field


class CreateProjectRequest(BaseModel):
    """创建项目请求体。"""

    model_config = ConfigDict(extra="forbid")

    project_name: str = Field(min_length=1, max_length=128)
    source_type: str = Field(pattern=r"^(local|repository)$")
    source_path: str = Field(min_length=1, max_length=2048)
    task_content: str = Field(min_length=1, max_length=20_000)
    environment_type: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_-]{0,63}$",
    )


class StartProjectRequest(BaseModel):
    """启动项目请求体，接口只接受空对象。"""

    model_config = ConfigDict(extra="forbid")


class StopProjectRequest(BaseModel):
    """停止项目请求体。"""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=500)


class DeleteProjectRequest(BaseModel):
    """删除项目二次确认请求体。"""

    model_config = ConfigDict(extra="forbid")

    confirm_project_name: str = Field(min_length=1, max_length=128)


class ProjectSummaryResponse(BaseModel):
    """项目列表项。"""

    id: str
    project_name: str
    source_type: str
    source_path: str
    environment_type: str
    project_status: str
    last_started_at: str | None
    last_finished_at: str | None
    created_at: str
    updated_at: str


class ProjectCreatedResponse(BaseModel):
    """项目创建响应。"""

    id: str
    project_name: str
    source_type: str
    source_path: str
    task_content: str
    environment_type: str
    project_status: str
    created_by: str
    created_at: str
    updated_at: str


class ProjectRuntimeResponse(BaseModel):
    """项目运行环境摘要。"""

    id: str
    runtime_identifier: str | None
    container_status: str
    started_at: str | None
    stopped_at: str | None
    error_message: str | None


class ProjectStatisticsResponse(BaseModel):
    """项目统计。"""

    vulnerability_count: int
    verified_vulnerability_count: int
    attack_path_count: int
    worker_task_count: int


class ProjectDetailResponse(ProjectSummaryResponse):
    """项目详情响应。"""

    task_content: str
    created_by: str
    stop_requested_at: str | None
    runtime: ProjectRuntimeResponse | None
    statistics: ProjectStatisticsResponse
    report_status: str | None


class ProjectListData(BaseModel):
    """项目列表分页数据。"""

    items: list[ProjectSummaryResponse] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    has_next: bool


class ProjectOperationResponse(BaseModel):
    """异步操作受理响应。"""

    model_config = ConfigDict(extra="ignore")

    project_id: str
    operation: str
    project_status: str | None = None
    accepted_at: str | None = None
    stop_requested_at: str | None = None
