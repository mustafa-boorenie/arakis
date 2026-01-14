"""Pydantic schemas for workflow endpoints."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStage(str, Enum):
    """Current workflow stage."""

    SEARCHING = "searching"
    SCREENING = "screening"
    ANALYZING = "analyzing"
    WRITING = "writing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"


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
                "papers_found": 234,
                "papers_screened": 234,
                "papers_included": 12,
                "total_cost": 15.43,
                "created_at": "2026-01-09T19:00:00Z",
                "completed_at": "2026-01-09T19:45:00Z",
            }
        }


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
