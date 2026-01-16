// Zustand store for global state management

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  WorkflowResponse,
  ManuscriptResponse,
  ChatMessage,
  ChatStage,
  WorkflowFormData,
  User,
} from '@/types';
import { DEFAULT_WORKFLOW_FORM, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '@/types';

// ============= Layout State =============

export type LayoutMode = 'landing' | 'chat-fullscreen' | 'split-view';
export type MobileView = 'sidebar' | 'editor';

interface LayoutState {
  mode: LayoutMode;
  sidebarWidth: number;
  isTransitioning: boolean;
  mobileView: MobileView;
  isMobileSidebarOpen: boolean;
  isSidebarCollapsed: boolean;
}

// ============= Workflow State =============

interface WorkflowState {
  current: WorkflowResponse | null;
  history: WorkflowResponse[];
  archived: string[]; // IDs of archived workflows
  isCreating: boolean;
  isPolling: boolean;
}

// ============= Editor State =============

interface EditorState {
  manuscript: ManuscriptResponse | null;
  activeSection: string;
  isDirty: boolean;
  isLoading: boolean;
}

// ============= Chat State =============

interface ChatState {
  messages: ChatMessage[];
  stage: ChatStage;
  formData: WorkflowFormData;
}

// ============= Auth State =============

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  showLoginDialog: boolean;
  loginDialogMessage: string | null;
}

// ============= Combined Store =============

interface AppState {
  // State slices
  layout: LayoutState;
  workflow: WorkflowState;
  editor: EditorState;
  chat: ChatState;
  auth: AuthState;

  // Layout actions
  setLayoutMode: (mode: LayoutMode) => void;
  setSidebarWidth: (width: number) => void;
  startTransition: () => void;
  endTransition: () => void;
  setMobileView: (view: MobileView) => void;
  toggleMobileSidebar: () => void;
  setMobileSidebarOpen: (open: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Workflow actions
  setCurrentWorkflow: (workflow: WorkflowResponse | null) => void;
  updateWorkflow: (workflow: WorkflowResponse) => void;
  addToHistory: (workflow: WorkflowResponse) => void;
  setHistory: (workflows: WorkflowResponse[]) => void;
  setIsCreating: (isCreating: boolean) => void;
  setIsPolling: (isPolling: boolean) => void;
  removeFromHistory: (id: string) => void;
  archiveWorkflow: (id: string) => void;
  unarchiveWorkflow: (id: string) => void;

  // Editor actions
  setManuscript: (manuscript: ManuscriptResponse | null) => void;
  setActiveSection: (section: string) => void;
  setEditorDirty: (isDirty: boolean) => void;
  setEditorLoading: (isLoading: boolean) => void;

  // Chat actions
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  setChatStage: (stage: ChatStage) => void;
  updateFormData: (data: Partial<WorkflowFormData>) => void;
  resetChat: () => void;
  clearMessages: () => void;

  // Auth actions
  setUser: (user: User | null) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setAuthLoading: (isLoading: boolean) => void;
  setAuthError: (error: string | null) => void;
  logout: () => void;
  initAuth: () => void;
  openLoginDialog: (message?: string) => void;
  closeLoginDialog: () => void;
}

// Generate unique message ID
const generateId = () => Math.random().toString(36).substring(2, 9);

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        // ============= Initial State =============
        layout: {
          mode: 'landing',
          sidebarWidth: 260,
          isTransitioning: false,
          mobileView: 'editor',
          isMobileSidebarOpen: false,
          isSidebarCollapsed: false,
        },
        workflow: {
          current: null,
          history: [],
          archived: [],
          isCreating: false,
          isPolling: false,
        },
        editor: {
          manuscript: null,
          activeSection: 'title',
          isDirty: false,
          isLoading: false,
        },
        chat: {
          messages: [],
          stage: 'welcome',
          formData: DEFAULT_WORKFLOW_FORM,
        },
        auth: {
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: true,
          error: null,
          showLoginDialog: false,
          loginDialogMessage: null,
        },

        // ============= Layout Actions =============
        setLayoutMode: (mode) =>
          set((state) => ({
            layout: { ...state.layout, mode },
          })),

        setSidebarWidth: (width) =>
          set((state) => ({
            layout: { ...state.layout, sidebarWidth: width },
          })),

        startTransition: () =>
          set((state) => ({
            layout: { ...state.layout, isTransitioning: true },
          })),

        endTransition: () =>
          set((state) => ({
            layout: { ...state.layout, isTransitioning: false },
          })),

        setMobileView: (mobileView) =>
          set((state) => ({
            layout: { ...state.layout, mobileView },
          })),

        toggleMobileSidebar: () =>
          set((state) => ({
            layout: { ...state.layout, isMobileSidebarOpen: !state.layout.isMobileSidebarOpen },
          })),

        setMobileSidebarOpen: (isMobileSidebarOpen) =>
          set((state) => ({
            layout: { ...state.layout, isMobileSidebarOpen },
          })),

        toggleSidebarCollapsed: () =>
          set((state) => ({
            layout: { ...state.layout, isSidebarCollapsed: !state.layout.isSidebarCollapsed },
          })),

        setSidebarCollapsed: (isSidebarCollapsed) =>
          set((state) => ({
            layout: { ...state.layout, isSidebarCollapsed },
          })),

        // ============= Workflow Actions =============
        setCurrentWorkflow: (workflow) =>
          set((state) => ({
            workflow: { ...state.workflow, current: workflow },
          })),

        updateWorkflow: (workflow) =>
          set((state) => ({
            workflow: {
              ...state.workflow,
              current: workflow,
              history: state.workflow.history.map((w) =>
                w.id === workflow.id ? workflow : w
              ),
            },
          })),

