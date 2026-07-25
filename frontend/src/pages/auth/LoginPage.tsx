import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { getErrorMessage } from '@/utils/errorHandler';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login({
        username,
        password,
        remember_me: rememberMe,
      });

      if (result.success) {
        navigate('/', { replace: true });
      } else if (result.mfaRequired) {
        navigate('/mfa/verify', { state: { mfaToken: result.mfaToken } });
      } else {
        setError(getErrorMessage(result.code ?? 0) || '登录失败，请重试');
      }
    } catch {
      setError('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800 text-center">登录</h2>

      <Input
        label="账号"
        placeholder="请输入账号"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        fullWidth
        required
      />

      <Input
        label="密码"
        type="password"
        placeholder="请输入密码"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        fullWidth
        required
      />

      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="rounded border-gray-300"
          />
          记住我
        </label>
        <Link to="/forgot-password" className="text-sm text-primary-600 hover:text-primary-700">
          忘记密码？
        </Link>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</div>
      )}

      <div className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 text-center">
        默认账号：admin　默认密码：admin
      </div>

      <Button type="submit" fullWidth loading={loading}>
        登录
      </Button>
    </form>
  );
}
