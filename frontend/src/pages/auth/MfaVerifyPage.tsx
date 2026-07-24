import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { mfaVerify } from '@/services/auth';
import { useAuthStore } from '@/stores/authStore';
import { getErrorMessage } from '@/utils/errorHandler';

export function MfaVerifyPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const mfaToken = (location.state as { mfaToken?: string })?.mfaToken || useAuthStore.getState().mfaToken;
  const storeLogin = useAuthStore((s) => s.login);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 6) return;
    setError('');
    setLoading(true);

    try {
      const res = await mfaVerify({ mfa_token: mfaToken!, code });
      if (res.code === 0) {
        storeLogin(res.data.user, res.data.access_token);
        navigate('/', { replace: true });
      } else {
        setError(getErrorMessage(res.code) || '验证失败');
      }
    } catch {
      setError('网络错误');
    } finally {
      setLoading(false);
    }
  };

  if (!mfaToken) {
    return (
      <div className="text-center">
        <p className="text-sm text-gray-500">无效的验证会话，请重新登录</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800 text-center">双重验证</h2>
      <p className="text-sm text-gray-500 text-center">请输入您的认证应用中的6位验证码</p>

      <div className="flex justify-center">
        <input
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={code}
          onChange={(e) => {
            const val = e.target.value.replace(/\D/g, '').slice(0, 6);
            setCode(val);
          }}
          className="w-48 text-center text-2xl tracking-[0.5em] font-mono border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500"
          placeholder="000000"
          autoFocus
        />
      </div>

      {error && <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 text-center">{error}</div>}

      <Button type="submit" fullWidth loading={loading} disabled={code.length !== 6}>
        验证
      </Button>
    </form>
  );
}