        addToHistory: (workflow) =>
          set((state) => {
            const exists = state.workflow.history.some((w) => w.id === workflow.id);
            if (exists) return state;
            return {
              workflow: {
                ...state.workflow,
                history: [workflow, ...state.workflow.history],
              },
            };
          }),

        setHistory: (workflows) =>
          set((state) => ({
            workflow: {
              ...state.workflow,
              history: workflows,
            },
          })),

        setIsCreating: (isCreating) =>
          set((state) => ({
            workflow: { ...state.workflow, isCreating },
          })),

        setIsPolling: (isPolling) =>
          set((state) => ({
            workflow: { ...state.workflow, isPolling },
          })),

        removeFromHistory: (id) =>
          set((state) => ({
            workflow: {
              ...state.workflow,
              history: state.workflow.history.filter((w) => w.id !== id),
              current: state.workflow.current?.id === id ? null : state.workflow.current,
            },
          })),

        archiveWorkflow: (id) =>
          set((state) => {
            const archived = state.workflow.archived || [];
            return {
              workflow: {
                ...state.workflow,
                archived: archived.includes(id) ? archived : [...archived, id],
                current: state.workflow.current?.id === id ? null : state.workflow.current,
              },
            };
          }),

        unarchiveWorkflow: (id) =>
          set((state) => {
            const archived = state.workflow.archived || [];
            return {
              workflow: {
                ...state.workflow,
                archived: archived.filter((archivedId) => archivedId !== id),
              },
            };
          }),

        // ============= Editor Actions =============
        setManuscript: (manuscript) =>
          set((state) => ({
            editor: { ...state.editor, manuscript, isLoading: false },
          })),

        setActiveSection: (section) =>
          set((state) => ({
            editor: { ...state.editor, activeSection: section },
          })),

        setEditorDirty: (isDirty) =>
          set((state) => ({
            editor: { ...state.editor, isDirty },
          })),

        setEditorLoading: (isLoading) =>
          set((state) => ({
            editor: { ...state.editor, isLoading },
          })),

        // ============= Chat Actions =============
        addMessage: (message) =>
          set((state) => ({
            chat: {
              ...state.chat,
              messages: [
                ...state.chat.messages,
                {
                  ...message,
                  id: generateId(),
                  timestamp: new Date(),
                },
              ],
            },
          })),

        setChatStage: (stage) =>
          set((state) => ({
            chat: { ...state.chat, stage },
          })),

        updateFormData: (data) =>
          set((state) => ({
            chat: {
              ...state.chat,
              formData: { ...state.chat.formData, ...data },
            },
          })),

        resetChat: () =>
          set((state) => ({
            chat: {
              messages: [],
              stage: 'welcome',
              formData: DEFAULT_WORKFLOW_FORM,
            },
            layout: {
              ...state.layout,
              mode: 'landing',
              mobileView: 'editor',
              isMobileSidebarOpen: false,
            },
            editor: {
              manuscript: null,
              activeSection: 'title',
              isDirty: false,
              isLoading: false,
            },
            workflow: {
              ...state.workflow,
              current: null,
              isCreating: false,
              isPolling: false,
            },
          })),

        clearMessages: () =>
          set((state) => ({
            chat: {
              ...state.chat,
              messages: [],
            },
          })),

        // ============= Auth Actions =============
        setUser: (user) =>
          set((state) => ({
            auth: {
              ...state.auth,
              user,
              isAuthenticated: !!user,
              isLoading: false,
            },
          })),

        setTokens: (accessToken, refreshToken) => {
          // Store tokens in localStorage
          if (typeof window !== 'undefined') {
            localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
            localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
          }
          set((state) => ({
            auth: {
              ...state.auth,
              accessToken,
              refreshToken,
            },
          }));
        },

        setAuthLoading: (isLoading) =>
          set((state) => ({
            auth: { ...state.auth, isLoading },
          })),

        setAuthError: (error) =>
          set((state) => ({
            auth: { ...state.auth, error, isLoading: false },
          })),

        logout: () => {
          // Clear tokens from localStorage
          if (typeof window !== 'undefined') {
            localStorage.removeItem(ACCESS_TOKEN_KEY);
            localStorage.removeItem(REFRESH_TOKEN_KEY);
          }
          set(() => ({
            auth: {
              user: null,
              accessToken: null,
              refreshToken: null,
              isAuthenticated: false,
              isLoading: false,
              error: null,
              showLoginDialog: false,
              loginDialogMessage: null,
            },
          }));
        },

        initAuth: () => {
          // Initialize auth from localStorage
          if (typeof window !== 'undefined') {
            const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
            const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
            if (accessToken && refreshToken) {
              set((state) => ({
                auth: {
                  ...state.auth,
                  accessToken,
                  refreshToken,
                  isLoading: true, // Will fetch user profile
                },
              }));
            } else {
              set((state) => ({
                auth: {
                  ...state.auth,
                  isLoading: false,
                },
              }));
            }
          }
        },

        openLoginDialog: (message) =>
          set((state) => ({
            auth: {
              ...state.auth,
              showLoginDialog: true,
              loginDialogMessage: message || null,
            },
          })),

        closeLoginDialog: () =>
          set((state) => ({
            auth: {
              ...state.auth,
              showLoginDialog: false,
              loginDialogMessage: null,
            },
          })),
      }),
      {
        name: 'arakis-storage',
        partialize: (state) => ({
          // Persist workflow history and archived IDs
          workflow: {
            history: state.workflow.history,
            archived: state.workflow.archived,
          },
        }),
      }
    )
  )
);
