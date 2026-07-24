import { get, getPaginated, patch, post } from './request';
import type { ApiResponse } from '@/types/api';
import type { Notification } from '@/types/common';

/** 获取通知列表 */
export async function listNotifications(params?: Record<string, unknown>): Promise<ApiResponse<{ items: Notification[]; total: number; page: number; page_size: number }>> {
  return getPaginated<Notification>('/notifications', params) as Promise<ApiResponse<{ items: Notification[]; total: number; page: number; page_size: number }>>;
}

/** 标记通知已读 */
export async function markNotificationRead(notificationId: string): Promise<ApiResponse<null>> {
  return patch<null>(`/notifications/${notificationId}/read`);
}

/** 全部标记已读 */
export async function markAllNotificationsRead(): Promise<ApiResponse<null>> {
  return post<null>('/notifications/read-all');
}
