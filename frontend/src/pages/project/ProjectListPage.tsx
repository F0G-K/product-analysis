import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { listProjects } from '@/services/projects';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatDate } from '@/utils/format';
import { CreateProjectDialog } from '@/components/create/CreateProjectDialog';

export function ProjectListPage() {
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => listProjects(),
  });

  const projects = data?.data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">项目与数据源</h1>
          <p className="text-xs text-gray-400 mt-0.5">项目概览 · 数据源管理 · 成员协作</p>
        </div>
        <Button variant="primary" onClick={() => setCreateOpen(true)}>+ 新建项目</Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <Skeleton key={i} variant="rectangular" height="150px" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <Card
              key={project.id}
              title={project.name}
              subtitle={project.description}
              hoverable
              className="cursor-pointer"
            >
              <div onClick={() => navigate(`/projects/${project.id}`)}>
                <div className="flex items-center gap-2 mb-3">
                  <Badge variant={project.status === 'active' ? 'green' : 'gray'}>
                    {project.status === 'active' ? '活跃' : project.status}
                  </Badge>
                  {project.timezone && <span className="text-xs text-gray-400">{project.timezone}</span>}
                </div>
                <div className="text-xs text-gray-400">
                  创建于 {formatDate(project.created_at)}
                </div>
              </div>
            </Card>
          ))}
          {projects.length === 0 && (
            <div className="col-span-full text-center py-16 text-gray-400">
              暂无项目，点击上方按钮创建
            </div>
          )}
        </div>
      )}

      <CreateProjectDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
