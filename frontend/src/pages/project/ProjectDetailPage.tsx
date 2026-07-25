import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getProject } from '@/services/projects';
import { listDataSources } from '@/services/projects';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import { useState } from 'react';
import { formatDate } from '@/utils/format';
import { CreateAnalysisDialog } from '@/components/create/CreateAnalysisDialog';

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [tab, setTab] = useState('overview');
  const [createOpen, setCreateOpen] = useState(false);

  const { data: projectRes, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId!),
    enabled: !!projectId,
  });

  const { data: dsRes } = useQuery({
    queryKey: ['project-datasources', projectId],
    queryFn: () => listDataSources(projectId!),
    enabled: !!projectId && tab === 'datasources',
  });

  const project = projectRes?.data;
  const dataSources = dsRes?.data?.items ?? [];

  if (isLoading) return <Skeleton count={5} />;
  if (!project) return <div className="text-center py-16 text-gray-400">项目不存在</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/projects" className="text-gray-400 hover:text-gray-600">←</Link>
          <div>
            <h1 className="text-lg font-semibold text-gray-800">{project.name}</h1>
            <p className="text-xs text-gray-400">{project.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to={`/projects/${projectId}/settings`}>
            <Button variant="secondary">项目设置</Button>
          </Link>
          <Button variant="primary" onClick={() => setCreateOpen(true)}>新建分析</Button>
        </div>
      </div>

      <Tabs
        tabs={[
          { key: 'overview', label: '概览' },
          { key: 'datasources', label: '数据源', count: dataSources.length },
          { key: 'members', label: '成员' },
        ]}
        activeKey={tab}
        onChange={setTab}
      />

      {tab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card title="项目信息">
            <div className="space-y-2 text-sm">
              <div><span className="text-gray-400">名称:</span> <span className="text-gray-700">{project.name}</span></div>
              <div><span className="text-gray-400">描述:</span> <span className="text-gray-700">{project.description ?? '-'}</span></div>
              <div><span className="text-gray-400">状态:</span> <Badge variant={project.status === 'active' ? 'green' : 'gray'}>{project.status}</Badge></div>
              <div><span className="text-gray-400">时区:</span> <span className="text-gray-700">{project.timezone ?? 'Asia/Shanghai'}</span></div>
              <div><span className="text-gray-400">创建时间:</span> <span className="text-gray-700">{formatDate(project.created_at)}</span></div>
            </div>
          </Card>
          <Card title="活跃统计">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-indigo-50 rounded-lg">
                <div className="text-2xl font-bold text-indigo-600">--</div>
                <div className="text-xs text-gray-500">评估任务</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">--</div>
                <div className="text-xs text-gray-500">数据源</div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {tab === 'datasources' && (
        <Card title="数据源列表">
          {dataSources.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-400">暂无数据源</div>
          ) : (
            <div className="divide-y divide-gray-100 -mx-5 -mb-5">
              {dataSources.map((ds) => (
                <div key={ds.id} className="px-5 py-3 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-800">{ds.name}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{ds.source_type} · {ds.status}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${ds.status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`} />
                    <span className="text-xs text-gray-500">{ds.status === 'connected' ? '已连接' : '未连接'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === 'members' && (
        <div className="text-center py-8 text-sm text-gray-400">成员管理（功能开发中）</div>
      )}

      <CreateAnalysisDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        initialProjectId={projectId}
        initialTaskType="assessment"
        allowTaskTypeChange
      />
    </div>
  );
}
