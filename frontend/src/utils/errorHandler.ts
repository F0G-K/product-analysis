import axios from 'axios'
import type { ApiErrorResponse } from '@/types/api'
import { ERROR_MESSAGES } from './constants'

/**
 * 根据错误码获取对应的中文错误描述
 */
export function getErrorMessage(code: number): string {
  return ERROR_MESSAGES[code] ?? `未知错误 (code: ${code})`
}

/**
 * 判断是否为认证相关错误
 */
export function isAuthError(code: number): boolean {
  return [40101, 40102, 40103].includes(code)
}

/**
 * 判断是否为限流错误 (HTTP 429)
 */
export function isRateLimitError(code: number): boolean {
  return code === 429
}

/** 将接口异常转换为可展示文案 */
export function getRequestErrorMessage(error: unknown, fallback = '操作失败'): string {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    return error.response?.data?.message || error.message || fallback
  }
  return error instanceof Error ? error.message : fallback
}
