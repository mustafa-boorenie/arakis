# Product Requirements Document: Unified Workflow System

## Overview

Refactor the Arakis workflow system to support 12 comprehensive stages with full state persistence, R2 figure uploads, and stage re-run capabilities.

---

## Requirements Summary

| Requirement | Implementation |
|-------------|----------------|
| **12 stages** | Search → Screen → PDF Fetch → Extract → RoB → Analysis → PRISMA → Tables → Intro → Methods → Results → Discussion |
| **No screening limit** | Remove `max_screen = 50` limit - process ALL papers |
| **PDF extraction** | Enable by default (`extract_text=True`) |
| **All sections** | Abstract, Introduction, Methods, Results, Discussion, Conclusions |
| **Full meta-analysis** | Forest plot, funnel plot, I², τ², Q-stat, subgroups |
| **Risk of Bias** | Auto-detect RoB 2/ROBINS-I/QUADAS-2 based on study design |
| **State saving** | Database checkpoints per stage, resume from any point |
| **Figure storage** | Upload to Cloudflare R2, return URLs |
| **3 tables** | Study Characteristics, Risk of Bias, GRADE Summary of Findings |
| **Retry logic** | 3 retries with exponential backoff, then prompt user |
| **Re-runs** | Any stage can be re-run independently |
| **Progress** | Polling endpoint (WebSocket later) |
| **Output** | Markdown + JSON |

---

## Database Schema Changes

### New Table: `workflow_stage_checkpoints`

```python
class WorkflowStageCheckpoint(Base):
    __tablename__ = "workflow_stage_checkpoints"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String(50), nullable=False)  # search, screen, pdf_fetch, etc.
    status = Column(String(20), default="pending")  # pending, in_progress, completed, failed, skipped
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    retry_count = Column(Integer, default=0)
    output_data = Column(JSON)  # Stage-specific output
    error_message = Column(Text)
    cost = Column(Float, default=0.0)

    __table_args__ = (UniqueConstraint('workflow_id', 'stage'),)
```

### New Table: `workflow_figures`

```python
class WorkflowFigure(Base):
    __tablename__ = "workflow_figures"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"))
    figure_type = Column(String(50))  # forest_plot, funnel_plot, prisma, rob_summary
    title = Column(String(255))
    caption = Column(Text)
    r2_key = Column(String(500))
    r2_url = Column(String(1000))
    file_size_bytes = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=utc_now)
```

### New Table: `workflow_tables`

```python
class WorkflowTable(Base):
    __tablename__ = "workflow_tables"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"))
    table_type = Column(String(50))  # study_characteristics, risk_of_bias, grade_sof
    title = Column(String(255))
    caption = Column(Text)
    headers = Column(JSON)
    rows = Column(JSON)
    footnotes = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utc_now)
```

### Modify `workflows` Table

Add columns:
```python
needs_user_action = Column(Boolean, default=False)
action_required = Column(Text)  # What action user needs to take
meta_analysis_feasible = Column(Boolean)
```

---

## Backend Architecture

### New Module Structure

```
src/arakis/workflow/
├── __init__.py
├── orchestrator.py          # WorkflowOrchestrator class
└── stages/
    ├── __init__.py
    ├── base.py              # BaseStageExecutor abstract class
    ├── search.py            # SearchStageExecutor
    ├── screen.py            # ScreenStageExecutor (NO 50-paper LIMIT)
    ├── pdf_fetch.py         # PDFFetchStageExecutor (extract_text=True)
    ├── extract.py           # ExtractStageExecutor (use_full_text=True)
    ├── rob.py               # RiskOfBiasStageExecutor (NEW)
    ├── analysis.py          # AnalysisStageExecutor (full meta-analysis + R2)
    ├── prisma.py            # PRISMAStageExecutor
    ├── tables.py            # TablesStageExecutor (3 tables)
    ├── introduction.py      # IntroductionStageExecutor
    ├── methods.py           # MethodsStageExecutor (NEW)
    ├── results.py           # ResultsStageExecutor
    └── discussion.py        # DiscussionStageExecutor
```

### BaseStageExecutor Pattern

```python
@dataclass
class StageResult:
    success: bool
    output_data: dict[str, Any]
    cost: float
    error: Optional[str] = None
    needs_user_action: bool = False
    action_required: Optional[str] = None

class BaseStageExecutor(ABC):
    MAX_RETRIES = 3

    @abstractmethod
    async def execute(self, input_data: dict) -> StageResult:
        pass

    @abstractmethod
    def get_required_stages(self) -> list[str]:
        pass

    async def run_with_retry(self, input_data: dict) -> StageResult:
        for attempt in range(self.MAX_RETRIES):
            result = await self.execute(input_data)
            if result.success or not self._is_retryable(result.error):
                return result
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        return StageResult(
            success=False,
            needs_user_action=True,
            action_required="Stage failed after 3 attempts. Please review."
        )
```

