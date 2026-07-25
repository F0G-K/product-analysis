import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { listTasks } from '@/services/tasks';
import { useDebounce } from '@/hooks/useDebounce';
import { usePagination } from '@/hooks/usePagination';
import { useProjectStore } from '@/stores/projectStore';
import { Table, type TableColumn } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { SearchInput } from '@/components/ui/SearchInput';
import { FilterBar } from '@/components/ui/FilterBar';
import { Pagination as PaginationUI } from '@/components/ui/Pagination';
import { TaskStatusBadge } from '@/components/task/TaskStatusBadge';
import { Select } from '@/components/ui/Select';
import { formatDate } from '@/utils/format';
import type { Task } from '@/types/task';
import { CreateAnalysisDialog } from '@/components/create/CreateAnalysisDialog';

const columns: TableColumn<Task>[] = [
  { key: 'title', title: '归因任务', dataIndex: 'title', render: (v) => (
    <span className="font-medium text-gray-800">{String(v ?? '-')}</span>
  )},
  { key: 'status', title: '状态', align: 'center', render: (_, r) => (
    <TaskStatusBadge status={r.status} />
  )},
  { key: 'creator', title: '创建人', render: (_, r) => r.created_by.name ?? '我' },
  { key: 'time', title: '时间', render: (_, r) => (
    <span className="text-xs text-gray-400">{formatDate(r.created_at)}</span>
  )},
];

export function AttributionListPage() {
  const navigate = useNavigate();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const { page, pageSize, setPage } = usePagination();
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', 'attribution', { page, pageSize, status, search: debouncedSearch, projectId: currentProjectId }],
    queryFn: () => listTasks({
      task_type: 'attribution',
      page,
      page_size: pageSize,
      ...(status && { status }),
      ...(debouncedSearch && { search: debouncedSearch }),
      ...(currentProjectId && { project_id: currentProjectId }),
    }),
  });

  const total = data?.data?.total ?? 0;
  const items = data?.data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">上线问题归因</h1>
          <p className="text-xs text-gray-400 mt-0.5">版本分析 · 时间线 · 归因推理</p>
        </div>
        <Button variant="primary" onClick={() => setCreateOpen(true)}>+ 新建归因</Button>
      </div>

      <FilterBar>
        <SearchInput value={search} onChange={setSearch} placeholder="搜索归因任务..." className="flex-1 min-w-[200px] max-w-sm" />
        <Select value={status} onChange={setStatus} placeholder="全部状态" options={[
          { value: 'pending_review', label: '待确认' },
          { value: 'completed', label: '已完成' },
          { value: 'analyzing', label: '分析中' },
        ]} />
        <Select placeholder="全部时间" options={[
          { value: '7d', label: '近7天' }, { value: '30d', label: '近30天' },
        ]} />
      </FilterBar>

      <div className="flex items-center gap-2 text-sm text-gray-500">
        <span>共 <strong className="text-gray-800">{total}</strong> 条记录</span>
      </div>

      <Table columns={columns} data={items} loading={isLoading} rowKey="id" onRowClick={(r) => navigate(`/attribution/${r.id}`)} />
      <PaginationUI current={page} total={total} pageSize={pageSize} onChange={setPage} />
      <CreateAnalysisDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        initialTaskType="attribution"
      />
    </div>
  );
}
