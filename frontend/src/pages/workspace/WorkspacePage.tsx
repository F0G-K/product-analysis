import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getWorkspace } from '@/services/tasks';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { TaskStatusBadge } from '@/components/task/TaskStatusBadge';
import { formatRelativeTime } from '@/utils/format';

export function WorkspacePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['workspace'],
    queryFn: () => getWorkspace(),
  });

  const workspace = data?.data;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl p-4 border shadow-sm">
              <Skeleton variant="text" className="mb-2" />
              <Skeleton variant="text" width="60%" height="2rem" />
              <Skeleton variant="text" width="80%" className="mt-1" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2">
            <div className="bg-white rounded-xl border shadow-sm p-5">
              <Skeleton count={5} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500">待处理任务</span>
            <span className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center">
              <span className="text-indigo-600 text-sm font-bold">{workspace?.pending_tasks ?? 0}</span>
            </span>
          </div>
          <div className="text-2xl font-bold text-gray-800">{workspace?.pending_tasks ?? 0}</div>
          <div className="text-xs text-gray-400 mt-1">全部待处理</div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500">待确认评估</span>
            <span className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
              <span className="text-amber-600 text-sm font-bold">{workspace?.pending_assessments ?? 0}</span>
            </span>
          </div>
          <div className="text-2xl font-bold text-gray-800">{workspace?.pending_assessments ?? 0}</div>
          <div className="text-xs text-gray-400 mt-1">需求价值评估</div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500">未解决阻断项</span>
            <span className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center">
              <span className="text-red-500 text-sm font-bold">{workspace?.blocker_issues ?? 0}</span>
            </span>
          </div>
          <div className="text-2xl font-bold text-red-600">{workspace?.blocker_issues ?? 0}</div>
          <div className="text-xs text-gray-400 mt-1">一致性检查中</div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500">待确认归因</span>
            <span className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
              <span className="text-blue-600 text-sm font-bold">{workspace?.pending_attribution ?? 0}</span>
            </span>
          </div>
          <div className="text-2xl font-bold text-gray-800">{workspace?.pending_attribution ?? 0}</div>
          <div className="text-xs text-gray-400 mt-1">问题归因</div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500">数据源异常</span>
            <span className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
              <span className={workspace?.data_source_errors ? 'text-red-500' : 'text-green-500'}>
                {workspace?.data_source_errors ?? 0}
              </span>
            </span>
          </div>
          <div className="text-2xl font-bold text-gray-800">{workspace?.data_source_errors ?? 0}</div>
          <div className="text-xs text-gray-400 mt-1">
            {workspace?.data_source_errors ? '需要关注' : '全部正常'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Todos */}
        <div className="lg:col-span-2">
          <Card title="我的待办">
            <div className="divide-y divide-gray-100 -mx-5 -mb-5">
              {workspace?.todos?.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-400">暂无待办事项</div>
              ) : (
                workspace?.todos?.map((task) => (
                  <Link
                    key={task.id}
                    to={getTaskLink(task)}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <TaskStatusBadge status={task.status} />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-800 hover:text-primary-600 truncate block">
                        {task.title}
                      </span>
                      <div className="text-xs text-gray-400 mt-0.5">
                        {task.task_type === 'assessment' && '需求价值评估'}
                        {task.task_type === 'check' && '一致性检查'}
                        {task.task_type === 'attribution' && '问题归因'}
                      </div>
                    </div>
                    <span className="text-xs text-gray-400 whitespace-nowrap">
                      {formatRelativeTime(task.updated_at || task.created_at)}
                    </span>
                  </Link>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Recent Tasks */}
        <div>
          <Card title="最近任务">
            <div className="divide-y divide-gray-100 -mx-5 -mb-5">
              {workspace?.recent_tasks?.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-400">暂无最近任务</div>
              ) : (
                workspace?.recent_tasks?.slice(0, 8).map((task) => (
                  <Link
                    key={task.id}
                    to={getTaskLink(task)}
                    className="flex items-center justify-between px-5 py-2.5 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-gray-700 truncate">{task.title}</div>
                      <div className="text-xs text-gray-400">{formatRelativeTime(task.created_at)}</div>
                    </div>
                    <TaskStatusBadge status={task.status} />
                  </Link>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function getTaskLink(task: { task_type: string; id: string }): string {
  switch (task.task_type) {
    case 'assessment':
      return `/assessment/${task.id}`;
    case 'check':
      return `/consistency/${task.id}`;
    case 'attribution':
      return `/attribution/${task.id}`;
    default:
      return '/';
  }
}
