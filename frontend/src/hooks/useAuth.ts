import { useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useProjectStore } from '@/stores/projectStore';
import * as authService from '@/services/auth';
import type { LoginRequest } from '@/types/user';
import type { ApiErrorResponse } from '@/types/api';

export function useAuth() {
  const navigate = useNavigate();
  const { user, isAuthenticated, login: storeLogin, logout: storeLogout, setMfaToken } = useAuthStore();
  const clearProject = useProjectStore((s) => s.clearProject);

  const login = useCallback(
    async (data: LoginRequest) => {
      try {
        const res = await authService.login(data);
        if (res.code === 0) {
          storeLogin(res.data.user, res.data.access_token);
          return { success: true };
        }
        if (res.code === 40105 && (res.data as unknown as { mfa_token?: string })?.mfa_token) {
          const mfaData = res.data as unknown as { mfa_token: string; user_id: string };
          setMfaToken(mfaData.mfa_token);
          return { mfaRequired: true, mfaToken: mfaData.mfa_token };
        }
        return { success: false, code: res.code, message: res.message };
      } catch (error) {
        if (axios.isAxiosError<ApiErrorResponse>(error) && error.response?.data) {
          return {
            success: false,
            code: error.response.data.code,
            message: error.response.data.message,
          };
        }
        throw error;
      }
    },
    [storeLogin, setMfaToken],
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      /* ignore */
    }
    storeLogout();
    clearProject();
    navigate('/login');
  }, [storeLogout, clearProject, navigate]);

  const refreshUser = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const res = await authService.getCurrentUser();
      if (res.code === 0) {
        useAuthStore.getState().setUser(res.data);
      }
    } catch {
      storeLogout();
    }
  }, [isAuthenticated, storeLogout]);

  return { user, isAuthenticated, login, logout, refreshUser };
}
