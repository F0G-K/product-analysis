import type { User } from '@/types/user';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  mfaToken: string | null;

  login: (user: User, token: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setAccessToken: (token: string) => void;
  setMfaToken: (token: string | null) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      mfaToken: null,

      login: (user, token) =>
        set({ user, accessToken: token, isAuthenticated: true, mfaToken: null }),

      logout: () =>
        set({ user: null, accessToken: null, isAuthenticated: false, mfaToken: null }),

      setUser: (user) => set({ user }),

      setAccessToken: (token) => set({ accessToken: token }),

      setMfaToken: (token) => set({ mfaToken: token }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
