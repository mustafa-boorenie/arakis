"""Workflow Orchestrator - coordinates 12-stage systematic review workflow.

Manages:
- Stage execution order
- Checkpoint saving/loading
- Retry logic with user prompts
- Stage re-runs
- Resume from any point
- Cost mode configuration
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arakis.config import get_mode_config, ModeConfig, get_default_mode_config
from arakis.database.models import Workflow, WorkflowStageCheckpoint
from arakis.workflow.stages import (
    BaseStageExecutor,
    StageResult,
    SearchStageExecutor,
    ScreenStageExecutor,
    PDFFetchStageExecutor,
    ExtractStageExecutor,
    RiskOfBiasStageExecutor,
    AnalysisStageExecutor,
    PRISMAStageExecutor,
    TablesStageExecutor,
    IntroductionStageExecutor,
    MethodsStageExecutor,
    ResultsStageExecutor,
    DiscussionStageExecutor,
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates the 12-stage systematic review workflow.

    Stages in order:
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
    """

    # Stage order - defines the execution sequence
    STAGE_ORDER = [
        "search",
        "screen",
        "pdf_fetch",
        "extract",
        "rob",
        "analysis",
        "prisma",
        "tables",
        "introduction",
        "methods",
        "results",
        "discussion",
    ]

    # Mapping of stage names to executor classes
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

    def __init__(self, db: AsyncSession):
        """Initialize the orchestrator.

        Args:
            db: Async database session
        """
        self.db = db

    async def execute_workflow(
        self,
        workflow_id: str,
        initial_data: dict[str, Any],
        start_from: Optional[str] = None,
        skip_stages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Execute the complete workflow or resume from a stage.

        Args:
            workflow_id: The workflow ID
            initial_data: Initial input data (research question, criteria, etc.)
            start_from: Stage to start from (None = beginning)
            skip_stages: List of stages to skip (in addition to mode-based skips)

        Returns:
            Dict with workflow results and status
        """
        skip_stages = skip_stages or []

        # Load workflow to get cost_mode
        workflow = await self._get_workflow(workflow_id)
        mode_config = get_mode_config(workflow.cost_mode)
        
        logger.info(
            f"[orchestrator] Workflow {workflow_id} using cost mode: {mode_config.name}"
        )

        # Determine starting index
        start_index = 0
        if start_from:
            if start_from not in self.STAGE_ORDER:
                raise ValueError(f"Invalid stage: {start_from}")
            start_index = self.STAGE_ORDER.index(start_from)

        logger.info(
            f"[orchestrator] Starting workflow {workflow_id} from stage "
            f"'{self.STAGE_ORDER[start_index]}'"
        )

        # Add mode-based stage skips
        if mode_config.skip_rob and "rob" not in skip_stages:
            skip_stages.append("rob")
            logger.info("[orchestrator] Skipping RoB stage (mode config)")
        if mode_config.skip_analysis and "analysis" not in skip_stages:
            skip_stages.append("analysis")
            logger.info("[orchestrator] Skipping Analysis stage (mode config)")

        # Initialize input data with initial data
        accumulated_data = dict(initial_data)

        # Load any existing checkpoint data
        existing_data = await self._load_checkpoint_data(workflow_id, start_index)
        accumulated_data.update(existing_data)

        # Execute stages in order
        for stage in self.STAGE_ORDER[start_index:]:
            if stage in skip_stages:
                logger.info(f"[orchestrator] Skipping stage: {stage}")
                await self._mark_stage_status(workflow_id, stage, "skipped")
                continue

            logger.info(f"[orchestrator] Executing stage: {stage}")

            # Get or create executor with mode config
            executor = self._get_executor(workflow_id, stage, mode_config)

            # Run stage with retry
            result = await executor.run_with_retry(accumulated_data)

            # Save checkpoint
            await self._save_checkpoint(workflow_id, stage, result)

            # Check result
            if not result.success:
                logger.error(f"[orchestrator] Stage {stage} failed: {result.error}")

                if result.needs_user_action:
                    # Pause workflow for user action
                    await self._set_needs_user_action(
                        workflow_id, result.action_required or "Stage failed, please review"
                    )
                    return {
                        "status": "needs_review",
                        "failed_stage": stage,
                        "error": result.error,
                        "action_required": result.action_required,
                        "completed_stages": self.STAGE_ORDER[start_index:self.STAGE_ORDER.index(stage)],
                    }
                else:
                    # Hard failure
                    await self._update_workflow_status(workflow_id, "failed")
                    return {
                        "status": "failed",
                        "failed_stage": stage,
                        "error": result.error,
                    }

            # Accumulate output data for next stage
            # Store under stage name to avoid key collisions between stages
            accumulated_data[stage] = result.output_data
            # Also merge top-level keys that downstream stages might need
            for key, value in result.output_data.items():
                if key not in accumulated_data:
                    accumulated_data[key] = value

            # Update total cost
            await self._update_workflow_cost(workflow_id, result.cost)

        # All stages complete - assemble manuscript
        await self._assemble_manuscript(workflow_id, accumulated_data)
        await self._update_workflow_status(workflow_id, "completed")

        logger.info(f"[orchestrator] Workflow {workflow_id} completed successfully")

        return {
            "status": "completed",
            "data": accumulated_data,
        }

    async def rerun_stage(
        self,
        workflow_id: str,
        stage: str,
        input_override: Optional[dict[str, Any]] = None,
    ) -> StageResult:
        """Re-run a specific stage.

        Args:
            workflow_id: The workflow ID
            stage: Stage to re-run
            input_override: Optional data to override previous checkpoint

        Returns:
            StageResult from the stage execution
        """
        if stage not in self.STAGE_ORDER:
            raise ValueError(f"Invalid stage: {stage}")

        logger.info(f"[orchestrator] Re-running stage {stage} for workflow {workflow_id}")

        # Validate dependencies are met
        stage_index = self.STAGE_ORDER.index(stage)
        if stage_index > 0:
            required_stages = self.STAGE_ORDER[:stage_index]
            for req_stage in required_stages:
                checkpoint = await self._get_checkpoint(workflow_id, req_stage)
                if not checkpoint or checkpoint.status not in ("completed", "skipped"):
                    raise ValueError(
                        f"Cannot re-run {stage}: required stage {req_stage} "
                        f"is not completed"
                    )

        # Load input data from previous stages
        input_data = await self._load_checkpoint_data(workflow_id, stage_index)

        # Apply any overrides
        if input_override:
            input_data.update(input_override)

        # Get executor and run
        executor = self._get_executor(workflow_id, stage)
        result = await executor.run_with_retry(input_data)

        # Save new checkpoint
        await self._save_checkpoint(workflow_id, stage, result)

        return result

    async def resume_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Resume a paused workflow from the last incomplete stage.

        Args:
            workflow_id: The workflow ID

        Returns:
            Workflow execution result
        """
        # Clear user action flag
        await self._clear_user_action(workflow_id)

        # Find last incomplete stage
        last_stage = await self._find_resume_point(workflow_id)

        if not last_stage:
            logger.info(f"[orchestrator] Workflow {workflow_id} already completed")
            return {"status": "already_completed"}

        # Load initial data
        workflow = await self._get_workflow(workflow_id)
        initial_data = {
            "research_question": workflow.research_question,
            "inclusion_criteria": workflow.inclusion_criteria or [],
            "exclusion_criteria": workflow.exclusion_criteria or [],
            "databases": workflow.databases or ["pubmed"],
        }

        return await self.execute_workflow(
            workflow_id, initial_data, start_from=last_stage
        )

    async def get_stage_status(self, workflow_id: str) -> list[dict]:
        """Get status of all stages for a workflow.

        Args:
            workflow_id: The workflow ID

        Returns:
            List of stage status dicts
        """
        stages = []

        for stage in self.STAGE_ORDER:
            checkpoint = await self._get_checkpoint(workflow_id, stage)

            if checkpoint:
                stages.append({
                    "stage": stage,
                    "status": checkpoint.status,
                    "started_at": checkpoint.started_at.isoformat() if checkpoint.started_at else None,
                    "completed_at": checkpoint.completed_at.isoformat() if checkpoint.completed_at else None,
                    "retry_count": checkpoint.retry_count,
                    "error_message": checkpoint.error_message,
                    "cost": checkpoint.cost,
                })
            else:
                stages.append({
                    "stage": stage,
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "retry_count": 0,
                    "error_message": None,
                    "cost": 0.0,
                })

        return stages

    def _get_executor(
        self, workflow_id: str, stage: str, mode_config: ModeConfig
    ) -> BaseStageExecutor:
        """Get the executor for a stage.
        
        Args:
            workflow_id: The workflow ID
            stage: Stage name
            mode_config: Cost mode configuration
            
        Returns:
            Stage executor instance
        """
        executor_class = self.STAGE_EXECUTORS.get(stage)
        if not executor_class:
            raise ValueError(f"No executor found for stage: {stage}")
        return executor_class(workflow_id, self.db, mode_config)

    async def _get_workflow(self, workflow_id: str) -> Workflow:
        """Get workflow from database."""
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return workflow

    async def _get_checkpoint(
        self, workflow_id: str, stage: str
    ) -> Optional[WorkflowStageCheckpoint]:
        """Get checkpoint for a stage."""
        result = await self.db.execute(
            select(WorkflowStageCheckpoint).where(
                WorkflowStageCheckpoint.workflow_id == workflow_id,
                WorkflowStageCheckpoint.stage == stage,
            )
        )
        return result.scalar_one_or_none()

    async def _save_checkpoint(
        self, workflow_id: str, stage: str, result: StageResult
    ) -> None:
        """Save or update a stage checkpoint."""
        checkpoint = await self._get_checkpoint(workflow_id, stage)

        if checkpoint:
            # Update existing
            checkpoint.status = "completed" if result.success else "failed"
            checkpoint.completed_at = datetime.now(timezone.utc)
            checkpoint.output_data = result.output_data
            checkpoint.error_message = result.error
            checkpoint.cost = result.cost
        else:
            # Create new
            checkpoint = WorkflowStageCheckpoint(
                workflow_id=workflow_id,
                stage=stage,
                status="completed" if result.success else "failed",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                output_data=result.output_data,
                error_message=result.error,
                cost=result.cost,
            )
            self.db.add(checkpoint)

        await self.db.commit()

    async def _mark_stage_status(
        self, workflow_id: str, stage: str, status: str
    ) -> None:
        """Mark a stage with a specific status."""
        checkpoint = await self._get_checkpoint(workflow_id, stage)

        if checkpoint:
            checkpoint.status = status
            checkpoint.completed_at = datetime.now(timezone.utc)
        else:
            checkpoint = WorkflowStageCheckpoint(
                workflow_id=workflow_id,
                stage=stage,
                status=status,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            self.db.add(checkpoint)

        await self.db.commit()

    async def _load_checkpoint_data(
        self, workflow_id: str, up_to_index: int
    ) -> dict[str, Any]:
        """Load accumulated data from completed checkpoints."""
        accumulated = {}

        for stage in self.STAGE_ORDER[:up_to_index]:
            checkpoint = await self._get_checkpoint(workflow_id, stage)
            if checkpoint and checkpoint.status == "completed" and checkpoint.output_data:
                # Store under stage name and also merge unique top-level keys
                accumulated[stage] = checkpoint.output_data
                for key, value in checkpoint.output_data.items():
                    if key not in accumulated:
                        accumulated[key] = value

        return accumulated

    async def _find_resume_point(self, workflow_id: str) -> Optional[str]:
        """Find the stage to resume from."""
        for stage in self.STAGE_ORDER:
            checkpoint = await self._get_checkpoint(workflow_id, stage)
            if not checkpoint or checkpoint.status not in ("completed", "skipped"):
                return stage
        return None  # All stages completed

    async def _update_workflow_status(self, workflow_id: str, status: str) -> None:
        """Update workflow status."""
        workflow = await self._get_workflow(workflow_id)
        workflow.status = status
        if status == "completed":
            workflow.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def _update_workflow_cost(self, workflow_id: str, cost: float) -> None:
        """Add to workflow total cost."""
        workflow = await self._get_workflow(workflow_id)
        current_cost = workflow.total_cost or 0.0
        workflow.total_cost = current_cost + cost
        await self.db.commit()

    async def _set_needs_user_action(
        self, workflow_id: str, action_required: str
    ) -> None:
        """Set workflow as needing user action."""
        workflow = await self._get_workflow(workflow_id)
        workflow.status = "needs_review"
        workflow.needs_user_action = True
        workflow.action_required = action_required
        await self.db.commit()

    async def _clear_user_action(self, workflow_id: str) -> None:
        """Clear user action flag."""
        workflow = await self._get_workflow(workflow_id)
        workflow.needs_user_action = False
        workflow.action_required = None
        await self.db.commit()

    async def _assemble_manuscript(
        self, workflow_id: str, accumulated_data: dict[str, Any]
    ) -> None:
        """Assemble final manuscript from all stage outputs.

        Args:
            workflow_id: The workflow ID
            accumulated_data: Data accumulated from all stages
        """
        from arakis.database.models import Manuscript

        workflow = await self._get_workflow(workflow_id)

        # Extract manuscript sections from stage outputs
        intro_data = accumulated_data.get("introduction", {})
        methods_data = accumulated_data.get("methods", {})
        results_data = accumulated_data.get("results", {})
        discussion_data = accumulated_data.get("discussion", {})

        # Get abstract from results stage or generate simple one
        abstract = accumulated_data.get("abstract", "")
        if not abstract:
            abstract = (
                f"**Background:** This systematic review examines {workflow.research_question}.\n\n"
                f"**Methods:** We searched {', '.join(workflow.databases or ['PubMed'])} "
                f"and screened {workflow.papers_screened or 0} papers.\n\n"
                f"**Results:** {workflow.papers_included or 0} studies met inclusion criteria.\n\n"
                f"**Conclusions:** See full text for detailed findings."
            )

        # Get figures and tables
        figures_data = accumulated_data.get("figures", {})
        tables_data = accumulated_data.get("tables", {})
        references_data = accumulated_data.get("references", [])

        # Build conclusions
        conclusions = accumulated_data.get("conclusions", "")
        if not conclusions:
            conclusions = (
                f"## Conclusions\n\n"
                f"This systematic review of {workflow.papers_included or 0} studies provides "
                f"insights into {workflow.research_question}. "
                f"The findings suggest the need for further research in this area."
            )

        # Create manuscript record
        manuscript = Manuscript(
            workflow_id=workflow_id,
            title=f"Systematic Review: {workflow.research_question}",
            abstract=abstract,
            introduction=intro_data.get("markdown", "") or intro_data.get("content", ""),
            methods=methods_data.get("markdown", "") or methods_data.get("content", ""),
            results=results_data.get("markdown", "") or results_data.get("content", ""),
            discussion=discussion_data.get("markdown", "") or discussion_data.get("content", ""),
            conclusions=conclusions,
            references=references_data,
            figures=figures_data,
            tables=tables_data,
            meta={
                "research_question": workflow.research_question,
                "databases": workflow.databases,
                "papers_found": workflow.papers_found,
                "papers_screened": workflow.papers_screened,
                "papers_included": workflow.papers_included,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(manuscript)
        await self.db.commit()

        logger.info(f"[orchestrator] Assembled manuscript for workflow {workflow_id}")
