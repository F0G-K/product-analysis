import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAttributionDetail, getTimeline, getAttributionResults } from '@/services/attribution';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import { TaskStatusBadge } from '@/components/task/TaskStatusBadge';
import { CONFIDENCE_MAP, ATTRIBUTION_CATEGORY_MAP } from '@/utils/constants';
import { formatDate } from '@/utils/format';
import { useState } from 'react';
import type { TimelineEvent } from '@/types/attribution';

export function AttributionDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [tab, setTab] = useState('timeline');

  const { data: taskRes, isLoading } = useQuery({
    queryKey: ['attribution', taskId],
    queryFn: () => getAttributionDetail(taskId!),
    enabled: !!taskId,
  });

  const { data: timelineRes } = useQuery({
    queryKey: ['attribution-timeline', taskId],
    queryFn: () => getTimeline(taskId!),
    enabled: !!taskId,
  });

  const { data: resultsRes } = useQuery({
    queryKey: ['attribution-results', taskId],
    queryFn: () => getAttributionResults(taskId!),
    enabled: !!taskId,
  });

  const task = taskRes?.data;
  const timeline = timelineRes?.data?.items ?? [];
  const results = resultsRes?.data ?? [];

  if (isLoading) {
    return <div className="space-y-6"><Skeleton variant="rectangular" height="150px" /><Skeleton count={8} /></div>;
  }

  if (!task) return <div className="text-center py-16 text-gray-400">任务不存在</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/attribution" className="text-gray-400 hover:text-gray-600">←</Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-gray-800">{task.title ?? '问题归因分析'}</h1>
              <TaskStatusBadge status={task.status} />
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              版本 {task.version_number ?? '-'} · 任务 #{taskId?.slice(0, 8)}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary">导出报告</Button>
          {task.status === 'pending_review' && (
            <Button variant="primary">确认结论</Button>
          )}
        </div>
      </div>

      {/* Anomaly Info */}
      {task.anomaly_description && (
        <Card title="异常概述">
          <p className="text-sm text-gray-600">{task.anomaly_description}</p>
          {task.impact_scope && (
            <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
              <div><span className="text-gray-400">影响范围:</span> <span className="text-gray-700">{task.impact_scope}</span></div>
              {task.user_impact && <div><span className="text-gray-400">用户影响:</span> <span className="text-gray-700">{task.user_impact}</span></div>}
            </div>
          )}
        </Card>
      )}

      <Tabs
        tabs={[
          { key: 'timeline', label: '事件时间线', count: timeline.length },
          { key: 'results', label: '归因结果', count: results.length },
          { key: 'evidence', label: '证据链' },
        ]}
        activeKey={tab}
        onChange={setTab}
      />

      <div className="min-h-[200px]">
        {tab === 'timeline' && (
          <div className="space-y-0">
            {timeline.length === 0 ? (
              <div className="text-center py-8 text-sm text-gray-400">暂无时间线事件</div>
            ) : (
              <div className="relative pl-8 border-l-2 border-gray-200 space-y-6">
                {timeline.map((event: TimelineEvent, idx: number) => (
                  <div key={event.id || idx} className="relative">
                    <div className="absolute -left-[25px] w-3 h-3 rounded-full bg-primary-500 border-2 border-white mt-1" />
                    <div className="text-xs text-gray-400">{formatDate(event.original_timestamp)}</div>
                    <div className="text-sm font-medium text-gray-800 mt-0.5">{event.summary}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="gray" size="sm">{event.event_source}</Badge>
                      {event.credibility && (
                        <span className={`text-xs ${event.credibility === 'confirmed' ? 'text-green-600' : 'text-amber-600'}`}>
                          {event.credibility === 'confirmed' ? '已确认' : '待确认'}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'results' && (
          <div className="space-y-4">
            {results.length === 0 ? (
              <div className="text-center py-8 text-sm text-gray-400">分析进行中，结果即将生成...</div>
            ) : (
              results.map((result, idx) => (
                <Card key={idx} title={result.category ? ATTRIBUTION_CATEGORY_MAP[result.category]?.label ?? result.category : '归因结论'}>
                  <div className="flex items-center gap-2 mb-2">
                    {result.is_primary && <Badge variant="amber">主要</Badge>}
                    <Badge variant={CONFIDENCE_MAP[result.confidence]?.color as 'green' | 'amber' | 'red'}>
                      置信度: {CONFIDENCE_MAP[result.confidence]?.label ?? result.confidence}
                    </Badge>
                  </div>
                  {result.reasoning_chain && (
                    <p className="text-sm text-gray-600 mt-2">{result.reasoning_chain}</p>
                  )}
                  {result.short_term_mitigation && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <span className="text-xs font-medium text-gray-500">短期措施:</span>
                      <p className="text-sm text-gray-600 mt-1">{result.short_term_mitigation}</p>
                    </div>
                  )}
                  {result.long_term_improvement && (
                    <div className="mt-2">
                      <span className="text-xs font-medium text-gray-500">长期改进:</span>
                      <p className="text-sm text-gray-600 mt-1">{result.long_term_improvement}</p>
                    </div>
                  )}
                </Card>
              ))
            )}
          </div>
        )}

        {tab === 'evidence' && (
          <div className="space-y-4">
            {results.flatMap((r) => [
              ...(r.supporting_evidence ?? []),
              ...(r.counter_evidence ?? []),
              ...(r.missing_evidence ?? []),
            ]).length === 0 ? (
              <div className="text-center py-8 text-sm text-gray-400">暂无证据数据</div>
            ) : (
              results.map((result, idx) => (
                <Card key={`ev-${idx}`} title={`证据 - ${result.category}`}>
                  {['supporting_evidence', 'counter_evidence', 'missing_evidence'].map((key) => {
                    const items = result[key as keyof typeof result];
                    if (!Array.isArray(items) || items.length === 0) return null;
                    const label = key === 'supporting_evidence' ? '支持证据' : key === 'counter_evidence' ? '反向证据' : '缺失证据';
                    return (
                      <div key={key} className="mb-3">
                        <span className="text-xs font-medium text-gray-500">{label}:</span>
                        {items.map((item, i) => (
                          <div key={i} className="mt-1 text-sm text-gray-600 pl-2 border-l-2 border-gray-200">
                            {item.excerpt ?? item.citation ?? item.source_label ?? '--'}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
