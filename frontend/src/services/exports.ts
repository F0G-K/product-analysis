import { get, getPaginated, post } from './request';
import type { ApiResponse } from '@/types/api';
import type { ExportRecord } from '@/types/common';

/** 导出任务结果 */
export async function exportTask(taskId: string, format: 'markdown' | 'excel'): Promise<ApiResponse<{ export_id: string }>> {
  return post(`/tasks/${taskId}/export`, { format });
}

/** 获取导出历史 */
export async function listExports(params?: Record<string, unknown>): Promise<ApiResponse<{ items: ExportRecord[]; total: number; page: number; page_size: number }>> {
  return getPaginated<ExportRecord>('/exports', params) as Promise<ApiResponse<{ items: ExportRecord[]; total: number; page: number; page_size: number }>>;
}

/** 获取导出文件下载 URL */
export function getExportDownloadUrl(exportId: string): string {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  return `${baseUrl}/exports/${exportId}/download`;
}
