import { get, getPaginated, post, patch, del } from './request';
import type { ApiResponse } from '@/types/api';
import type { Deliverable, CheckBaseline, CheckRule, CheckTask, CheckIssue, IssueAssignment, IssueRecheck } from '@/types/consistency';

/** 获取交付物列表 */
export async function listDeliverables(projectId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: Deliverable[]; total: number; page: number; page_size: number }>> {
  return getPaginated<Deliverable>(`/projects/${projectId}/deliverables`, params) as Promise<ApiResponse<{ items: Deliverable[]; total: number; page: number; page_size: number }>>;
}

/** 获取交付物详情 */
export async function getDeliverable(projectId: string, deliverableId: string): Promise<ApiResponse<Deliverable>> {
  return get<Deliverable>(`/projects/${projectId}/deliverables/${deliverableId}`);
}

/** 更新交付物 */
export async function updateDeliverable(projectId: string, deliverableId: string, data: Record<string, unknown>): Promise<ApiResponse<Deliverable>> {
  return patch<Deliverable>(`/projects/${projectId}/deliverables/${deliverableId}`, data);
}

/** 获取交付物下载 URL */
export function getDeliverableDownloadUrl(projectId: string, deliverableId: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  return `${baseUrl}/projects/${projectId}/deliverables/${deliverableId}/download`;
}

/** 获取检查基线列表 */
export async function listCheckBaselines(projectId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: CheckBaseline[]; total: number; page: number; page_size: number }>> {
  return getPaginated<CheckBaseline>(`/projects/${projectId}/check-baselines`, params) as Promise<ApiResponse<{ items: CheckBaseline[]; total: number; page: number; page_size: number }>>;
}

/** 获取基线详情 */
export async function getCheckBaseline(projectId: string, baselineId: string): Promise<ApiResponse<CheckBaseline>> {
  return get<CheckBaseline>(`/projects/${projectId}/check-baselines/${baselineId}`);
}

/** 创建检查基线 */
export async function createCheckBaseline(projectId: string, data: Record<string, unknown>): Promise<ApiResponse<CheckBaseline>> {
  return post<CheckBaseline>(`/projects/${projectId}/check-baselines`, data);
}

/** 获取检查规则列表 */
export async function listCheckRules(projectId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: CheckRule[]; total: number; page: number; page_size: number }>> {
  return getPaginated<CheckRule>(`/projects/${projectId}/check-rules`, params) as Promise<ApiResponse<{ items: CheckRule[]; total: number; page: number; page_size: number }>>;
}

/** 创建检查规则 */
export async function createCheckRule(projectId: string, data: Record<string, unknown>): Promise<ApiResponse<CheckRule>> {
  return post<CheckRule>(`/projects/${projectId}/check-rules`, data);
}

/** 更新检查规则 */
export async function updateCheckRule(projectId: string, ruleId: string, data: Record<string, unknown>): Promise<ApiResponse<CheckRule>> {
  return patch<CheckRule>(`/projects/${projectId}/check-rules/${ruleId}`, data);
}

/** 删除检查规则 */
export async function deleteCheckRule(projectId: string, ruleId: string): Promise<ApiResponse<null>> {
  return del<null>(`/projects/${projectId}/check-rules/${ruleId}`);
}

/** 发起一致性检查 */
export async function createCheckTask(projectId: string, baselineId: string, data?: Record<string, unknown>): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return post(`/projects/${projectId}/check-baselines/${baselineId}/check`, data);
}

/** 获取检查任务详情 */
export async function getCheckTaskDetail(taskId: string): Promise<ApiResponse<CheckTask>> {
  return get<CheckTask>(`/tasks/${taskId}/check`);
}

/** 获取问题列表 */
export async function getCheckIssueList(taskId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: CheckIssue[]; total: number; page: number; page_size: number }>> {
  return getPaginated<CheckIssue>(`/tasks/${taskId}/check/issues`, params) as Promise<ApiResponse<{ items: CheckIssue[]; total: number; page: number; page_size: number }>>;
}

/** 获取问题详情 */
export async function getCheckIssueDetail(issueId: string): Promise<ApiResponse<CheckIssue>> {
  return get<CheckIssue>(`/check-issues/${issueId}`);
}

/** 调整问题级别 */
export async function updateIssueLevel(issueId: string, data: { level: string }): Promise<ApiResponse<CheckIssue>> {
  return patch<CheckIssue>(`/check-issues/${issueId}/level`, data);
}

/** 处置问题 */
export async function assignIssue(issueId: string, data: Record<string, unknown>): Promise<ApiResponse<IssueAssignment>> {
  return post<IssueAssignment>(`/check-issues/${issueId}/assignments`, data);
}

/** 获取处置历史 */
export async function getIssueAssignments(issueId: string): Promise<ApiResponse<IssueAssignment[]>> {
  return get<IssueAssignment[]>(`/check-issues/${issueId}/assignments`);
}

/** 发起复检 */
export async function createRecheck(issueId: string, data?: Record<string, unknown>): Promise<ApiResponse<IssueRecheck>> {
  return post<IssueRecheck>(`/check-issues/${issueId}/recheck`, data);
}

/** 获取复检历史 */
export async function getRecheckHistory(issueId: string): Promise<ApiResponse<IssueRecheck[]>> {
  return get<IssueRecheck[]>(`/check-issues/${issueId}/rechecks`);
}
