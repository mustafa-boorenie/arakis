# Arakis Frontend

Modern Next.js frontend for the Arakis AI-powered systematic review assistant.

## Features

- **Chat-based Workflow Creation** - Conversational interface for setting up systematic reviews
- **Smooth Layout Transition** - Animated transition from full-screen chat to split-view editor
- **Lexical Rich Text Editor** - Google Docs-like manuscript editing with academic styling
- **Real-time Progress Tracking** - Live updates during workflow execution
- **Multi-format Export** - Download manuscripts as JSON, Markdown, PDF, or DOCX
- **Workflow History** - Access and manage previous systematic reviews

## Tech Stack

- **Framework**: Next.js 14+ with TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **Editor**: Lexical (Meta) for rich text editing
- **State Management**: Zustand
- **Animations**: Framer Motion

## Getting Started

### Prerequisites

- Node.js 18+
- Arakis backend running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Environment Variables

Create a `.env.local` file (already created with defaults):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
src/
├── app/                    # Next.js app router
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Main page
│   └── globals.css        # Global styles
├── components/
│   ├── ui/                # shadcn/ui components
│   ├── chat/              # Chat interface
│   │   ├── ChatContainer.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   ├── DatabaseSelector.tsx
│   │   └── WorkflowProgress.tsx
│   ├── editor/            # Lexical editor
│   │   ├── ManuscriptEditor.tsx
│   │   ├── EditorToolbar.tsx
│   │   ├── FigureRenderer.tsx
│   │   └── TableRenderer.tsx
│   ├── sidebar/           # Sidebar components
│   │   ├── Sidebar.tsx
│   │   ├── WorkflowHistory.tsx
│   │   └── ExportMenu.tsx
│   └── layout/            # Layout components
│       └── AppShell.tsx
├── lib/
│   ├── api/               # API client
│   │   └── client.ts
│   └── editor/            # Lexical configuration
│       └── config.ts
├── hooks/                 # Custom React hooks
│   ├── usePolling.ts
│   ├── useWorkflow.ts
│   └── useManuscript.ts
├── store/                 # Zustand store
│   └── index.ts
└── types/                 # TypeScript types
    ├── workflow.ts
    ├── manuscript.ts
    └── chat.ts
```

## User Flow

1. **Chat Interface** - User answers questions to configure the review:
   - Research question
   - Inclusion criteria
   - Exclusion criteria
   - Database selection

2. **Workflow Creation** - Click "Start Review" to begin processing

3. **Progress Tracking** - Watch real-time updates as papers are searched, screened, and analyzed

4. **Editor View** - When complete, the UI transitions to show:
   - Sidebar with chat history and workflow list
   - Main editor with the generated manuscript

5. **Export** - Download the manuscript in your preferred format

## Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

## API Endpoints Used

- `POST /api/workflows/` - Create new workflow
- `GET /api/workflows/` - List workflows
- `GET /api/workflows/{id}` - Get workflow status
- `DELETE /api/workflows/{id}` - Delete workflow
- `GET /api/manuscripts/{id}/json` - Get manuscript JSON
- `GET /api/manuscripts/{id}/markdown` - Export as Markdown
- `GET /api/manuscripts/{id}/pdf` - Export as PDF
- `GET /api/manuscripts/{id}/docx` - Export as Word document
