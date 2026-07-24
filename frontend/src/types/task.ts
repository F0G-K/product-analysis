// ===== 任务 =====

import type { PaginationParams } from './api'

/** 任务状态 */
export type TaskStatus =
  | 'draft'
  | 'validating'
  | 'analyzing'
  | 'pending_review'
  | 'completed'
  | 'failed'
  | 'cancelled'

/** 任务类型 */
export type TaskType = 'assessment' | 'check' | 'attribution'

/** 基础任务 */
export interface Task {
  id: string
  tenant_id: string
  project_id: string
  task_type: TaskType
  status: TaskStatus
  title: string
  description?: string
  model_name?: string
  model_version?: string
  created_by: string
  created_by_name?: string
  created_at: string
  updated_at: string
  completed_at?: string
  failure_reason?: string
  retry_count: number
}

/** 任务列表查询参数 */
export interface TaskListParams extends PaginationParams {
  status?: TaskStatus
  task_type?: TaskType
  project_id?: string
  search?: string
  start_time?: string
  end_time?: string
}
