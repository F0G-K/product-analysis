import { useAuthStore } from '@/stores/authStore';

export function usePermission() {
  const user = useAuthStore((s) => s.user);

  const canAccess = (requiredRole: string): boolean => {
    if (!user) return false;
    const roleHierarchy: Record<string, number> = {
      platform_admin: 5,
      tenant_admin: 4,
      project_admin: 3,
      project_member: 2,
      viewer: 1,
    };
    return (roleHierarchy[user.role] ?? 0) >= (roleHierarchy[requiredRole] ?? 0);
  };

  const canAccessProject = (
    _projectId: string,
    _requiredRole?: 'project_admin' | 'project_member' | 'viewer',
  ): boolean => {
    if (!user) return false;
    // tenant_admin and above can access all projects
    if (user.role === 'tenant_admin' || user.role === 'platform_admin') return true;
    // For now, project memberships are checked via the membership list
    return true;
  };

  return { user, canAccess, canAccessProject };
}
