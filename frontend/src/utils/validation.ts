import { z } from 'zod'

// ===== 登录 =====

export const loginSchema = z.object({
  tenant_slug: z.string().min(1, '请输入租户标识'),
  email: z.string().email('请输入有效邮箱'),
  password: z.string().min(1, '请输入密码'),
  remember_me: z.boolean().optional(),
})

export type LoginFormValues = z.infer<typeof loginSchema>

// ===== 密码重置 =====

export const passwordResetSchema = z
  .object({
    new_password: z
      .string()
      .min(8, '密码至少8个字符')
      .regex(/[A-Z]/, '需包含大写字母')
      .regex(/[a-z]/, '需包含小写字母')
      .regex(/[0-9]/, '需包含数字'),
    confirm_password: z.string(),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: '两次密码不一致',
    path: ['confirm_password'],
  })

export type PasswordResetFormValues = z.infer<typeof passwordResetSchema>

// ===== 需求 =====

export const requirementSchema = z.object({
  name: z.string().min(1, '需求名称不能为空').max(256, '需求名称最多256个字符'),
  external_id: z.string().optional(),
  background: z.string().optional(),
})

export type RequirementFormValues = z.infer<typeof requirementSchema>

// ===== 项目 =====

export const projectSchema = z.object({
  name: z.string().min(1, '项目名称不能为空').max(128, '项目名称最多128个字符'),
  description: z.string().optional(),
  timezone: z.string().optional(),
})

export type ProjectFormValues = z.infer<typeof projectSchema>

// ===== MFA 验证 =====

export const mfaVerifySchema = z.object({
  code: z.string().length(6, '请输入6位验证码'),
})

export type MfaVerifyFormValues = z.infer<typeof mfaVerifySchema>
