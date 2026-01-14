// Zustand store for global state management

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type {
  WorkflowResponse,
  ManuscriptResponse,
  ChatMessage,
  ChatStage,
  WorkflowFormData,
} from '@/types';
import { DEFAULT_WORKFLOW_FORM } from '@/types';

// ============= Layout State =============

export type LayoutMode = 'chat-fullscreen' | 'split-view';
export type MobileView = 'sidebar' | 'editor';

interface LayoutState {
  mode: LayoutMode;
  sidebarWidth: number;
  isTransitioning: boolean;
  mobileView: MobileView;
  isMobileSidebarOpen: boolean;
}

// ============= Workflow State =============

interface WorkflowState {
  current: WorkflowResponse | null;
  history: WorkflowResponse[];
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

// ============= Combined Store =============

interface AppState {
  // State slices
  layout: LayoutState;
  workflow: WorkflowState;
  editor: EditorState;
  chat: ChatState;

  // Layout actions
  setLayoutMode: (mode: LayoutMode) => void;
  setSidebarWidth: (width: number) => void;
  startTransition: () => void;
  endTransition: () => void;
  setMobileView: (view: MobileView) => void;
  toggleMobileSidebar: () => void;
  setMobileSidebarOpen: (open: boolean) => void;

  // Workflow actions
  setCurrentWorkflow: (workflow: WorkflowResponse | null) => void;
  updateWorkflow: (workflow: WorkflowResponse) => void;
  addToHistory: (workflow: WorkflowResponse) => void;
  setIsCreating: (isCreating: boolean) => void;
  setIsPolling: (isPolling: boolean) => void;
  removeFromHistory: (id: string) => void;

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
}

// Generate unique message ID
const generateId = () => Math.random().toString(36).substring(2, 9);

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        // ============= Initial State =============
        layout: {
          mode: 'chat-fullscreen',
          sidebarWidth: 380,
          isTransitioning: false,
          mobileView: 'editor',
          isMobileSidebarOpen: false,
        },
        workflow: {
          current: null,
          history: [],
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
              mode: 'chat-fullscreen',
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
      }),
      {
        name: 'arakis-storage',
        partialize: (state) => ({
          // Only persist workflow history
          workflow: { history: state.workflow.history },
        }),
      }
    )
  )
);
