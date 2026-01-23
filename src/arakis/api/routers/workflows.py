"""Workflow CRUD and execution endpoints."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.api.dependencies import get_current_user, get_db
from arakis.api.schemas.workflow import (
    StageCheckpoint,
    StageRerunRequest,
    StageRerunResponse,
    WorkflowCreate,
    WorkflowList,
    WorkflowResponse,
)
from arakis.database.models import User, Workflow, WorkflowStageCheckpoint, WorkflowFigure

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Create a new systematic review workflow and start execution in background.

    Trial Mode:
    - Anonymous users get ONE free workflow (tracked via session cookie)
    - Second workflow attempt returns 402 (Payment Required) with X-Auth-Required header
    - After authentication, trial workflows are automatically claimed

    The workflow will run asynchronously and update its status as it progresses:
    - pending → running → completed (or failed)

    You can poll GET /api/workflows/{id} to check status.
    """
    workflow_id = str(uuid4())
    user_id = None
    session_id = None

    if current_user:
        # Authenticated user - assign workflow to user
        user_id = current_user.id
    else:
        # Anonymous user - check trial quota
        session_id = request.cookies.get("arakis_session")

        if not session_id:
            # Generate new session ID for trial tracking
            session_id = str(uuid4())
            response.set_cookie(
                key="arakis_session",
                value=session_id,
                max_age=60 * 60 * 24 * 30,  # 30 days
                httponly=True,
                samesite="lax",
            )
        else:
            # Check if session already has a workflow (trial limit)
            result = await db.execute(
                select(Workflow).where(Workflow.session_id == session_id).limit(1)
            )
            existing = result.scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Trial limit reached. Please sign in to continue.",
                    headers={"X-Auth-Required": "true"},
                )

    # Create workflow in database
    workflow = Workflow(
        id=workflow_id,
        research_question=workflow_data.research_question,
        inclusion_criteria=workflow_data.inclusion_criteria,
        exclusion_criteria=workflow_data.exclusion_criteria,
        databases=workflow_data.databases,
        status="pending",
        created_at=datetime.now(timezone.utc),
        user_id=user_id,
        session_id=session_id,
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

    return await _build_workflow_response(workflow, db)


@router.get("/", response_model=WorkflowList)
async def list_workflows(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    List workflows for the current user.

    - Authenticated users see their own workflows
    - Anonymous users see their trial workflow (if any)

    Query parameters:
    - skip: Number of workflows to skip (for pagination)
    - limit: Maximum number of workflows to return
    - status: Filter by status (pending, running, completed, failed)
    """
    # Build base query with user isolation
    if current_user:
        # Authenticated user - show their workflows
        base_filter = Workflow.user_id == current_user.id
    else:
        # Anonymous user - show workflows for their session
        session_id = request.cookies.get("arakis_session")
        if not session_id:
            # No session - return empty list
            return WorkflowList(workflows=[], total=0)
        base_filter = Workflow.session_id == session_id

    # Build query
    query = select(Workflow).where(base_filter).order_by(Workflow.created_at.desc())

    if status:
        query = query.where(Workflow.status == status)

    # Get total count
    count_query = select(Workflow).where(base_filter)
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get details of a specific workflow by ID.

    Returns workflow status, statistics, and metadata.
    Only returns workflows owned by the current user or session.
    """
    # Build query with ownership check
    query = select(Workflow).where(Workflow.id == workflow_id)

    if current_user:
        # Authenticated user - verify ownership
        query = query.where(Workflow.user_id == current_user.id)
    else:
        # Anonymous user - verify session ownership
        session_id = request.cookies.get("arakis_session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            )
        query = query.where(Workflow.session_id == session_id)

    result = await db.execute(query)
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    return await _build_workflow_response(workflow, db)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Delete a workflow and all associated data (papers, screening decisions, etc.).

    This is a cascade delete that removes all related records.
    Only allows deletion of workflows owned by the current user or session.
    """
    # Build query with ownership check
    query = select(Workflow).where(Workflow.id == workflow_id)

    if current_user:
        # Authenticated user - verify ownership
        query = query.where(Workflow.user_id == current_user.id)
    else:
        # Anonymous user - verify session ownership
        session_id = request.cookies.get("arakis_session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            )
        query = query.where(Workflow.session_id == session_id)

    result = await db.execute(query)
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    await db.delete(workflow)
    await db.commit()


@router.post("/claim/{workflow_id}", response_model=WorkflowResponse)
async def claim_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Claim an orphan workflow (no user_id) for the authenticated user.

    This allows users to claim workflows created before authentication
    if they have the workflow ID.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to claim workflows",
        )

    # Find workflow with no user
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.user_id.is_(None),
        )
    )
    workflow = result.scalar_one_or_none()

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found or already claimed",
        )

    # Claim the workflow
    workflow.user_id = current_user.id
    workflow.session_id = None
    await db.commit()
    await db.refresh(workflow)

    return await _build_workflow_response(workflow, db)


# Helper function to build workflow response with stages and figures
async def _build_workflow_response(workflow: Workflow, db: AsyncSession) -> WorkflowResponse:
    """Build WorkflowResponse with stages and figure URLs."""
    # Get stage checkpoints
    result = await db.execute(
        select(WorkflowStageCheckpoint)
        .where(WorkflowStageCheckpoint.workflow_id == workflow.id)
        .order_by(WorkflowStageCheckpoint.started_at)
    )
    checkpoints = result.scalars().all()

    stages = [
        StageCheckpoint(
            stage=cp.stage,
            status=cp.status,
            started_at=cp.started_at,
            completed_at=cp.completed_at,
            retry_count=cp.retry_count,
            error_message=cp.error_message,
            cost=cp.cost or 0.0,
        )
        for cp in checkpoints
    ]

    # Get figure URLs
    result = await db.execute(
        select(WorkflowFigure)
        .where(WorkflowFigure.workflow_id == workflow.id)
    )
    figures = result.scalars().all()

    forest_plot_url = None
    funnel_plot_url = None
    prisma_url = None

    for fig in figures:
        if fig.figure_type == "forest_plot":
            forest_plot_url = fig.r2_url
        elif fig.figure_type == "funnel_plot":
            funnel_plot_url = fig.r2_url
        elif fig.figure_type == "prisma_flow":
            prisma_url = fig.r2_url

    return WorkflowResponse(
        id=workflow.id,
        research_question=workflow.research_question,
        inclusion_criteria=workflow.inclusion_criteria,
        exclusion_criteria=workflow.exclusion_criteria,
        databases=workflow.databases,
        status=workflow.status,
        current_stage=workflow.current_stage,
        papers_found=workflow.papers_found or 0,
        papers_screened=workflow.papers_screened or 0,
        papers_included=workflow.papers_included or 0,
        total_cost=workflow.total_cost or 0.0,
        created_at=workflow.created_at,
        completed_at=workflow.completed_at,
        error_message=workflow.error_message,
        needs_user_action=workflow.needs_user_action or False,
        action_required=workflow.action_required,
        meta_analysis_feasible=workflow.meta_analysis_feasible,
        stages=stages,
        forest_plot_url=forest_plot_url,
        funnel_plot_url=funnel_plot_url,
        prisma_url=prisma_url,
    )


@router.get("/{workflow_id}/stages", response_model=list[StageCheckpoint])
async def get_stage_checkpoints(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get all stage checkpoints for a workflow.

    Returns the status, timing, and error information for each stage.
    """
    # Verify ownership
    query = select(Workflow).where(Workflow.id == workflow_id)
    if current_user:
        query = query.where(Workflow.user_id == current_user.id)
    else:
        session_id = request.cookies.get("arakis_session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            )
        query = query.where(Workflow.session_id == session_id)

    result = await db.execute(query)
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    # Get checkpoints
    result = await db.execute(
        select(WorkflowStageCheckpoint)
        .where(WorkflowStageCheckpoint.workflow_id == workflow_id)
        .order_by(WorkflowStageCheckpoint.started_at)
    )
    checkpoints = result.scalars().all()

    return [
        StageCheckpoint(
            stage=cp.stage,
            status=cp.status,
            started_at=cp.started_at,
            completed_at=cp.completed_at,
            retry_count=cp.retry_count,
            error_message=cp.error_message,
            cost=cp.cost or 0.0,
        )
        for cp in checkpoints
    ]


@router.post("/{workflow_id}/stages/{stage}/rerun", response_model=StageRerunResponse)
async def rerun_stage(
    workflow_id: str,
    stage: str,
    request: Request,
    rerun_request: StageRerunRequest = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Re-run a specific stage of a workflow.

    This allows you to retry a failed stage or re-run a completed stage
    with modified input data.
    """
    from arakis.workflow.orchestrator import WorkflowOrchestrator

    # Verify ownership
    query = select(Workflow).where(Workflow.id == workflow_id)
    if current_user:
        query = query.where(Workflow.user_id == current_user.id)
    else:
        session_id = request.cookies.get("arakis_session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            )
        query = query.where(Workflow.session_id == session_id)

    result = await db.execute(query)
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    # Validate stage
    valid_stages = [
        "search", "screen", "pdf_fetch", "extract", "rob",
        "analysis", "prisma", "tables", "introduction",
        "methods", "results", "discussion"
    ]
    if stage not in valid_stages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage: {stage}. Must be one of: {', '.join(valid_stages)}",
        )

    try:
        orchestrator = WorkflowOrchestrator(db)
        input_override = rerun_request.input_override if rerun_request else None
        result = await orchestrator.rerun_stage(workflow_id, stage, input_override)

        return StageRerunResponse(
            success=result.success,
            stage=stage,
            output_data=result.output_data if result.success else None,
            error=result.error,
            cost=result.cost,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-run stage: {str(e)}",
        )


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    workflow_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Resume a paused workflow after user action.

    Use this endpoint when a workflow is in 'needs_review' status
    and you're ready to continue processing.
    """
    # Verify ownership
    query = select(Workflow).where(Workflow.id == workflow_id)
    if current_user:
        query = query.where(Workflow.user_id == current_user.id)
    else:
        session_id = request.cookies.get("arakis_session")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            )
        query = query.where(Workflow.session_id == session_id)

    result = await db.execute(query)
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found",
        )

    if workflow.status != "needs_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow is not paused. Current status: {workflow.status}",
        )

    # Start resume in background
    background_tasks.add_task(
        execute_workflow_resume,
        workflow_id=workflow_id,
    )

    # Update status to running
    workflow.status = "running"
    workflow.needs_user_action = False
    workflow.action_required = None
    await db.commit()
    await db.refresh(workflow)

    return await _build_workflow_response(workflow, db)


# Background task for resuming workflow
async def execute_workflow_resume(workflow_id: str):
    """Resume workflow execution in background."""
    from arakis.database.connection import AsyncSessionLocal
    from arakis.workflow.orchestrator import WorkflowOrchestrator

    async with AsyncSessionLocal() as db:
        try:
            orchestrator = WorkflowOrchestrator(db)
            await orchestrator.resume_workflow(workflow_id)
        except Exception as e:
            import traceback
            print(f"[{workflow_id}] Resume failed: {e}")
            print(traceback.format_exc())

            # Mark as failed
            result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
            workflow = result.scalar_one_or_none()
            if workflow:
                workflow.status = "failed"
                workflow.error_message = str(e)
                await db.commit()


# Background task execution function
async def execute_workflow(workflow_id: str, workflow_data: WorkflowCreate):
    """
    Execute complete systematic review workflow pipeline in background.

    Uses WorkflowOrchestrator to run 12 stages with checkpointing:
    1. search - Multi-database literature search
    2. screen - AI-powered paper screening (NO 50-paper limit)
    3. pdf_fetch - Download PDFs and extract text
    4. extract - Structured data extraction from papers
    5. rob - Risk of Bias assessment (auto-detect tool)
    6. analysis - Meta-analysis with forest/funnel plots
    7. prisma - Flow diagram generation
    8. tables - Generate all 3 tables (characteristics, RoB, GRADE)
    9. introduction - Write introduction section
    10. methods - Write methods section
    11. results - Write results section
    12. discussion - Write discussion section

    Note: This function runs in a background task with its own DB session.
    """
    import traceback

    from arakis.database.connection import AsyncSessionLocal
    from arakis.workflow.orchestrator import WorkflowOrchestrator

    async with AsyncSessionLocal() as db:
        try:
            # Update status to running
            result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
            workflow = result.scalar_one()
            workflow.status = "running"
            await db.commit()

            # Prepare initial data for orchestrator
            # Convert comma-separated criteria to lists for stage executors
            inclusion_list = [c.strip() for c in workflow_data.inclusion_criteria.split(",")]
            exclusion_list = [c.strip() for c in workflow_data.exclusion_criteria.split(",")]

            initial_data = {
                "research_question": workflow_data.research_question,
                "inclusion_criteria": inclusion_list,
                "exclusion_criteria": exclusion_list,
                "databases": workflow_data.databases or ["pubmed"],
                "max_results_per_query": workflow_data.max_results_per_query or 100,
                "fast_mode": workflow_data.fast_mode or False,
            }

            # Determine stages to skip based on workflow options
            skip_stages = []
            if workflow_data.skip_analysis:
                skip_stages.extend(["analysis"])
            if workflow_data.skip_writing:
                skip_stages.extend(["introduction", "methods", "results", "discussion"])

            # Run the orchestrator
            orchestrator = WorkflowOrchestrator(db)
            result = await orchestrator.execute_workflow(
                workflow_id=workflow_id,
                initial_data=initial_data,
                skip_stages=skip_stages if skip_stages else None,
            )

            print(f"[{workflow_id}] Workflow finished with status: {result['status']}")

        except Exception as e:
            # Mark workflow as failed with error message
            error_msg = str(e)
            full_error = traceback.format_exc()

            # Extract more useful error info
            if "Semantic Scholar" in full_error:
                error_msg = (
                    "Semantic Scholar rate limit exceeded. Try using only PubMed or OpenAlex."
                )
            elif "OpenAlex" in full_error and "RateLimitError" in full_error:
                error_msg = "OpenAlex rate limit exceeded. Try using only PubMed."
            elif "PubMed" in full_error and "RateLimitError" in full_error:
                error_msg = "PubMed rate limit exceeded. Please wait a minute and try again."
            elif "RateLimitError" in error_msg or "RateLimitError" in full_error:
                if "openai" in full_error.lower():
                    error_msg = (
                        "OpenAI API rate limit exceeded. Please wait a few minutes and try again."
                    )
                else:
                    error_msg = (
                        "API rate limit exceeded. Try using fewer databases or wait a moment."
                    )
            elif "APIError" in error_msg or "APIError" in full_error:
                error_msg = "OpenAI API error. Please check your API key and try again."
            elif "HTTPStatusError" in error_msg or "HTTPStatusError" in full_error:
                if "429" in full_error:
                    error_msg = "Database API rate limit exceeded. Please wait and try again."
                elif "503" in full_error:
                    error_msg = "Database service temporarily unavailable. Please try again."
                else:
                    error_msg = "Database search failed. Please try again with fewer databases."
            elif "RetryError" in error_msg:
                error_msg = "Search request failed after multiple retries. Try using only PubMed."

            try:
                result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
                workflow = result.scalar_one()
                workflow.status = "failed"
                workflow.error_message = error_msg
                workflow.completed_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception:
                pass

            print(f"Workflow {workflow_id} failed: {error_msg}")
            print(f"Full traceback:\n{full_error}")
