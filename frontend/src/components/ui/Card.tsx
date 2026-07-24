import { type ReactNode } from 'react';
import { cn } from '@/utils/cn';

interface CardProps {
  title?: string;
  subtitle?: string;
  headerAction?: ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  children: ReactNode;
  className?: string;
}

export function Card({
  title,
  subtitle,
  headerAction,
  padding = 'md',
  hoverable = false,
  children,
  className,
}: CardProps) {
  const paddingStyles: Record<string, string> = {
    none: '',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-6',
  };

  return (
    <div
      className={cn(
        'bg-white rounded-xl border border-gray-200 shadow-sm',
        hoverable && 'hover:shadow-md transition-shadow',
        className,
      )}
    >
      {(title || headerAction) && (
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <div>
            {title && <h3 className="font-semibold text-gray-800">{title}</h3>}
            {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
          </div>
          {headerAction && <div>{headerAction}</div>}
        </div>
      )}
      <div className={paddingStyles[padding]}>{children}</div>
    </div>
  );
}
