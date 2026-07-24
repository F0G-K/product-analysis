import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { cn } from '@/utils/cn';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

let toastId = 0;
let globalAddToast: ((type: ToastType, message: string) => void) | null = null;

export function toast(type: ToastType, message: string) {
  globalAddToast?.(type, message);
}

toast.success = (msg: string) => toast('success', msg);
toast.error = (msg: string) => toast('error', msg);
toast.warning = (msg: string) => toast('warning', msg);
toast.info = (msg: string) => toast('info', msg);

const typeStyles: Record<ToastType, string> = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
};

const typeIcons: Record<ToastType, string> = {
  success: '✓',
  error: '✕',
  warning: '!',
  info: 'ℹ',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5_000);
  }, []);

  globalAddToast = addToast;

  return (
    <>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              'flex items-center gap-2 px-4 py-3 rounded-lg border shadow-lg text-sm animate-in slide-in-from-right',
              typeStyles[t.type],
            )}
          >
            <span className="font-bold text-base leading-none">{typeIcons[t.type]}</span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </>
  );
}
