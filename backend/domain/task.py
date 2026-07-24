from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Any, ClassVar
from uuid import UUID, uuid4

from backend.core.enums import ProjectRole, TaskStatus, TaskType
from backend.core.errors import BusinessError, ErrorCode, PermissionDeniedError


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TaskActor:
    user_id: UUID
    tenant_id: UUID
    project_roles: Mapping[UUID, ProjectRole] = field(default_factory=dict)
    is_tenant_admin: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_roles", MappingProxyType(dict(self.project_roles)))

    def can_view_project(self, project_id: UUID) -> bool:
        return self.is_tenant_admin or project_id in self.project_roles

    def role_for(self, project_id: UUID) -> ProjectRole | None:
        if self.is_tenant_admin:
            return ProjectRole.PROJECT_ADMIN
        return self.project_roles.get(project_id)


@dataclass(frozen=True, slots=True)
class ModelBinding:
    name: str
    version: str
    prompt_version: str
    temperature: Decimal = Decimal("0.30")

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.version.strip() or not self.prompt_version.strip():
            raise ValueError("模型名称、版本和提示词版本不能为空")
        if not Decimal("0") <= self.temperature <= Decimal("0.30"):
            raise ValueError("关键分析任务 temperature 必须在 0 到 0.30 之间")


@dataclass(frozen=True, slots=True)
class Task:
    id: UUID
    tenant_id: UUID
    project_id: UUID
    task_type: TaskType
    status: TaskStatus
    title: str
    created_by: UUID
    description: str | None = None
    input_snapshot_id: UUID | None = None
    model_binding: ModelBinding | None = None
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None
    failure_reason: str | None = None
    retry_count: int = 0
    retry_of_task_id: UUID | None = None
    error_details: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    MAX_RETRIES: ClassVar[int] = 3
    CANCELLABLE_STATUSES: ClassVar[frozenset[TaskStatus]] = frozenset(
        {
            TaskStatus.DRAFT,
            TaskStatus.VALIDATING,
            TaskStatus.ANALYZING,
            TaskStatus.PENDING_REVIEW,
        }
    )
    ALLOWED_TRANSITIONS: ClassVar[Mapping[TaskStatus, frozenset[TaskStatus]]] = (
        MappingProxyType(
            {
                TaskStatus.DRAFT: frozenset(
                    {TaskStatus.VALIDATING, TaskStatus.CANCELLED}
                ),
                TaskStatus.VALIDATING: frozenset(
                    {TaskStatus.ANALYZING, TaskStatus.FAILED, TaskStatus.CANCELLED}
                ),
                TaskStatus.ANALYZING: frozenset(
                    {
                        TaskStatus.PENDING_REVIEW,
                        TaskStatus.FAILED,
                        TaskStatus.CANCELLED,
                    }
                ),
                TaskStatus.PENDING_REVIEW: frozenset(
                    {
                        TaskStatus.ANALYZING,
                        TaskStatus.COMPLETED,
                        TaskStatus.FAILED,
                        TaskStatus.CANCELLED,
                    }
                ),
                TaskStatus.FAILED: frozenset(),
                TaskStatus.COMPLETED: frozenset(),
                TaskStatus.CANCELLED: frozenset(),
            }
        )
    )

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("任务标题不能为空")
        if self.retry_count < 0 or self.retry_count > self.MAX_RETRIES:
            raise ValueError("retry_count 必须在 0 到 3 之间")
        object.__setattr__(self, "error_details", dict(self.error_details))

    def transition(
        self,
        target: TaskStatus,
        *,
        failure_reason: str | None = None,
        error_details: Mapping[str, Any] | None = None,
        actor_id: UUID | None = None,
        now: datetime | None = None,
    ) -> Task:
        if target not in self.ALLOWED_TRANSITIONS[self.status]:
            raise BusinessError(
                ErrorCode.BUSINESS_RULE_VIOLATION,
                "任务状态不允许该操作",
                detail=f"{self.status.value} -> {target.value}",
            )

        changed_at = now or utc_now()
        changes: dict[str, Any] = {"status": target, "updated_at": changed_at}
        if target == TaskStatus.FAILED:
            if not failure_reason:
                raise ValueError("失败任务必须记录 failure_reason")
            changes["failure_reason"] = failure_reason
            changes["error_details"] = dict(error_details or {})
        elif target == TaskStatus.COMPLETED:
            if actor_id is None:
                raise ValueError("完成任务必须记录确认人")
            changes.update(
                confirmed_by=actor_id,
                confirmed_at=changed_at,
                completed_at=changed_at,
                failure_reason=None,
                error_details={},
            )
        return replace(self, **changes)

    def ensure_actor_can_manage(self, actor: TaskActor) -> None:
        if actor.tenant_id != self.tenant_id:
            raise PermissionDeniedError(
                ErrorCode.PROJECT_ACCESS_DENIED,
                "无权访问该租户任务",
            )
        if not actor.can_view_project(self.project_id):
            raise PermissionDeniedError(
                ErrorCode.PROJECT_ACCESS_DENIED,
                "无权访问该项目任务",
            )
        if (
            actor.user_id != self.created_by
            and actor.role_for(self.project_id) != ProjectRole.PROJECT_ADMIN
        ):
            raise PermissionDeniedError(
                ErrorCode.OPERATION_PERMISSION_DENIED,
                "仅任务创建人或项目管理员可执行该操作",
            )

    def create_retry(self, *, now: datetime | None = None) -> Task:
        if self.status != TaskStatus.FAILED:
            raise BusinessError(
                ErrorCode.BUSINESS_RULE_VIOLATION,
                "仅失败任务可以重试",
            )
        if self.retry_count >= self.MAX_RETRIES:
            raise BusinessError(
                ErrorCode.BUSINESS_RULE_VIOLATION,
                "任务重试次数已达上限",
            )

        changed_at = now or utc_now()
        return replace(
            self,
            id=uuid4(),
            status=TaskStatus.DRAFT,
            input_snapshot_id=None,
            confirmed_by=None,
            confirmed_at=None,
            completed_at=None,
            failure_reason=None,
            retry_count=self.retry_count + 1,
            retry_of_task_id=self.id,
            error_details={},
            created_at=changed_at,
            updated_at=changed_at,
        )
