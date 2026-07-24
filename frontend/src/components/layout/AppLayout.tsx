import { Outlet } from 'react-router-dom';
import { useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useAuth } from '@/hooks/useAuth';
import { useProjectStore } from '@/stores/projectStore';

export function AppLayout() {
  const { refreshUser } = useAuth();
  const fetchProjects = useProjectStore((s) => s.fetchProjects);

  useEffect(() => {
    refreshUser();
    fetchProjects();
  }, [refreshUser, fetchProjects]);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <div className="flex-1 p-6 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
