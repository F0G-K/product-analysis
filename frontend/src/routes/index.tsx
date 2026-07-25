import { createBrowserRouter, Navigate, Outlet, useLocation, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useProjectStore } from '@/stores/projectStore';
import { getCurrentUser } from '@/services/auth';
import { Spinner } from '@/components/ui/Spinner';

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
import { ChatPage } from '@/pages/chat/ChatPage';
import { ProjectListPage } from '@/pages/project/ProjectListPage';
import { ProjectDetailPage } from '@/pages/project/ProjectDetailPage';
import { ProjectSettingsPage } from '@/pages/project/ProjectSettingsPage';
import { ProfilePage } from '@/pages/settings/ProfilePage';
import { SecurityPage } from '@/pages/settings/SecurityPage';
import { AdminPage } from '@/pages/settings/AdminPage';

// Auth guard
function AuthGuard() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);
  const location = useLocation();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      setChecking(false);
      return;
    }
    setChecking(true);
    getCurrentUser()
      .then((res) => {
        if (res.code === 0) setUser(res.data);
        else logout();
      })
      .catch(() => logout())
      .finally(() => setChecking(false));
  }, [accessToken, isAuthenticated, logout, setUser]);

  if (!isAuthenticated || !accessToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (checking) {
    return <div className="min-h-screen flex items-center justify-center"><Spinner size="lg" /></div>;
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
          { path: 'chat', element: <ChatPage /> },
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
