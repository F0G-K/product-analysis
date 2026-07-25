import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { streamChat, listConversations, getConversation } from '@/services/chat';
import { listTasks } from '@/services/tasks';
import { cn } from '@/utils/cn';
import type { ChatMessage, SSEEvent } from '@/types/chat';
import type { Task, TaskType, TaskStatus } from '@/types/task';
import { ChatMarkdown } from './ChatMarkdown';

// ---- 任务类型 & 状态 映射 ----
const TYPE_LABEL: Record<TaskType, string> = {
  assessment: '需求评估',
  consistency_check: '一致性检查',
  attribution: '问题归因',
};

const STATUS_STYLE: Record<TaskStatus, string> = {
  draft: 'bg-gray-100 text-gray-600',
  validating: 'bg-yellow-100 text-yellow-700',
  analyzing: 'bg-blue-100 text-blue-700',
  pending_review: 'bg-purple-100 text-purple-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-400 line-through',
};

const STATUS_LABEL: Record<TaskStatus, string> = {
  draft: '草稿',
  validating: '校验中',
  analyzing: '分析中',
  pending_review: '待审核',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

export function ChatPage() {
  // 任务列表
  const { data: tasksData } = useQuery({
    queryKey: ['tasks', { page_size: 200 }],
    queryFn: () => listTasks({ page_size: 200 }),
  });

  const { data: conversations, refetch: refetchConversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => listConversations(),
  });

  const tasks = tasksData?.data?.items ?? [];
  const convList = conversations ?? [];

  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loadingConv, setLoadingConv] = useState(false);

  // 任务下拉面板
  const [taskDropdownOpen, setTaskDropdownOpen] = useState(false);
  const [taskSearch, setTaskSearch] = useState('');
  const taskDropdownRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (taskDropdownRef.current && !taskDropdownRef.current.contains(e.target as Node)) {
        setTaskDropdownOpen(false);
        setTaskSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // 过滤任务
  const filteredTasks = useMemo(() => {
    if (!taskSearch.trim()) return tasks;
    const q = taskSearch.toLowerCase();
    return tasks.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        t.task_type.toLowerCase().includes(q) ||
        t.id.toLowerCase().includes(q),
    );
  }, [tasks, taskSearch]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // 发送消息
  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || streaming) return;

    setInputValue('');
    setError(null);

    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);
    setStreamingContent('');

    try {
      let fullContent = '';
      for await (const event of streamChat({
        conversation_id: conversationId,
        task_id: selectedTaskId || null,
        message: text,
      })) {
        if (event.type === 'delta') {
          fullContent += event.content;
          setStreamingContent(fullContent);
        } else if (event.type === 'done') {
          if (event.conversation_id && !conversationId) {
            setConversationId(event.conversation_id);
          }
        } else if (event.type === 'error') {
          setError(event.content);
        }
      }
      if (fullContent) {
        setMessages((prev) => [...prev, { role: 'assistant', content: fullContent }]);
      }
      refetchConversations();
    } catch (e) {
      setError(e instanceof Error ? e.message : '发送失败');
    } finally {
      setStreaming(false);
      setStreamingContent('');
    }
  }, [inputValue, streaming, conversationId, selectedTaskId, refetchConversations]);

  // 键盘发送
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 新建对话
  const handleNewChat = () => {
    setConversationId(null);
    setMessages([]);
    setStreamingContent('');
    setError(null);
  };

  // 加载历史对话
  const handleSelectConversation = useCallback(async (convId: string) => {
    if (convId === conversationId) return;
    setConversationId(convId);
    setStreamingContent('');
    setError(null);
    setLoadingConv(true);
    try {
      const detail = await getConversation(convId);
      setMessages(detail.messages ?? []);
      if (detail.task_id) {
        setSelectedTaskId(detail.task_id);
      }
    } catch {
      setError('加载对话失败');
      setMessages([]);
    } finally {
      setLoadingConv(false);
    }
  }, [conversationId]);

  // 选定任务
  const selectedTask = tasks.find((t) => t.id === selectedTaskId);

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-4">
      {/* 左侧栏 */}
      <aside className="w-72 shrink-0 flex flex-col bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* 任务选择器 — 自定义下拉 */}
        <div className="p-3 border-b border-gray-100 relative" ref={taskDropdownRef}>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">关联任务（可选）</label>

          {/* 触发器 */}
          <button
            type="button"
            onClick={() => setTaskDropdownOpen((v) => !v)}
            className={cn(
              'w-full flex items-center gap-2 rounded-lg border px-2.5 py-2 text-sm transition-colors',
              'hover:border-primary-400 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none',
              taskDropdownOpen ? 'border-primary-500 ring-1 ring-primary-500' : 'border-gray-300',
            )}
          >
            {selectedTask ? (
              <>
                <span className="flex-1 text-left truncate text-gray-800 font-medium">
                  {selectedTask.title}
                </span>
                <span
                  className={cn(
                    'shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                    STATUS_STYLE[selectedTask.status],
                  )}
                >
                  {STATUS_LABEL[selectedTask.status]}
                </span>
              </>
            ) : (
              <span className="flex-1 text-left text-gray-400">不关联任务</span>
            )}
            <svg
              className={cn('w-4 h-4 text-gray-400 shrink-0 transition-transform', taskDropdownOpen && 'rotate-180')}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* 下拉面板 */}
          {taskDropdownOpen && (
            <div className="absolute z-50 mt-1 w-[calc(100%-1.5rem)] bg-white rounded-lg border border-gray-200 shadow-lg overflow-hidden">
              {/* 搜索框 */}
              <div className="p-2 border-b border-gray-100">
                <input
                  type="text"
                  placeholder="搜索任务标题 / 类型 / ID..."
                  value={taskSearch}
                  onChange={(e) => setTaskSearch(e.target.value)}
                  autoFocus
                  className="w-full text-xs rounded-md border border-gray-200 px-2.5 py-1.5 outline-none focus:border-primary-400 bg-gray-50"
                />
              </div>

              {/* 列表 */}
              <div className="max-h-64 overflow-y-auto">
                {/* 不关联 */}
                <button
                  type="button"
                  onClick={() => { setSelectedTaskId(''); setTaskDropdownOpen(false); setTaskSearch(''); }}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors text-left',
                    !selectedTaskId ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:bg-gray-50',
                  )}
                >
                  <span className="flex-1">不关联任务</span>
                  {!selectedTaskId && <span className="text-primary-500 text-xs">→ 当前</span>}
                </button>

                {filteredTasks.length === 0 && (
                  <div className="px-3 py-4 text-xs text-gray-400 text-center">
                    {taskSearch ? '无匹配任务' : '暂无任务'}
                  </div>
                )}

                {filteredTasks.map((t) => {
                  const isSelected = t.id === selectedTaskId;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => { setSelectedTaskId(t.id); setTaskDropdownOpen(false); setTaskSearch(''); }}
                      className={cn(
                        'w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors border-b border-gray-50 last:border-0',
                        isSelected ? 'bg-primary-50' : 'hover:bg-gray-50',
                      )}
                    >
                      {/* 选中指示箭头 */}
                      <span
                        className={cn(
                          'shrink-0 text-xs w-5 text-center transition-all',
                          isSelected ? 'text-primary-500 font-bold' : 'text-transparent',
                        )}
                      >
                        →
                      </span>

                      {/* 任务信息 */}
                      <div className="flex-1 min-w-0">
                        <div className={cn('text-sm truncate', isSelected ? 'text-primary-700 font-medium' : 'text-gray-800')}>
                          {t.title}
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-[10px] text-gray-400 bg-gray-100 px-1 py-0.5 rounded">
                            {TYPE_LABEL[t.task_type] ?? t.task_type}
                          </span>
                          <span
                            className={cn(
                              'text-[10px] px-1 py-0.5 rounded font-medium',
                              STATUS_STYLE[t.status],
                            )}
                          >
                            {STATUS_LABEL[t.status]}
                          </span>
                        </div>
                      </div>

                      {/* hover 时显示箭头 */}
                      <span
                        className={cn(
                          'shrink-0 text-gray-300 transition-all text-xs',
                          isSelected ? 'opacity-0' : 'opacity-0 group-hover:opacity-100',
                        )}
                      />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* 已选任务摘要 */}
          {selectedTask && (
            <div className="mt-2 p-2.5 bg-blue-50 rounded-lg border border-blue-100">
              <div className="flex items-center gap-2">
                <span className="text-blue-500 text-xs">→</span>
                <span className="text-xs font-medium text-blue-800 truncate">{selectedTask.title}</span>
              </div>
              <div className="flex items-center gap-1.5 mt-1.5 ml-5">
                <span className="text-[10px] text-blue-500 bg-blue-100 px-1.5 py-0.5 rounded font-medium">
                  {TYPE_LABEL[selectedTask.task_type] ?? selectedTask.task_type}
                </span>
                <span
                  className={cn(
                    'text-[10px] px-1.5 py-0.5 rounded font-medium',
                    STATUS_STYLE[selectedTask.status],
                  )}
                >
                  {STATUS_LABEL[selectedTask.status]}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* 新建对话 */}
        <button
          onClick={handleNewChat}
          className="m-3 px-3 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
        >
          + 新建对话
        </button>

        {/* 对话列表 */}
        <div className="flex-1 overflow-y-auto px-2 pb-2">
          <div className="text-xs font-medium text-gray-400 px-2 py-1">历史对话</div>
          {convList.length === 0 && (
            <div className="text-xs text-gray-400 text-center py-4">暂无对话</div>
          )}
          {convList.map((conv) => (
            <button
              key={conv.id}
              onClick={() => handleSelectConversation(conv.id)}
              className={cn(
                'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors mb-0.5',
                conversationId === conv.id
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-50',
              )}
            >
              <div className="truncate font-medium text-xs">{conv.first_message || '新对话'}</div>
              <div className="text-xs text-gray-400 mt-0.5">
                {conv.message_count} 条消息
                {conv.task_id && ' · 已关联任务'}
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* 聊天主区域 */}
      <main className="flex-1 flex flex-col bg-white rounded-lg border border-gray-200 overflow-hidden min-w-0">
        {/* 消息区 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loadingConv && (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <div className="animate-spin w-6 h-6 border-2 border-primary-300 border-t-primary-600 rounded-full mx-auto mb-3" />
                <div className="text-sm">加载对话中...</div>
              </div>
            </div>
          )}
          {!loadingConv && messages.length === 0 && !streaming && (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <div className="text-4xl mb-3">💬</div>
                <div className="text-sm">选择任务后开始对话，AI 将结合任务上下文回答</div>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={cn('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center text-xs shrink-0 mt-0.5">
                  AI
                </div>
              )}
              <div
                className={cn(
                  'max-w-[75%] rounded-xl px-4 py-2.5 text-sm leading-relaxed',
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-800',
                )}
              >
                {msg.role === 'assistant' ? <ChatMarkdown content={msg.content} /> : msg.content}
              </div>
              {msg.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-gray-300 flex items-center justify-center text-xs shrink-0 mt-0.5 text-white">
                  U
                </div>
              )}
            </div>
          ))}

          {/* 流式输出 */}
          {streaming && streamingContent && (
            <div className="flex gap-3 justify-start">
              <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center text-xs shrink-0 mt-0.5">
                AI
              </div>
              <div className="max-w-[75%] rounded-xl px-4 py-2.5 text-sm bg-gray-100 text-gray-800">
                <ChatMarkdown content={streamingContent} />
                <span className="inline-block w-1.5 h-4 bg-primary-500 animate-pulse ml-0.5 align-text-bottom" />
              </div>
            </div>
          )}

          {streaming && !streamingContent && (
            <div className="flex gap-3 justify-start">
              <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center text-xs shrink-0">AI</div>
              <div className="bg-gray-100 rounded-xl px-4 py-3">
                <span className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="text-center text-sm text-red-500 py-2">{error}</div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区 */}
        <div className="border-t border-gray-200 p-3">
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息，Enter 发送，Shift+Enter 换行..."
              rows={1}
              disabled={streaming}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 disabled:bg-gray-50"
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || streaming}
              className="shrink-0 w-10 h-10 rounded-xl bg-primary-600 text-white flex items-center justify-center hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
