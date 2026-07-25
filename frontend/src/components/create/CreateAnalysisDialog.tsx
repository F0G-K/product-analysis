import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { createAnalysisTask } from '@/services/tasks';
import { useProjectStore } from '@/stores/projectStore';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { toast } from '@/components/ui/Toast';
import { getRequestErrorMessage } from '@/utils/errorHandler';
import type { TaskType } from '@/types/task';

interface CreateAnalysisDialogProps {
  open: boolean;
  onClose: () => void;
  initialTaskType?: TaskType;
  initialProjectId?: string;
  allowTaskTypeChange?: boolean;
}

const taskOptions: { value: TaskType; label: string }[] = [
  { value: 'assessment', label: '需求价值评估' },
  { value: 'consistency_check', label: '交付物一致性检查' },
  { value: 'attribution', label: '上线问题归因' },
];

const defaults: Record<TaskType, { title: string; query: string; materialLabel: string; placeholder: string }> = {
  assessment: {
    title: '新建需求价值评估',
    query: '请评估该需求的用户覆盖、业务价值、战略契合度、实现成本和风险。',
    materialLabel: '需求材料',
    placeholder: '填写需求背景、目标用户、核心场景、预期收益和交付成本等信息。',
  },
  consistency_check: {
    title: '新建交付物一致性检查',
    query: '请检查需求、原型、接口、埋点和测试材料之间的不一致。',
    materialLabel: '待检查材料',
    placeholder: '粘贴或概述需求、原型、接口和测试用例的关键内容。',
  },
  attribution: {
    title: '新建上线问题归因',
    query: '请基于异常现象、时间线和变更信息分析最可能的根因。',
    materialLabel: '异常与时间线',
    placeholder: '填写异常现象、影响范围、发生时间、关联发布、告警和已采取的处置。',
  },
};

export function CreateAnalysisDialog({
  open,
  onClose,
  initialTaskType = 'assessment',
  initialProjectId,
  allowTaskTypeChange = false,
}: CreateAnalysisDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useProjectStore((state) => state.projects);
  const currentProjectId = useProjectStore((state) => state.currentProjectId);
  const [taskType, setTaskType] = useState<TaskType>(initialTaskType);
  const [projectId, setProjectId] = useState('');
  const [title, setTitle] = useState('');
  const [query, setQuery] = useState('');
  const [material, setMaterial] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const config = useMemo(() => defaults[taskType], [taskType]);

  useEffect(() => {
    if (!open) return;
    const nextType = initialTaskType;
    setTaskType(nextType);
    setProjectId(initialProjectId || currentProjectId || projects[0]?.id || '');
    setTitle(defaults[nextType].title);
    setQuery(defaults[nextType].query);
    setMaterial('');
    setErrors({});
  }, [currentProjectId, initialProjectId, initialTaskType, open, projects]);

  useEffect(() => {
    if (!open) return;
    setTitle(defaults[taskType].title);
    setQuery(defaults[taskType].query);
  }, [open, taskType]);

  const mutation = useMutation({
    mutationFn: () => createAnalysisTask(projectId, {
      task_type: taskType,
      title: title.trim(),
      description: material.trim().slice(0, 500),
      query: query.trim(),
      input_data: { content: material.trim() },
    }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('分析任务已创建为草稿');
      onClose();
      const route = taskType === 'assessment'
        ? 'assessment'
        : taskType === 'consistency_check' ? 'consistency' : 'attribution';
      navigate(`/${route}/${response.data.id}`);
    },
    onError: (error) => toast.error(getRequestErrorMessage(error, '任务创建失败')),
  });

  const submit = () => {
    const nextErrors: Record<string, string> = {};
    if (!projectId) nextErrors.projectId = '请选择项目';
    if (!title.trim()) nextErrors.title = '请输入任务标题';
    if (!material.trim()) nextErrors.material = `请填写${config.materialLabel}`;
    if (!query.trim()) nextErrors.query = '请输入分析目标';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length === 0) mutation.mutate();
  };

  return (
    <Modal
      open={open}
      onClose={mutation.isPending ? () => undefined : onClose}
      title="新建分析"
      description="先创建草稿，确认输入后再开始 AI 分析"
      size="lg"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>取消</Button>
          <Button onClick={submit} loading={mutation.isPending}>创建草稿</Button>
        </>
      )}
    >
      <div className="space-y-4">
        {allowTaskTypeChange && (
          <Select
            label="分析类型"
            value={taskType}
            onChange={(value) => setTaskType(value as TaskType)}
            options={taskOptions}
            fullWidth
          />
        )}
        <Select
          label="所属项目"
          value={projectId}
          onChange={setProjectId}
          options={projects.map((project) => ({ value: project.id, label: project.name }))}
          error={errors.projectId}
          placeholder={projects.length || initialProjectId ? '请选择项目' : '请先创建项目'}
          disabled={Boolean(initialProjectId) || projects.length === 0}
          fullWidth
        />
        {projects.length === 0 && !initialProjectId && (
          <p className="text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
            当前没有可用项目，请先到“项目与数据源”创建项目。
          </p>
        )}
        <Input
          label="任务标题"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          error={errors.title}
          maxLength={256}
        />
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700" htmlFor="analysis-material">{config.materialLabel}</label>
          <textarea
            id="analysis-material"
            value={material}
            onChange={(event) => setMaterial(event.target.value)}
            rows={7}
            className={`rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 ${errors.material ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200 focus:border-primary-500'}`}
            placeholder={config.placeholder}
          />
          {errors.material && <p className="text-xs text-red-600">{errors.material}</p>}
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700" htmlFor="analysis-query">分析目标</label>
          <textarea
            id="analysis-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={3}
            className={`rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 ${errors.query ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-primary-200 focus:border-primary-500'}`}
          />
          {errors.query && <p className="text-xs text-red-600">{errors.query}</p>}
        </div>
      </div>
    </Modal>
  );
}
