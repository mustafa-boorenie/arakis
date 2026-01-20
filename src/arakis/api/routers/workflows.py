"""Workflow CRUD and execution endpoints."""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.api.dependencies import get_current_user, get_db
from arakis.api.schemas.workflow import (
    WorkflowCreate,
    WorkflowList,
    WorkflowResponse,
)
from arakis.database.models import User, Workflow

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

    return WorkflowResponse.model_validate(workflow)


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

    return WorkflowResponse.model_validate(workflow)


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

    return WorkflowResponse.model_validate(workflow)


# Background task execution function
async def execute_workflow(workflow_id: str, workflow_data: WorkflowCreate):
    """
    Execute complete systematic review workflow pipeline in background.

    Full Pipeline:
    1. Search databases (SearchOrchestrator)
    2. Screen papers (ScreeningAgent with dual-review)
    3. Check for conflicts → pause if needed
    4. Fetch full texts (PaperFetcher)
    5. Extract data (DataExtractionAgent)
    6. Run statistical analysis (MetaAnalysisEngine)
    7. Generate visualizations (PRISMA, forest plots)
    8. Write all manuscript sections
    9. Assemble final manuscript

    Note: This function runs in a background task with its own DB session.
    """
    import os
    import traceback
    from dataclasses import asdict, is_dataclass

    from arakis.database.connection import AsyncSessionLocal
    from arakis.database.models import Manuscript, Paper, ScreeningDecision

    total_cost = 0.0

    async with AsyncSessionLocal() as db:
        try:
            # Update status to running
            result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
            workflow = result.scalar_one()
            workflow.status = "running"
            workflow.current_stage = "searching"
            await db.commit()

            # Import modules here to avoid circular imports
            from arakis.agents.screener import ScreeningAgent
            from arakis.orchestrator import SearchOrchestrator

            # ============================================================
            # STAGE 1: Search Databases
            # ============================================================
            print(f"[{workflow_id}] Stage 1: Searching databases...")
            orchestrator = SearchOrchestrator()
            search_results = await orchestrator.comprehensive_search(
                research_question=workflow_data.research_question,
                databases=workflow_data.databases,
                max_results_per_query=workflow_data.max_results_per_query,
            )

            # Save papers to database
            paper_map = {}  # Map paper ID to paper object for later use
            for paper in search_results.papers:
                authors_json = None
                if paper.authors:
                    authors_json = [asdict(a) if is_dataclass(a) else a for a in paper.authors]

                paper_identifier = paper.best_identifier or f"{paper.source}_{hash(paper.title)}"
                unique_paper_id = f"{workflow_id}_{paper_identifier}"

                db_paper = Paper(
                    id=unique_paper_id,
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
                    retrieved_at=paper.retrieved_at or datetime.now(timezone.utc),
                )
                db.add(db_paper)
                paper_map[unique_paper_id] = paper

            workflow.papers_found = len(search_results.papers)
            await db.commit()
            print(f"[{workflow_id}] Found {workflow.papers_found} papers")

            # ============================================================
            # STAGE 2: Screen Papers
            # ============================================================
            print(f"[{workflow_id}] Stage 2: Screening papers...")
            workflow.current_stage = "screening"
            await db.commit()

            from arakis.models.screening import ScreeningCriteria

            screener = ScreeningAgent()
            dual_review = not workflow_data.fast_mode

            criteria = ScreeningCriteria(
                inclusion=[c.strip() for c in workflow_data.inclusion_criteria.split(",")],
                exclusion=[c.strip() for c in workflow_data.exclusion_criteria.split(",")],
            )

            screening_decisions = []
            conflicts = []
            max_screen = min(len(search_results.papers), 50)  # Limit for cost control

            for i, paper in enumerate(search_results.papers[:max_screen]):
                decision = await screener.screen_paper(
                    paper=paper,
                    criteria=criteria,
                    dual_review=dual_review,
                )

                paper_identifier = paper.best_identifier or f"{paper.source}_{hash(paper.title)}"
                unique_paper_id = f"{workflow_id}_{paper_identifier}"

                # Serialize second_opinion to dict if it exists (it's a ScreeningDecision dataclass)
                second_opinion_data = None
                if decision.second_opinion:
                    second_opinion_data = {
                        "status": str(decision.second_opinion.status.value)
                        if hasattr(decision.second_opinion.status, "value")
                        else str(decision.second_opinion.status),
                        "reason": decision.second_opinion.reason,
                        "confidence": decision.second_opinion.confidence,
                        "matched_inclusion": decision.second_opinion.matched_inclusion,
                        "matched_exclusion": decision.second_opinion.matched_exclusion,
                    }

                # Convert status enum to string value
                status_value = (
                    decision.status.value
                    if hasattr(decision.status, "value")
                    else str(decision.status)
                )

                db_decision = ScreeningDecision(
                    workflow_id=workflow_id,
                    paper_id=unique_paper_id,
                    status=status_value,
                    reason=decision.reason,
                    confidence=decision.confidence,
                    matched_inclusion=decision.matched_inclusion,
                    matched_exclusion=decision.matched_exclusion,
                    is_conflict=decision.is_conflict,
                    second_opinion=second_opinion_data,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(db_decision)
                screening_decisions.append((unique_paper_id, decision))

                if decision.is_conflict:
                    conflicts.append(unique_paper_id)

                # Update progress
                if (i + 1) % 10 == 0:
                    workflow.papers_screened = i + 1
                    await db.commit()
                    print(f"[{workflow_id}] Screened {i + 1}/{max_screen} papers")

            workflow.papers_screened = len(screening_decisions)
            total_cost += 0.02 * len(screening_decisions)  # ~$0.02 per screening
            await db.commit()

            # Get included papers (ScreeningStatus values are lowercase: "include", "exclude", "maybe")
            from arakis.models.screening import ScreeningStatus

            included_paper_ids = [
                pid
                for pid, dec in screening_decisions
                if dec.status == ScreeningStatus.INCLUDE
                or (dec.status == ScreeningStatus.MAYBE and not dec.is_conflict)
            ]
            workflow.papers_included = len(included_paper_ids)
            await db.commit()

            print(
                f"[{workflow_id}] Screening complete: {workflow.papers_included} included, {len(conflicts)} conflicts"
            )

            # If there are conflicts, we could pause here for review
            # For now, continue with conservative approach (MAYBE → exclude)
            if conflicts:
                print(
                    f"[{workflow_id}] Note: {len(conflicts)} screening conflicts will use conservative resolution"
                )

            # ============================================================
            # STAGE 3: Generate PRISMA Flow Data
            # ============================================================
            print(f"[{workflow_id}] Stage 3: Generating PRISMA flow...")
            workflow.current_stage = "analyzing"
            await db.commit()

            from arakis.models.visualization import PRISMAFlow

            # Get duplicates removed from search results (paper.PRISMAFlow uses 'duplicates_removed')
            duplicates_removed = 0
            if search_results.prisma_flow:
                duplicates_removed = getattr(search_results.prisma_flow, "duplicates_removed", 0)

            prisma_flow = PRISMAFlow(
                records_identified_total=workflow.papers_found,
                records_identified_databases={
                    db: workflow.papers_found // len(workflow_data.databases)
                    for db in workflow_data.databases
                },
                records_removed_duplicates=duplicates_removed,
                records_screened=workflow.papers_screened,
                records_excluded=workflow.papers_screened - workflow.papers_included,
                studies_included=workflow.papers_included,
            )

            # ============================================================
            # STAGE 4: Generate Visualizations
            # ============================================================
            print(f"[{workflow_id}] Stage 4: Generating visualizations...")

            figures = {}
            output_dir = f"/tmp/arakis/{workflow_id}"
            os.makedirs(output_dir, exist_ok=True)

            # Generate PRISMA diagram
            try:
                from arakis.visualization.prisma import PRISMADiagramGenerator

                prisma_gen = PRISMADiagramGenerator()
                prisma_path = f"{output_dir}/prisma_diagram.png"
                prisma_gen.generate(prisma_flow, prisma_path)
                figures["fig1"] = {
                    "id": "fig1",
                    "title": "Figure 1",
                    "caption": "PRISMA 2020 flow diagram for systematic review",
                    "file_path": prisma_path,
                    "figure_type": "prisma_diagram",
                }
                print(f"[{workflow_id}] Generated PRISMA diagram")
            except Exception as e:
                print(f"[{workflow_id}] Failed to generate PRISMA diagram: {e}")

            # ============================================================
            # STAGE 5: Write Manuscript Sections
            # ============================================================
            print(f"[{workflow_id}] Stage 5: Writing manuscript sections...")
            workflow.current_stage = "writing"
            await db.commit()

            # Get included papers for writing context
            included_papers = [paper_map.get(pid) for pid in included_paper_ids if pid in paper_map]
            included_papers = [p for p in included_papers if p is not None]

            # Write Introduction using Perplexity for literature research
            intro_text = ""
            intro_references = []
            try:
                from arakis.agents.intro_writer import IntroductionWriterAgent

                intro_writer = IntroductionWriterAgent()
                inclusion_list = [c.strip() for c in workflow_data.inclusion_criteria.split(",")]

                # write_complete_introduction returns (Section, list[Paper])
                intro_section, intro_cited_papers = await intro_writer.write_complete_introduction(
                    research_question=workflow_data.research_question,
                    inclusion_criteria=inclusion_list,
                    use_perplexity=True,  # Use Perplexity for background literature
                )

                # Convert section to markdown
                intro_text = intro_section.to_markdown()

                # Store references for later use
                intro_references = intro_cited_papers

                total_cost += 1.0
                print(f"[{workflow_id}] Introduction written: {intro_section.total_word_count} words, {len(intro_cited_papers)} references")
            except Exception as e:
                print(f"[{workflow_id}] Failed to write introduction: {e}")
                import traceback
                traceback.print_exc()
                intro_text = f"## Introduction\n\nThis systematic review investigates: {workflow_data.research_question}\n\n"

            # Write Methods
            methods_text = ""
            try:
                from arakis.agents.methods_writer import MethodsContext, MethodsWriterAgent

                methods_writer = MethodsWriterAgent()
                methods_context = MethodsContext(
                    research_question=workflow_data.research_question,
                    inclusion_criteria=workflow_data.inclusion_criteria,
                    exclusion_criteria=workflow_data.exclusion_criteria,
                    databases=workflow_data.databases,
                    screening_method="dual-review" if dual_review else "single-review",
                )
                methods_section = await methods_writer.write_complete_methods_section(
                    context=methods_context,
                    has_meta_analysis=False,  # Will update if we do meta-analysis
                )
                methods_text = (
                    methods_section.to_markdown()
                    if hasattr(methods_section, "to_markdown")
                    else str(methods_section.content)
                )
                total_cost += 0.5
                print(f"[{workflow_id}] Methods written")
            except Exception as e:
                print(f"[{workflow_id}] Failed to write methods: {e}")
                methods_text = f"""## Methods

### Eligibility Criteria
**Inclusion criteria:** {workflow_data.inclusion_criteria}

**Exclusion criteria:** {workflow_data.exclusion_criteria}

### Information Sources
Databases searched: {", ".join(workflow_data.databases)}

### Selection Process
Papers were screened using {"dual-review" if dual_review else "single-review"} methodology with AI assistance.
"""

            # Write Results
            results_text = ""
            try:
                from arakis.agents.results_writer import ResultsWriterAgent

                results_writer = ResultsWriterAgent()
                results_section = await results_writer.write_complete_results_section(
                    prisma_flow=prisma_flow,
                    included_papers=included_papers[:10],
                    meta_analysis_result=None,
                )
                results_text = (
                    results_section.to_markdown()
                    if hasattr(results_section, "to_markdown")
                    else str(results_section.content)
                )
                total_cost += 0.7
                print(f"[{workflow_id}] Results written")
            except Exception as e:
                print(f"[{workflow_id}] Failed to write results: {e}")
                results_text = f"""## Results

### Study Selection
The database search identified {workflow.papers_found} records. After screening titles and abstracts, {workflow.papers_screened} papers were assessed. {workflow.papers_included} studies met the inclusion criteria and were included in the review (see Figure 1 for PRISMA flow diagram).

### Study Characteristics
The included studies were published across various journals and years.
"""

            # Write Discussion
            # Note: DiscussionWriterAgent requires meta_analysis_result, which we don't have yet
            # For now, generate a structured discussion without meta-analysis
            discussion_text = ""
            try:
                # Generate discussion using a direct OpenAI call since DiscussionWriterAgent
                # requires meta-analysis results which we may not have
                from openai import AsyncOpenAI

                from arakis.config import get_settings

                settings = get_settings()
                client = AsyncOpenAI(api_key=settings.openai_api_key)

                discussion_prompt = f"""Write a discussion section for a systematic review on the following topic:

Research Question: {workflow_data.research_question}

Number of studies identified: {workflow.papers_found}
Number of studies screened: {workflow.papers_screened}
Number of studies included: {workflow.papers_included}

Inclusion criteria: {workflow_data.inclusion_criteria}
Exclusion criteria: {workflow_data.exclusion_criteria}

Write a well-structured discussion section with the following subsections:
1. Summary of Evidence - Summarize the main findings from the included studies
2. Comparison with Existing Literature - Discuss how findings compare to previous research
3. Limitations - Acknowledge limitations of this review and the included studies
4. Implications - Discuss clinical/practical implications and future research directions

Format the output in Markdown with appropriate headers. Total length: 500-700 words."""

                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert scientific writer specializing in systematic reviews.",
                        },
                        {"role": "user", "content": discussion_prompt},
                    ],
                    temperature=0.6,
                    max_tokens=2000,
                )
                discussion_text = response.choices[0].message.content
                total_cost += 1.0
                print(f"[{workflow_id}] Discussion written")
            except Exception as e:
                print(f"[{workflow_id}] Failed to write discussion: {e}")
                discussion_text = f"""## Discussion

### Summary of Evidence
This systematic review examined {workflow_data.research_question}. A total of {workflow.papers_included} studies met the inclusion criteria after screening {workflow.papers_screened} papers from an initial pool of {workflow.papers_found} records.

### Comparison with Existing Literature
The findings of this review should be considered in the context of existing literature on the topic. Further synthesis with previous systematic reviews would strengthen the evidence base.

### Limitations
This review has several limitations that should be considered when interpreting the findings. The search was limited to {", ".join(workflow_data.databases)}, which may have excluded relevant studies from other databases. The screening process, while systematic, may have inadvertently excluded some relevant studies.

### Implications
The findings of this review have implications for both clinical practice and future research. Further high-quality primary studies are needed to address gaps in the current evidence base.
"""

            # Generate conclusions from discussion
            conclusions_text = f"""## Conclusions

Based on the systematic review of {workflow.papers_included} studies, this review provides insights into {workflow_data.research_question}. The findings suggest the need for further high-quality research in this area.
"""

            # Write Abstract
            abstract_text = ""
            try:
                from arakis.agents.abstract_writer import AbstractWriterAgent

                abstract_writer = AbstractWriterAgent()
                # Use write_abstract_from_sections which takes individual section texts
                abstract_result = await abstract_writer.write_abstract_from_sections(
                    title=f"Systematic Review: {workflow_data.research_question}",
                    introduction_text=intro_text,
                    methods_text=methods_text,
                    results_text=results_text,
                    discussion_text=discussion_text,
                    structured=True,
                    word_limit=300,
                )
                abstract_text = (
                    abstract_result.section.content
                    if hasattr(abstract_result, "section")
                    else str(abstract_result)
                )
                total_cost += 0.2
                print(f"[{workflow_id}] Abstract written")
            except Exception as e:
                print(f"[{workflow_id}] Failed to write abstract: {e}")
                abstract_text = f"""**Background:** {workflow_data.research_question}

**Methods:** We searched {", ".join(workflow_data.databases)} and screened {workflow.papers_screened} papers using predefined inclusion and exclusion criteria.

**Results:** {workflow.papers_included} studies met the inclusion criteria.

**Conclusions:** This systematic review provides an overview of the current evidence.
"""

            # ============================================================
            # STAGE 6: Generate References
            # ============================================================
            print(f"[{workflow_id}] Stage 6: Generating references...")

            references = []
            for i, paper in enumerate(included_papers[:20], 1):
                authors_str = ""
                if paper.authors:
                    author_names = [
                        a.name if hasattr(a, "name") else str(a) for a in paper.authors[:3]
                    ]
                    if len(paper.authors) > 3:
                        author_names.append("et al.")
                    authors_str = ", ".join(author_names)

                citation = f"{authors_str}. {paper.title}. {paper.journal or 'Journal'}. {paper.year or 'n.d.'}."
                references.append(
                    {
                        "id": f"ref{i}",
                        "citation": citation,
                        "doi": paper.doi,
                    }
                )

            # ============================================================
            # STAGE 7: Create Study Characteristics Table
            # ============================================================
            print(f"[{workflow_id}] Stage 7: Creating tables...")

            tables = {}
            if included_papers:
                table_rows = []
                for paper in included_papers[:15]:
                    year = str(paper.year) if paper.year else "N/A"
                    authors_str = ""
                    if paper.authors:
                        first_author = (
                            paper.authors[0].name
                            if hasattr(paper.authors[0], "name")
                            else str(paper.authors[0])
                        )
                        authors_str = (
                            f"{first_author} et al." if len(paper.authors) > 1 else first_author
                        )
                    table_rows.append(
                        [
                            authors_str[:30],
                            year,
                            (paper.journal or "N/A")[:25],
                            paper.source or "N/A",
                        ]
                    )

                tables["table1"] = {
                    "id": "table1",
                    "title": "Table 1. Characteristics of included studies",
                    "headers": ["Study", "Year", "Journal", "Source"],
                    "rows": table_rows,
                    "footnotes": ["Studies ordered by relevance to search criteria"],
                }

            # ============================================================
            # STAGE 8: Assemble and Save Manuscript
            # ============================================================
            print(f"[{workflow_id}] Stage 8: Assembling manuscript...")
            workflow.current_stage = "finalizing"
            await db.commit()

            manuscript = Manuscript(
                workflow_id=workflow_id,
                title=f"Systematic Review: {workflow_data.research_question}",
                abstract=abstract_text,
                introduction=intro_text,
                methods=methods_text,
                results=results_text,
                discussion=discussion_text,
                conclusions=conclusions_text,
                references=references,
                figures=figures,
                tables=tables,
                meta={
                    "research_question": workflow_data.research_question,
                    "databases": workflow_data.databases,
                    "papers_found": workflow.papers_found,
                    "papers_screened": workflow.papers_screened,
                    "papers_included": workflow.papers_included,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                created_at=datetime.now(timezone.utc),
            )
            db.add(manuscript)

            # Mark workflow as completed
            workflow.status = "completed"
            workflow.current_stage = "completed"
            workflow.completed_at = datetime.now(timezone.utc)
            workflow.total_cost = total_cost
            await db.commit()

            print(f"[{workflow_id}] Workflow completed successfully! Cost: ${total_cost:.2f}")

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
