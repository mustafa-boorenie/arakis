# Arakis Frontend Architecture

## Overview

The Arakis frontend is a Next.js 14+ application that provides an intuitive interface for creating AI-powered systematic reviews. It features a chat-first design that transitions into a professional manuscript editor, inspired by Google Docs.

## Technology Stack

| Technology | Purpose |
|------------|---------|
| **Next.js 14+** | React framework with App Router |
| **TypeScript** | Type safety throughout the codebase |
| **Tailwind CSS** | Utility-first styling |
| **shadcn/ui** | High-quality UI components |
| **Zustand** | Lightweight state management |
| **Framer Motion** | Smooth layout animations |
| **Lexical** | Rich text editor (Meta) |

## Key Features

### 1. Chat-First Workflow Creation

The application starts with a conversational interface that guides users through:

```
Welcome → Research Question → Inclusion Criteria → Exclusion Criteria → Database Selection → Confirmation → Workflow Execution
```

Each step collects structured data while maintaining a natural conversation flow.

### 2. Seamless Layout Transition

When a workflow completes, the UI smoothly animates from:
- **Full-screen chat** → **Split-view** (sidebar + editor)

This is achieved using Framer Motion's `AnimatePresence` and layout animations.

### 3. Real-time Progress Tracking

The frontend polls the backend every 5 seconds while a workflow is running, displaying:
- Current stage (Searching → Screening → Writing → Complete)
- Papers found/screened/included statistics
- Estimated cost

### 4. Mobile-Responsive Design

- **Desktop**: Side-by-side sidebar (300-450px) and editor
- **Mobile**: Tab-based switching between Chat and Editor views
- Automatic detection via `useIsMobile()` hook (breakpoint: 768px)

## Architecture

### Directory Structure

```
frontend-next/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # Root layout with providers
│   │   ├── page.tsx            # Main page component
│   │   └── globals.css         # Global styles
│   │
│   ├── components/
│   │   ├── chat/               # Chat interface
│   │   │   ├── ChatContainer.tsx    # Main chat orchestrator
│   │   │   ├── ChatMessage.tsx      # Individual message display
│   │   │   ├── ChatInput.tsx        # User input component
│   │   │   ├── DatabaseSelector.tsx # Multi-select for databases
│   │   │   └── WorkflowProgress.tsx # Real-time progress display
│   │   │
│   │   ├── editor/             # Manuscript editor
│   │   │   ├── ManuscriptEditor.tsx # Lexical editor wrapper
│   │   │   ├── EditorToolbar.tsx    # Formatting toolbar
│   │   │   ├── FigureRenderer.tsx   # Figure display
│   │   │   └── TableRenderer.tsx    # Table display
│   │   │
│   │   ├── sidebar/            # Sidebar components
│   │   │   ├── Sidebar.tsx          # Main sidebar container
│   │   │   ├── WorkflowHistory.tsx  # Past workflows list
│   │   │   └── ExportMenu.tsx       # Export dropdown
│   │   │
│   │   ├── layout/             # Layout components
│   │   │   └── AppShell.tsx         # Main layout orchestrator
│   │   │
│   │   └── ui/                 # shadcn/ui components
│   │
│   ├── hooks/
│   │   ├── useWorkflow.ts      # Workflow CRUD operations
│   │   ├── useManuscript.ts    # Manuscript fetching
│   │   └── usePolling.ts       # Generic polling hook
│   │
│   ├── store/
│   │   └── index.ts            # Zustand store
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   └── client.ts       # API client
│   │   └── editor/
│   │       └── config.ts       # Lexical configuration
│   │
│   └── types/
│       ├── workflow.ts         # Workflow types
│       ├── manuscript.ts       # Manuscript types
│       └── chat.ts             # Chat types
```

### State Management (Zustand)

The store is organized into logical slices:

```typescript
interface AppState {
  // Layout state
  layout: {
    mode: 'chat-fullscreen' | 'split-view';
    sidebarWidth: number;
    mobileView: 'sidebar' | 'editor';
    isMobileSidebarOpen: boolean;
  };

  // Workflow state
  workflow: {
    current: WorkflowResponse | null;
    history: WorkflowResponse[];
    isCreating: boolean;
    isPolling: boolean;
  };

  // Editor state
  editor: {
    manuscript: ManuscriptResponse | null;
    activeSection: string;
    isDirty: boolean;
    isLoading: boolean;
  };

  // Chat state
  chat: {
    messages: ChatMessage[];
    stage: ChatStage;
    formData: WorkflowFormData;
  };
}
```

### Chat Flow State Machine

```
┌─────────────┐
│   welcome   │ → Initial greeting
└──────┬──────┘
       ▼
┌─────────────┐
│  question   │ → Collect research question
└──────┬──────┘
       ▼
┌─────────────┐
│  inclusion  │ → Collect inclusion criteria
└──────┬──────┘
       ▼
┌─────────────┐
│  exclusion  │ → Collect exclusion criteria
└──────┬──────┘
       ▼
┌─────────────┐
│  databases  │ → Select databases (UI selector)
└──────┬──────┘
       ▼
┌─────────────┐
│   confirm   │ → Review and confirm
└──────┬──────┘
       ▼
┌─────────────┐
│  creating   │ → Workflow in progress
└──────┬──────┘
       ▼
┌─────────────┐
│  complete   │ → Show manuscript editor
└─────────────┘
```

