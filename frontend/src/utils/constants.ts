// ===== 状态 / 级别 / 优先级 常量映射 =====

import type { TaskStatus } from '@/types/task'
import type { Priority } from '@/types/assessment'
import type { IssueLevel } from '@/types/consistency'
import type { AttributionCategory } from '@/types/attribution'

/** 任务状态 → 标签 & 颜色 */
export const TASK_STATUS_MAP: Record<TaskStatus, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'gray' },
  validating: { label: '校验中', color: 'blue' },
  analyzing: { label: '分析中', color: 'indigo' },
  pending_review: { label: '待确认', color: 'amber' },
  completed: { label: '已完成', color: 'green' },
  failed: { label: '失败', color: 'red' },
  cancelled: { label: '已取消', color: 'gray' },
} as const

/** 优先级 → 标签 & 颜色 & 背景色 */
export const PRIORITY_MAP: Record<Priority, { label: string; color: string; bg: string }> = {
  P0: { label: 'P0', color: 'text-red-700', bg: 'bg-red-100' },
  P1: { label: 'P1', color: 'text-amber-700', bg: 'bg-amber-100' },
  P2: { label: 'P2', color: 'text-blue-700', bg: 'bg-blue-100' },
  P3: { label: 'P3', color: 'text-gray-500', bg: 'bg-gray-100' },
} as const

/** 置信度 → 标签 & 颜色 */
export const CONFIDENCE_MAP: Record<string, { label: string; color: string }> = {
  high: { label: '高', color: 'green' },
  medium: { label: '中', color: 'amber' },
  low: { label: '低', color: 'red' },
} as const

/** 问题级别 → 标签 & 颜色 */
export const ISSUE_LEVEL_MAP: Record<IssueLevel, { label: string; color: string }> = {
  blocker: { label: '阻断', color: 'red' },
  critical: { label: '严重', color: 'amber' },
  general: { label: '一般', color: 'blue' },
  info: { label: '提示', color: 'gray' },
} as const

/** 归因类别 → 标签 */
export const ATTRIBUTION_CATEGORY_MAP: Record<AttributionCategory, { label: string }> = {
  requirement_omission: { label: '需求遗漏' },
  design_flaw: { label: '设计缺陷' },
  implementation_error: { label: '实现错误' },
  config_change: { label: '配置变更' },
  data_anomaly: { label: '数据异常' },
} as const

/** 错误码 → 错误描述 */
export const ERROR_MESSAGES: Record<number, string> = {
  40101: '用户名或密码错误',
  40102: '登录已过期',
  40104: '账号已锁定',
  40105: '需要 MFA 验证',
  40106: 'MFA 验证失败',
  40301: '无租户权限',
  40302: '无项目权限',
  40303: '无权执行此操作',
  40401: '资源不存在',
  40901: '数据冲突',
  42201: '输入信息不完整',
  42202: '超出使用限制',
  50001: '服务器繁忙',
} as const
