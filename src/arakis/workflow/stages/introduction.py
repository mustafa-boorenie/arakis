"""Introduction stage executor - generates introduction section.

Generates:
- Background subsection
- Rationale subsection
- Objectives subsection

Uses OpenAI Responses API with web search for background literature.
Uses o3/o3-pro extended thinking models for high-quality writing.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from arakis.agents.intro_writer import IntroductionWriterAgent
from arakis.workflow.stages.base import BaseStageExecutor, StageResult

logger = logging.getLogger(__name__)


class IntroductionStageExecutor(BaseStageExecutor):
    """Generate introduction section of the manuscript.

    Creates:
    1. Background (broad context → specific problem)
    2. Rationale (gaps in literature, justification)
    3. Objectives (clear, specific aims)

    Uses OpenAI's Responses API with web search for background literature.
    Uses o3/o3-pro extended thinking models for high-quality writing.
    """

    STAGE_NAME = "introduction"

    def __init__(self, workflow_id: str, db: AsyncSession):
        super().__init__(workflow_id, db)
        self.writer = IntroductionWriterAgent()

    def get_required_stages(self) -> list[str]:
        """Introduction can be written early in the workflow."""
        return ["search"]

    async def execute(self, input_data: dict[str, Any]) -> StageResult:
        """Execute introduction writing.

        Args:
            input_data: Should contain:
                - research_question: str
                - inclusion_criteria: list[str]
                - use_web_search: bool (default True) - uses OpenAI web search
                - use_perplexity: bool (deprecated, use use_web_search)
                - literature: list[dict] (optional, for fallback mode)

        Returns:
            StageResult with introduction section
        """
        research_question = input_data.get("research_question", "")
        inclusion_criteria = input_data.get("inclusion_criteria", [])
        # Support both new and deprecated parameter names
        use_web_search = input_data.get("use_web_search", input_data.get("use_perplexity", True))
        literature = input_data.get("literature", [])

        if not research_question:
            return StageResult(
                success=False,
                error="Research question is required for introduction",
            )

        logger.info(
            f"[introduction] Writing introduction for: {research_question[:50]}..."
        )

        # Update workflow stage
        await self.update_workflow_stage("introduction")
        await self.save_checkpoint("in_progress")

        try:
            # Write introduction section
            section, cited_papers = await self.writer.write_complete_introduction(
                research_question=research_question,
                inclusion_criteria=inclusion_criteria,
                use_web_search=use_web_search,
                literature_context=literature,
            )

            # Build output data
            output_data = {
                "title": section.title,
                "content": section.content,
                "subsections": [
                    {
                        "title": sub.title,
                        "content": sub.content,
                    }
                    for sub in section.subsections
                ],
                "word_count": section.total_word_count,
                "citations": section.citations,
                "cited_papers": [
                    {
                        "id": p.best_identifier,
                        "title": p.title,
                        "authors": [a.name for a in (p.authors or [])],
                        "year": p.year,
                        "doi": p.doi,
                    }
                    for p in cited_papers
                ],
            }

            # Generate markdown version
            output_data["markdown"] = section.to_markdown()

            logger.info(
                f"[introduction] Completed: {section.total_word_count} words, "
                f"{len(cited_papers)} citations"
            )

            return StageResult(
                success=True,
                output_data=output_data,
                cost=1.0,  # Estimated LLM cost
            )

        except Exception as e:
            logger.exception(f"[introduction] Writing failed: {e}")
            return StageResult(
                success=False,
                error=str(e),
            )
