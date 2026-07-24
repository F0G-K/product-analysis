import { type FC, type ReactNode, useCallback } from 'react';
import { cn } from '@/utils/cn';
import { Spinner } from './Spinner';

export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  type?: 'button' | 'submit' | 'reset';
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}

export const Button: FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  fullWidth = false,
  type = 'button',
  leftIcon,
  rightIcon,
  children,
  onClick,
  className,
}) => {
  const handleClick = useCallback(() => {
    if (loading || disabled) return;
    onClick?.();
  }, [loading, disabled, onClick]);

  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        // variant
        variant === 'primary' && 'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800',
        variant === 'secondary' && 'bg-gray-100 text-gray-900 hover:bg-gray-200 active:bg-gray-300',
        variant === 'danger' && 'bg-red-600 text-white hover:bg-red-700 active:bg-red-800',
        variant === 'ghost' && 'text-gray-600 hover:bg-gray-100 active:bg-gray-200',
        variant === 'outline' && 'border border-gray-300 text-gray-700 hover:bg-gray-50 active:bg-gray-100',
        // size
        size === 'sm' && 'h-8 px-3 text-xs gap-1.5',
        size === 'md' && 'h-10 px-4 text-sm gap-2',
        size === 'lg' && 'h-12 px-6 text-base gap-2.5',
        // width
        fullWidth && 'w-full',
        className,
      )}
      disabled={disabled || loading}
      onClick={handleClick}
    >
      {loading && <Spinner size="sm" className="shrink-0" />}
      {!loading && leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  );
};
