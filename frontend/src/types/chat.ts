/** 聊天消息 */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

/** 对话摘要 */
export interface ConversationSummary {
  id: string
  task_id: string | null
  message_count: number
  first_message: string
  created_at: string
}

/** 对话详情 */
export interface ConversationDetail {
  id: string
  task_id: string | null
  messages: ChatMessage[]
  created_at: string
}

/** SSE 流事件 */
export type SSEEvent =
  | { type: 'delta'; content: string }
  | { type: 'done'; conversation_id?: string }
  | { type: 'error'; content: string }
