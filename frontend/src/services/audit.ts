import { getPaginated } from './request';
import type { ApiResponse } from '@/types/api';
import type { AuditLog } from '@/types/common';

/** 获取审计日志 */
export async function listAuditLogs(params?: Record<string, unknown>): Promise<ApiResponse<{ items: AuditLog[]; total: number; page: number; page_size: number }>> {
  return getPaginated<AuditLog>('/audit-logs', params) as Promise<ApiResponse<{ items: AuditLog[]; total: number; page: number; page_size: number }>>;
}
