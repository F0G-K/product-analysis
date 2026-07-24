import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getUsers } from '@/services/auth';
import { listAuditLogs } from '@/services/audit';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';
import { Table, type TableColumn } from '@/components/ui/Table';
import { formatDate } from '@/utils/format';
import type { User } from '@/types/user';
import type { AuditLog } from '@/types/common';

const userColumns: TableColumn<User>[] = [
  { key: 'name', title: '名称', dataIndex: 'name', render: (v, r) => (
    <div>
      <div className="text-sm font-medium text-gray-800">{String(v ?? r.name ?? '-')}</div>
      <div className="text-xs text-gray-400">{r.email}</div>
    </div>
  )},
  { key: 'role', title: '角色', dataIndex: 'role', render: (v) => (
    <Badge variant="indigo">{String(v ?? '-')}</Badge>
  )},
  { key: 'mfa', title: 'MFA', dataIndex: 'mfa_enabled', align: 'center', render: (v) => (
    <Badge variant={v ? 'green' : 'gray'}>{v ? '已启用' : '未启用'}</Badge>
  )},
  { key: 'time', title: '加入时间', render: (_, r) => (
    <span className="text-xs text-gray-400">{formatDate(r.last_login_at ?? '')}</span>
  )},
];

const auditColumns: TableColumn<AuditLog>[] = [
  { key: 'operation', title: '操作', dataIndex: 'operation', render: (v) => (
    <Badge variant="gray">{String(v ?? '-')}</Badge>
  )},
  { key: 'user', title: '操作人', dataIndex: 'user_name' },
  { key: 'object', title: '对象', dataIndex: 'object_type' },
  { key: 'result', title: '结果', dataIndex: 'result', render: (v) => (
    <Badge variant={v === 'success' ? 'green' : 'red'}>{String(v ?? '-')}</Badge>
  )},
  { key: 'time', title: '时间', render: (_, r) => (
    <span className="text-xs text-gray-400">{formatDate(r.created_at)}</span>
  )},
];

export function AdminPage() {
  const [tab, setTab] = useState('users');

  const { data: usersRes, isLoading: usersLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => getUsers({ page_size: 50 }),
    enabled: tab === 'users',
  });

  const { data: auditRes, isLoading: auditLoading } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => listAuditLogs({ page_size: 50 }),
    enabled: tab === 'audit',
  });

  const users = (usersRes?.data as { items: User[] })?.items ?? [];
  const auditLogs = (auditRes?.data as { items: AuditLog[] })?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-gray-800">系统管理</h1>
        <p className="text-xs text-gray-400 mt-0.5">用户管理 · 审计日志 · 系统配置</p>
      </div>

      <Tabs
        tabs={[
          { key: 'users', label: '用户管理', count: users.length },
          { key: 'audit', label: '审计日志' },
        ]}
        activeKey={tab}
        onChange={setTab}
      />

      {tab === 'users' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button variant="primary">+ 邀请成员</Button>
          </div>
          <Table columns={userColumns} data={users} loading={usersLoading} rowKey="id" />
        </div>
      )}

      {tab === 'audit' && (
        <Table columns={auditColumns} data={auditLogs} loading={auditLoading} rowKey="id" />
      )}
    </div>
  );
}
