import api from './api';
import type { ApiResponse, PaginatedData } from '@/types/api';

export async function get<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> {
  const res = await api.get<ApiResponse<T>>(url, { params });
  return res.data;
}

export async function getPaginated<T>(url: string, params?: Record<string, unknown>): Promise<ApiResponse<PaginatedData<T>>> {
  const res = await api.get<ApiResponse<PaginatedData<T>>>(url, { params });
  return res.data;
}

export async function post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const res = await api.post<ApiResponse<T>>(url, data);
  return res.data;
}

export async function put<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const res = await api.put<ApiResponse<T>>(url, data);
  return res.data;
}

export async function patch<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  const res = await api.patch<ApiResponse<T>>(url, data);
  return res.data;
}

export async function del<T = null>(url: string): Promise<ApiResponse<T>> {
  const res = await api.delete<ApiResponse<T>>(url);
  return res.data;
}
