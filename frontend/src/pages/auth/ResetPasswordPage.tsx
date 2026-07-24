import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { verifyResetToken, executePasswordReset } from '@/services/auth';
import { toast } from '@/components/ui/Toast';

export function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) return;
    verifyResetToken(token)
      .then((res) => {
        setTokenValid(res.code === 0);
      })
      .catch(() => setTokenValid(false))
      .finally(() => setValidating(false));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('两次密码不一致');
      return;
    }
    if (newPassword.length < 8) {
      setError('密码至少8个字符');
      return;
    }

    setLoading(true);
    try {
      const res = await executePasswordReset(token!, { new_password: newPassword });
      if (res.code === 0) {
        setDone(true);
        toast.success('密码重置成功，请重新登录');
      } else {
        setError(res.message || '重置失败');
      }
    } catch {
      setError('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  if (validating) {
    return <div className="text-center text-sm text-gray-500 py-8">验证令牌中...</div>;
  }

  if (!tokenValid) {
    return (
      <div className="text-center space-y-4">
        <p className="text-sm text-red-600">重置链接已过期或无效</p>
        <Link to="/forgot-password" className="text-sm text-primary-600 hover:text-primary-700">
          重新发送
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="text-center space-y-4">
        <div className="text-sm text-green-600 bg-green-50 rounded-lg px-4 py-3">密码重置成功</div>
        <Link to="/login" className="text-sm text-primary-600 hover:text-primary-700 block">
          前往登录
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800 text-center">重置密码</h2>
      <Input
        label="新密码"
        type="password"
        placeholder="至少8个字符，含大小写字母和数字"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        fullWidth
        required
      />
      <Input
        label="确认密码"
        type="password"
        placeholder="再次输入新密码"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        fullWidth
        required
      />
      {error && <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</div>}
      <Button type="submit" fullWidth loading={loading}>
        重置密码
      </Button>
    </form>
  );
}
