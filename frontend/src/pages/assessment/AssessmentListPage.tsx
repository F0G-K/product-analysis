import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { listTasks } from '@/services/tasks';
import { useDebounce } from '@/hooks/useDebounce';
import { usePagination } from '@/hooks/usePagination';
import { useProjectStore } from '@/stores/projectStore';
import { Table, type TableColumn } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { SearchInput } from '@/components/ui/SearchInput';
import { FilterBar } from '@/components/ui/FilterBar';
import { Pagination as PaginationUI } from '@/components/ui/Pagination';
import { TaskStatusBadge } from '@/components/task/TaskStatusBadge';
import { Select } from '@/components/ui/Select';
import { PRIORITY_MAP } from '@/utils/constants';
import { formatDate } from '@/utils/format';
import type { Task } from '@/types/task';

const columns: TableColumn<Task>[] = [
  { key: 'title', title: '任务名称', dataIndex: 'title', render: (v, r) => (
    <span className="font-medium text-gray-800">{String(v ?? r.title ?? '-')}</span>
  )},
  { key: 'status', title: '状态', align: 'center', render: (_, r) => (
    <TaskStatusBadge status={r.status} />
  )},
  { key: 'model', title: '模型版本', dataIndex: 'model_version', align: 'center', render: (v) => (
    <span className="text-xs text-gray-500">{String(v ?? '-')}</span>
  )},
  { key: 'creator', title: '创建人', dataIndex: 'created_by_name' },
  { key: 'time', title: '时间', render: (_, r) => (
    <span className="text-xs text-gray-400">{formatDate(r.created_at)}</span>
  )},
];

export function AssessmentListPage() {
  const navigate = useNavigate();
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const { page, pageSize, setPage } = usePagination();
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search);

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', 'assessment', { page, pageSize, status, search: debouncedSearch, projectId: currentProjectId }],
    queryFn: () => listTasks({
      task_type: 'assessment',
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
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-gray-800">需求价值评估</h1>
          <span className="text-xs text-gray-400">评估模型 V2.1 · 大模型版本: Claude-5-Opus</span>
        </div>
        <Button variant="primary">+ 新建评估</Button>
      </div>

      <FilterBar>
        <SearchInput value={search} onChange={setSearch} placeholder="搜索需求名称、编号..." className="flex-1 min-w-[200px] max-w-sm" />
        <Select
          value={status}
          onChange={setStatus}
          placeholder="全部状态"
          options={[
            { value: 'pending_review', label: '待确认' },
            { value: 'completed', label: '已完成' },
            { value: 'analyzing', label: '分析中' },
            { value: 'draft', label: '草稿' },
          ]}
        />
        <Select
          placeholder="全部时间"
          options={[
            { value: '7d', label: '近 7 天' },
            { value: '30d', label: '近 30 天' },
            { value: '90d', label: '近 90 天' },
          ]}
        />
      </FilterBar>

      <div className="flex items-center gap-2 text-sm text-gray-500">
        <span>共 <strong className="text-gray-800">{total}</strong> 条记录</span>
      </div>

      <Table
        columns={columns}
        data={items}
        loading={isLoading}
        rowKey="id"
        onRowClick={(r) => navigate(`/assessment/${r.id}`)}
      />

      <PaginationUI current={page} total={total} pageSize={pageSize} onChange={setPage} />
    </div>
  );
}
