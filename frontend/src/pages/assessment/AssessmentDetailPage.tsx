import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAssessmentDetail } from '@/services/assessment';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import { TaskStatusBadge } from '@/components/task/TaskStatusBadge';
import { PRIORITY_MAP } from '@/utils/constants';
import { useState } from 'react';

export function AssessmentDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [tab, setTab] = useState('scores');

  const { data, isLoading } = useQuery({
    queryKey: ['assessment', taskId],
    queryFn: () => getAssessmentDetail(taskId!),
    enabled: !!taskId,
  });

  const task = data?.data;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="rectangular" height="200px" />
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2"><Skeleton count={5} /></div>
          <div><Skeleton variant="rectangular" height="300px" /></div>
        </div>
      </div>
    );
  }

  if (!task) {
    return <div className="text-center py-16 text-gray-400">任务不存在</div>;
  }

  const dimensions = task.dimensions ?? [];
  const avgTotalScore = dimensions.length > 0
    ? Math.round(dimensions.reduce((s, d) => s + d.converted_score, 0) / dimensions.length)
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/assessment" className="text-gray-400 hover:text-gray-600">←</Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-gray-800">{task.title ?? '需求价值评估'}</h1>
              <TaskStatusBadge status={task.status} />
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              {task.requirement_name ? `需求: ${task.requirement_name} · ` : ''}
              任务 #{task.id.slice(0, 8)} · 模型 {task.model_version ?? '-'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary">导出报告</Button>
          {task.status === 'pending_review' && (
            <Button variant="primary">确认评估</Button>
          )}
        </div>
      </div>

      {/* Score Overview */}
      <Card>
        <div className="flex items-start gap-8 flex-wrap">
          {/* Total Score Circle */}
          <div className="text-center shrink-0">
            <div className="relative w-32 h-32 mx-auto">
              <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="#e5e7eb" strokeWidth="10" />
                <circle
                  cx="60" cy="60" r="52" fill="none" stroke="#6366f1" strokeWidth="10"
                  strokeDasharray="327"
                  strokeDashoffset={327 - (327 * avgTotalScore) / 100}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-gray-800">{avgTotalScore}</span>
                <span className="text-xs text-gray-400">/ 100</span>
              </div>
            </div>
            <div className="mt-2">
              <span className="inline-flex px-3 py-1 rounded-full text-sm font-bold bg-red-100 text-red-700">
                P{avgTotalScore > 80 ? '0' : avgTotalScore > 65 ? '1' : avgTotalScore > 50 ? '2' : '3'}
              </span>
            </div>
          </div>

          {/* Dimension Scores */}
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-5 gap-3">
            {dimensions.map((dim) => {
              const colors: Record<number, string> = {
                0: 'indigo', 1: 'green', 2: 'purple', 3: 'amber', 4: 'red',
              };
              const idx = dimensions.indexOf(dim);
              const color = colors[idx % 5] ?? 'blue';
              return (
                <div key={dim.dimension_name} className={`text-center p-3 rounded-xl bg-${color}-50 border border-${color}-100`}>
                  <div className="text-xs text-gray-500 mb-1">{dim.dimension_name}</div>
                  <div className={`text-2xl font-bold text-${color}-700`}>{dim.raw_score.toFixed(1)}</div>
                  <div className="text-[10px] text-gray-400">权重 {(dim.weight * 100).toFixed(0)}%</div>
                  <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                    <div className={`bg-${color}-500 h-1.5 rounded-full`} style={{ width: `${dim.converted_score}%` }} />
                  </div>
                </div>
              );
            })}
            {dimensions.length === 0 && (
              <div className="col-span-5 text-center text-sm text-gray-400 py-8">暂无维度评分数据</div>
            )}
          </div>
        </div>
      </Card>

      {/* Tabs */}
      <Tabs
        tabs={[
          { key: 'scores', label: '维度评分明细' },
          { key: 'evidence', label: '证据链' },
          { key: 'sensitivity', label: '敏感性分析' },
          { key: 'history', label: '评估历史' },
        ]}
        activeKey={tab}
        onChange={setTab}
      />

      <div className="min-h-[200px]">
        {tab === 'scores' && (
          <div className="space-y-4">
            {dimensions.map((dim) => (
              <Card key={dim.dimension_name} title={dim.dimension_name} subtitle={`权重 ${(dim.weight * 100).toFixed(0)}% · 得分 ${dim.raw_score.toFixed(1)} / 5 · 转换分 ${dim.converted_score} · 置信度 ${dim.confidence}`}>
                {dim.inference_explanation ? (
                  <p className="text-sm text-gray-600">{dim.inference_explanation}</p>
                ) : (
                  <p className="text-sm text-gray-400">暂无分析说明</p>
                )}
                {dim.missing_evidence && dim.missing_evidence.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <span className="text-xs text-amber-600 font-medium">缺失证据:</span>
                    <ul className="mt-1 list-disc list-inside text-xs text-gray-500">
                      {dim.missing_evidence.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
        {tab === 'evidence' && <div className="text-center py-8 text-sm text-gray-400">证据链内容将在此展示</div>}
        {tab === 'sensitivity' && <div className="text-center py-8 text-sm text-gray-400">敏感性分析结果将在此展示</div>}
        {tab === 'history' && <div className="text-center py-8 text-sm text-gray-400">评估历史将在此展示</div>}
      </div>
    </div>
  );
}
