import { cn } from '@/utils/cn';

interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string;
  height?: string;
  count?: number;
  className?: string;
}

export function Skeleton({
  variant = 'text',
  width,
  height,
  count = 1,
  className,
}: SkeletonProps) {
  const baseClass = 'animate-pulse bg-gray-200 rounded';

  const variantClass: Record<string, string> = {
    text: 'h-4 w-full rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  };

  const items = Array.from({ length: count }, (_, i) => (
    <div
      key={i}
      className={cn(baseClass, variantClass[variant], className)}
      style={{ width, height }}
    />
  ));

  return (
    <div className={cn('space-y-2', count > 1 && variant === 'text' && 'space-y-3')}>
      {items}
    </div>
  );
}
