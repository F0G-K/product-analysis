import { createBrowserRouter, Navigate, Outlet, useLocation, useParams } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useProjectStore } from '@/stores/projectStore';

// Layouts (lazy loaded later)
import { AppLayout } from '@/components/layout/AppLayout';
import { AuthLayout } from '@/components/layout/AuthLayout';

// Auth pages
import { LoginPage } from '@/pages/auth/LoginPage';
import { ForgotPasswordPage } from '@/pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from '@/pages/auth/ResetPasswordPage';
import { MfaVerifyPage } from '@/pages/auth/MfaVerifyPage';
import { AcceptInvitationPage } from '@/pages/auth/AcceptInvitationPage';

// Business pages
import { WorkspacePage } from '@/pages/workspace/WorkspacePage';
import { AssessmentListPage } from '@/pages/assessment/AssessmentListPage';
import { AssessmentDetailPage } from '@/pages/assessment/AssessmentDetailPage';
import { ConsistencyListPage } from '@/pages/consistency/ConsistencyListPage';
import { ConsistencyDetailPage } from '@/pages/consistency/ConsistencyDetailPage';
import { AttributionListPage } from '@/pages/attribution/AttributionListPage';
import { AttributionDetailPage } from '@/pages/attribution/AttributionDetailPage';
import { ReportsPage } from '@/pages/reports/ReportsPage';
import { ProjectListPage } from '@/pages/project/ProjectListPage';
import { ProjectDetailPage } from '@/pages/project/ProjectDetailPage';
import { ProjectSettingsPage } from '@/pages/project/ProjectSettingsPage';
import { ProfilePage } from '@/pages/settings/ProfilePage';
import { SecurityPage } from '@/pages/settings/SecurityPage';
import { AdminPage } from '@/pages/settings/AdminPage';

// Auth guard
function AuthGuard() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();

  // 开发模式跳过登录
  if (import.meta.env.VITE_SKIP_AUTH === 'true') {
    return <Outlet />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Outlet />;
}

// Project context guard
function ProjectGuard() {
  const { projectId } = useParams<{ projectId: string }>();
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject);

  useEffect(() => {
    if (projectId) {
      setCurrentProject(projectId);
    }
  }, [projectId, setCurrentProject]);

  return <Outlet />;
}

export const router = createBrowserRouter([
  // Public auth routes
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password/:token', element: <ResetPasswordPage /> },
      { path: '/mfa/verify', element: <MfaVerifyPage /> },
      { path: '/invitations/:token', element: <AcceptInvitationPage /> },
    ],
  },

  // Authenticated routes
  {
    element: <AuthGuard />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <WorkspacePage /> },
          { path: 'projects', element: <ProjectListPage /> },
          {
            path: 'projects/:projectId',
            element: <ProjectGuard />,
            children: [
              { index: true, element: <ProjectDetailPage /> },
              { path: 'settings', element: <ProjectSettingsPage /> },
            ],
          },
          { path: 'assessment', element: <AssessmentListPage /> },
          { path: 'assessment/:taskId', element: <AssessmentDetailPage /> },
          { path: 'consistency', element: <ConsistencyListPage /> },
          { path: 'consistency/:taskId', element: <ConsistencyDetailPage /> },
          { path: 'attribution', element: <AttributionListPage /> },
          { path: 'attribution/:taskId', element: <AttributionDetailPage /> },
          { path: 'reports', element: <ReportsPage /> },
          { path: 'settings/profile', element: <ProfilePage /> },
          { path: 'settings/security', element: <SecurityPage /> },
          { path: 'admin', element: <AdminPage /> },
        ],
      },
    ],
  },

  // Catch-all redirect
  { path: '*', element: <Navigate to="/" replace /> },
]);
