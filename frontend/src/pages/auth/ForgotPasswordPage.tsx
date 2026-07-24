import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { sendPasswordResetEmail } from '@/services/auth';

export function ForgotPasswordPage() {
  const [tenantSlug, setTenantSlug] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await sendPasswordResetEmail({ tenant_slug: tenantSlug, email });
    } catch {
      /* silent */
    }
    setSent(true);
    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800 text-center">忘记密码</h2>

      {sent ? (
        <div className="text-center space-y-4">
          <div className="text-sm text-green-600 bg-green-50 rounded-lg px-4 py-3">
            如果该邮箱存在，重置链接已发送，请查收邮件
          </div>
          <Link to="/login" className="text-sm text-primary-600 hover:text-primary-700 block">
            返回登录
          </Link>
        </div>
      ) : (
        <>
          <Input
            label="租户标识"
            placeholder="请输入租户标识"
            value={tenantSlug}
            onChange={(e) => setTenantSlug(e.target.value)}
            fullWidth
            required
          />
          <Input
            label="邮箱"
            type="email"
            placeholder="请输入注册邮箱"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            required
          />
          <Button type="submit" fullWidth loading={loading}>
            发送重置链接
          </Button>
          <div className="text-center">
            <Link to="/login" className="text-sm text-primary-600 hover:text-primary-700">
              返回登录
            </Link>
          </div>
        </>
      )}
    </form>
  );
}
