import { get, getPaginated, post, patch, del } from './request';
import type { ApiResponse } from '@/types/api';
import type { Project, ProjectMember, DataSource, SyncRecord } from '@/types/common';

/** 获取项目列表 */
export async function listProjects(params?: Record<string, unknown>): Promise<ApiResponse<{ items: Project[]; total: number; page: number; page_size: number }>> {
  return getPaginated<Project>('/projects', params) as Promise<ApiResponse<{ items: Project[]; total: number; page: number; page_size: number }>>;
}

/** 获取项目详情 */
export async function getProject(projectId: string): Promise<ApiResponse<Project>> {
  return get<Project>(`/projects/${projectId}`);
}

/** 创建项目 */
export async function createProject(data: { name: string; description?: string; timezone?: string }): Promise<ApiResponse<Project>> {
  return post<Project>('/projects', data);
}

/** 更新项目 */
export async function updateProject(projectId: string, data: Record<string, unknown>): Promise<ApiResponse<Project>> {
  return patch<Project>(`/projects/${projectId}`, data);
}

/** 删除/归档项目 */
export async function deleteProject(projectId: string): Promise<ApiResponse<null>> {
  return del<null>(`/projects/${projectId}`);
}

/** 获取项目成员列表 */
export async function getMembers(projectId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: ProjectMember[]; total: number; page: number; page_size: number }>> {
  return getPaginated<ProjectMember>(`/projects/${projectId}/members`, params) as Promise<ApiResponse<{ items: ProjectMember[]; total: number; page: number; page_size: number }>>;
}

/** 添加项目成员 */
export async function addMember(projectId: string, data: { user_id: string; role: string }): Promise<ApiResponse<ProjectMember>> {
  return post<ProjectMember>(`/projects/${projectId}/members`, data);
}

/** 更新成员角色 */
export async function updateMember(projectId: string, userId: string, data: { role: string }): Promise<ApiResponse<ProjectMember>> {
  return patch<ProjectMember>(`/projects/${projectId}/members/${userId}`, data);
}

/** 移除成员 */
export async function removeMember(projectId: string, userId: string): Promise<ApiResponse<null>> {
  return del<null>(`/projects/${projectId}/members/${userId}`);
}

/** 获取数据源列表 */
export async function listDataSources(projectId: string): Promise<ApiResponse<{ items: DataSource[]; total: number; page: number; page_size: number }>> {
  return getPaginated<DataSource>(`/projects/${projectId}/data-sources`) as Promise<ApiResponse<{ items: DataSource[]; total: number; page: number; page_size: number }>>;
}

/** 创建数据源 */
export async function createDataSource(projectId: string, data: Record<string, unknown>): Promise<ApiResponse<DataSource>> {
  return post<DataSource>(`/projects/${projectId}/data-sources`, data);
}

/** 更新数据源 */
export async function updateDataSource(projectId: string, sourceId: string, data: Record<string, unknown>): Promise<ApiResponse<DataSource>> {
  return patch<DataSource>(`/projects/${projectId}/data-sources/${sourceId}`, data);
}

/** 测试数据源连接 */
export async function testConnection(projectId: string, sourceId: string): Promise<ApiResponse<{ status: string; latency_ms: number; tested_at: string }>> {
  return post(`/projects/${projectId}/data-sources/${sourceId}/test`);
}

/** 手动触发同步 */
export async function triggerSync(projectId: string, sourceId: string, data?: Record<string, unknown>): Promise<ApiResponse<{ sync_record_id: string }>> {
  return post(`/projects/${projectId}/data-sources/${sourceId}/sync`, data);
}

/** 删除数据源 */
export async function deleteDataSource(projectId: string, sourceId: string): Promise<ApiResponse<null>> {
  return del<null>(`/projects/${projectId}/data-sources/${sourceId}`);
}

/** 获取同步记录 */
export async function getSyncRecords(projectId: string, sourceId: string, params?: Record<string, unknown>): Promise<ApiResponse<{ items: SyncRecord[]; total: number; page: number; page_size: number }>> {
  return getPaginated<SyncRecord>(`/projects/${projectId}/data-sources/${sourceId}/sync-records`, params) as Promise<ApiResponse<{ items: SyncRecord[]; total: number; page: number; page_size: number }>>;
}
