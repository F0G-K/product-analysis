import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { createProject } from '@/services/projects';
import { useProjectStore } from '@/stores/projectStore';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { toast } from '@/components/ui/Toast';
import { getRequestErrorMessage } from '@/utils/errorHandler';

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
}

export function CreateProjectDialog({ open, onClose }: CreateProjectDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fetchProjects = useProjectStore((state) => state.fetchProjects);
  const setCurrentProject = useProjectStore((state) => state.setCurrentProject);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [timezone, setTimezone] = useState('Asia/Shanghai');
  const [nameError, setNameError] = useState('');

  useEffect(() => {
    if (!open) return;
    setName('');
    setDescription('');
    setTimezone('Asia/Shanghai');
    setNameError('');
  }, [open]);

  const mutation = useMutation({
    mutationFn: () => createProject({ name: name.trim(), description: description.trim() || undefined, timezone }),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
      await fetchProjects();
      setCurrentProject(response.data.id);
      toast.success('项目创建成功');
      onClose();
      navigate(`/projects/${response.data.id}`);
    },
    onError: (error) => toast.error(getRequestErrorMessage(error, '项目创建失败')),
  });

  const submit = () => {
    if (!name.trim()) {
      setNameError('请输入项目名称');
      return;
    }
    setNameError('');
    mutation.mutate();
  };

  return (
    <Modal
      open={open}
      onClose={mutation.isPending ? () => undefined : onClose}
      title="新建项目"
      description="创建后你将成为该项目的项目管理员"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>取消</Button>
          <Button onClick={submit} loading={mutation.isPending}>创建项目</Button>
        </>
      )}
    >
      <div className="space-y-4">
        <Input
          label="项目名称"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={nameError}
          maxLength={128}
          placeholder="例如：智慧零售平台"
          autoFocus
        />
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-gray-700" htmlFor="project-description">项目描述</label>
          <textarea
            id="project-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-500"
            placeholder="简要说明项目背景和目标"
          />
        </div>
        <Select
          label="项目时区"
          value={timezone}
          onChange={setTimezone}
          options={[
            { value: 'Asia/Shanghai', label: 'Asia/Shanghai (UTC+8)' },
            { value: 'UTC', label: 'UTC' },
            { value: 'Asia/Tokyo', label: 'Asia/Tokyo (UTC+9)' },
          ]}
          fullWidth
        />
      </div>
    </Modal>
  );
}
