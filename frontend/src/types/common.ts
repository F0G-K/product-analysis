// ===== 项目 / 数据源 / 通知 / 审计 / 导出 / 工作台 =====

import type { Task } from './task'

/** 项目状态 */
export type ProjectStatus = 'active' | 'archived' | 'suspended'

/** 数据源类型 */
export type DataSourceType =
  | 'prd_repo'
  | 'api_platform'
  | 'tracking_system'
  | 'code_repo'
  | 'monitoring'
  | 'logging'
  | 'ticketing'

/** 数据源连接状态 */
export type DataSourceStatus = 'connected' | 'disconnected' | 'error'

// ---- 实体 ----

/** 项目 */
export interface Project {
  id: string
  tenant_id: string
  name: string
  description?: string
  status: ProjectStatus
  timezone?: string
  settings?: Record<string, unknown>
  created_at: string
  updated_at: string
}

/** 项目成员 */
export interface ProjectMember {
  user_id: string
  project_id: string
  user_name?: string
  user_email?: string
  role: 'project_admin' | 'project_member' | 'viewer'
  joined_at: string
}

/** 数据源 */
export interface DataSource {
  id: string
  project_id: string
  name: string
  source_type: DataSourceType
  connection_config?: Record<string, unknown>
  sync_interval?: number
  status: DataSourceStatus
  last_sync_at?: string
  created_at: string
}

/** 同步记录 */
export interface SyncRecord {
  id: string
  data_source_id: string
  sync_type: string
  started_at: string
  ended_at?: string
  result: string
  items_added?: number
  items_updated?: number
  items_deleted?: number
  items_failed?: number
}

/** 快照 */
export interface Snapshot {
  id: string
  task_id: string
  snapshot_type: string
  created_at: string
}

/** 通知 */
export interface Notification {
  id: string
  title: string
  message: string
  is_read: boolean
  notification_type: string
  related_task_id?: string
  created_at: string
}

/** 审计日志 */
export interface AuditLog {
  id: string
  user_id: string
  user_name?: string
  operation: string
  object_type: string
  object_id?: string
  detail?: string
  result: string
  created_at: string
  ip_address?: string
}

/** 导出记录 */
export interface ExportRecord {
  id: string
  task_id: string
  format: string
  file_name?: string
  status: string
  download_url?: string
  expires_at?: string
  created_at: string
}

/** 工作台数据 */
export interface WorkspaceData {
  pending_tasks: number
  pending_assessments: number
  blocker_issues: number
  pending_attribution: number
  data_source_errors: number
  todos: Task[]
  recent_tasks: Task[]
}
