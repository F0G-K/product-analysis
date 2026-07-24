import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { acceptInvitation } from '@/services/auth';
import { toast } from '@/components/ui/Toast';

export function AcceptInvitationPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await acceptInvitation(token!, { name, password });
      if (res.code === 0) {
        toast.success('账号激活成功，请登录');
        navigate('/login');
      } else {
        setError(res.message || '激活失败');
      }
    } catch {
      setError('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800 text-center">接受邀请</h2>
      <p className="text-sm text-gray-500 text-center">设置您的账号信息以完成激活</p>

      <Input
        label="显示名称"
        placeholder="请输入您的姓名"
        value={name}
        onChange={(e) => setName(e.target.value)}
        fullWidth
        required
      />
      <Input
        label="密码"
        type="password"
        placeholder="至少8个字符"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        fullWidth
        required
      />

      {error && <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</div>}

      <Button type="submit" fullWidth loading={loading}>
        激活账号
      </Button>
    </form>
  );
}
