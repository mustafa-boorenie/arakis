"""Workflow CRUD and execution endpoints."""

import asyncio
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.api.dependencies import get_db, get_current_user
from arakis.api.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowList,
)
from arakis.database.models import Workflow

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new systematic review workflow and start execution in background.

    The workflow will run asynchronously and update its status as it progresses:
    - pending → running → completed (or failed)

    You can poll GET /api/workflows/{id} to check status.
    """
    # Create workflow in database
    workflow_id = str(uuid4())
    workflow = Workflow(
        id=workflow_id,
        research_question=workflow_data.research_question,
        inclusion_criteria=workflow_data.inclusion_criteria,
        exclusion_criteria=workflow_data.exclusion_criteria,
        databases=workflow_data.databases,
        status="pending",
        created_at=datetime.utcnow(),
    )

    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    # Start workflow execution in background
    background_tasks.add_task(
        execute_workflow,
        workflow_id=workflow_id,
        workflow_data=workflow_data,
    )

    return WorkflowResponse.model_validate(workflow)


@router.get("/", response_model=WorkflowList)
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all workflows with optional filtering.

    Query parameters:
    - skip: Number of workflows to skip (for pagination)
    - limit: Maximum number of workflows to return
    - status: Filter by status (pending, running, completed, failed)
    """
    # Build query
    query = select(Workflow).order_by(Workflow.created_at.desc())

    if status:
        query = query.where(Workflow.status == status)

    # Get total count
    count_query = select(Workflow)
    if status:
        count_query = count_query.where(Workflow.status == status)
    result = await db.execute(count_query)
    total = len(result.scalars().all())

    # Get paginated results
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    workflows = result.scalars().all()

    return WorkflowList(
        workflows=[WorkflowResponse.model_validate(w) for w in workflows],
        total=total,
    )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get details of a specific workflow by ID.

    Returns workflow status, statistics, and metadata.
    """
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return WorkflowResponse.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a workflow and all associated data (papers, screening decisions, etc.).

    This is a cascade delete that removes all related records.
    """
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    await db.delete(workflow)
    await db.commit()


# Background task execution function
async def execute_workflow(workflow_id: str, workflow_data: WorkflowCreate):
    """
    Execute complete workflow pipeline in background.

    This is a simplified version for Phase 2 API demonstration.
    Full workflow execution will be integrated in Phase 2.5.

    Steps:
    1. Update status to 'running'
    2. Search databases (using existing SearchOrchestrator)
    3. Screen papers (using existing ScreeningAgent)
    4. Mark as completed

    Note: This function runs in a background task, so it needs its own DB session.
    """
    from arakis.database.connection import AsyncSessionLocal
    from arakis.database.models import Paper, ScreeningDecision, Manuscript

    async with AsyncSessionLocal() as db:
        try:
            # Update status to running
            result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
            workflow = result.scalar_one()
            workflow.status = "running"
            await db.commit()

            # Import modules here to avoid import issues
            from arakis.orchestrator import SearchOrchestrator
            from arakis.agents.screener import ScreeningAgent

            # Step 1: Search databases
            orchestrator = SearchOrchestrator()
            search_results = await orchestrator.comprehensive_search(
                research_question=workflow_data.research_question,
                databases=workflow_data.databases,
                max_results_per_query=workflow_data.max_results_per_query,
            )

            # Save papers to database
            for paper in search_results.papers:
                # Serialize authors to JSON-compatible format
                authors_json = None
                if paper.authors:
                    from dataclasses import asdict, is_dataclass
                    authors_json = [
                        asdict(a) if is_dataclass(a) else a
                        for a in paper.authors
                    ]

                db_paper = Paper(
                    id=paper.best_identifier or f"{paper.source}_{hash(paper.title)}",
                    workflow_id=workflow_id,
                    doi=paper.doi,
                    pmid=paper.pmid,
                    pmcid=paper.pmcid,
                    arxiv_id=paper.arxiv_id,
                    s2_id=paper.s2_id,
                    openalex_id=paper.openalex_id,
                    title=paper.title,
                    abstract=paper.abstract,
                    journal=paper.journal,
                    year=paper.year,
                    authors=authors_json,
                    keywords=paper.keywords,
                    mesh_terms=paper.mesh_terms,
                    pdf_url=paper.pdf_url,
                    open_access=paper.open_access,
                    source=paper.source,
                    source_url=paper.source_url,
                    retrieved_at=paper.retrieved_at or datetime.utcnow(),
                )
                db.add(db_paper)

            workflow.papers_found = len(search_results.papers)
            await db.commit()

            # Step 2: Screen papers
            from arakis.models.screening import ScreeningCriteria

            screener = ScreeningAgent()
            dual_review = not workflow_data.fast_mode

            # Create screening criteria object
            criteria = ScreeningCriteria(
                inclusion=[c.strip() for c in workflow_data.inclusion_criteria.split(",")],
                exclusion=[c.strip() for c in workflow_data.exclusion_criteria.split(",")],
            )

            for paper in search_results.papers[:min(len(search_results.papers), 5)]:  # Limit to 5 for demo
                decision = await screener.screen_paper(
                    paper=paper,
                    criteria=criteria,
                    dual_review=dual_review,
                )

                # Save screening decision
                db_decision = ScreeningDecision(
                    workflow_id=workflow_id,
                    paper_id=paper.best_identifier or f"{paper.source}_{hash(paper.title)}",
                    status=decision.status,
                    reason=decision.reason,
                    confidence=decision.confidence,
                    matched_inclusion=decision.matched_inclusion,
                    matched_exclusion=decision.matched_exclusion,
                    is_conflict=decision.is_conflict,
                    second_opinion=decision.second_opinion,
                    created_at=datetime.utcnow(),
                )
                db.add(db_decision)

            workflow.papers_screened = min(len(search_results.papers), 5)
            await db.commit()

            # Get included papers count
            result = await db.execute(
                select(ScreeningDecision)
                .where(ScreeningDecision.workflow_id == workflow_id)
                .where(ScreeningDecision.status == "INCLUDE")
            )
            included_decisions = result.scalars().all()
            workflow.papers_included = len(included_decisions)

            # Create a simple manuscript placeholder
            manuscript = Manuscript(
                workflow_id=workflow_id,
                title=f"Systematic Review: {workflow_data.research_question}",
                abstract="This is an automated systematic review generated by Arakis.",
                introduction="Full manuscript generation will be implemented in Phase 2.5.",
                methods=f"Searched {', '.join(workflow_data.databases)}. Screened {workflow.papers_screened} papers.",
                results=f"Found {workflow.papers_found} papers, included {workflow.papers_included} studies.",
                discussion="Discussion section will be generated automatically.",
                conclusions="Conclusions will be based on extracted data and analysis.",
                references=[],
                figures={},
                tables={},
                meta={},
                created_at=datetime.utcnow(),
            )
            db.add(manuscript)

            # Mark workflow as completed
            workflow.status = "completed"
            workflow.completed_at = datetime.utcnow()
            workflow.total_cost = 0.5  # Estimated cost for demo
            await db.commit()

        except Exception as e:
            # Mark workflow as failed
            try:
                result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
                workflow = result.scalar_one()
                workflow.status = "failed"
                workflow.completed_at = datetime.utcnow()
                await db.commit()
            except:
                pass
            # Log the error but don't re-raise to avoid background task failures
            print(f"Workflow {workflow_id} failed: {str(e)}")
