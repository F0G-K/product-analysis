import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { getSessions, getMfaStatus } from '@/services/auth';
import { formatDate } from '@/utils/format';

export function SecurityPage() {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const { data: sessionsRes } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => getSessions(),
  });

  const { data: mfaRes } = useQuery({
    queryKey: ['mfa'],
    queryFn: () => getMfaStatus(),
  });

  const sessions = sessionsRes?.data ?? [];
  const mfaStatus = mfaRes?.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-800">安全设置</h1>
        <p className="text-xs text-gray-400 mt-0.5">管理密码、MFA 和活跃会话</p>
      </div>

      <Card title="修改密码">
        <div className="space-y-4 max-w-md">
          <Input type="password" label="当前密码" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
          <Input type="password" label="新密码" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} helperText="至少8位，含大小写字母和数字" />
          <Button variant="primary">更新密码</Button>
        </div>
      </Card>

      <Card title="MFA 双重认证">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-gray-800">
              {mfaStatus?.is_enabled ? '已启用' : '未启用'}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              {mfaStatus?.is_enabled ? 'MFA 已绑定' : '启用后登录时需要输入动态验证码'}
            </p>
          </div>
          <Button variant={mfaStatus?.is_enabled ? 'danger' : 'primary'}>
            {mfaStatus?.is_enabled ? '解除绑定' : '启用 MFA'}
          </Button>
        </div>
      </Card>

      <Card title="活跃会话">
        <div className="divide-y divide-gray-100 -mx-5 -mb-5">
          {sessions.map((session) => (
            <div key={session.id} className="px-5 py-3 flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-700">
                  {session.device_info}
                  {session.is_current && <Badge variant="green" className="ml-2">当前</Badge>}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">
                  IP: {session.ip_address} · 登录: {formatDate(session.logged_in_at)}
                </div>
              </div>
              {!session.is_current && (
                <Button variant="ghost" size="sm">终止</Button>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
