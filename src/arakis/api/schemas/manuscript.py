"""Pydantic schemas for manuscript endpoints."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ManuscriptExportFormat(str, Enum):
    """Supported manuscript export formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"


class WorkflowMetadata(BaseModel):
    """Metadata about the workflow."""

    workflow_id: str
    research_question: str
    papers_found: int
    papers_included: int
    total_cost: float
    databases_searched: list[str]


class ManuscriptSection(BaseModel):
    """A section of the manuscript."""

    title: str
    content: str
    word_count: int


class Figure(BaseModel):
    """A figure in the manuscript."""

    id: str
    title: str
    caption: str
    file_path: Optional[str] = None
    figure_type: str  # "forest_plot", "funnel_plot", "prisma_diagram", etc.


class Table(BaseModel):
    """A table in the manuscript."""

    id: str
    title: str
    headers: list[str]
    rows: list[list[Any]]
    footnotes: Optional[list[str]] = None


class ManuscriptResponse(BaseModel):
    """Complete manuscript data for frontend display."""

    metadata: WorkflowMetadata
    manuscript: dict[str, str] = Field(
        description="Manuscript sections (title, abstract, introduction, etc.)"
    )
    figures: list[Figure] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    statistics: Optional[dict[str, Any]] = Field(
        default=None, description="Summary statistics from the review"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                    "research_question": "Effect of aspirin on sepsis mortality",
                    "papers_found": 234,
                    "papers_included": 12,
                    "total_cost": 15.43,
                    "databases_searched": ["pubmed", "openalex"],
                },
                "manuscript": {
                    "title": "Aspirin and Sepsis Mortality: A Systematic Review",
                    "abstract": "Background: ... Methods: ... Results: ... Conclusions: ...",
                    "introduction": "## Background\n\nSepsis is...",
                    "methods": "## Search Strategy\n\nWe searched...",
                    "results": "## Study Selection\n\nOur search identified...",
                    "discussion": "## Summary of Findings\n\nThis review...",
                    "conclusions": "Aspirin may reduce mortality in sepsis patients.",
                },
                "figures": [
                    {
                        "id": "fig1",
                        "title": "PRISMA Flow Diagram",
                        "caption": "Study selection process",
                        "file_path": "/figures/prisma.png",
                        "figure_type": "prisma_diagram",
                    }
                ],
                "tables": [
                    {
                        "id": "table1",
                        "title": "Characteristics of Included Studies",
                        "headers": ["Study", "Year", "N", "Intervention", "Outcome"],
                        "rows": [["Smith et al.", "2020", "100", "Aspirin 81mg", "30% mortality"]],
                    }
                ],
                "references": [
                    {
                        "id": "ref1",
                        "citation": "Smith J, et al. Aspirin in sepsis. JAMA. 2020;324(1):45-52.",
                        "doi": "10.1001/jama.2020.0001",
                    }
                ],
            }
        }
