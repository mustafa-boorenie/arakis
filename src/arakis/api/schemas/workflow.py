"""Pydantic schemas for workflow endpoints."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from arakis.config import CostMode


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStage(str, Enum):
    """Workflow stages - 12 comprehensive stages."""

    SEARCH = "search"
    SCREEN = "screen"
    PDF_FETCH = "pdf_fetch"
    EXTRACT = "extract"
    ROB = "rob"
    ANALYSIS = "analysis"
    PRISMA = "prisma"
    TABLES = "tables"
    INTRODUCTION = "introduction"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    COMPLETED = "completed"


class StageStatus(str, Enum):
    """Stage execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RecentDecision(BaseModel):
    """A recent screening/processing decision for progress feed."""

    paper_id: str
    title: str
    decision: str
    confidence: float
    reason: str
    matched_inclusion: list[str] = []
    matched_exclusion: list[str] = []
    is_conflict: bool = False
    timestamp: datetime


class StageProgress(BaseModel):
    """Real-time progress data for a workflow stage."""

    # Common fields
    phase: Optional[str] = None
    thought_process: Optional[str] = None
    estimated_remaining_seconds: Optional[int] = None
    updated_at: Optional[datetime] = None

    # Current item being processed
    current_item: Optional[dict] = None

    # Summary statistics
    summary: Optional[dict] = None

    # Rolling buffer of recent decisions/events
    recent_decisions: list[dict] = []

    # For search stage
    current_database: Optional[str] = None
    databases_completed: list[str] = []
    queries: dict = {}
    results_per_database: dict = {}

    # For writing stages
    current_subsection: Optional[str] = None
    subsections_completed: list[str] = []
    subsections_pending: list[str] = []
    word_count: int = 0


class StageCheckpoint(BaseModel):
    """Schema for a stage checkpoint."""

    stage: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    cost: float = 0.0

    # Real-time progress data
    progress: Optional[StageProgress] = None

    class Config:
        from_attributes = True


class WorkflowCreate(BaseModel):
    """Schema for creating a new workflow."""

    research_question: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="The research question for the systematic review",
        examples=["Effect of aspirin on sepsis mortality in adult patients"],
    )
    inclusion_criteria: str = Field(
        ...,
        description="Comma-separated inclusion criteria",
        examples=["Adult patients,Sepsis,Aspirin intervention,Mortality outcome"],
    )
    exclusion_criteria: str = Field(
        ...,
        description="Comma-separated exclusion criteria",
        examples=["Pediatric patients,Animal studies,In vitro studies"],
    )
    databases: list[str] = Field(
        default=["pubmed", "openalex"],
        description="List of databases to search",
        examples=[["pubmed", "openalex", "semantic_scholar"]],
    )
    max_results_per_query: int = Field(
        default=500,
        ge=10,
        le=5000,
        description="Maximum results per database query",
    )
    fast_mode: bool = Field(
        default=False,
        description="Use fast mode (single-pass screening and extraction)",
    )
    skip_analysis: bool = Field(
        default=False,
        description="Skip statistical analysis",
    )
    skip_writing: bool = Field(
        default=False,
        description="Skip manuscript writing",
    )
    cost_mode: CostMode = Field(
        default=CostMode.BALANCED,
        description="Cost/quality optimization mode (QUALITY, BALANCED, FAST, ECONOMY)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "research_question": "Effect of aspirin on sepsis mortality",
                "inclusion_criteria": "Adult patients,Sepsis,Aspirin intervention,Mortality",
                "exclusion_criteria": "Pediatric,Animal studies",
                "databases": ["pubmed", "openalex"],
                "max_results_per_query": 500,
                "fast_mode": False,
                "skip_analysis": False,
                "skip_writing": False,
                "cost_mode": "BALANCED",
            }
        }


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""

    id: str
    research_question: str
    inclusion_criteria: Optional[str] = None
    exclusion_criteria: Optional[str] = None
    databases: Optional[list[str]] = None
    status: str
    current_stage: Optional[str] = None
    papers_found: int = 0
    papers_screened: int = 0
    papers_included: int = 0
    total_cost: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # New fields for unified workflow
    needs_user_action: bool = False
    action_required: Optional[str] = None
    meta_analysis_feasible: Optional[bool] = None
    stages: list[StageCheckpoint] = []
    cost_mode: str = "BALANCED"

    # Figure URLs from R2
    forest_plot_url: Optional[str] = None
    funnel_plot_url: Optional[str] = None
    prisma_url: Optional[str] = None

    class Config:
        from_attributes = True  # For SQLAlchemy model conversion
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "research_question": "Effect of aspirin on sepsis mortality",
                "inclusion_criteria": "Adult patients,Sepsis,Aspirin intervention",
                "exclusion_criteria": "Pediatric,Animal studies",
                "databases": ["pubmed", "openalex"],
                "status": "completed",
                "current_stage": "completed",
                "papers_found": 234,
                "papers_screened": 234,
                "papers_included": 12,
                "total_cost": 15.43,
                "created_at": "2026-01-09T19:00:00Z",
                "completed_at": "2026-01-09T19:45:00Z",
                "needs_user_action": False,
                "action_required": None,
                "meta_analysis_feasible": True,
                "stages": [],
                "forest_plot_url": "https://r2.example.com/workflow-123/forest_plot.png",
                "funnel_plot_url": "https://r2.example.com/workflow-123/funnel_plot.png",
                "prisma_url": "https://r2.example.com/workflow-123/prisma_flow.png",
            }
        }


class StageRerunRequest(BaseModel):
    """Schema for re-running a stage."""

    input_override: Optional[dict] = Field(
        default=None,
        description="Optional data to override previous checkpoint",
    )


class StageRerunResponse(BaseModel):
    """Schema for stage re-run response."""

    success: bool
    stage: str
    output_data: Optional[dict] = None
    error: Optional[str] = None
    cost: float = 0.0


class WorkflowList(BaseModel):
    """Schema for list of workflows."""

    workflows: list[WorkflowResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "workflows": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "research_question": "Effect of aspirin on sepsis mortality",
                        "status": "completed",
                        "papers_found": 234,
                        "papers_included": 12,
                        "total_cost": 15.43,
                        "created_at": "2026-01-09T19:00:00Z",
                        "completed_at": "2026-01-09T19:45:00Z",
                    }
                ],
                "total": 1,
            }
        }
