import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useLayoutEffect,
  useCallback,
  ReactNode,
} from "react";
import { useQueryClient } from "react-query";
import { projectsApi, setActiveProjectIdForApi } from "../services/api";
import { WorkspaceProject } from "../types";
import {
  getActiveProjectId,
  setActiveProjectId,
  setActiveProjectIdForStorage,
} from "../utils/localStorage";

interface ProjectContextType {
  projects: WorkspaceProject[];
  activeProject: WorkspaceProject | null;
  activeProjectId: string | null;
  isLoading: boolean;
  switchProject: (projectId: string) => void;
  createProject: (name: string) => Promise<WorkspaceProject>;
  refreshProjects: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const useProject = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error("useProject must be used within a ProjectProvider");
  }
  return context;
};

interface ProjectProviderProps {
  children: ReactNode;
}

export const ProjectProvider: React.FC<ProjectProviderProps> = ({ children }) => {
  const queryClient = useQueryClient();
  const [projects, setProjects] = useState<WorkspaceProject[]>([]);
  const [activeProjectId, setActiveProjectIdState] = useState<string | null>(
    () => getActiveProjectId()
  );
  const [isLoading, setIsLoading] = useState(true);

  useLayoutEffect(() => {
    const storedId = getActiveProjectId();
    if (storedId) {
      setActiveProjectIdForApi(storedId);
    }
  }, []);

  const applyActiveProject = useCallback((projectId: string | null) => {
    setActiveProjectIdState(projectId);
    setActiveProjectIdForApi(projectId);
    setActiveProjectIdForStorage(projectId);
    if (projectId) {
      setActiveProjectId(projectId);
    }
  }, []);

  const refreshProjects = useCallback(async () => {
    const list = await projectsApi.list();
    if (!Array.isArray(list)) {
      throw new Error("Invalid projects response");
    }
    setProjects(list);

    if (list.length === 0) {
      applyActiveProject(null);
      return;
    }

    const storedId = getActiveProjectId();
    const validStored = storedId && list.some((p) => p.id === storedId);
    const nextId = validStored ? storedId! : list[0].id;
    applyActiveProject(nextId);
  }, [applyActiveProject]);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    refreshProjects()
      .catch((error) => {
        console.error("Failed to load projects:", error);
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
    };
    // Load project list once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const switchProject = useCallback(
    (projectId: string) => {
      if (!projects.some((p) => p.id === projectId)) {
        return;
      }
      applyActiveProject(projectId);
      queryClient.clear();
    },
    [projects, applyActiveProject, queryClient]
  );

  const createProject = useCallback(
    async (name: string) => {
      const project = await projectsApi.create({ name });
      await refreshProjects();
      applyActiveProject(project.id);
      queryClient.clear();
      return project;
    },
    [refreshProjects, applyActiveProject, queryClient]
  );

  const activeProject =
    projects.find((p) => p.id === activeProjectId) ?? null;

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        activeProjectId,
        isLoading,
        switchProject,
        createProject,
        refreshProjects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
};
