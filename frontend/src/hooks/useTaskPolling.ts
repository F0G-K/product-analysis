import { useEffect, useRef, useState } from 'react';
import type { TaskStatus } from '@/types/task';
import { getTask } from '@/services/tasks';

export function useTaskPolling(
  taskId: string | undefined,
  enabled = true,
  interval = 15_000,
) {
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [data, setData] = useState<unknown>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (!taskId || !enabled) return;

    const terminalStatuses: TaskStatus[] = ['completed', 'failed', 'cancelled'];

    const poll = async () => {
      setIsPolling(true);
      try {
        const res = await getTask(taskId);
        if (res.code === 0) {
          const taskStatus = res.data.status;
          setStatus(taskStatus);
          setData(res.data);
          if (terminalStatuses.includes(taskStatus)) {
            clearInterval(timerRef.current);
            setIsPolling(false);
          }
        }
      } catch {
        /* silent fail */
      }
    };

    poll(); // immediate first poll
    timerRef.current = setInterval(poll, interval);

    return () => {
      clearInterval(timerRef.current);
      setIsPolling(false);
    };
  }, [taskId, enabled, interval]);

  return { status, data, isPolling };
}
