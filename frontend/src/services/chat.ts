import api from './api';
import type { ConversationSummary, ConversationDetail, SSEEvent } from '@/types/chat';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/** 获取 auth token */
function getToken(): string | null {
  try {
    const stored = localStorage.getItem('auth-storage');
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed?.state?.accessToken || null;
    }
  } catch { /* ignore */ }
  return null;
}

/** SSE 流式聊天 */
export async function* streamChat(params: {
  conversation_id?: string | null;
  task_id?: string | null;
  message: string;
  provider?: string;
  model?: string;
}): AsyncGenerator<SSEEvent> {
  const token = getToken();
  const response = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      conversation_id: params.conversation_id || null,
      task_id: params.task_id || null,
      message: params.message,
      provider: params.provider || '',
      model: params.model || '',
    }),
  });

  if (!response.ok) {
    throw new Error(`Chat stream failed: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim();
        if (!data) continue;
        try {
          const event = JSON.parse(data) as SSEEvent;
          yield event;
        } catch {
          // skip malformed events
        }
      }
    }
  }
}

/** 获取对话列表 */
export async function listConversations(): Promise<ConversationSummary[]> {
  const res = await api.get<ConversationSummary[]>('/chat/conversations');
  return res.data;
}

/** 获取对话详情 */
export async function getConversation(id: string): Promise<ConversationDetail> {
  const res = await api.get<ConversationDetail>(`/chat/conversations/${id}`);
  return res.data;
}