### WorkflowOrchestrator

```python
class WorkflowOrchestrator:
    STAGE_ORDER = [
        "search", "screen", "pdf_fetch", "extract", "rob",
        "analysis", "prisma", "tables", "introduction",
        "methods", "results", "discussion"
    ]

    STAGE_EXECUTORS = {
        "search": SearchStageExecutor,
        "screen": ScreenStageExecutor,
        "pdf_fetch": PDFFetchStageExecutor,
        "extract": ExtractStageExecutor,
        "rob": RiskOfBiasStageExecutor,
        "analysis": AnalysisStageExecutor,
        "prisma": PRISMAStageExecutor,
        "tables": TablesStageExecutor,
        "introduction": IntroductionStageExecutor,
        "methods": MethodsStageExecutor,
        "results": ResultsStageExecutor,
        "discussion": DiscussionStageExecutor,
    }

    async def execute_workflow(self, workflow_id: str, start_from: str = None):
        """Execute workflow stages with checkpointing."""
        pass

    async def rerun_stage(self, workflow_id: str, stage: str):
        """Re-run a specific stage independently."""
        pass
```

---

## Key Code Changes

### 1. Remove 50-Paper Screening Limit

**File:** `src/arakis/api/routers/workflows.py` (Line 396)

```python
# REMOVE THIS LINE:
max_screen = min(len(search_results.papers), 50)  # Limit for cost control

# REPLACE WITH:
# Process ALL papers - no artificial limit
for paper in search_results.papers:
    decision = await screener.screen_paper(paper, criteria, dual_review)
```

### 2. Enable PDF Text Extraction

**File:** `src/arakis/api/routers/workflows.py` (Line 545)

```python
# CHANGE FROM:
use_full_text=False,  # Use abstracts for API workflow

# CHANGE TO:
use_full_text=True,  # Use full text from PDFs
```

### 3. Add R2 Figure Upload

**File:** `src/arakis/workflow/stages/analysis.py`

```python
async def _upload_to_r2(self, local_path: str, figure_type: str) -> str:
    """Upload figure to R2 and return URL."""
    with open(local_path, "rb") as f:
        content = f.read()

    key = f"workflows/{self.workflow_id}/figures/{figure_type}.png"
    result = self.storage_client.upload_bytes(
        data=content,
        key=key,
        content_type="image/png",
    )

    # Save figure record to database
    await self._save_figure_record(figure_type, key, result.url)
    return result.url
```

---

## API Endpoint Changes

### File: `src/arakis/api/routers/workflows.py`

**Refactor `execute_workflow()`** to use orchestrator:
```python
async def execute_workflow(workflow_id: str, workflow_data: WorkflowCreate):
    orchestrator = WorkflowOrchestrator()
    await orchestrator.execute_workflow(workflow_id)
```

**New Endpoints:**

```python
@router.post("/{workflow_id}/stages/{stage}/rerun")
async def rerun_stage(workflow_id: str, stage: str):
    """Re-run a specific stage."""

@router.post("/{workflow_id}/resume")
async def resume_workflow(workflow_id: str):
    """Resume workflow after user action."""

@router.get("/{workflow_id}/stages")
async def get_stage_checkpoints(workflow_id: str):
    """Get all stage checkpoints."""
```

### File: `src/arakis/api/schemas/workflow.py`

**Enhanced Response:**
```python
class StageCheckpoint(BaseModel):
    stage: str
    status: str  # pending, in_progress, completed, failed, skipped
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int = 0
    error_message: Optional[str]
    cost: float = 0.0

class WorkflowResponse(BaseModel):
    # Existing fields...
    stages: list[StageCheckpoint] = []
    needs_user_action: bool = False
    action_required: Optional[str]
    forest_plot_url: Optional[str]
    funnel_plot_url: Optional[str]
    prisma_url: Optional[str]
```

---

## Frontend Changes

### File: `frontend-next/src/types/workflow.ts`

```typescript
export type WorkflowStage =
  | 'search' | 'screen' | 'pdf_fetch' | 'extract' | 'rob'
  | 'analysis' | 'prisma' | 'tables' | 'introduction'
  | 'methods' | 'results' | 'discussion' | 'completed';

export interface StageCheckpoint {
  stage: WorkflowStage;
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
  error_message: string | null;
  cost: number;
}

export interface WorkflowResponse {
  // ... existing fields
  stages: StageCheckpoint[];
  needs_user_action: boolean;
  action_required: string | null;
  forest_plot_url: string | null;
  funnel_plot_url: string | null;
  prisma_url: string | null;
}
```

### File: `frontend-next/src/components/workflow/WorkflowDetailView.tsx`

