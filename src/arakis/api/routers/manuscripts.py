"""Manuscript export endpoints in multiple formats."""

import tempfile

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.api.dependencies import get_current_user, get_db
from arakis.api.schemas.manuscript import (
    Figure,
    ManuscriptResponse,
    Table,
    WorkflowMetadata,
)
from arakis.database.models import Manuscript, Workflow

router = APIRouter(prefix="/api/manuscripts", tags=["manuscripts"])


@router.get("/{workflow_id}/json", response_model=ManuscriptResponse)
async def export_manuscript_json(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export manuscript as structured JSON for frontend display.

    Returns complete manuscript data including:
    - Workflow metadata
    - All manuscript sections (introduction, methods, results, etc.)
    - Figures and tables
    - References
    """
    # Get workflow
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    # Get manuscript
    result = await db.execute(select(Manuscript).where(Manuscript.workflow_id == workflow_id))
    manuscript = result.scalar_one_or_none()

    if manuscript is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manuscript for workflow {workflow_id} not found. The workflow may still be running.",
        )

    # Build metadata
    metadata = WorkflowMetadata(
        workflow_id=workflow.id,
        research_question=workflow.research_question,
        papers_found=workflow.papers_found,
        papers_included=workflow.papers_included,
        total_cost=workflow.total_cost,
        databases_searched=workflow.databases or [],
    )

    # Build manuscript sections
    manuscript_sections = {
        "title": manuscript.title or "Untitled Systematic Review",
        "abstract": manuscript.abstract or "",
        "introduction": manuscript.introduction or "",
        "methods": manuscript.methods or _generate_methods_section(workflow),
        "results": manuscript.results or "",
        "discussion": manuscript.discussion or "",
        "conclusions": manuscript.conclusions or "",
    }

    # Parse figures
    figures = []
    if manuscript.figures:
        for fig_id, fig_data in manuscript.figures.items():
            figures.append(
                Figure(
                    id=fig_id,
                    title=fig_data.get("title", ""),
                    caption=fig_data.get("caption", ""),
                    file_path=fig_data.get("path"),
                    figure_type=fig_data.get("type", "unknown"),
                )
            )

    # Parse tables
    tables = []
    if manuscript.tables:
        for table_id, table_data in manuscript.tables.items():
            tables.append(
                Table(
                    id=table_id,
                    title=table_data.get("title", ""),
                    headers=table_data.get("headers", []),
                    rows=table_data.get("rows", []),
                    footnotes=table_data.get("footnotes"),
                )
            )

    return ManuscriptResponse(
        metadata=metadata,
        manuscript=manuscript_sections,
        figures=figures,
        tables=tables,
        references=manuscript.references or [],
    )


@router.get("/{workflow_id}/markdown")
async def export_manuscript_markdown(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export manuscript as Markdown (.md) file.

    Returns a downloadable Markdown file containing the complete manuscript.
    """
    # Get manuscript JSON data
    manuscript_data = await export_manuscript_json(workflow_id, db, current_user)

    # Build Markdown content
    markdown_content = _build_markdown(manuscript_data)

    # Return as downloadable file
    return Response(
        content=markdown_content.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=manuscript_{workflow_id}.md"},
    )


@router.get("/{workflow_id}/pdf")
async def export_manuscript_pdf(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export manuscript as PDF file.

    Converts Markdown to PDF using pandoc.
    Requires pandoc to be installed on the system.
    """
    # Get manuscript JSON data
    manuscript_data = await export_manuscript_json(workflow_id, db, current_user)

    # Build Markdown content
    markdown_content = _build_markdown(manuscript_data)

    try:
        # Convert to PDF using pandoc
        pdf_bytes = await _convert_markdown_to_pdf(markdown_content)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=manuscript_{workflow_id}.pdf"},
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pandoc is not installed. Please install pandoc to generate PDF exports.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}",
        )


@router.get("/{workflow_id}/docx")
async def export_manuscript_docx(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export manuscript as Microsoft Word (.docx) file.

    Converts Markdown to DOCX using pandoc.
    Requires pandoc to be installed on the system.
    """
    # Get manuscript JSON data
    manuscript_data = await export_manuscript_json(workflow_id, db, current_user)

    # Build Markdown content
    markdown_content = _build_markdown(manuscript_data)

    try:
        # Convert to DOCX using pandoc
        docx_bytes = await _convert_markdown_to_docx(markdown_content)

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=manuscript_{workflow_id}.docx"},
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pandoc is not installed. Please install pandoc to generate DOCX exports.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate DOCX: {str(e)}",
        )


# Helper functions


def _generate_methods_section(workflow: Workflow) -> str:
    """Generate methods section from workflow metadata."""
    methods = f"""## Methods

### Search Strategy

We conducted a systematic search of the following databases: {", ".join(workflow.databases or [])}.

**Research Question:** {workflow.research_question}

**Inclusion Criteria:**
{chr(10).join("- " + c.strip() for c in (workflow.inclusion_criteria or "").split(","))}

**Exclusion Criteria:**
{chr(10).join("- " + c.strip() for c in (workflow.exclusion_criteria or "").split(","))}

### Study Selection

Two independent reviewers screened all titles and abstracts. Conflicts were resolved through discussion.

### Data Extraction

Structured data was extracted from included studies using a standardized form.

### Statistical Analysis

Statistical analyses were performed as appropriate for the included studies.
"""
    return methods


def _build_markdown(manuscript_data: ManuscriptResponse) -> str:
    """Build complete Markdown document from manuscript data."""
    sections = []

    # Title
    sections.append(f"# {manuscript_data.manuscript.get('title', 'Untitled Review')}\n")

    # Abstract
    if manuscript_data.manuscript.get("abstract"):
        sections.append("## Abstract\n")
        sections.append(manuscript_data.manuscript["abstract"])
        sections.append("\n")

    # Introduction
    if manuscript_data.manuscript.get("introduction"):
        sections.append("## Introduction\n")
        sections.append(manuscript_data.manuscript["introduction"])
        sections.append("\n")

    # Methods
    if manuscript_data.manuscript.get("methods"):
        sections.append(manuscript_data.manuscript["methods"])
        sections.append("\n")

    # Results
    if manuscript_data.manuscript.get("results"):
        sections.append("## Results\n")
        sections.append(manuscript_data.manuscript["results"])
        sections.append("\n")

    # Discussion
    if manuscript_data.manuscript.get("discussion"):
        sections.append("## Discussion\n")
        sections.append(manuscript_data.manuscript["discussion"])
        sections.append("\n")

    # Conclusions
    if manuscript_data.manuscript.get("conclusions"):
        sections.append("## Conclusions\n")
        sections.append(manuscript_data.manuscript["conclusions"])
        sections.append("\n")

    # References
    if manuscript_data.references:
        sections.append("## References\n")
        for i, ref in enumerate(manuscript_data.references, 1):
            sections.append(f"{i}. {ref.get('citation', 'No citation')}\n")

    # Metadata footer
    sections.append("\n---\n")
    sections.append("\nGenerated by Arakis Systematic Review Platform\n")
    sections.append(f"Research Question: {manuscript_data.metadata.research_question}\n")
    sections.append(
        f"Papers Found: {manuscript_data.metadata.papers_found} | "
        f"Papers Included: {manuscript_data.metadata.papers_included}\n"
    )

    return "\n".join(sections)


async def _convert_markdown_to_pdf(markdown_content: str) -> bytes:
    """Convert Markdown to PDF using pandoc."""
    import subprocess

    # Create temporary files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as md_file:
        md_file.write(markdown_content)
        md_path = md_file.name

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_file:
        pdf_path = pdf_file.name

    try:
        # Run pandoc
        subprocess.run(
            [
                "pandoc",
                md_path,
                "-o",
                pdf_path,
                "--pdf-engine=xelatex",
                "-V",
                "geometry:margin=1in",
            ],
            check=True,
            capture_output=True,
        )

        # Read PDF bytes
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        return pdf_bytes
    finally:
        # Clean up temporary files
        import os

        os.unlink(md_path)
        os.unlink(pdf_path)


async def _convert_markdown_to_docx(markdown_content: str) -> bytes:
    """Convert Markdown to DOCX using pandoc."""
    import subprocess

    # Create temporary files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as md_file:
        md_file.write(markdown_content)
        md_path = md_file.name

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as docx_file:
        docx_path = docx_file.name

    try:
        # Run pandoc
        subprocess.run(
            ["pandoc", md_path, "-o", docx_path],
            check=True,
            capture_output=True,
        )

        # Read DOCX bytes
        with open(docx_path, "rb") as f:
            docx_bytes = f.read()

        return docx_bytes
    finally:
        # Clean up temporary files
        import os

        os.unlink(md_path)
        os.unlink(docx_path)
