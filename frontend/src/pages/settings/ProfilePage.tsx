import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuthStore } from '@/stores/authStore';
import { useState } from 'react';

export function ProfilePage() {
  const user = useAuthStore((s) => s.user);
  const [name, setName] = useState(user?.name ?? '');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-800">个人设置</h1>
        <p className="text-xs text-gray-400 mt-0.5">管理您的个人资料</p>
      </div>

      <Card title="基本资料">
        <div className="space-y-4 max-w-lg">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-2xl font-bold">
              {user?.name?.[0] ?? 'U'}
            </div>
            <div>
              <div className="text-sm font-medium text-gray-800">{user?.name}</div>
              <div className="text-xs text-gray-400">{user?.email}</div>
            </div>
          </div>
          <Input label="显示名称" value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="邮箱" value={user?.email ?? ''} disabled helperText="邮箱不可修改" />
          <Button variant="primary">保存</Button>
        </div>
      </Card>
    </div>
  );
}
