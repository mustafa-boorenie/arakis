"""Stage executors for the unified workflow system.

Each stage executor handles a specific phase of the systematic review workflow:
1. Search - Multi-database literature search
2. Screen - AI-powered paper screening (NO 50-paper limit)
3. PDF Fetch - Download PDFs and extract text
4. Extract - Structured data extraction from papers
5. RoB - Risk of Bias assessment (auto-detect tool)
6. Analysis - Meta-analysis with forest/funnel plots
7. PRISMA - Flow diagram generation
8. Tables - Generate all 3 tables (characteristics, RoB, GRADE)
9. Introduction - Write introduction section
10. Methods - Write methods section
11. Results - Write results section
12. Discussion - Write discussion, conclusions, abstract
"""

from arakis.workflow.stages.analysis import AnalysisStageExecutor
from arakis.workflow.stages.base import BaseStageExecutor, StageResult
from arakis.workflow.stages.discussion import DiscussionStageExecutor
from arakis.workflow.stages.extract import ExtractStageExecutor
from arakis.workflow.stages.introduction import IntroductionStageExecutor
from arakis.workflow.stages.methods import MethodsStageExecutor
from arakis.workflow.stages.pdf_fetch import PDFFetchStageExecutor
from arakis.workflow.stages.prisma import PRISMAStageExecutor
from arakis.workflow.stages.results import ResultsStageExecutor
from arakis.workflow.stages.rob import RiskOfBiasStageExecutor
from arakis.workflow.stages.screen import ScreenStageExecutor
from arakis.workflow.stages.search import SearchStageExecutor
from arakis.workflow.stages.tables import TablesStageExecutor

__all__ = [
    "BaseStageExecutor",
    "StageResult",
    "SearchStageExecutor",
    "ScreenStageExecutor",
    "PDFFetchStageExecutor",
    "ExtractStageExecutor",
    "RiskOfBiasStageExecutor",
    "AnalysisStageExecutor",
    "PRISMAStageExecutor",
    "TablesStageExecutor",
    "IntroductionStageExecutor",
    "MethodsStageExecutor",
    "ResultsStageExecutor",
    "DiscussionStageExecutor",
]
