import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getCheckTaskDetail, getCheckIssueList } from '@/services/consistency';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { TaskStatusBadge } from '@/components/task/TaskStatusBadge';
import { ISSUE_LEVEL_MAP } from '@/utils/constants';
import type { CheckIssue, IssueLevel } from '@/types/consistency';
import { getTask } from '@/services/tasks';
import { TaskDispatchButton } from '@/components/task/TaskDispatchButton';

const levelColors: Record<IssueLevel, 'red' | 'amber' | 'blue' | 'gray'> = {
  blocker: 'red',
  critical: 'amber',
  general: 'blue',
  info: 'gray',
};

export function ConsistencyDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();

  const { data: taskRes, isLoading } = useQuery({
    queryKey: ['check-task', taskId],
    queryFn: async () => {
      try {
        return await getCheckTaskDetail(taskId!);
      } catch {
        const response = await getTask(taskId!);
        return { ...response, data: { ...response.data, baseline_id: '', involved_deliverables: [] } };
      }
    },
    enabled: !!taskId,
  });

  const { data: issuesRes } = useQuery({
    queryKey: ['check-issues', taskId],
    queryFn: () => getCheckIssueList(taskId!),
    enabled: !!taskId && taskRes?.data?.status !== 'draft',
  });

  const task = taskRes?.data;
  const issues = issuesRes?.data?.items ?? [];

  if (isLoading) {
    return <div className="space-y-6"><Skeleton variant="rectangular" height="150px" /><Skeleton count={8} /></div>;
  }

  if (!task) return <div className="text-center py-16 text-gray-400">任务不存在</div>;

  const issueCounts = { blocker: 0, critical: 0, general: 0, info: 0 };
  issues.forEach((i) => { issueCounts[i.level]++; });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/consistency" className="text-gray-400 hover:text-gray-600">←</Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-gray-800">{task.title ?? '一致性检查'}</h1>
              <TaskStatusBadge status={task.status} />
            </div>
            <div className="text-xs text-gray-400 mt-0.5">基线 {task.baseline_name ?? '-'} · 任务 #{taskId?.slice(0, 8)}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary">导出报告</Button>
          {task.status === 'draft' ? <TaskDispatchButton taskId={task.id} /> : <Button variant="primary">发起复检</Button>}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issue Overview */}
        <div className="lg:col-span-2">
          <Card title="问题列表" subtitle={`共 ${issues.length} 项`}>
            <div className="divide-y divide-gray-100 -mx-5 -mb-5">
              {issues.length === 0 ? (
                <div className="text-center py-8 text-sm text-gray-400">暂无问题</div>
              ) : (
                issues.map((issue) => (
                  <div key={issue.id} className="px-5 py-3 hover:bg-gray-50">
                    <div className="flex items-start gap-3">
                      <Badge variant={levelColors[issue.level]}>{ISSUE_LEVEL_MAP[issue.level]?.label ?? issue.level}</Badge>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-800">{issue.title}</h4>
                        <p className="text-xs text-gray-500 mt-1">{issue.description ?? '暂无描述'}</p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                          <span>维度: {issue.dimension}</span>
                          <span>置信度: {issue.confidence}</span>
                          {issue.status && <Badge variant="gray">{issue.status}</Badge>}
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Summary */}
        <div>
          <Card title="问题概览">
            <div className="space-y-3">
              {(['blocker', 'critical', 'general', 'info'] as IssueLevel[]).map((level) => (
                <div key={level} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 flex items-center gap-2">
                    <span className={`w-3 h-3 rounded-full bg-${levelColors[level]}-500`} />
                    {ISSUE_LEVEL_MAP[level]?.label ?? level}
                  </span>
                  <span className={`text-lg font-bold text-${levelColors[level]}-600`}>{issueCounts[level]}</span>
                </div>
              ))}
              <div className="pt-3 border-t flex justify-between text-sm">
                <span className="text-gray-500">总计</span>
                <span className="font-bold text-gray-800">{issues.length} 项</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
