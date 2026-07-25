import { useMutation, useQueryClient } from '@tanstack/react-query';
import { dispatchTask } from '@/services/tasks';
import { Button } from '@/components/ui/Button';
import { toast } from '@/components/ui/Toast';
import { getRequestErrorMessage } from '@/utils/errorHandler';

interface TaskDispatchButtonProps {
  taskId: string;
}

export function TaskDispatchButton({ taskId }: TaskDispatchButtonProps) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => dispatchTask(taskId),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      toast.success('任务已提交分析');
    },
    onError: (error) => toast.error(getRequestErrorMessage(error, '任务提交失败')),
  });

  return (
    <Button onClick={() => mutation.mutate()} loading={mutation.isPending}>
      开始分析
    </Button>
  );
}
