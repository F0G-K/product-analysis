// ===== 一致性检查 =====

import type { Task } from './task'

/** 问题级别 */
export type IssueLevel = 'blocker' | 'critical' | 'general' | 'info'

/** 置信度 */
export type CheckConfidence = 'high' | 'medium' | 'low'

/** 问题状态 */
export type IssueStatus =
  | 'open'
  | 'assigned'
  | 'resolved'
  | 'waived'
  | 'false_positive'
  | 'closed'

/** 操作类型 */
export type OperationType =
  | 'acknowledge'
  | 'fix'
  | 'waive'
  | 'false_positive'

// ---- 实体 ----

/** 检查基线 */
export interface CheckBaseline {
  id: string
  project_id: string
  name: string
  description?: string
  check_type?: string
  created_at: string
}

/** 检查规则 */
export interface CheckRule {
  id: string
  project_id: string
  name: string
  dimension: string
  description: string
  level: IssueLevel
  is_active: boolean
}

/** 交付物 */
export interface Deliverable {
  id: string
  project_id: string
  name: string
  file_name: string
  file_type: string
  file_size?: number
  version?: string
  created_at: string
}

/** 检查任务（扩展基础 Task） */
export interface CheckTask extends Task {
  baseline_id: string
  baseline_name?: string
  rule_version?: string
  involved_deliverables: string[]
}

/** 检查发现的问题 */
export interface CheckIssue {
  id: string
  check_task_id: string
  dimension: string
  title: string
  level: IssueLevel
  confidence: CheckConfidence
  description?: string
  involved_deliverables?: string[]
  conflict_comparison?: string
  potential_impact?: string
  suggested_fix?: string
  recommended_role?: string
  status: IssueStatus
  assigned_to?: string
  created_at: string
  updated_at: string
}

/** 问题处理记录 */
export interface IssueAssignment {
  id: string
  issue_id: string
  operation_type: OperationType
  assignee_id?: string
  description?: string
  valid_until?: string
  created_at: string
}

/** 问题复检 */
export interface IssueRecheck {
  id: string
  issue_id: string
  recheck_status: string
  result?: string
  created_at: string
}
