import type { Project } from '@/types/common';
import { create } from 'zustand';
import { listProjects } from '@/services/projects';
import { toast } from '@/components/ui/Toast';
import { getRequestErrorMessage } from '@/utils/errorHandler';

interface ProjectState {
  projects: Project[];
  currentProjectId: string | null;

  setProjects: (projects: Project[]) => void;
  setCurrentProject: (id: string) => void;
  clearProject: () => void;
  fetchProjects: () => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  currentProjectId: null,

  setProjects: (projects) => set({ projects }),

  setCurrentProject: (id) => set({ currentProjectId: id }),

  clearProject: () => set({ currentProjectId: null }),

  fetchProjects: async () => {
    try {
      const res = await listProjects({ page_size: 100 });
      set({ projects: res.data.items });
    } catch (error) {
      toast.error(getRequestErrorMessage(error, '项目列表加载失败'));
    }
  },
}));
