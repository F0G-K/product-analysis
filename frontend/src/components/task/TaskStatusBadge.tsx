import { cn } from '@/utils/cn';
import type { TaskStatus } from '@/types/task';
import { TASK_STATUS_MAP } from '@/utils/constants';

interface TaskStatusBadgeProps {
  status: TaskStatus;
  withDot?: boolean;
  className?: string;
}

const colorMap: Record<TaskStatus, string> = {
  draft: 'bg-gray-100 text-gray-700',
  validating: 'bg-blue-100 text-blue-700',
  analyzing: 'bg-indigo-100 text-indigo-700',
  pending_review: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500 line-through',
};

export function TaskStatusBadge({ status, withDot = false, className }: TaskStatusBadgeProps) {
  const info = TASK_STATUS_MAP[status];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        colorMap[status],
        status === 'analyzing' && 'animate-pulse',
        className,
      )}
    >
      {withDot && (
        <span
          className={cn(
            'w-1.5 h-1.5 rounded-full',
            status === 'analyzing' ? 'bg-indigo-500' : 'bg-current opacity-70',
          )}
        />
      )}
      {info?.label ?? status}
    </span>
  );
}
