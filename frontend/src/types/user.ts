// ===== 用户 / 认证 / 租户 / 邀请 =====

/** 用户角色 */
export type UserRole =
  | 'platform_admin'
  | 'tenant_admin'
  | 'project_admin'
  | 'project_member'
  | 'viewer'

/** 项目成员角色 */
export type ProjectMemberRole = 'project_admin' | 'project_member' | 'viewer'

/** 邀请状态 */
export type InvitationStatus = 'pending' | 'activated' | 'expired'

// ---- 实体 ----

/** 用户 */
export interface User {
  id: string
  tenant_id: string
  email: string
  name: string
  avatar_url?: string
  role: UserRole
  is_first_login: boolean
  mfa_enabled: boolean
  auth_provider?: string
  last_login_at?: string
  last_login_ip?: string
  memberships: ProjectMembership[]
}

/** 项目成员关系 */
export interface ProjectMembership {
  project_id: string
  project_name: string
  role: ProjectMemberRole
}

/** 租户 */
export interface Tenant {
  id: string
  name: string
  slug: string
  status: string
  max_users?: number
  max_projects?: number
  settings?: Record<string, unknown>
  created_at: string
}

/** 邀请 */
export interface Invitation {
  id: string
  email: string
  role: string
  status: InvitationStatus
  created_at: string
  expires_at: string
}

/** 会话信息 */
export interface SessionInfo {
  id: string
  device_info: string
  ip_address: string
  logged_in_at: string
  last_active_at: string
  expires_at: string
  is_current: boolean
}

// ---- 请求 / 响应 ----

/** 登录请求 */
export interface LoginRequest {
  username: string
  password: string
  remember_me?: boolean
}

/** 登录响应 */
export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

/** MFA 验证请求 */
export interface MfaVerifyRequest {
  mfa_token: string
  code: string
}

/** MFA 状态 */
export interface MfaStatus {
  is_enabled: boolean
  bound_at?: string
  last_used_at?: string
}

/** MFA 绑定响应 */
export interface MfaBindResponse {
  secret: string
  qr_code_url: string
  recovery_codes: string[]
}

/** 修改密码 */
export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

/** 发送重置密码邮件 */
export interface PasswordResetRequest {
  tenant_slug: string
  email: string
}

/** 执行密码重置 */
export interface PasswordResetExecute {
  new_password: string
}

/** 创建邀请 */
export interface InvitationCreate {
  email: string
  role?: string
}

/** 接受邀请 */
export interface AcceptInvitationRequest {
  name: string
  password: string
}
