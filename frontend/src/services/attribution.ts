import { get, getPaginated, post, patch, del } from './request';
import type { ApiResponse } from '@/types/api';
import type { ReleaseVersion, AttributionTask, TimelineEvent, AttributionResult, AttributionConfirmation } from '@/types/attribution';

/** 获取发布版本列表 */
export async function listReleases(projectId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: ReleaseVersion[]; total: number; page: number; page_size: number }>> {
  return getPaginated<ReleaseVersion>(`/projects/${projectId}/releases`, params) as Promise<ApiResponse<{ items: ReleaseVersion[]; total: number; page: number; page_size: number }>>;
}

/** 获取版本详情 */
export async function getRelease(projectId: string, releaseId: string): Promise<ApiResponse<ReleaseVersion>> {
  return get<ReleaseVersion>(`/projects/${projectId}/releases/${releaseId}`);
}

/** 创建发布版本 */
export async function createRelease(projectId: string, data: Record<string, unknown>): Promise<ApiResponse<ReleaseVersion>> {
  return post<ReleaseVersion>(`/projects/${projectId}/releases`, data);
}

/** 更新发布版本 */
export async function updateRelease(projectId: string, releaseId: string, data: Record<string, unknown>): Promise<ApiResponse<ReleaseVersion>> {
  return patch<ReleaseVersion>(`/projects/${projectId}/releases/${releaseId}`, data);
}

/** 删除发布版本 */
export async function deleteRelease(projectId: string, releaseId: string): Promise<ApiResponse<null>> {
  return del<null>(`/projects/${projectId}/releases/${releaseId}`);
}

/** 发起归因 */
export async function createAttribution(projectId: string, releaseId: string, data?: Record<string, unknown>): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return post(`/projects/${projectId}/releases/${releaseId}/attribute`, data);
}

/** 获取归因详情 */
export async function getAttributionDetail(taskId: string): Promise<ApiResponse<AttributionTask>> {
  return get<AttributionTask>(`/tasks/${taskId}/attribution`);
}

/** 获取时间线 */
export async function getTimeline(taskId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: TimelineEvent[]; total: number; page: number; page_size: number }>> {
  return getPaginated<TimelineEvent>(`/tasks/${taskId}/attribution/timeline`, params) as Promise<ApiResponse<{ items: TimelineEvent[]; total: number; page: number; page_size: number }>>;
}

/** 手动添加时间线事件 */
export async function addTimelineEvent(taskId: string, data: Record<string, unknown>): Promise<ApiResponse<TimelineEvent>> {
  return post<TimelineEvent>(`/tasks/${taskId}/attribution/timeline`, data);
}

/** 获取归因结果 */
export async function getAttributionResults(taskId: string): Promise<ApiResponse<AttributionResult[]>> {
  return get<AttributionResult[]>(`/tasks/${taskId}/attribution/results`);
}

/** 确认归因 */
export async function confirmAttribution(taskId: string, data: AttributionConfirmation): Promise<ApiResponse<null>> {
  return post<null>(`/tasks/${taskId}/attribution/confirm`, data);
}
