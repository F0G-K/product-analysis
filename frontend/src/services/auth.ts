import { get, getPaginated, post, put, patch, del } from './request';
import type { ApiResponse } from '@/types/api';
import type {
  User,
  LoginRequest,
  LoginResponse,
  MfaVerifyRequest,
  MfaStatus,
  MfaBindResponse,
  SessionInfo,
  Invitation,
} from '@/types/user';

/** 用户登录 */
export async function login(data: LoginRequest): Promise<ApiResponse<LoginResponse>> {
  return post<LoginResponse>('/auth/login', data);
}

/** MFA 二次验证 */
export async function mfaVerify(data: MfaVerifyRequest): Promise<ApiResponse<LoginResponse>> {
  return post<LoginResponse>('/auth/mfa/verify', data);
}

/** 用户登出 */
export async function logout(): Promise<ApiResponse<null>> {
  return post<null>('/auth/logout');
}

/** 获取当前用户信息 */
export async function getCurrentUser(): Promise<ApiResponse<User>> {
  return get<User>('/auth/me');
}

/** 修改密码 */
export async function changePassword(data: {
  old_password: string;
  new_password: string;
}): Promise<ApiResponse<null>> {
  return put<null>('/auth/password', data);
}

/** 获取活跃会话列表 */
export async function getSessions(): Promise<ApiResponse<SessionInfo[]>> {
  return get<SessionInfo[]>('/auth/sessions');
}

/** 终止指定会话 */
export async function terminateSession(sessionId: string): Promise<ApiResponse<null>> {
  return del<null>(`/auth/sessions/${sessionId}`);
}

/** 获取 MFA 绑定状态 */
export async function getMfaStatus(): Promise<ApiResponse<MfaStatus>> {
  return get<MfaStatus>('/auth/mfa');
}

/** 发起 MFA 绑定 */
export async function bindMfaInit(password: string): Promise<ApiResponse<MfaBindResponse>> {
  return post<MfaBindResponse>('/auth/mfa/bind', { password });
}

/** 确认 MFA 绑定 */
export async function bindMfaConfirm(code: string): Promise<ApiResponse<null>> {
  return post<null>('/auth/mfa/bind/confirm', { code });
}

/** 解除 MFA 绑定 */
export async function unbindMfa(password: string): Promise<ApiResponse<null>> {
  return apiDeleteWithBody('/auth/mfa', { password });
}

// Helper for DELETE with body
async function apiDeleteWithBody<T>(url: string, data: unknown): Promise<ApiResponse<T>> {
  const { default: api } = await import('./api');
  const res = await api.delete<ApiResponse<T>>(url, { data });
  return res.data;
}

/** 发送密码重置邮件 */
export async function sendPasswordResetEmail(data: {
  tenant_slug: string;
  email: string;
}): Promise<ApiResponse<null>> {
  return post<null>('/auth/password/reset', data);
}

/** 验证重置令牌 */
export async function verifyResetToken(token: string): Promise<ApiResponse<null>> {
  return get<null>(`/auth/password/reset/${token}`);
}

/** 执行密码重置 */
export async function executePasswordReset(
  token: string,
  data: { new_password: string },
): Promise<ApiResponse<null>> {
  return post<null>(`/auth/password/reset/${token}`, data);
}

/** 获取用户列表（tenant_admin） */
export async function getUsers(params?: Record<string, unknown>): Promise<ApiResponse<{
  items: User[];
  total: number;
  page: number;
  page_size: number;
}>> {
  return getPaginated<User>('/users', params) as Promise<ApiResponse<{
    items: User[];
    total: number;
    page: number;
    page_size: number;
  }>>;
}

/** 创建用户 */
export async function createUser(data: {
  email: string;
  name: string;
  role?: string;
  password?: string;
}): Promise<ApiResponse<User>> {
  return post<User>('/users', data);
}

/** 更新用户 */
export async function updateUser(
  userId: string,
  data: Record<string, unknown>,
): Promise<ApiResponse<User>> {
  return patch<User>(`/users/${userId}`, data);
}

/** 删除用户（软删除） */
export async function deleteUser(userId: string): Promise<ApiResponse<null>> {
  return del<null>(`/users/${userId}`);
}

/** 获取邀请列表 */
export async function getInvitations(
  tenantId: string,
  params?: Record<string, unknown>,
): Promise<ApiResponse<{ items: Invitation[]; total: number; page: number; page_size: number }>> {
  return getPaginated<Invitation>(`/tenants/${tenantId}/invitations`, params) as Promise<
    ApiResponse<{ items: Invitation[]; total: number; page: number; page_size: number }>
  >;
}

/** 发起邀请 */
export async function createInvitation(
  tenantId: string,
  data: { email: string; role?: string },
): Promise<ApiResponse<Invitation>> {
  return post<Invitation>(`/tenants/${tenantId}/invitations`, data);
}

/** 撤销邀请 */
export async function revokeInvitation(
  tenantId: string,
  invitationId: string,
): Promise<ApiResponse<null>> {
  return del<null>(`/tenants/${tenantId}/invitations/${invitationId}`);
}

/** 接受邀请 */
export async function acceptInvitation(
  token: string,
  data: { name: string; password: string },
): Promise<ApiResponse<User>> {
  return post<User>(`/invitations/${token}`, data);
}

/** 获取登录审计日志 */
export async function getLoginAuditLogs(
  params?: Record<string, unknown>,
): Promise<ApiResponse<{ items: unknown[]; total: number; page: number; page_size: number }>> {
  return getPaginated('/audit/login-logs', params) as Promise<
    ApiResponse<{ items: unknown[]; total: number; page: number; page_size: number }>
  >;
}