Update STAGES constant to 12 stages:
```typescript
const STAGES = [
  { key: 'search', label: 'Searching databases', icon: Search },
  { key: 'screen', label: 'Screening papers', icon: FileText },
  { key: 'pdf_fetch', label: 'Fetching PDFs', icon: Download },
  { key: 'extract', label: 'Extracting data', icon: ClipboardList },
  { key: 'rob', label: 'Risk of Bias', icon: Shield },
  { key: 'analysis', label: 'Meta-analysis', icon: BarChart3 },
  { key: 'prisma', label: 'PRISMA diagram', icon: GitBranch },
  { key: 'tables', label: 'Generating tables', icon: Table },
  { key: 'introduction', label: 'Writing introduction', icon: BookOpen },
  { key: 'methods', label: 'Writing methods', icon: FileCode },
  { key: 'results', label: 'Writing results', icon: FileBarChart },
  { key: 'discussion', label: 'Writing discussion', icon: MessageSquare },
] as const;
```

---

## Implementation Tasks

### Phase 1: Database (Tasks 1-3)
- [ ] **Task 1:** Create Alembic migration for `workflow_stage_checkpoints` table
- [ ] **Task 2:** Create Alembic migration for `workflow_figures` table
- [ ] **Task 3:** Create Alembic migration for `workflow_tables` table
- [ ] **Task 4:** Add `needs_user_action`, `action_required`, `meta_analysis_feasible` columns to `workflows`
- [ ] **Task 5:** Add SQLAlchemy models to `src/arakis/database/models.py`

### Phase 2: Stage Executors (Tasks 6-17)
- [ ] **Task 6:** Create `src/arakis/workflow/stages/base.py` with BaseStageExecutor
- [ ] **Task 7:** Create SearchStageExecutor
- [ ] **Task 8:** Create ScreenStageExecutor (NO 50-paper limit)
- [ ] **Task 9:** Create PDFFetchStageExecutor (extract_text=True)
- [ ] **Task 10:** Create ExtractStageExecutor (use_full_text=True)
- [ ] **Task 11:** Create RiskOfBiasStageExecutor (NEW)
- [ ] **Task 12:** Create AnalysisStageExecutor (full meta-analysis + R2 upload)
- [ ] **Task 13:** Create PRISMAStageExecutor
- [ ] **Task 14:** Create TablesStageExecutor (3 tables)
- [ ] **Task 15:** Create IntroductionStageExecutor
- [ ] **Task 16:** Create MethodsStageExecutor (NEW)
- [ ] **Task 17:** Create ResultsStageExecutor
- [ ] **Task 18:** Create DiscussionStageExecutor

### Phase 3: Orchestrator (Tasks 19-22)
- [ ] **Task 19:** Create WorkflowOrchestrator class
- [ ] **Task 20:** Implement checkpoint saving/loading
- [ ] **Task 21:** Implement retry logic with exponential backoff
- [ ] **Task 22:** Implement stage re-run functionality

### Phase 4: API Updates (Tasks 23-27)
- [ ] **Task 23:** Refactor `execute_workflow()` to use orchestrator
- [ ] **Task 24:** Add `POST /{id}/stages/{stage}/rerun` endpoint
- [ ] **Task 25:** Add `POST /{id}/resume` endpoint
- [ ] **Task 26:** Add `GET /{id}/stages` endpoint
- [ ] **Task 27:** Update WorkflowResponse schema with stages array

### Phase 5: Frontend (Tasks 28-32)
- [ ] **Task 28:** Update TypeScript types in `workflow.ts`
- [ ] **Task 29:** Update WorkflowDetailView with 12 stages
- [ ] **Task 30:** Add stage retry button component
- [ ] **Task 31:** Add user action prompt component
- [ ] **Task 32:** Add figure preview components (forest/funnel plots)

### Phase 6: Testing (Tasks 33-35)
- [ ] **Task 33:** Unit tests for each stage executor
- [ ] **Task 34:** Integration tests for full workflow
- [ ] **Task 35:** E2E test with frontend

---

## Critical Files

| File | Purpose |
|------|---------|
| `src/arakis/database/models.py` | Add new SQLAlchemy models |
| `src/arakis/models/workflow_state.py` | Update WorkflowStage enum |
| `src/arakis/api/routers/workflows.py` | Refactor execute_workflow, add endpoints |
| `src/arakis/api/schemas/workflow.py` | Update response schemas |
| `src/arakis/workflow/orchestrator.py` | NEW: Main orchestrator |
| `src/arakis/workflow/stages/*.py` | NEW: 12 stage executors |
| `frontend-next/src/types/workflow.ts` | Update TypeScript types |
| `frontend-next/src/components/workflow/WorkflowDetailView.tsx` | Update UI for 12 stages |

---

## Verification Steps

1. **Database:** Run migrations, verify tables created
2. **Backend:** Run `pytest tests/workflow/` - all tests pass
3. **API:** Test endpoints with curl/Postman
4. **Frontend:** Run `npm run build` - no TypeScript errors
5. **E2E:** Create workflow, watch 12 stages complete, verify figures in R2
