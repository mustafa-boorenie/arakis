# Arakis Frontend - Simple Demo

A lightweight single-page application for testing the Arakis API during alpha development.

## Features

✅ **Create Systematic Reviews**
- Research question input
- Inclusion/exclusion criteria
- Database selection
- Max results configuration

✅ **View Workflow Status**
- List all workflows
- Real-time status updates (auto-refresh every 10s)
- Workflow metadata (papers found, included, cost)

✅ **Manuscript Preview**
- View generated manuscript sections
- Basic markdown rendering

✅ **Export Functionality**
- Download as JSON
- Download as Markdown
- Download as PDF
- Download as Word (DOCX)

## Quick Start

### Option 1: Serve with Python (Simplest)

```bash
cd frontend
python -m http.server 3000
```

Open http://localhost:3000

### Option 2: Serve with Node.js

```bash
cd frontend
npx serve -p 3000
```

### Option 3: Add to FastAPI (Recommended for Production)

Update `src/arakis/api/main.py`:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

Then access at http://localhost:8000/

## Configuration

Edit `index.html` line 309 to change API URL:

```javascript
const API_BASE_URL = 'http://localhost:8000';  // Your API URL
```

For production:
```javascript
const API_BASE_URL = 'https://api.your-domain.com';
```

## API Endpoints Used

The frontend calls these API endpoints:

- `POST /api/workflows` - Create workflow
- `GET /api/workflows` - List workflows
- `GET /api/workflows/{id}` - Get workflow details
- `GET /api/manuscripts/{id}/json` - Get manuscript JSON
- `GET /api/manuscripts/{id}/markdown` - Export markdown
- `GET /api/manuscripts/{id}/pdf` - Export PDF
- `GET /api/manuscripts/{id}/docx` - Export Word

## Screenshot

```
┌─────────────────────────────────────────┐
│ 🔬 Arakis                               │
│ AI-Powered Systematic Review Automation │
└─────────────────────────────────────────┘

┌──────────────┬──────────────┐
│ Create Review │ My Reviews  │
└──────────────┴──────────────┘

┌─────────────────────────────────────────┐
│ Create New Systematic Review            │
│                                         │
│ Research Question *                     │
│ [________________________________]      │
│                                         │
│ Inclusion Criteria *                    │
│ [________________________________]      │
│                                         │
│ [ Start Systematic Review ]             │
└─────────────────────────────────────────┘
```

## Tech Stack

- **Zero dependencies** - Pure HTML/CSS/JavaScript
- **Fetch API** - For API calls
- **Responsive design** - Works on mobile/tablet/desktop
- **Auto-refresh** - Updates workflow list every 10 seconds

## Next Steps (For Production Frontend)

This is a **demo/alpha testing UI**. For production, consider:

1. **React/Next.js** - Better state management, routing
2. **Authentication** - User login/signup
3. **Rich text editor** - Edit manuscript sections
4. **Advanced visualizations** - PRISMA diagram viewer, forest plots
5. **Real-time updates** - WebSocket for workflow progress
6. **Collaborative editing** - Multiple users on same review

## Development Tips

**Enable CORS** in FastAPI for local development:

```python
# src/arakis/api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Test without backend:**

Use mock data by replacing API calls:

```javascript
// Mock for testing UI
async function loadWorkflows() {
    const mockData = [
        {
            id: "123",
            research_question: "Test question",
            status: "completed",
            papers_found: 50,
            papers_included: 10,
            total_cost: 2.50
        }
    ];
    // ... render mockData
}
```

## Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## License

Same as Arakis main project.
