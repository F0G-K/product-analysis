// ===== 统一 API 响应格式 =====

/** 成功 / 列表 / 错误 的统一包装 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  request_id: string
}

/** 分页列表数据 */
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 错误响应体 */
export interface ApiErrorResponse {
  code: number
  message: string
  detail?: string
  request_id: string
}

/** 通用分页查询参数 */
export interface PaginationParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}
