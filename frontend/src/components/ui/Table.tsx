import { type ReactNode } from 'react';
import { cn } from '@/utils/cn';
import { Spinner } from './Spinner';
import { EmptyState } from './EmptyState';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface TableColumn<T = any> {
  key: string;
  title: string;
  dataIndex?: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
  render?: (value: unknown, record: T, index: number) => ReactNode;
  className?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TableProps<T = any> {
  columns: TableColumn<T>[];
  data: T[];
  loading?: boolean;
  rowKey?: string | ((record: T) => string);
  onRowClick?: (record: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  className?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function Table<T = any>({
  columns,
  data,
  loading = false,
  rowKey,
  onRowClick,
  emptyTitle = '暂无数据',
  emptyDescription = '当前列表为空',
  className,
}: TableProps<T>) {
  const getRowKey = (record: T, index: number): string => {
    if (typeof rowKey === 'function') return rowKey(record);
    if (typeof rowKey === 'string') return String((record as Record<string, unknown>)[rowKey] ?? index);
    return String(index);
  };

  if (loading) {
    return (
      <div className={cn('bg-white rounded-xl border border-gray-200 shadow-sm', className)}>
        <div className="flex items-center justify-center py-16">
          <Spinner size="lg" className="text-gray-400" />
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={cn('bg-white rounded-xl border border-gray-200 shadow-sm', className)}>
        <EmptyState title={emptyTitle} description={emptyDescription} />
      </div>
    );
  }

  return (
    <div className={cn('bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-5 py-3 font-medium whitespace-nowrap',
                    col.align === 'center' && 'text-center',
                    col.align === 'right' && 'text-right',
                    col.align === 'left' && 'text-left',
                    !col.align && 'text-left',
                    col.className,
                  )}
                  style={col.width ? { width: col.width } : undefined}
                >
                  {col.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((record, index) => (
              <tr
                key={getRowKey(record, index)}
                onClick={() => onRowClick?.(record)}
                className={cn(
                  'transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-gray-50',
                )}
              >
                {columns.map((col) => {
                  const value = col.dataIndex ? (record as Record<string, unknown>)[col.dataIndex] : undefined;
                  return (
                    <td
                      key={col.key}
                      className={cn(
                        'px-5 py-3 text-gray-700',
                        col.align === 'center' && 'text-center',
                        col.align === 'right' && 'text-right',
                        col.align === 'left' && 'text-left',
                        !col.align && 'text-left',
                        col.className,
                      )}
                    >
                      {col.render ? col.render(value, record, index) : (value as ReactNode) ?? '-'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
