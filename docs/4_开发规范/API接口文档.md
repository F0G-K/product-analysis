# 产品管理智能助手平台 — API 接口文档

> **版本**: V1.0  
> **最后更新**: 2026-07-24  
> **基线上线版本**: V1.0-MVP  
> **对应数据库**: PostgreSQL 16（`init.sql`）  
> **技术栈**: FastAPI + LangGraph + Celery + Redis

---

## 目录

1. [通用约定](#1-通用约定)
2. [认证与用户管理](#2-认证与用户管理)
   - [租户管理](#21-租户管理)
   - [用户与认证](#22-用户与认证)
   - [会话管理](#23-会话管理)
   - [MFA 多因素认证](#24-mfa-多因素认证)
   - [SSO 单点登录](#25-sso-单点登录)
   - [密码重置](#26-密码重置)
   - [成员邀请](#27-成员邀请)
   - [登录审计日志](#28-登录审计日志)
3. [项目管理与数据源](#3-项目管理与数据源)
   - [项目管理](#31-项目管理)
   - [项目成员](#32-项目成员)
   - [数据源管理](#33-数据源管理)
   - [同步记录](#34-同步记录)
4. [需求池与评估模型](#4-需求池与评估模型)
   - [需求管理](#41-需求管理)
   - [评估模型](#42-评估模型)
   - [评估维度与锚点](#43-评估维度与锚点)
   - [评估任务](#44-评估任务)
   - [评分确认](#45-评分确认)
5. [交付物一致性检查](#5-交付物一致性检查)
   - [交付物管理](#51-交付物管理)
   - [检查基线](#52-检查基线)
   - [检查规则](#53-检查规则)
   - [检查任务](#54-检查任务)
   - [问题管理](#55-问题管理)
   - [问题处置与复检](#56-问题处置与复检)
6. [上线问题归因](#6-上线问题归因)
   - [发布版本](#61-发布版本)
   - [归因任务](#62-归因任务)
   - [时间线事件](#63-时间线事件)
   - [归因结果与确认](#64-归因结果与确认)
7. [公共能力](#7-公共能力)
   - [通用任务](#71-通用任务)
   - [快照管理](#72-快照管理)
   - [审计日志](#73-审计日志)
   - [通知管理](#74-通知管理)
   - [导出管理](#75-导出管理)
   - [WebSocket 推送](#76-websocket-推送)
8. [附录](#8-附录)

---

## 1. 通用约定

### 1.1 基础信息

| 项目 | 值 |
| --- | --- |
| Base URL | `https://{domain}/api/v1` |
| 请求格式 | `application/json; charset=utf-8` |
| 响应格式 | `application/json; charset=utf-8` |
| 字符编码 | UTF-8 |
| API 版本策略 | URL 路径版本 `/api/v1` → `/api/v2` |

### 1.2 认证方式

平台采用 **JWT Access Token + Session Cookie** 双通道认证：

| 通道 | 方式 | 有效期 | 存储 |
| --- | --- | --- | --- |
| API 请求 | `Authorization: Bearer <jwt_token>` | 30 分钟 | Header |
| 浏览器 | `Set-Cookie: session_token=<token>; HttpOnly; Secure; SameSite=Lax` | 12 小时 | Cookie |

除 `/api/v1/auth/login`、`/api/v1/auth/sso/callback`、`/api/v1/auth/password/reset` 外，所有接口均需携带有效凭证。

### 1.3 请求头

```http
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Accept-Language: zh-CN
```

### 1.4 通用响应格式

**成功响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": { },
  "request_id": "req_abc123"
}
```

**列表响应：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "total": 142,
    "page": 1,
    "page_size": 20
  },
  "request_id": "req_abc123"
}
```

**错误响应：**

```json
{
  "code": 40101,
  "message": "Invalid credentials",
  "detail": "Email or password is incorrect",
  "request_id": "req_abc123"
}
```

### 1.5 通用状态码

| HTTP 状态码 | 说明 |
| --- | --- |
| `200 OK` | 请求成功 |
| `201 Created` | 创建成功 |
| `202 Accepted` | 已接受，异步处理中 |
| `204 No Content` | 成功但无响应体（常用于删除、登出） |
| `400 Bad Request` | 请求参数错误 |
| `401 Unauthorized` | 未认证或凭证过期 |
| `403 Forbidden` | 无权限 |
| `404 Not Found` | 资源不存在 |
| `409 Conflict` | 资源冲突（重复创建等） |
| `422 Unprocessable Entity` | 业务规则校验失败 |
| `429 Too Many Requests` | 请求频率限制 |
| `500 Internal Server Error` | 服务端错误 |

### 1.6 通用错误码

| 业务码 | 说明 |
| --- | --- |
| `0` | 成功 |
| `40101` | 凭证无效 |
| `40102` | Token 过期 |
| `40103` | 会话已失效 |
| `40104` | 账号已锁定 |
| `40105` | 需要 MFA 验证 |
| `40106` | MFA 验证失败 |
| `40301` | 租户权限不足 |
| `40302` | 项目权限不足 |
| `40303` | 操作权限不足 |
| `40401` | 资源不存在 |
| `40901` | 资源冲突 |
| `42201` | 参数校验失败 |
| `42202` | 业务规则限制 |
| `50001` | 内部服务错误 |

### 1.7 分页参数

分页接口统一使用以下查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | `integer` | 否 | `1` | 页码，从 1 开始 |
| `page_size` | `integer` | 否 | `20` | 每页条数，最大 100 |
| `sort_by` | `string` | 否 | `created_at` | 排序字段 |
| `sort_order` | `string` | 否 | `desc` | `asc` / `desc` |

### 1.8 软删除

以下资源使用软删除（`deleted_at IS NOT NULL` 视为已删除），删除接口不物理删除记录：

- `tenants`、`users`、`projects`、`data_sources`
- `requirements`、`deliverables`
- `check_rules`、`release_versions`

列表接口默认不返回已删除资源，可通过 `include_deleted=true` 显式查询。

---

## 2. 认证与用户管理

### 2.1 租户管理

#### 2.1.1 创建租户

创建新租户（平台管理员操作）。

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建租户 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tenants` |
| **认证** | `platform_admin` 角色 |

**请求头：**

```http
Content-Type: application/json
Authorization: Bearer <platform_admin_token>
```

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | — | 租户名称，最长 128 字符 |
| `slug` | `string` | 是 | — | URL 标识，3-64 字符，`[a-z0-9-]+` |
| `max_users` | `integer` | 否 | `null` | 用户数上限，null 不限制 |
| `max_projects` | `integer` | 否 | `null` | 项目数上限，null 不限制 |
| `settings` | `object` | 否 | `{}` | 租户级配置 |
| `settings.password_policy` | `object` | 否 | — | 密码策略 |
| `settings.password_policy.min_length` | `integer` | 否 | `8` | 最小密码长度 |
| `settings.password_policy.require_mfa` | `boolean` | 否 | `false` | 是否强制 MFA |
| `settings.password_policy.session_max_count` | `integer` | 否 | `3` | 单用户最大并发会话数 |

**请求示例：**

```json
{
  "name": "星云科技",
  "slug": "nebula-tech",
  "max_users": 200,
  "settings": {
    "password_policy": {
      "min_length": 10,
      "require_mfa": true
    }
  }
}
```

**成功响应 `201`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "星云科技",
    "slug": "nebula-tech",
    "status": "active",
    "max_users": 200,
    "max_projects": null,
    "settings": {
      "password_policy": {
        "min_length": 10,
        "require_mfa": true
      }
    },
    "created_at": "2026-07-24T10:30:00+08:00"
  },
  "request_id": "req_abc123"
}
```

**错误响应 `409` — slug 冲突：**

```json
{
  "code": 40901,
  "message": "Tenant slug already exists",
  "detail": "slug 'nebula-tech' is already taken by another tenant",
  "request_id": "req_abc123"
}
```

---

#### 2.1.2 获取租户列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取租户列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tenants` |
| **认证** | `platform_admin` |

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `status` | `string` | 否 | — | 过滤：`active` / `suspended` / `disabled` |
| `search` | `string` | 否 | — | 按 name 模糊搜索 |
| `page` | `integer` | 否 | `1` | 页码 |
| `page_size` | `integer` | 否 | `20` | 每页条数 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "name": "星云科技",
        "slug": "nebula-tech",
        "status": "active",
        "max_users": 200,
        "created_at": "2026-07-24T10:30:00+08:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "request_id": "req_abc123"
}
```

---

#### 2.1.3 获取租户详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取租户详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tenants/{tenant_id}` |
| **认证** | 同租户的 `tenant_admin` 或 `platform_admin` |

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `tenant_id` | `string(UUID)` | 是 | 租户 ID |

---

#### 2.1.4 更新租户

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新租户 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/tenants/{tenant_id}` |
| **认证** | `platform_admin` |

**请求体（全部可选）：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | `string` | 否 | 租户名称 |
| `status` | `string` | 否 | `active` / `suspended` / `disabled` |
| `max_users` | `integer` | 否 | 用户数上限 |
| `max_projects` | `integer` | 否 | 项目数上限 |
| `settings` | `object` | 否 | 租户配置（增量合并） |

---

#### 2.1.5 删除租户（软删除）

| 项目 | 值 |
| --- | --- |
| **接口名称** | 删除租户 |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/tenants/{tenant_id}` |
| **认证** | `platform_admin` |

**注意事项：**
- 软删除后该租户及所有关联数据不可访问
- 90 天后由定时任务物理清理

---

### 2.2 用户与认证

#### 2.2.1 用户登录

| 项目 | 值 |
| --- | --- |
| **接口名称** | 用户登录 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/login` |
| **认证** | 无需（仅限失败次数未超限的 IP） |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `tenant_slug` | `string` | 是 | — | 租户标识 |
| `email` | `string` | 是 | — | 邮箱 |
| `password` | `string` | 是 | — | 密码 |
| `remember_me` | `boolean` | 否 | `false` | 是否记住登录（延长 Session 至 30 天） |

**请求示例：**

```json
{
  "tenant_slug": "nebula-tech",
  "email": "zhangsan@nebula-tech.com",
  "password": "MyS3cureP@ss!",
  "remember_me": false
}
```

**成功响应 `200`（无需 MFA）：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 1800,
    "user": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "email": "zhangsan@nebula-tech.com",
      "name": "张三",
      "role": "project_member",
      "is_first_login": false,
      "last_login_at": "2026-07-24T09:15:00+08:00"
    }
  },
  "request_id": "req_abc123"
}
```

**成功响应 `200`（需要 MFA 验证）：**

```json
{
  "code": 40105,
  "message": "MFA required",
  "data": {
    "mfa_token": "mfa_session_token_xxx",
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  },
  "request_id": "req_abc123"
}
```

**错误响应 `401` — 账号已锁定：**

```json
{
  "code": 40104,
  "message": "Account locked",
  "detail": "Account locked until 2026-07-24T10:15:00+08:00 due to 5 consecutive login failures",
  "request_id": "req_abc123"
}
```

**注意事项：**
- 连续 5 次登录失败后账号锁定 15 分钟
- 失败登录记录写入 `login_audit_logs`
- 首次登录用户（`is_first_login = true`）需强制修改密码

---

#### 2.2.2 MFA 验证

| 项目 | 值 |
| --- | --- |
| **接口名称** | MFA 验证 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/mfa/verify` |
| **认证** | MFA session token |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `mfa_token` | `string` | 是 | 登录响应中返回的 MFA session token |
| `code` | `string` | 是 | 6 位 TOTP 动态码（或 8 位恢复码） |

**请求示例：**

```json
{
  "mfa_token": "mfa_session_token_xxx",
  "code": "482139"
}
```

**成功响应 `200`：** 同登录成功响应，返回 access_token。

**错误响应 `401`：**

```json
{
  "code": 40106,
  "message": "MFA verification failed",
  "detail": "Invalid TOTP code",
  "request_id": "req_abc123"
}
```

---

#### 2.2.3 用户登出

| 项目 | 值 |
| --- | --- |
| **接口名称** | 用户登出 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/logout` |
| **认证** | 用户 Token |

**请求头：**

```http
Authorization: Bearer <access_token>
```

**成功响应 `204`**（无响应体）。

---

#### 2.2.4 获取当前用户信息

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取当前用户 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/auth/me` |
| **认证** | 用户 Token |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "tenant_name": "星云科技",
    "email": "zhangsan@nebula-tech.com",
    "name": "张三",
    "avatar_url": "https://cdn.example.com/avatars/zhangsan.png",
    "role": "project_member",
    "is_first_login": false,
    "auth_provider": "local",
    "mfa_enabled": true,
    "last_login_at": "2026-07-24T09:15:00+08:00",
    "last_login_ip": "192.168.1.100",
    "memberships": [
      {
        "project_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "project_name": "智慧零售平台",
        "role": "project_admin"
      }
    ]
  },
  "request_id": "req_abc123"
}
```

---

#### 2.2.5 修改密码

| 项目 | 值 |
| --- | --- |
| **接口名称** | 修改密码 |
| **请求方式** | `PUT` |
| **URL** | `/api/v1/auth/password` |
| **认证** | 用户 Token |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `old_password` | `string` | 是 | 当前密码 |
| `new_password` | `string` | 是 | 新密码（需满足租户密码策略） |

**请求示例：**

```json
{
  "old_password": "MyS3cureP@ss!",
  "new_password": "N3wEvenS@ferP@ss#2026"
}
```

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "Password changed successfully, please re-login",
  "data": null,
  "request_id": "req_abc123"
}
```

**注意事项：**
- 密码修改后所有活跃会话立即失效（`terminated_reason = 'password_change'`）

---

#### 2.2.6 获取用户列表（租户管理员）

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取用户列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/users` |
| **认证** | `tenant_admin` |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `role` | `string` | 否 | `tenant_admin` / `project_member` |
| `search` | `string` | 否 | 按 name 或 email 模糊搜索 |
| `status` | `string` | 否 | `active` / `locked` / `deleted` |
| `page` | `integer` | 否 | 页码 |
| `page_size` | `integer` | 否 | 每页条数 |

---

#### 2.2.7 创建用户（管理员直接创建）

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建用户 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/users` |
| **认证** | `tenant_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `email` | `string` | 是 | — | 邮箱，租户内唯一 |
| `name` | `string` | 是 | — | 显示名，最长 128 字符 |
| `role` | `string` | 否 | `project_member` | 租户级角色 |
| `password` | `string` | 否 | — | 初始密码，不填则通过邀请链接激活 |

**注意事项：**
- 若提供密码，`is_first_login = true` 强制首次修改
- 不提供密码则走邀请激活流程

---

#### 2.2.8 更新用户

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新用户 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/users/{user_id}` |
| **认证** | `tenant_admin` |

---

#### 2.2.9 删除用户（软删除）

| 项目 | 值 |
| --- | --- |
| **接口名称** | 删除用户 |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/users/{user_id}` |
| **认证** | `tenant_admin` |

---

### 2.3 会话管理

#### 2.3.1 获取当前活跃会话

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取我的活跃会话列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/auth/sessions` |
| **认证** | 用户 Token |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "device_info": "Chrome 120 / macOS",
      "ip_address": "192.168.1.100",
      "logged_in_at": "2026-07-24T09:15:00+08:00",
      "last_active_at": "2026-07-24T11:30:00+08:00",
      "expires_at": "2026-07-24T21:15:00+08:00",
      "is_current": true
    }
  ],
  "request_id": "req_abc123"
}
```

---

#### 2.3.2 终止会话

| 项目 | 值 |
| --- | --- |
| **接口名称** | 终止指定会话 |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/auth/sessions/{session_id}` |
| **认证** | 用户 Token |

**注意事项：**
- 只能终止自己的会话
- 管理员可强制终止任一用户会话（操作记录写入审计日志）

---

### 2.4 MFA 多因素认证

#### 2.4.1 获取 MFA 绑定信息

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取 MFA 状态 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/auth/mfa` |
| **认证** | 用户 Token |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "is_enabled": false,
    "bound_at": null,
    "last_used_at": null
  },
  "request_id": "req_abc123"
}
```

---

#### 2.4.2 发起 MFA 绑定

| 项目 | 值 |
| --- | --- |
| **接口名称** | 发起 MFA 绑定 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/mfa/bind` |
| **认证** | 用户 Token + 密码确认 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `password` | `string` | 是 | 当前密码（二次确认） |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "secret": "JBSWY3DPEHPK3PXP",
    "qr_code_url": "otpauth://totp/ProductAnalysis:zhangsan@nebula-tech.com?secret=JBSWY3DPEHPK3PXP&issuer=ProductAnalysis",
    "recovery_codes": [
      "A1B2-C3D4-E5F6-G7H8",
      "I9J0-K1L2-M3N4-O5P6",
      "Q7R8-S9T0-U1V2-W3X4",
      "Y5Z6-A7B8-C9D0-E1F2",
      "G3H4-I5J6-K7L8-M9N0",
      "O1P2-Q3R4-S5T6-U7V8",
      "W9X0-Y1Z2-A3B4-C5D6",
      "E7F8-G9H0-I1J2-K3L4"
    ]
  },
  "request_id": "req_abc123"
}
```

**注意事项：**
- 恢复码仅此次返回，服务端存储 `code_hash`
- `totp_secret_encrypted` 使用 AES-256-GCM 加密存储

---

#### 2.4.3 确认 MFA 绑定

| 项目 | 值 |
| --- | --- |
| **接口名称** | 确认 MFA 绑定 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/mfa/bind/confirm` |
| **认证** | 用户 Token |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | `string` | 是 | TOTP 动态码 |

---

#### 2.4.4 解除 MFA 绑定

| 项目 | 值 |
| --- | --- |
| **接口名称** | 解除 MFA |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/auth/mfa` |
| **认证** | 用户 Token + 密码确认 |

---

### 2.5 SSO 单点登录

#### 2.5.1 获取 SSO 配置

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取租户 SSO 配置 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tenants/{tenant_id}/sso` |
| **认证** | `tenant_admin` |

---

#### 2.5.2 配置 SSO

| 项目 | 值 |
| --- | --- |
| **接口名称** | 配置/更新 SSO |
| **请求方式** | `PUT` |
| **URL** | `/api/v1/tenants/{tenant_id}/sso` |
| **认证** | `tenant_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `protocol` | `string` | 是 | `saml2` / `oidc` |
| `idp_metadata_url` | `string` | 否 | IdP 元数据 URL |
| `idp_metadata_xml` | `string` | 否 | IdP 元数据 XML（上传模式） |
| `idp_entity_id` | `string` | 否 | IdP Entity ID |
| `idp_sso_url` | `string` | 否 | IdP 单点登录 URL |
| `idp_certificate` | `string` | 否 | IdP 签名证书（PEM） |
| `sp_entity_id` | `string` | 否 | SP Entity ID |
| `sp_acs_url` | `string` | 否 | SP ACS URL |
| `attribute_mapping` | `object` | 否 | 属性映射 |
| `allowed_email_domains` | `string[]` | 否 | JIT 邮箱域名白名单 |
| `jit_provisioning` | `boolean` | 否 | 是否启用 JIT |
| `is_enabled` | `boolean` | 否 | 是否启用 SSO |

**请求示例：**

```json
{
  "protocol": "oidc",
  "idp_metadata_url": "https://sso.nebula-tech.com/.well-known/openid-configuration",
  "attribute_mapping": {
    "email": "mail",
    "name": "displayName"
  },
  "allowed_email_domains": ["nebula-tech.com"],
  "jit_provisioning": true,
  "is_enabled": true
}
```

---

#### 2.5.3 SSO 登录发起

| 项目 | 值 |
| --- | --- |
| **接口名称** | SSO 登录跳转 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/auth/sso/{tenant_slug}/login` |
| **认证** | 无需 |

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `tenant_slug` | `string` | 是 | 租户 slug |

**响应：** `302` 重定向至 IdP 登录页。

---

#### 2.5.4 SSO 回调

| 项目 | 值 |
| --- | --- |
| **接口名称** | SSO 回调处理 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/sso/{tenant_slug}/callback` |
| **认证** | 无需 |

**注意事项：**
- 验证 SAML Response / OIDC code 后签发平台 Token
- JIT 模式下自动创建用户（需邮箱域名在白名单中）
- 登录事件写入 `login_audit_logs`

---

#### 2.5.5 SSO 连通性测试

| 项目 | 值 |
| --- | --- |
| **接口名称** | 测试 SSO 连通性 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tenants/{tenant_id}/sso/test` |
| **认证** | `tenant_admin` |

---

### 2.6 密码重置

#### 2.6.1 发送重置邮件

| 项目 | 值 |
| --- | --- |
| **接口名称** | 发送密码重置邮件 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/password/reset` |
| **认证** | 无需（限流：同 IP 5 次 / 10 分钟） |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `tenant_slug` | `string` | 是 | 租户标识 |
| `email` | `string` | 是 | 邮箱 |

**注意事项：**
- 无论邮箱是否存在均返回成功（防止枚举攻击）
- 重置链接有效期 30 分钟
- 同一用户最多 1 个待使用令牌（创建新令牌时旧令牌自动失效）

---

#### 2.6.2 验证重置令牌

| 项目 | 值 |
| --- | --- |
| **接口名称** | 验证重置令牌 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/auth/password/reset/{token}` |
| **认证** | 无需 |

---

#### 2.6.3 执行密码重置

| 项目 | 值 |
| --- | --- |
| **接口名称** | 重置密码 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/auth/password/reset/{token}` |
| **认证** | 无需 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `new_password` | `string` | 是 | 新密码 |

---

### 2.7 成员邀请

#### 2.7.1 发起邀请

| 项目 | 值 |
| --- | --- |
| **接口名称** | 邀请成员 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tenants/{tenant_id}/invitations` |
| **认证** | `tenant_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `email` | `string` | 是 | 被邀请人邮箱 |
| `role` | `string` | 否 | 默认角色 `project_member` |

**注意事项：**
- 同一邮箱 24 小时内最多 3 次邀请
- 邀请链接 48 小时有效

---

#### 2.7.2 获取邀请列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取邀请列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tenants/{tenant_id}/invitations` |
| **认证** | `tenant_admin` |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | `string` | 否 | `pending` / `activated` / `expired` |

---

#### 2.7.3 撤销邀请

| 项目 | 值 |
| --- | --- |
| **接口名称** | 撤销邀请 |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/tenants/{tenant_id}/invitations/{invitation_id}` |
| **认证** | `tenant_admin` |

---

#### 2.7.4 接受邀请

| 项目 | 值 |
| --- | --- |
| **接口名称** | 接受邀请并激活账号 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/invitations/{token}` |
| **认证** | 无需 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | `string` | 是 | 显示名 |
| `password` | `string` | 是 | 密码 |

---

### 2.8 登录审计日志

#### 2.8.1 获取登录审计日志

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取登录审计日志 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/audit/login-logs` |
| **认证** | `tenant_admin` |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_id` | `string` | 否 | 按用户过滤 |
| `operation` | `string` | 否 | `login` / `logout` / `password_change` / `password_reset` / `mfa_enable` / `mfa_disable` / `session_terminated` / `account_locked` / `account_unlocked` / `sso_config_change` |
| `result` | `string` | 否 | `success` / `failure` |
| `start_time` | `string` | 否 | 开始时间（ISO 8601） |
| `end_time` | `string` | 否 | 结束时间（ISO 8601） |
| `page` | `integer` | 否 | 页码 |
| `page_size` | `integer` | 否 | 每页条数 |

**注意事项：**
- 审计日志只读，普通用户不可删除或修改
- 数据按月分区，查询跨越分区时性能依数据量而定

---

## 3. 项目管理与数据源

### 3.1 项目管理

#### 3.1.1 创建项目

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建项目 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects` |
| **认证** | `tenant_admin` 或 `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | — | 项目名称，最长 128 字符 |
| `description` | `string` | 否 | — | 项目描述 |
| `timezone` | `string` | 否 | `Asia/Shanghai` | 项目时区 |
| `settings` | `object` | 否 | `{}` | 项目级配置 |

**请求示例：**

```json
{
  "name": "智慧零售平台",
  "description": "面向零售行业的智能数据分析与运营管理平台",
  "timezone": "Asia/Shanghai"
}
```

**成功响应 `201`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "智慧零售平台",
    "description": "面向零售行业的智能数据分析与运营管理平台",
    "status": "active",
    "timezone": "Asia/Shanghai",
    "settings": {},
    "created_at": "2026-07-24T11:00:00+08:00"
  },
  "request_id": "req_abc123"
}
```

**错误响应 `400` — 超过租户项目数上限：**

```json
{
  "code": 42202,
  "message": "Project limit exceeded",
  "detail": "Tenant 'nebula-tech' has reached the maximum project limit of 10",
  "request_id": "req_abc123"
}
```

---

#### 3.1.2 获取项目列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取项目列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects` |
| **认证** | 用户 Token |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | `string` | 否 | `active` / `archived` / `suspended` |
| `search` | `string` | 否 | 按 name 模糊搜索 |
| `page` | `integer` | 否 | 页码 |
| `page_size` | `integer` | 否 | 每页条数 |

**注意事项：**
- 普通成员只返回自己加入的项目
- `tenant_admin` 可查看租户下所有项目

---

#### 3.1.3 获取项目详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取项目详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}` |
| **认证** | 项目成员 |

---

#### 3.1.4 更新项目

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新项目 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}` |
| **认证** | `project_admin` 或 `tenant_admin` |

---

#### 3.1.5 删除/归档项目

| 项目 | 值 |
| --- | --- |
| **接口名称** | 删除/归档项目 |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/projects/{project_id}` |
| **认证** | `tenant_admin` |

---

### 3.2 项目成员

#### 3.2.1 获取项目成员

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取项目成员列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/members` |
| **认证** | 项目成员 |

---

#### 3.2.2 添加项目成员

| 项目 | 值 |
| --- | --- |
| **接口名称** | 添加项目成员 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/members` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `user_id` | `string` | 是 | — | 用户 ID |
| `role` | `string` | 否 | `project_member` | 项目内角色：`project_admin` / `project_member` / `viewer` |

---

#### 3.2.3 更新成员角色

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新成员角色 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}/members/{user_id}` |
| **认证** | `project_admin` |

---

#### 3.2.4 移除成员

| 项目 | 值 |
| --- | --- |
| **接口名称** | 移除项目成员 |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/projects/{project_id}/members/{user_id}` |
| **认证** | `project_admin` |

---

### 3.3 数据源管理

#### 3.3.1 创建数据源

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建数据源 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/data-sources` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | — | 名称，最长 128 字符 |
| `source_type` | `string` | 是 | — | 类型：`prd_repo` / `api_platform` / `tracking_system` / `code_repo` / `monitoring` / `logging` / `ticketing` |
| `connection_config` | `object` | 是 | — | 连接配置（服务端 AES-256-GCM 加密存储） |
| `sync_interval` | `integer` | 否 | `3600` | 自动同步间隔（秒），null 仅手动 |

**请求示例：**

```json
{
  "name": "GitLab 主仓库",
  "source_type": "code_repo",
  "connection_config": {
    "type": "gitlab",
    "base_url": "https://gitlab.nebula-tech.com",
    "project_path": "retail/smart-retail-platform",
    "access_token": "glpat-xxxxxxxxxxxx"
  },
  "sync_interval": 1800
}
```

---

#### 3.3.2 获取数据源列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取数据源列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/data-sources` |
| **认证** | 项目成员 |

---

#### 3.3.3 更新数据源

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新数据源 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}/data-sources/{source_id}` |
| **认证** | `project_admin` |

---

#### 3.3.4 测试数据源连接

| 项目 | 值 |
| --- | --- |
| **接口名称** | 测试数据源连接 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/data-sources/{source_id}/test` |
| **认证** | `project_admin` |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "Connection test passed",
  "data": {
    "status": "connected",
    "latency_ms": 320,
    "tested_at": "2026-07-24T11:30:00+08:00"
  },
  "request_id": "req_abc123"
}
```

---

#### 3.3.5 手动触发同步

| 项目 | 值 |
| --- | --- |
| **接口名称** | 手动触发数据源同步 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/data-sources/{source_id}/sync` |
| **认证** | `project_admin` |

**请求体（可选）：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `sync_scope` | `object` | 否 | 限定同步范围（项目子集、文档类型、时间窗） |

**成功响应 `202`：**

```json
{
  "code": 0,
  "message": "Sync job queued",
  "data": {
    "sync_record_id": "d4e5f6a7-b8c9-0123-defa-123456789012"
  },
  "request_id": "req_abc123"
}
```

---

#### 3.3.6 删除数据源

| 项目 | 值 |
| --- | --- |
| **接口名称** | 删除数据源（软删除） |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/projects/{project_id}/data-sources/{source_id}` |
| **认证** | `project_admin` |

---

### 3.4 同步记录

#### 3.4.1 获取同步记录列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取同步记录 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/data-sources/{source_id}/sync-records` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `result` | `string` | 否 | `success` / `partial` / `failure` |
| `start_time` | `string` | 否 | 开始时间 |
| `end_time` | `string` | 否 | 结束时间 |
| `page` | `integer` | 否 | 页码 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "d4e5f6a7-b8c9-0123-defa-123456789012",
        "data_source_id": "e5f6a7b8-c9d0-1234-efab-123456789012",
        "sync_type": "manual",
        "started_at": "2026-07-24T11:30:05+08:00",
        "ended_at": "2026-07-24T11:30:45+08:00",
        "result": "success",
        "items_added": 12,
        "items_updated": 3,
        "items_deleted": 0,
        "items_failed": 0
      }
    ],
    "total": 45,
    "page": 1,
    "page_size": 20
  },
  "request_id": "req_abc123"
}
```

---

## 4. 需求池与评估模型

### 4.1 需求管理

#### 4.1.1 创建需求

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建需求 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/requirements` |
| **认证** | 项目成员 |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | — | 需求名称，最长 256 字符 |
| `external_id` | `string` | 否 | — | 外部系统编号 |
| `background` | `string` | 否 | — | 背景描述 |
| `target_users` | `string` | 否 | — | 目标用户 |
| `core_scenarios` | `string` | 否 | — | 核心场景 |
| `user_coverage_description` | `string` | 否 | — | 用户覆盖范围 |
| `business_value_description` | `string` | 否 | — | 业务价值说明 |
| `strategic_alignment` | `string` | 否 | — | 战略匹配度 |
| `estimated_man_days` | `number` | 否 | — | 预计人天 |
| `estimated_duration_days` | `integer` | 否 | — | 预计工期（天） |
| `technical_complexity` | `string` | 否 | — | `low` / `medium` / `high` / `critical` |
| `dependencies` | `string` | 否 | — | 依赖说明 |
| `business_risks` | `string` | 否 | — | 业务风险 |
| `technical_risks` | `string` | 否 | — | 技术风险 |
| `compliance_risks` | `string` | 否 | — | 合规风险 |
| `delivery_risks` | `string` | 否 | — | 交付风险 |
| `assignee_id` | `string` | 否 | — | 负责人 ID |
| `expected_launch_date` | `string` | 否 | — | 期望上线日期 |

**请求示例：**

```json
{
  "name": "用户画像看板 — 实时行为分析",
  "external_id": "SRP-2026-042",
  "background": "零售运营人员缺少对用户实时行为的可视化分析工具，当前只能依赖离线 T+1 报表",
  "target_users": "运营专员、门店经理、数据分析师",
  "core_scenarios": "实时查看用户在 App 内的浏览路径、加购/收藏行为、优惠券核销链路",
  "estimated_man_days": 45.0,
  "estimated_duration_days": 15,
  "technical_complexity": "high",
  "expected_launch_date": "2026-09-01"
}
```

---

#### 4.1.2 获取需求列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取需求列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/requirements` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | `string` | 否 | `draft` / `submitted` / `evaluating` / `prioritized` / `scheduled` / `in_development` / `closed` |
| `current_priority` | `string` | 否 | `P0` / `P1` / `P2` / `P3` |
| `assignee_id` | `string` | 否 | 负责人 ID |
| `search` | `string` | 否 | 按 name 模糊搜索 |
| `page` | `integer` | 否 | 页码 |
| `page_size` | `integer` | 否 | 每页条数 |
| `sort_by` | `string` | 否 | 排序字段，支持 `current_total_score` |

---

#### 4.1.3 获取需求详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取需求详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/requirements/{requirement_id}` |
| **认证** | 项目成员 |

**成功响应 `200` 额外包含：**
- `latest_assessment` — 最新评估结果摘要
- `assessment_history` — 评估历史列表（最近 5 次）

---

#### 4.1.4 更新需求

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新需求 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}/requirements/{requirement_id}` |
| **认证** | 项目成员（仅创建人或 `project_admin` 可修改状态） |

**注意事项：**
- `status` 变更规则：
  - `draft → submitted`（提交评估）
  - `submitted → evaluating`（评估任务启动后系统自动变更）
  - `evaluating → prioritized`（评估完成后系统自动变更）
  - `prioritized → scheduled / in_development / closed`（人工流转）

---

#### 4.1.5 删除需求

| 项目 | 值 |
| --- | --- |
| **接口名称** | 删除需求（软删除） |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/projects/{project_id}/requirements/{requirement_id}` |
| **认证** | `project_admin` |

---

### 4.2 评估模型

#### 4.2.1 创建评估模型

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建评估模型 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/assessment-models` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | — | 模型名称 |
| `total_score_formula` | `string` | 是 | — | 总分计算公式 DSL |
| `priority_thresholds` | `object` | 是 | — | 优先级阈值 |
| `dimensions` | `array` | 是 | — | 评估维度配置 |

**请求示例：**

```json
{
  "name": "零售平台标准评估模型",
  "total_score_formula": "SUM(dimension.converted_score * dimension.weight)",
  "priority_thresholds": {
    "P0": 80,
    "P1": 65,
    "P2": 50,
    "P3": 0
  },
  "dimensions": [
    {
      "name": "用户覆盖",
      "weight": 0.200,
      "scoring_direction": "positive",
      "sort_order": 1,
      "anchors": [
        {"score": 5, "description": "覆盖平台 80% 以上活跃用户", "criteria": "功能上线后预计日均触达用户数 ≥ 平台 DAU 的 80%"},
        {"score": 4, "description": "覆盖平台 50%–80% 活跃用户", "criteria": "功能上线后预计日均触达用户数占平台 DAU 50%–80%"},
        {"score": 3, "description": "覆盖特定核心用户群", "criteria": "覆盖 1–2 个核心用户分群，占比 20%–50%"},
        {"score": 2, "description": "覆盖少量长尾用户", "criteria": "覆盖小众场景或 5%–20% 用户"},
        {"score": 1, "description": "仅覆盖极少用户", "criteria": "覆盖率不足 5%，或仅面向内部管理"}
      ]
    },
    {
      "name": "业务价值",
      "weight": 0.300,
      "scoring_direction": "positive",
      "sort_order": 2,
      "anchors": []
    }
  ]
}
```

---

#### 4.2.2 获取评估模型列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取评估模型列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/assessment-models` |
| **认证** | 项目成员 |

---

#### 4.2.3 获取模型详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取评估模型详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/assessment-models/{model_id}` |
| **认证** | 项目成员 |

**成功响应包含：** 维度列表、评分锚点、完整公式。

---

#### 4.2.4 更新模型

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新评估模型 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}/assessment-models/{model_id}` |
| **认证** | `project_admin` |

**注意事项：**
- 模型更新后 `version` 自增
- 已在执行中的评估任务不受影响（锁定创建时版本）

---

#### 4.2.5 激活/停用模型

| 项目 | 值 |
| --- | --- |
| **接口名称** | 激活/停用评估模型 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/assessment-models/{model_id}/activate` |
| **认证** | `project_admin` |

---

### 4.3 评估维度与锚点

#### 4.3.1 更新维度

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新评估维度 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}/assessment-models/{model_id}/dimensions/{dimension_id}` |
| **认证** | `project_admin` |

**约束：**
- 所有维度 `weight` 之和必须为 `1.000`

---

#### 4.3.2 更新评分锚点

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新评分锚点 |
| **请求方式** | `PUT` |
| **URL** | `/api/v1/projects/{project_id}/assessment-models/{model_id}/dimensions/{dimension_id}/anchors/{score}` |
| **认证** | `project_admin` |

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `score` | `integer` | 是 | 分数 1–5 |

---

### 4.4 评估任务

#### 4.4.1 发起评估

| 项目 | 值 |
| --- | --- |
| **接口名称** | 发起需求评估 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/requirements/{requirement_id}/assess` |
| **认证** | 项目成员 |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `model_id` | `string` | 是 | — | 使用的评估模型 ID |
| `title` | `string` | 否 | — | 评估任务标题，默认 "{需求名称} 评估" |

**请求示例：**

```json
{
  "model_id": "f6a7b8c9-d0e1-2345-fabc-123456789012",
  "title": "用户画像看板 V1 价值评估"
}
```

**成功响应 `202`（异步执行）：**

```json
{
  "code": 0,
  "message": "Assessment task created and queued",
  "data": {
    "task_id": "a7b8c9d0-e1f2-3456-abcd-123456789012",
    "status": "draft",
    "created_at": "2026-07-24T14:00:00+08:00"
  },
  "request_id": "req_abc123"
}
```

**注意事项：**
- 评估任务异步执行，通过 WebSocket 推送状态变更
- 同一需求可多次发起评估（历史评估记录保留）
- 评估完成进入 `pending_review` 状态后需人工确认

---

#### 4.4.2 获取评估任务详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取评估任务详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/assessment` |
| **认证** | 项目成员 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "task": {
      "id": "a7b8c9d0-e1f2-3456-abcd-123456789012",
      "task_id": "a7b8c9d0-e1f2-3456-abcd-123456789012",
      "requirement_id": "b8c9d0e1-f2a3-4567-bcde-123456789012",
      "model_id": "f6a7b8c9-d0e1-2345-fabc-123456789012",
      "model_name": "零售平台标准评估模型 V3",
      "total_score": 72.5,
      "suggested_priority": "P1",
      "has_risk_flag": false,
      "status": "pending_review"
    },
    "dimension_scores": [
      {
        "id": "c9d0e1f2-a3b4-5678-cdef-123456789012",
        "dimension_name": "用户覆盖",
        "weight": 0.200,
        "raw_score": 4,
        "converted_score": 80.0,
        "confidence": "high",
        "evidence_citations": "根据需求文档 §3.1，该功能预计覆盖平台 65% 活跃用户",
        "inference_explanation": "基于锚点定义，65% 覆盖率对应 4 分",
        "missing_evidence": null
      },
      {
        "id": "d0e1f2a3-b4c5-6789-defa-123456789012",
        "dimension_name": "业务价值",
        "weight": 0.300,
        "raw_score": 4,
        "converted_score": 80.0,
        "confidence": "medium"
      },
      {
        "id": "e1f2a3b4-c5d6-7890-efab-123456789012",
        "dimension_name": "战略匹配度",
        "weight": 0.200,
        "raw_score": 4,
        "converted_score": 80.0,
        "confidence": "high"
      },
      {
        "id": "f2a3b4c5-d6e7-8901-fabc-123456789012",
        "dimension_name": "实现成本",
        "weight": 0.150,
        "raw_score": 3,
        "converted_score": 60.0,
        "confidence": "low",
        "missing_evidence": "缺少详细技术方案和工期估算"
      },
      {
        "id": "a3b4c5d6-e7f8-9012-abcd-123456789012",
        "dimension_name": "风险",
        "weight": 0.150,
        "raw_score": 2,
        "converted_score": 40.0,
        "confidence": "medium"
      }
    ],
    "sensitivity": [
      {
        "adjusted_weights": {"用户覆盖": 0.220, "业务价值": 0.270, "战略匹配度": 0.220, "实现成本": 0.135, "风险": 0.155},
        "adjusted_total_score": 74.1,
        "priority_changed": false
      }
    ],
    "snapshot_at": "2026-07-24T14:00:05+08:00",
    "created_at": "2026-07-24T14:00:00+08:00"
  },
  "request_id": "req_abc123"
}
```

---

#### 4.4.3 获取需求评估历史

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取需求评估历史 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/requirements/{requirement_id}/assessments` |
| **认证** | 项目成员 |

---

### 4.5 评分确认

#### 4.5.1 确认评估结果

| 项目 | 值 |
| --- | --- |
| **接口名称** | 确认/修正评估结果 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tasks/{task_id}/assessment/confirm` |
| **认证** | `project_admin` 或需求负责人 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `confirmation_type` | `string` | 是 | `accept` / `revise` / `reject` |
| `adjustments` | `object` | `revise` 时必填 | 调整内容 |
| `adjustments.dimension_scores` | `array` | 否 | 调整各维度分数 |
| `adjustments.priority` | `string` | 否 | 手动指定优先级 |
| `adjustment_reason` | `string` | `revise` 时必填 | 调整理由 |

**请求示例（修正评分）：**

```json
{
  "confirmation_type": "revise",
  "adjustments": {
    "dimension_scores": [
      {"dimension_id": "f2a3b4c5-d6e7-8901-fabc-123456789012", "raw_score": 4}
    ],
    "adjustment_reason": "经过与技术负责人沟通，实现成本实际可控，调整实现成本为 4 分"
  }
}
```

**注意事项：**
- P0 修正或跨两级调整时 `needs_review = true`，需复核人审批
- 确认后更新 `requirements.current_priority` 和 `requirements.current_total_score`

---

#### 4.5.2 复核评估确认

| 项目 | 值 |
| --- | --- |
| **接口名称** | 复核评估确认 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tasks/{task_id}/assessment/confirm/{confirmation_id}/review` |
| **认证** | 指定复核人 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `review_status` | `string` | 是 | `approved` / `rejected` |
| `review_comment` | `string` | 是 | 复核意见 |

---

## 5. 交付物一致性检查

### 5.1 交付物管理

#### 5.1.1 创建交付物

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建/上传交付物 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/deliverables` |
| **认证** | 项目成员 |
| **Content-Type** | `multipart/form-data` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | — | 交付物名称 |
| `deliverable_type` | `string` | 是 | — | `prd` / `prototype_spec` / `api_doc` / `tracking_plan` / `test_case` |
| `requirement_id` | `string` | 否 | — | 关联需求 ID |
| `file` | `file` | 是 | — | 上传文件 |
| `source_system` | `string` | 否 | — | 来源系统 |
| `source_version` | `string` | 否 | — | 来源版本号 |
| `is_primary_version` | `boolean` | 否 | `false` | 多版本冲突时是否为主版本 |

---

#### 5.1.2 获取交付物列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取交付物列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/deliverables` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `deliverable_type` | `string` | 否 | 按类型过滤 |
| `requirement_id` | `string` | 否 | 按关联需求过滤 |
| `is_primary_version` | `boolean` | 否 | 仅主版本 |

---

#### 5.1.3 获取交付物详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取交付物详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/deliverables/{deliverable_id}` |
| **认证** | 项目成员 |

**成功响应包含：**
- `content_summary` — AI 生成的摘要
- `file_download_url` — 预签名下载链接（5 分钟有效）
- `associated_baselines` — 关联的基线列表

---

#### 5.1.4 更新交付物

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新交付物元数据 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}/deliverables/{deliverable_id}` |
| **认证** | 项目成员 |

---

#### 5.1.5 下载交付物

| 项目 | 值 |
| --- | --- |
| **接口名称** | 下载交付物文件 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/deliverables/{deliverable_id}/download` |
| **认证** | 项目成员 |

**响应：** `302` 重定向至 MinIO 预签名 URL。

---

### 5.2 检查基线

#### 5.2.1 创建检查基线

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建检查基线 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/check-baselines` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `requirement_id` | `string` | 否 | — | 关联需求 |
| `baseline_number` | `string` | 是 | — | 基线编号 |
| `check_scope` | `string` | 否 | `full` | `full` / `incremental` / `specified_rules` |
| `previous_baseline_id` | `string` | `incremental` 时必填 | — | 上一基线 ID |
| `deliverable_ids` | `array` | 是 | — | 纳入检查的交付物 ID 列表 |

**请求示例：**

```json
{
  "requirement_id": "b8c9d0e1-f2a3-4567-bcde-123456789012",
  "baseline_number": "BL-SRP-2026-003",
  "check_scope": "full",
  "deliverable_ids": [
    "b3c4d5e6-f7a8-9012-bcde-223456789012",
    "c4d5e6f7-a8b9-0123-cdef-323456789012",
    "d5e6f7a8-b9c0-1234-defa-423456789012"
  ]
}
```

**注意事项：**
- 基线创建后 `baseline_number` 和 `check_scope` 不可修改
- 项目内 `baseline_number` 唯一

---

#### 5.2.2 获取基线列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取基线列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/check-baselines` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | `string` | 否 | `active` / `superseded` |
| `requirement_id` | `string` | 否 | 按需求过滤 |

---

#### 5.2.3 获取基线详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取基线详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/check-baselines/{baseline_id}` |
| **认证** | 项目成员 |

**成功响应包含：**
- `deliverables` — 关联交付物列表（含快照版本和路径）
- `check_tasks` — 基线关联的检查任务历史

---

### 5.3 检查规则

#### 5.3.1 创建检查规则

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建检查规则 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/check-rules` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `dimension` | `string` | 是 | — | 维度：`field` / `flow` / `permission` / `exception` / `acceptance` |
| `name` | `string` | 是 | — | 规则名称 |
| `description` | `string` | 否 | — | 规则描述 |
| `judgment_logic` | `string` | 是 | — | 判定逻辑 DSL |
| `suggested_level` | `string` | 否 | `general` | `blocker` / `critical` / `general` / `info` |
| `is_enabled` | `boolean` | 否 | `true` | 是否启用 |
| `priority` | `integer` | 否 | `0` | 规则优先级 |

**请求示例：**

```json
{
  "dimension": "field",
  "name": "字段类型一致性检查",
  "description": "检查 PRD 中定义的字段类型与接口文档是否一致",
  "judgment_logic": "MATCH prd.fields[*].type WITH api.schema.properties[*].type WHERE name = name RETURN CONFLICT IF type != type",
  "suggested_level": "critical",
  "is_enabled": true,
  "priority": 10
}
```

---

#### 5.3.2 获取规则列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取检查规则列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/check-rules` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `dimension` | `string` | 否 | 按维度过滤 |
| `is_enabled` | `boolean` | 否 | 仅启用/停用 |
| `include_global` | `boolean` | 否 | 是否包含全局通用规则 |

---

#### 5.3.3 更新规则

| 项目 | 值 |
| --- | --- |
| **接口名称** | 更新检查规则 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/projects/{project_id}/check-rules/{rule_id}` |
| **认证** | `project_admin` |

---

#### 5.3.4 删除规则

| 项目 | 值 |
| --- | --- |
| **接口名称** | 删除检查规则（软删除） |
| **请求方式** | `DELETE` |
| **URL** | `/api/v1/projects/{project_id}/check-rules/{rule_id}` |
| **认证** | `project_admin` |

---

### 5.4 检查任务

#### 5.4.1 发起一致性检查

| 项目 | 值 |
| --- | --- |
| **接口名称** | 发起一致性检查 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/check-baselines/{baseline_id}/check` |
| **认证** | 项目成员 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `title` | `string` | 否 | 检查标题 |
| `rule_ids` | `array` | 否 | 指定使用的规则 ID 列表（不填则使用全部启用规则） |

**成功响应 `202`：**

```json
{
  "code": 0,
  "message": "Consistency check task queued",
  "data": {
    "task_id": "e5f6a7b8-c9d0-1234-efab-523456789012",
    "baseline_id": "f6a7b8c9-d0e1-2345-fabc-123456789012",
    "status": "draft",
    "created_at": "2026-07-24T15:00:00+08:00"
  },
  "request_id": "req_abc123"
}
```

**注意事项：**
- 检查任务 95% 在 10 分钟内完成（≤ 20 文件 / 500 页）
- 规则引擎前置过滤确定性冲突，减少大模型调用
- 结果结构包含 `total_issues`、`blocker_count`、`critical_count`、`general_count`、`info_count`

---

#### 5.4.2 获取检查任务详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取检查任务详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/check` |
| **认证** | 项目成员 |

---

#### 5.4.3 获取检查问题列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取检查问题列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/check/issues` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `level` | `string` | 否 | `blocker` / `critical` / `general` / `info` |
| `dimension` | `string` | 否 | 按检查维度过滤 |
| `status` | `string` | 否 | `pending` / `acknowledged` / `in_progress` / `pending_recheck` / `closed` / `waived` / `false_positive` |
| `assigned_to` | `string` | 否 | 按责任人过滤 |

---

### 5.5 问题管理

#### 5.5.1 获取问题详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取问题详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/check-issues/{issue_id}` |
| **认证** | 项目成员 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "a7b8c9d0-e1f2-3456-abcd-623456789012",
    "check_task_id": "e5f6a7b8-c9d0-1234-efab-523456789012",
    "rule_id": "f6a7b8c9-d0e1-2345-fabc-723456789012",
    "dimension": "field",
    "title": "用户状态字段类型不一致：PRD 定义 string vs API 定义 integer",
    "level": "blocker",
    "confidence": "high",
    "involved_deliverables": [
      {
        "deliverable_id": "b3c4d5e6-f7a8-9012-bcde-223456789012",
        "name": "智慧零售平台 PRD V4",
        "citation": "§2.3 用户管理 > 用户状态字段",
        "excerpt": "用户状态（status）取值为 active / inactive / suspended"
      },
      {
        "deliverable_id": "c4d5e6f7-a8b9-0123-cdef-323456789012",
        "name": "用户管理 API V2",
        "citation": "GET /api/v2/users > Response Schema > status",
        "excerpt": "status: integer, 0=正常 1=禁用 2=挂起"
      }
    ],
    "conflict_comparison": "PRD 将用户状态定义为字符串类型（active/inactive/suspended），API 接口定义为整型（0/1/2），前端/客户端需维护两套转换逻辑，容易产生数据一致性问题",
    "potential_impact": "前后端状态映射错误可能导致用户权限判断异常、运营报表统计偏差",
    "suggested_fix": "统一为 string 类型，API 端调整返回格式，增加状态枚举值校验",
    "recommended_role": "developer",
    "status": "pending",
    "assigned_to": null,
    "created_at": "2026-07-24T15:05:30+08:00"
  },
  "request_id": "req_abc123"
}
```

---

#### 5.5.2 更新问题级别

| 项目 | 值 |
| --- | --- |
| **接口名称** | 调整问题级别 |
| **请求方式** | `PATCH` |
| **URL** | `/api/v1/check-issues/{issue_id}/level` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `adjusted_level` | `string` | 是 | 调整后级别 |
| `level_adjust_reason` | `string` | 是 | 调整理由 |

---

### 5.6 问题处置与复检

#### 5.6.1 处置问题

| 项目 | 值 |
| --- | --- |
| **接口名称** | 处置问题（认领/修复/豁免/标记误报） |
| **请求方式** | `POST` |
| **URL** | `/api/v1/check-issues/{issue_id}/assignments` |
| **认证** | 项目成员 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `assignee_id` | `string` | 是 | 责任人 |
| `operation` | `string` | 是 | `acknowledge` / `fix` / `waive` / `mark_false_positive` |

**fix 操作额外参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `fix_description` | `string` | 是 | 修正说明 |
| `new_material_version` | `string` | 否 | 新材料版本号 |
| `new_material_path` | `string` | 否 | 新材料路径 |

**waive 操作额外参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `waiver_reason` | `string` | 是 | 豁免理由 |
| `waiver_valid_until` | `string` | 否 | 豁免有效期 |

**注意事项：**
- 阻断级问题豁免需两方确认（`waiver_approvals` 至少 2 条记录）

**请求示例（豁免操作）：**

```json
{
  "assignee_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "operation": "waive",
  "waiver_reason": "该字段类型差异已在 V3 规划中统一，当前版本对业务无实际影响",
  "waiver_valid_until": "2026-09-30"
}
```

---

#### 5.6.2 获取问题处置历史

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取问题处置历史 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/check-issues/{issue_id}/assignments` |
| **认证** | 项目成员 |

---

#### 5.6.3 复检问题

| 项目 | 值 |
| --- | --- |
| **接口名称** | 发起问题复检 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/check-issues/{issue_id}/recheck` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `recheck_baseline_id` | `string` | 是 | 用于复检的基线 ID |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "Recheck passed",
  "data": {
    "recheck_result": "passed",
    "recheck_detail": "API 文档已更新为 string 类型，与 PRD 定义一致，问题已解决",
    "rechecked_at": "2026-07-24T16:00:00+08:00"
  },
  "request_id": "req_abc123"
}
```

**注意事项：**
- 复检通过 → 问题状态变更为 `closed`
- 复检失败 → 问题状态回退为 `in_progress`

---

#### 5.6.4 获取复检历史

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取复检历史 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/check-issues/{issue_id}/rechecks` |
| **认证** | 项目成员 |

---

## 6. 上线问题归因

### 6.1 发布版本

#### 6.1.1 创建发布版本

| 项目 | 值 |
| --- | --- |
| **接口名称** | 创建发布版本 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/releases` |
| **认证** | `project_admin` |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `version_number` | `string` | 是 | — | 版本号，项目内唯一 |
| `release_date` | `string` | 否 | — | 发布日期 |
| `associated_requirements` | `array` | 否 | `[]` | 关联需求 ID 列表 |
| `status` | `string` | 否 | `planned` | `planned` / `released` / `rolled_back` |
| `release_notes` | `string` | 否 | — | 发布说明 |

**请求示例：**

```json
{
  "version_number": "v2.5.0",
  "release_date": "2026-07-20",
  "associated_requirements": [
    "b8c9d0e1-f2a3-4567-bcde-123456789012",
    "c9d0e1f2-a3b4-5678-cdef-123456789012"
  ],
  "status": "released",
  "release_notes": "新增用户画像看板、优化搜索性能、修复订单状态同步 Bug"
}
```

---

#### 6.1.2 获取版本列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取版本列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/releases` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | `string` | 否 | `planned` / `released` / `rolled_back` |

---

#### 6.1.3 获取版本详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取版本详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/releases/{release_id}` |
| **认证** | 项目成员 |

---

### 6.2 归因任务

#### 6.2.1 发起归因分析

| 项目 | 值 |
| --- | --- |
| **接口名称** | 发起问题归因 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/projects/{project_id}/releases/{release_id}/attribute` |
| **认证** | 项目成员 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `anomaly_name` | `string` | 是 | 异常名称 |
| `anomaly_window_start` | `string` | 是 | 异常时间窗开始（ISO 8601） |
| `anomaly_window_end` | `string` | 否 | 异常时间窗结束（未恢复时为空） |
| `impact_scope` | `string` | 否 | 影响范围 |
| `user_impact` | `string` | 否 | 用户表现描述 |
| `current_handling_status` | `string` | 否 | 当前处置状态 |
| `associated_alerts` | `array` | 否 | 关联告警/工单编号列表 |
| `title` | `string` | 否 | 任务标题 |

**请求示例：**

```json
{
  "anomaly_name": "订单提交接口 P99 延迟飙升",
  "anomaly_window_start": "2026-07-21T14:00:00+08:00",
  "anomaly_window_end": "2026-07-21T16:30:00+08:00",
  "impact_scope": "订单提交成功率从 99.7% 降至 87.2%",
  "user_impact": "用户下单时频繁收到"提交失败"或长时间等待后超时",
  "current_handling_status": "mitigating",
  "associated_alerts": ["ALERT-20260721-0034", "ONCALL-2884"],
  "title": "v2.5.0 上线后订单提交接口延迟归因"
}
```

**成功响应 `202`：**

```json
{
  "code": 0,
  "message": "Attribution task created and queued",
  "data": {
    "task_id": "f6a7b8c9-d0e1-2345-fabc-823456789012",
    "status": "draft",
    "created_at": "2026-07-24T16:30:00+08:00"
  },
  "request_id": "req_abc123"
}
```

---

#### 6.2.2 获取归因任务详情

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取归因任务详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/attribution` |
| **认证** | 项目成员 |

**成功响应包含：**
- `timeline_events` — 时间线事件列表
- `attribution_results` — 归因结果（主因 + 促成因素）
- `confirmations` — 人工确认历史

---

#### 6.2.3 获取版本归因历史

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取版本归因历史 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/projects/{project_id}/releases/{release_id}/attributions` |
| **认证** | 项目成员 |

---

### 6.3 时间线事件

#### 6.3.1 获取归因任务时间线

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取归因时间线 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/attribution/timeline` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_source` | `string` | 否 | 按来源过滤 |
| `credibility` | `string` | 否 | `confirmed` / `uncertain` |
| `start_time` | `string` | 否 | 项目时区开始时间 |
| `end_time` | `string` | 否 | 项目时区结束时间 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "events": [
      {
        "id": "a8b9c0d1-e2f3-4567-bcde-723456789012",
        "event_source": "code_merge",
        "original_timestamp": "2026-07-20T10:15:00Z",
        "project_timestamp": "2026-07-20T18:15:00+08:00",
        "summary": "Merge Request !2841: 订单提交流程重构，引入异步支付网关",
        "source_url": "https://gitlab.nebula-tech.com/retail/smart-retail/-/merge_requests/2841",
        "related_object_type": "merge_request",
        "related_object_id": "2841",
        "credibility": "confirmed"
      },
      {
        "id": "b9c0d1e2-f3a4-5678-cdef-723456789012",
        "event_source": "monitor_alert",
        "original_timestamp": "2026-07-21T06:15:00Z",
        "project_timestamp": "2026-07-21T14:15:00+08:00",
        "summary": "监控告警：订单提交 P99 延迟从 200ms 升至 3500ms，触发 P0 告警",
        "source_url": "https://monitor.nebula-tech.com/alerts/ALERT-20260721-0034",
        "related_object_type": "alert",
        "related_object_id": "ALERT-20260721-0034",
        "credibility": "confirmed"
      }
    ],
    "total": 18
  },
  "request_id": "req_abc123"
}
```

---

#### 6.3.2 手动添加时间线事件

| 项目 | 值 |
| --- | --- |
| **接口名称** | 手动添加时间线事件 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tasks/{task_id}/attribution/timeline` |
| **认证** | 项目成员 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `event_source` | `string` | 是 | 事件来源 |
| `original_timestamp` | `string` | 是 | 原始时间 |
| `summary` | `string` | 是 | 事件摘要 |
| `credibility` | `string` | 否 | `confirmed` / `uncertain`，默认 `confirmed` |

---

### 6.4 归因结果与确认

#### 6.4.1 获取归因结果

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取归因结果 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/attribution/results` |
| **认证** | 项目成员 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "c0d1e2f3-a4b5-6789-defa-723456789012",
      "category": "implementation_error",
      "is_primary": true,
      "confidence": "high",
      "reasoning_chain": "MR !2841 引入异步支付网关后，支付回调处理未设置合理的超时和重试机制。在支付网关响应变慢时，线程池耗尽导致订单提交整体阻塞。时间线显示：MR 合并后 28 小时出现延迟飙升，与异步改造上线时间高度吻合。",
      "supporting_evidence": [
        {"type": "fact", "source": "GitLab MR !2841", "citation": "src/order/submit.py:156-203", "excerpt": "新增 async_payment_gateway.process() 调用，未设置 timeout 参数"}
      ],
      "counter_evidence": [],
      "missing_evidence": [
        {"type": "missing", "description": "缺少 MR !2841 的压测报告，无法确认是否在预发环境做过性能测试"}
      ],
      "short_term_mitigation": "1) 恢复支付网关同步模式作为降级方案 2) 增加订单提交接口的 Hystrix 熔断配置 3) 扩容 Web 容器线程池",
      "long_term_improvement": "1) 代码评审增加性能影响检查项 2) 预发环境建立 10% 流量压测要求 3) 关键路径异步化改造需提供降级方案和压测报告",
      "suggested_owner_role": "developer"
    },
    {
      "id": "d1e2f3a4-b5c6-7890-efab-723456789012",
      "category": "config_change",
      "is_primary": false,
      "confidence": "medium",
      "reasoning_chain": "v2.5.0 上线同时更新了支付网关的连接池配置，原有 200 连接降为 50，在高并发场景下加剧了连接竞争。"
    }
  ],
  "request_id": "req_abc123"
}
```

---

#### 6.4.2 确认归因结果

| 项目 | 值 |
| --- | --- |
| **接口名称** | 确认/修正/异议归因结果 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tasks/{task_id}/attribution/confirm` |
| **认证** | `project_admin` 或版本负责人 |

**请求体：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `operation` | `string` | 是 | `accept` / `revise` / `dispute` |
| `confirmed_category` | `string` | `revise` 时必填 | 确认后归因类别 |
| `revise_reason` | `string` | `revise` 时必填 | 修正理由 |
| `dispute_explanation` | `string` | `dispute` 时必填 | 异议说明 |

---

## 7. 公共能力

### 7.1 通用任务

#### 7.1.1 获取任务列表（工作台）

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取任务列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks` |
| **认证** | 用户 Token |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_type` | `string` | 否 | `assessment` / `consistency_check` / `attribution` |
| `status` | `string` | 否 | 任务状态 |
| `project_id` | `string` | 否 | 按项目过滤 |
| `created_by` | `string` | 否 | 按创建人过滤（默认当前用户） |
| `page` | `integer` | 否 | 页码 |
| `page_size` | `integer` | 否 | 每页条数 |
| `sort_by` | `string` | 否 | `created_at` / `updated_at` / `status` |

---

#### 7.1.2 获取任务详情（通用）

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取通用任务详情 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}` |
| **认证** | 项目成员 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "a7b8c9d0-e1f2-3456-abcd-123456789012",
    "tenant_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "project_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "task_type": "assessment",
    "status": "pending_review",
    "title": "用户画像看板 V1 价值评估",
    "description": null,
    "model_name": "claude-opus-4-8",
    "model_version": "20250715",
    "prompt_version": "a1b2c3d",
    "temperature": 0.3,
    "created_by": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "张三"
    },
    "confirmed_by": null,
    "completed_at": null,
    "failure_reason": null,
    "retry_count": 0,
    "created_at": "2026-07-24T14:00:00+08:00",
    "updated_at": "2026-07-24T14:01:30+08:00"
  },
  "request_id": "req_abc123"
}
```

---

#### 7.1.3 取消任务

| 项目 | 值 |
| --- | --- |
| **接口名称** | 取消任务 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tasks/{task_id}/cancel` |
| **认证** | 任务创建人或 `project_admin` |

**注意事项：**
- 仅 `draft` / `validating` / `analyzing` / `pending_review` 状态可取消
- 已完成的任务不可取消

---

#### 7.1.4 重试失败任务

| 项目 | 值 |
| --- | --- |
| **接口名称** | 重试失败任务 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tasks/{task_id}/retry` |
| **认证** | 任务创建人或 `project_admin` |

**注意事项：**
- 仅 `failed` 状态可重试
- `retry_count` 自增，`retry_of_task_id` 指向原任务
- 同一任务最多重试 3 次

---

### 7.2 快照管理

#### 7.2.1 获取任务快照

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取任务快照 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/snapshots` |
| **认证** | 项目成员 |

---

#### 7.2.2 获取快照明细

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取快照明细 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/snapshots/{snapshot_id}` |
| **认证** | 项目成员 |

**成功响应包含：**
- `snapshot_data` — 元数据
- `associated_deliverable_versions` — 交付物版本快照
- `download_url` — 完整快照文件下载链接

---

#### 7.2.3 获取任务证据链

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取任务证据 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/tasks/{task_id}/evidence` |
| **认证** | 项目成员 |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `evidence_type` | `string` | 否 | `fact` / `inference` / `missing` |
| `related_conclusion_id` | `string` | 否 | 关联结论 ID |

---

### 7.3 审计日志

#### 7.3.1 获取审计日志

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取审计日志 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/audit-logs` |
| **认证** | `tenant_admin` |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `operation` | `string` | 否 | 操作类型 |
| `object_type` | `string` | 否 | 对象类型 |
| `object_id` | `string` | 否 | 对象 ID |
| `operator_id` | `string` | 否 | 操作人 ID |
| `start_time` | `string` | 否 | 开始时间 |
| `end_time` | `string` | 否 | 结束时间 |
| `page` | `integer` | 否 | 页码 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "e2f3a4b5-c6d7-8901-fabc-823456789012",
        "operator": {"id": "a1b2c3d4", "name": "张三"},
        "operation": "task.create",
        "object_type": "task",
        "object_id": "a7b8c9d0-e1f2-3456-abcd-123456789012",
        "changes_before": null,
        "changes_after": {"status": "draft", "task_type": "assessment"},
        "source_ip": "192.168.1.100",
        "created_at": "2026-07-24T14:00:00+08:00"
      }
    ],
    "total": 1520,
    "page": 1,
    "page_size": 20
  },
  "request_id": "req_abc123"
}
```

**注意事项：**
- 审计日志只读，不可修改或删除
- 按月分区，查询跨越分区时注意性能

---

### 7.4 通知管理

#### 7.4.1 获取通知列表

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取通知列表 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/notifications` |
| **认证** | 用户 Token |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `is_read` | `boolean` | 否 | `true` / `false` |
| `notification_type` | `string` | 否 | 通知类型 |
| `page` | `integer` | 否 | 页码 |
| `page_size` | `integer` | 否 | 每页条数，最大 50 |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "f3a4b5c6-d7e8-9012-abcd-823456789012",
        "notification_type": "task_completed",
        "title": "评估任务完成",
        "content": "**用户画像看板 V1 价值评估** 已完成，建议优先级 **P1**（72.5 分）。[查看详情](/tasks/a7b8c9d0)",
        "is_read": false,
        "channel": "in_app",
        "related_task_type": "assessment",
        "related_task_id": "a7b8c9d0-e1f2-3456-abcd-123456789012",
        "created_at": "2026-07-24T14:01:30+08:00"
      }
    ],
    "unread_count": 5,
    "total": 48,
    "page": 1,
    "page_size": 20
  },
  "request_id": "req_abc123"
}
```

---

#### 7.4.2 标记已读

| 项目 | 值 |
| --- | --- |
| **接口名称** | 标记通知已读 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/notifications/{notification_id}/read` |
| **认证** | 用户 Token |

---

#### 7.4.3 全部标记已读

| 项目 | 值 |
| --- | --- |
| **接口名称** | 全部标记已读 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/notifications/read-all` |
| **认证** | 用户 Token |

---

### 7.5 导出管理

#### 7.5.1 导出任务结果

| 项目 | 值 |
| --- | --- |
| **接口名称** | 导出任务结果 |
| **请求方式** | `POST` |
| **URL** | `/api/v1/tasks/{task_id}/export` |
| **认证** | 项目成员 |

**请求体：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `export_format` | `string` | 是 | — | `markdown` / `excel` |

**成功响应 `200`：**

```json
{
  "code": 0,
  "message": "Export completed",
  "data": {
    "export_id": "a4b5c6d7-e8f9-0123-abcd-923456789012",
    "file_path": "exports/tenant_xxx/assessment/a7b8c9d0/report.md",
    "file_size_bytes": 15360,
    "download_url": "https://storage.nebula-tech.com/exports/xxx/report.md"
  },
  "request_id": "req_abc123"
}
```

---

#### 7.5.2 获取导出历史

| 项目 | 值 |
| --- | --- |
| **接口名称** | 获取导出历史 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/exports` |
| **认证** | 用户 Token |

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `task_id` | `string` | 否 | 按任务过滤 |
| `task_type` | `string` | 否 | 按任务类型过滤 |

---

#### 7.5.3 下载导出文件

| 项目 | 值 |
| --- | --- |
| **接口名称** | 下载导出文件 |
| **请求方式** | `GET` |
| **URL** | `/api/v1/exports/{export_id}/download` |
| **认证** | 用户 Token |

**响应：** `302` 重定向至 MinIO 预签名下载 URL。

**注意事项：**
- 导出文件 30 天后自动清理

---

### 7.6 WebSocket 推送

#### 7.6.1 连接

| 项目 | 值 |
| --- | --- |
| **接口名称** | WebSocket 实时推送 |
| **连接地址** | `wss://{domain}/ws?token=<access_token>` |
| **认证** | `access_token` 作为查询参数 |

**推送事件类型：**

| 事件 | 触发时机 | Payload |
| --- | --- | --- |
| `task.status_changed` | 任务状态变更 | `{task_id, old_status, new_status, timestamp}` |
| `task.completed` | 分析完成 | `{task_id, task_type, summary}` |
| `task.failed` | 任务失败 | `{task_id, task_type, failure_reason}` |
| `notification.new` | 新通知 | `{notification_id, notification_type, title}` |
| `issue.assigned` | 问题分配 | `{issue_id, title, level, check_task_id}` |
| `issue.recheck_completed` | 复检完成 | `{issue_id, result}` |
| `sync.completed` | 同步完成 | `{source_id, result, items_added, items_updated}` |

**示例推送消息：**

```json
{
  "event": "task.status_changed",
  "data": {
    "task_id": "a7b8c9d0-e1f2-3456-abcd-123456789012",
    "task_type": "assessment",
    "old_status": "analyzing",
    "new_status": "pending_review",
    "title": "用户画像看板 V1 价值评估",
    "timestamp": "2026-07-24T14:01:30+08:00"
  }
}
```

---

## 8. 附录

### 8.1 枚举值速查

#### 8.1.1 任务状态流转

```
draft → validating → analyzing → pending_review → completed
draft → cancelled
validating → failed → draft (重试)
pending_review → analyzing (修正后重新分析)
```

终态（不可再流转）：`completed`、`cancelled`

#### 8.1.2 用户角色

| 角色 | 说明 |
| --- | --- |
| `tenant_admin` | 租户管理员：管理用户、项目、规则、审计 |
| `platform_admin` | 平台管理员：管理租户、全局配置 |
| `project_admin` | 项目管理员：管理项目成员、配置、模型 |
| `project_member` | 项目成员：创建需求、发起任务、查看结果 |
| `viewer` | 只读：查看项目内数据 |

#### 8.1.3 数据源类型

| 类型 | 说明 |
| --- | --- |
| `prd_repo` | PRD 文档仓库 |
| `api_platform` | 接口平台 |
| `tracking_system` | 埋点系统 |
| `code_repo` | 代码仓库 |
| `monitoring` | 监控系统 |
| `logging` | 日志平台 |
| `ticketing` | 工单系统 |

#### 8.1.4 交付物类型

| 类型 | 说明 |
| --- | --- |
| `prd` | 产品需求文档 |
| `prototype_spec` | 原型说明 |
| `api_doc` | 接口文档 |
| `tracking_plan` | 埋点方案 |
| `test_case` | 测试用例 |

#### 8.1.5 一致性问题级别

| 级别 | 说明 | 处置要求 |
| --- | --- | --- |
| `blocker` | 阻断 | 必须修复，豁免需两方确认 |
| `critical` | 严重 | 强烈建议修复，可豁免 |
| `general` | 一般 | 建议修复 |
| `info` | 提示 | 可选处理 |

#### 8.1.6 归因类别

| 类别 | 说明 |
| --- | --- |
| `requirement_omission` | 需求遗漏 |
| `design_flaw` | 设计缺陷 |
| `implementation_error` | 实现错误 |
| `config_change` | 配置变更 |
| `data_anomaly` | 数据异常 |

#### 8.1.7 置信度

| 值 | 说明 |
| --- | --- |
| `high` | 多条事实证据支撑，无已知反例 |
| `medium` | 有证据但部分依赖推断 |
| `low` | 证据不足，以推断为主 |

### 8.2 速率限制

| 接口类别 | 限制策略 |
| --- | --- |
| 登录系列 | 同 IP 5 次/分钟；同账号 5 次/10 分钟（失败锁定） |
| 密码重置 | 同 IP 5 次/10 分钟 |
| 创建类接口 | 单用户 30 次/分钟 |
| 查询类接口 | 单用户 100 次/分钟 |
| 文件上传 | 单用户 20 次/分钟；单文件 ≤ 50MB |
| WebSocket | 单用户 1 个连接 |
| 导出 | 单用户 5 次/小时 |

### 8.3 安全注意事项

1. **凭据管理**：外部数据源凭据使用 AES-256-GCM 加密存储，接口响应中不返回明文凭据。
2. **脱敏**：手机号、身份证号、邮箱、密钥在进入 RAG 管道前脱敏处理。
3. **会话安全**：Cookie 设置 `HttpOnly; Secure; SameSite=Lax`，单用户最多 3 个并发会话。
4. **租户隔离**：每个请求根据用户 Token 自动注入租户上下文，数据库层 RLS 策略兜底。
5. **审核**：关键操作（评估确认、问题豁免、归因修改）写入审计日志，标记操作前后值。
6. **MFA**：管理角色建议强制开启 MFA，支持 TOTP 和恢复码。
7. **API 版本**：通过 URL 路径进行版本管理 `/api/v{n}`，废弃版本提前 90 天通知。

### 8.4 性能目标

| 接口类型 | P95 延迟 |
| --- | --- |
| 认证/登录 | ≤ 1s |
| 列表查询 | ≤ 2s |
| 详情查询 | ≤ 1s |
| 文件上传（50MB 以内） | ≤ 30s |
| 价值评估任务 | ≤ 60s |
| 一致性检查任务（≤ 20 文件） | ≤ 10min |
| 归因任务（≤ 72h 时间窗） | ≤ 15min |
| 导出 | ≤ 30s |

### 8.5 变更记录

| 版本 | 日期 | 变更内容 |
| --- | --- | --- |
| V1.0 | 2026-07-24 | 初始版本，基于数据库设计文档（`init.sql`）和概要设计总纲编写 |
