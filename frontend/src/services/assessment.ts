import { get, getPaginated, post, patch, del } from './request';
import type { ApiResponse } from '@/types/api';
import type { Requirement, AssessmentModel, AssessmentTask, AssessmentConfirmation } from '@/types/assessment';

/** 获取需求列表 */
export async function listRequirements(projectId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: Requirement[]; total: number; page: number; page_size: number }>> {
  return getPaginated<Requirement>(`/projects/${projectId}/requirements`, params) as Promise<ApiResponse<{ items: Requirement[]; total: number; page: number; page_size: number }>>;
}

/** 获取需求详情 */
export async function getRequirement(projectId: string, reqId: string): Promise<ApiResponse<Requirement>> {
  return get<Requirement>(`/projects/${projectId}/requirements/${reqId}`);
}

/** 创建需求 */
export async function createRequirement(projectId: string, data: Record<string, unknown>): Promise<ApiResponse<Requirement>> {
  return post<Requirement>(`/projects/${projectId}/requirements`, data);
}

/** 更新需求 */
export async function updateRequirement(projectId: string, reqId: string, data: Record<string, unknown>): Promise<ApiResponse<Requirement>> {
  return patch<Requirement>(`/projects/${projectId}/requirements/${reqId}`, data);
}

/** 删除需求 */
export async function deleteRequirement(projectId: string, reqId: string): Promise<ApiResponse<null>> {
  return del<null>(`/projects/${projectId}/requirements/${reqId}`);
}

/** 获取评估模型列表 */
export async function listAssessmentModels(projectId: string): Promise<ApiResponse<{ items: AssessmentModel[]; total: number; page: number; page_size: number }>> {
  return getPaginated<AssessmentModel>(`/projects/${projectId}/assessment-models`) as Promise<ApiResponse<{ items: AssessmentModel[]; total: number; page: number; page_size: number }>>;
}

/** 获取评估模型详情 */
export async function getAssessmentModel(projectId: string, modelId: string): Promise<ApiResponse<AssessmentModel>> {
  return get<AssessmentModel>(`/projects/${projectId}/assessment-models/${modelId}`);
}

/** 发起评估 */
export async function createAssessment(projectId: string, reqId: string, data: { model_id: string; title?: string }): Promise<ApiResponse<{ task_id: string; status: string }>> {
  return post(`/projects/${projectId}/requirements/${reqId}/assess`, data);
}

/** 获取评估详情 */
export async function getAssessmentDetail(taskId: string): Promise<ApiResponse<AssessmentTask>> {
  return get<AssessmentTask>(`/tasks/${taskId}/assessment`);
}

/** 获取需求评估历史 */
export async function getAssessmentHistory(projectId: string, reqId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: AssessmentTask[]; total: number; page: number; page_size: number }>> {
  return getPaginated<AssessmentTask>(`/projects/${projectId}/requirements/${reqId}/assessments`, params) as Promise<ApiResponse<{ items: AssessmentTask[]; total: number; page: number; page_size: number }>>;
}

/** 确认评估 */
export async function confirmAssessment(taskId: string, data: AssessmentConfirmation): Promise<ApiResponse<null>> {
  return post<null>(`/tasks/${taskId}/assessment/confirm`, data);
}

/** 复核评估确认 */
export async function reviewConfirmation(taskId: string, confirmationId: string, data: Record<string, unknown>): Promise<ApiResponse<null>> {
  return post<null>(`/tasks/${taskId}/assessment/confirm/${confirmationId}/review`, data);
}
