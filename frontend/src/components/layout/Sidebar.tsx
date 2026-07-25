import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/utils/cn';
import { useAuthStore } from '@/stores/authStore';

const navItems = [
  { to: '/', icon: 'gauge', label: '工作台' },
  { to: '/chat', icon: 'comments', label: 'AI 对话' },
  { to: '/assessment', icon: 'scale-balanced', label: '需求价值评估' },
  { to: '/consistency', icon: 'circle-check', label: '交付物一致性检查' },
  { to: '/attribution', icon: 'magnifying-glass-chart', label: '上线问题归因' },
];

const secondaryItems = [
  { to: '/projects', icon: 'diagram-project', label: '项目与数据源' },
  { to: '/reports', icon: 'chart-bar', label: '报表' },
  { to: '/admin', icon: 'gear', label: '系统管理' },
];

export function Sidebar() {
  const user = useAuthStore((s) => s.user);

  return (
    <aside
      className={cn(
        'w-60 bg-sidebar-bg text-white shrink-0 flex flex-col min-h-screen',
        'fixed left-0 top-0 z-30 lg:relative',
      )}
    >
      {/* Logo */}
      <div className="p-4 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 3a1 1 0 011-1h4l3 6-2 4h2l-2 4H4l3-6-2-4H4V3z" clipRule="evenodd" />
            </svg>
          </div>
          <span className="font-bold text-sm">产品管理智能助手</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 space-y-0.5 px-2 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-sidebar-active text-white'
                  : 'text-gray-300 hover:bg-sidebar-hover hover:text-white',
              )
            }
          >
            <span className="w-4 text-center text-xs opacity-70">{getIcon(item.icon)}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}

        <div className="my-3 border-t border-gray-700/50" />

        {secondaryItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-sidebar-active text-white'
                  : 'text-gray-300 hover:bg-sidebar-hover hover:text-white',
              )
            }
          >
            <span className="w-4 text-center text-xs opacity-70">{getIcon(item.icon)}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User */}
      {user && (
        <div className="p-3 border-t border-gray-700/50">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-xs font-bold text-white">
              {user.name?.[0] ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="truncate text-gray-300 text-xs font-medium">{user.name}</div>
              <div className="text-[10px] text-gray-500">{user.email}</div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

function getIcon(name: string): string {
  const icons: Record<string, string> = {
    gauge: '⊡',
    comments: '💬',
    'scale-balanced': '⚖',
    'circle-check': '✓',
    'magnifying-glass-chart': '⊙',
    'diagram-project': '⊞',
    'chart-bar': '▤',
    gear: '⚙',
  };
  return icons[name] ?? '●';
}
