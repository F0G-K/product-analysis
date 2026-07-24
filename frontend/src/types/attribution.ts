// ===== 归因分析 =====

import type { Task } from './task'

/** 归因类别 */
export type AttributionCategory =
  | 'requirement_omission'
  | 'design_flaw'
  | 'implementation_error'
  | 'config_change'
  | 'data_anomaly'

/** 置信度 */
export type AttributionConfidence = 'high' | 'medium' | 'low'

/** 证据类型 */
export type EvidenceType = 'fact' | 'inference' | 'missing'

/** 确认动作 */
export type AttributionAction = 'accept' | 'revise' | 'dispute'

// ---- 实体 ----

/** 发布版本 */
export interface ReleaseVersion {
  id: string
  project_id: string
  version_number: string
  name?: string
  description?: string
  released_at?: string
  created_at: string
}

/** 时间线事件 */
export interface TimelineEvent {
  id: string
  task_id: string
  event_source: string
  original_timestamp: string
  project_timestamp?: string
  summary: string
  source_url?: string
  credibility: 'confirmed' | 'uncertain'
  created_at: string
}

/** 归因任务（扩展基础 Task） */
export interface AttributionTask extends Task {
  release_version_id: string
  version_number?: string
  anomaly_description?: string
  anomaly_start_time?: string
  anomaly_end_time?: string
  impact_scope?: string
  user_impact?: string
}

/** 归因结果 */
export interface AttributionResult {
  id: string
  task_id: string
  category: AttributionCategory
  is_primary: boolean
  confidence: AttributionConfidence
  reasoning_chain?: string
  supporting_evidence: EvidenceItem[]
  counter_evidence: EvidenceItem[]
  missing_evidence: EvidenceItem[]
  short_term_mitigation?: string
  long_term_improvement?: string
  suggested_owner_role?: string
}

/** 证据条目 */
export interface EvidenceItem {
  evidence_type: EvidenceType
  source_label?: string
  citation?: string
  excerpt?: string
}

/** 归因确认 */
export interface AttributionConfirmation {
  action: AttributionAction
  reason?: string
  primary_category?: AttributionCategory
}
