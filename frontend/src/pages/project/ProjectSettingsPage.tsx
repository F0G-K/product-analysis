import { useParams, Link } from 'react-router-dom';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useState } from 'react';

export function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to={`/projects/${projectId}`} className="text-gray-400 hover:text-gray-600">←</Link>
        <h1 className="text-lg font-semibold text-gray-800">项目设置</h1>
      </div>

      <Card title="基本信息">
        <div className="space-y-4 max-w-lg">
          <Input label="项目名称" value={name} onChange={(e) => setName(e.target.value)} placeholder="请输入项目名称" />
          <Input label="项目描述" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="请输入项目描述" />
          <Button variant="primary">保存修改</Button>
        </div>
      </Card>

      <Card title="危险操作">
        <div className="space-y-3">
          <p className="text-sm text-gray-500">删除项目将软删除所有关联数据，90天后自动清理</p>
          <Button variant="danger">删除项目</Button>
        </div>
      </Card>
    </div>
  );
}
