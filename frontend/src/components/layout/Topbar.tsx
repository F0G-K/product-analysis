import { useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useProjectStore } from '@/stores/projectStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { useEffect } from 'react';

const pageTitles: Record<string, string> = {
  '/': '工作台',
  '/projects': '项目与数据源',
  '/assessment': '需求价值评估',
  '/consistency': '交付物一致性检查',
  '/attribution': '上线问题归因',
  '/reports': '报表',
  '/settings/profile': '个人设置',
  '/settings/security': '安全设置',
  '/admin': '系统管理',
};

export function Topbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const projects = useProjectStore((s) => s.projects);
  const currentProjectId = useProjectStore((s) => s.currentProjectId);
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject);
  const { unreadCount } = useNotificationStore();

  // Determine title from current path
  const currentTitle = pageTitles[location.pathname]
    || Object.entries(pageTitles).find(([path]) =>
        location.pathname.startsWith(path) && path !== '/')?.[1]
    || '';

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-20">
      {/* Left: Title */}
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-gray-800">{currentTitle}</h1>
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          系统正常
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3">
        {/* Project Selector */}
        {projects.length > 0 && (
          <select
            value={currentProjectId ?? ''}
            onChange={(e) => setCurrentProject(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white text-gray-600 max-w-[200px]"
          >
            <option value="">选择项目</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}

        {/* Notifications */}
        <button className="relative text-gray-500 hover:text-gray-700 p-1">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        {/* User Dropdown */}
        {user && (
          <div className="flex items-center gap-2 text-sm">
            <div className="w-7 h-7 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-bold">
              {user.name?.[0] ?? 'U'}
            </div>
            <span className="text-gray-700 hidden sm:inline">{user.name}</span>
            <button
              onClick={logout}
              className="text-gray-400 hover:text-gray-600 text-xs ml-2"
              title="退出登录"
            >
              退出
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
