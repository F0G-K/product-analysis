import { get, getPaginated, post } from './request';
import type { ApiResponse } from '@/types/api';
import type { Task } from '@/types/task';
import type { WorkspaceData, Snapshot } from '@/types/common';

/** 获取任务列表 */
export async function listTasks(params?: Record<string, unknown>): Promise<ApiResponse<{ items: Task[]; total: number; page: number; page_size: number }>> {
  return getPaginated<Task>('/tasks', params) as Promise<ApiResponse<{ items: Task[]; total: number; page: number; page_size: number }>>;
}

/** 获取任务详情 */
export async function getTask(taskId: string): Promise<ApiResponse<Task>> {
  return get<Task>(`/tasks/${taskId}`);
}

/** 取消任务 */
export async function cancelTask(taskId: string): Promise<ApiResponse<null>> {
  return post<null>(`/tasks/${taskId}/cancel`);
}

/** 重试失败任务 */
export async function retryTask(taskId: string): Promise<ApiResponse<null>> {
  return post<null>(`/tasks/${taskId}/retry`);
}

/** 获取任务快照 */
export async function getTaskSnapshots(taskId: string): Promise<ApiResponse<Snapshot[]>> {
  return get<Snapshot[]>(`/tasks/${taskId}/snapshots`);
}

/** 获取任务证据 */
export async function getTaskEvidence(taskId: string): Promise<ApiResponse<unknown[]>> {
  return get<unknown[]>(`/tasks/${taskId}/evidence`);
}

/** 获取工作台数据 */
export async function getWorkspace(params?: Record<string, unknown>): Promise<ApiResponse<WorkspaceData>> {
  return get<WorkspaceData>('/workspace', params);
}