### Polling Architecture

The `usePolling` hook provides a reusable polling mechanism:

```typescript
const { isPolling } = usePolling<WorkflowResponse>(
  () => api.getWorkflow(workflowId),
  {
    enabled: status === 'running' || status === 'pending',
    interval: 5000,
    shouldStop: (data) => data.status === 'completed' || data.status === 'failed',
    onSuccess: (data) => updateWorkflow(data),
  }
);
```

Key features:
- Configurable polling interval
- Auto-stop on completion condition
- Cleanup on unmount
- Error handling with retry logic

### API Integration

The API client provides typed methods for all backend endpoints:

```typescript
const api = {
  // Workflows
  createWorkflow: (data: WorkflowCreateRequest) => Promise<WorkflowResponse>,
  getWorkflow: (id: string) => Promise<WorkflowResponse>,
  listWorkflows: () => Promise<{ workflows: WorkflowResponse[] }>,
  deleteWorkflow: (id: string) => Promise<void>,

  // Manuscripts
  getManuscript: (workflowId: string) => Promise<ManuscriptResponse>,
  exportManuscript: (workflowId: string, format: string) => Promise<Blob>,
};
```

### Layout Transition Flow

```
┌────────────────────────────────────┐
│         Chat Fullscreen            │
│  ┌──────────────────────────────┐  │
│  │                              │  │
│  │    Centered Chat (max 3xl)   │  │
│  │                              │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
                 │
                 │ Workflow completes
                 ▼
┌────────────────────────────────────┐
│           Split View               │
│  ┌──────────┐ ┌─────────────────┐  │
│  │          │ │                 │  │
│  │ Sidebar  │ │     Editor      │  │
│  │ (Chat +  │ │   (Manuscript)  │  │
│  │ History) │ │                 │  │
│  │          │ │                 │  │
│  └──────────┘ └─────────────────┘  │
└────────────────────────────────────┘
```

## Backend Integration

### Workflow Execution Pipeline

```
Frontend                          Backend
   │                                 │
   │ POST /api/workflows/            │
   ├────────────────────────────────►│
   │                                 │ Create workflow (status: pending)
   │◄────────────────────────────────┤
   │                                 │
   │                                 │ Background task starts:
   │                                 │ 1. Status → running
   │                                 │ 2. Generate search queries (OpenAI)
   │                                 │ 3. Search databases (PubMed, etc.)
   │                                 │ 4. Screen papers (OpenAI)
   │                                 │ 5. Generate manuscript
   │                                 │ 6. Status → completed
   │                                 │
   │ GET /api/workflows/{id}         │
   ├────────────────────────────────►│ (polling every 5s)
   │◄────────────────────────────────┤
   │                                 │
   │ GET /api/manuscripts/{id}/json  │
   ├────────────────────────────────►│ (when completed)
   │◄────────────────────────────────┤
   │                                 │
```

### Supported Databases

| Database | Status | Notes |
|----------|--------|-------|
| PubMed | ✅ Stable | NCBI biomedical literature |
| OpenAlex | ✅ Stable | Open scholarly metadata |
| Semantic Scholar | ✅ Stable | AI-powered academic search |
| Google Scholar | ❌ Disabled | Frequently blocked |
| Embase | ❌ Disabled | Requires paid API key |

### Error Handling

The backend captures and returns meaningful error messages:

```typescript
// Error types handled:
- RateLimitError → "OpenAI API rate limit exceeded"
- HTTPStatusError (429) → "Database API rate limit exceeded"
- HTTPStatusError (503) → "Database service temporarily unavailable"
- RetryError → "Search request failed after multiple retries"
```

## Development

### Running the Application

```bash
# Terminal 1: Start the backend
cd /Users/mustafaboorenie/arakis
DATABASE_URL="postgresql+asyncpg://arakis:arakis_dev_password@localhost:5432/arakis" \
uvicorn arakis.api.main:app --host 0.0.0.0 --port 8001

# Terminal 2: Start the frontend
cd frontend-next
npm run dev
```

### Environment Variables

```env
# frontend-next/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### Building for Production

```bash
cd frontend-next
npm run build
npm start
```

## Key Design Decisions

### 1. Chat-First UX
Users are guided through structured data collection via natural conversation, reducing cognitive load compared to complex forms.

### 2. Optimistic UI Updates
The UI immediately reflects user actions while background sync ensures consistency.

### 3. Polling over WebSockets
For simplicity and reliability, polling is used for status updates. WebSockets could be added for real-time updates in future.

### 4. Lexical for Rich Text
Meta's Lexical editor provides extensibility for custom nodes (figures, tables, citations) while maintaining performance.

### 5. Zustand over Redux
Lightweight state management with minimal boilerplate, perfect for medium-complexity applications.

## Future Enhancements

- [ ] Real-time collaboration via WebSockets
- [ ] Citation management and formatting
- [ ] PDF export with proper academic formatting
- [ ] User authentication and multi-user support
- [ ] Saved searches and templates
- [ ] Integration with reference managers (Zotero, Mendeley)

---

*Built with Next.js, TypeScript, and love for systematic reviews.*
