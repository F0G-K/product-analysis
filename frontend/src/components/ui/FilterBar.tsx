import { type ReactNode } from 'react';
import { cn } from '@/utils/cn';

interface FilterBarProps {
  children: ReactNode;
  onReset?: () => void;
  className?: string;
}

export function FilterBar({ children, onReset, className }: FilterBarProps) {
  return (
    <div className={cn('bg-white rounded-xl border border-gray-200 shadow-sm p-4', className)}>
      <div className="flex items-center gap-3 flex-wrap">
        {children}
        {onReset && (
          <button
            onClick={onReset}
            className="text-sm text-gray-400 hover:text-gray-600 transition-colors ml-auto"
          >
            重置
          </button>
        )}
      </div>
    </div>
  );
}
