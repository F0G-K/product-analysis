import { cn } from '@/utils/cn';

interface PaginationProps {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  showTotal?: boolean;
  className?: string;
}

export function Pagination({
  current,
  total,
  pageSize,
  onChange,
  onPageSizeChange,
  showTotal = true,
  className,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const getPageNumbers = (): (number | 'ellipsis')[] => {
    const pages: (number | 'ellipsis')[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (current > 3) pages.push('ellipsis');
      for (let i = Math.max(2, current - 1); i <= Math.min(totalPages - 1, current + 1); i++) {
        pages.push(i);
      }
      if (current < totalPages - 2) pages.push('ellipsis');
      pages.push(totalPages);
    }
    return pages;
  };

  if (total === 0) return null;

  return (
    <div className={cn('flex items-center justify-between px-5 py-3', className)}>
      {showTotal && (
        <span className="text-sm text-gray-500">
          共 <strong className="text-gray-800">{total}</strong> 条
        </span>
      )}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(current - 1)}
          disabled={current <= 1}
          className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          上一页
        </button>
        {getPageNumbers().map((page, idx) =>
          page === 'ellipsis' ? (
            <span key={`e-${idx}`} className="px-2 text-gray-400">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onChange(page)}
              className={cn(
                'w-9 h-9 text-sm rounded-lg transition-colors',
                page === current
                  ? 'bg-primary-600 text-white'
                  : 'hover:bg-gray-100 text-gray-700',
              )}
            >
              {page}
            </button>
          ),
        )}
        <button
          onClick={() => onChange(current + 1)}
          disabled={current >= totalPages}
          className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          下一页
        </button>
        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="ml-2 text-sm border rounded-lg px-2 py-1.5 text-gray-600"
          >
            {[10, 20, 50, 100].map((s) => (
              <option key={s} value={s}>
                {s} 条/页
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
