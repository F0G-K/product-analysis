import { cn } from '@/utils/cn';

interface BadgeProps {
  variant?: 'gray' | 'blue' | 'indigo' | 'green' | 'amber' | 'red';
  size?: 'sm' | 'md';
  dot?: boolean;
  children?: React.ReactNode;
  className?: string;
}

const variantStyles: Record<string, string> = {
  gray: 'bg-gray-100 text-gray-700',
  blue: 'bg-blue-100 text-blue-700',
  indigo: 'bg-indigo-100 text-indigo-700',
  green: 'bg-green-100 text-green-700',
  amber: 'bg-amber-100 text-amber-700',
  red: 'bg-red-100 text-red-700',
};

export function Badge({ variant = 'gray', size = 'sm', dot = false, children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium',
        size === 'sm' && 'px-2 py-0.5 text-xs',
        size === 'md' && 'px-2.5 py-1 text-sm',
        variantStyles[variant],
        className,
      )}
    >
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full', variant === 'indigo' ? 'bg-indigo-500' : 'bg-current')} />}
      {children}
    </span>
  );
}
