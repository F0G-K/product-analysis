// ===== 评估 =====

import type { Task } from './task'

/** 优先级 */
export type Priority = 'P0' | 'P1' | 'P2' | 'P3'

/** 置信度 */
export type Confidence = 'high' | 'medium' | 'low'

/** 评分方向 */
export type ScoringDirection = 'positive' | 'negative'

/** 确认动作 */
export type ConfirmationAction = 'accept' | 'revise' | 'reject'

// ---- 实体 ----

/** 需求 */
export interface Requirement {
  id: string
  project_id: string
  name: string
  external_id?: string
  background?: string
  target_users?: string
  core_scenarios?: string
  status: string
  current_priority?: Priority
  current_total_score?: number
  estimated_man_days?: number
  technical_complexity?: string
  assignee_id?: string
  expected_launch_date?: string
  created_at: string
  updated_at: string
}

/** 评估模型 */
export interface AssessmentModel {
  id: string
  project_id: string
  name: string
  total_score_formula: string
  priority_thresholds: Record<Priority, number>
  is_active: boolean
  version: number
  created_at: string
}

/** 评估维度 */
export interface AssessmentDimension {
  id: string
  model_id: string
  name: string
  weight: number
  scoring_direction: ScoringDirection
  sort_order: number
  anchors: ScoringAnchor[]
}

/** 评分锚点 */
export interface ScoringAnchor {
  /** 1-5 */
  score: number
  description: string
  criteria: string
}

/** 评估任务（扩展基础 Task） */
export interface AssessmentTask extends Task {
  requirement_id: string
  requirement_name?: string
  model_id: string
  model_name?: string
  model_version?: string
  dimensions: DimensionScore[]
}

/** 维度评分 */
export interface DimensionScore {
  dimension_name: string
  weight: number
  raw_score: number
  converted_score: number
  confidence: Confidence
  evidence_citations?: string[]
  inference_explanation?: string
  missing_evidence?: string[]
}

/** 敏感度分析结果 */
export interface SensitivityResult {
  adjusted_dimension: string
  adjusted_weight: number
  new_total_score: number
  priority_change: boolean
}

// ---- 请求 / 响应 ----

/** 评估确认 */
export interface AssessmentConfirmation {
  action: ConfirmationAction
  comment?: string
  adjustments?: {
    dimension_name: string
    adjusted_score: number
  }[]
}

/** 创建需求 */
export interface RequirementCreate {
  name: string
  external_id?: string
  background?: string
  target_users?: string
  core_scenarios?: string
  estimated_man_days?: number
  technical_complexity?: string
  expected_launch_date?: string
}
