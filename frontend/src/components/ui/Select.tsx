import { type ReactNode } from 'react';
import { cn } from '@/utils/cn';

interface SelectProps {
  label?: string;
  options: { value: string; label: string }[];
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  placeholder?: string;
  fullWidth?: boolean;
  className?: string;
  disabled?: boolean;
}

export function Select({
  label,
  options,
  value,
  onChange,
  error,
  placeholder = '请选择',
  fullWidth,
  className,
  disabled,
}: SelectProps) {
  return (
    <div className={cn('flex flex-col gap-1.5', fullWidth && 'w-full')}>
      {label && <label className="text-sm font-medium text-gray-700">{label}</label>}
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={disabled}
        className={cn(
          'rounded-lg border px-3 py-2 text-sm bg-white transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500',
          'disabled:bg-gray-50 disabled:text-gray-400',
          error ? 'border-red-300' : 'border-gray-300',
          className,
        )}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
