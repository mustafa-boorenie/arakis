"""LLM-powered statistical analysis recommender.

Analyzes extracted data and recommends appropriate statistical tests.
"""

import json
from typing import Any

from openai import AsyncOpenAI

from arakis.config import get_settings
from arakis.models.analysis import (
    AnalysisRecommendation,
    EffectMeasure,
    StatisticalTest,
    TestType,
)
from arakis.models.extraction import ExtractionResult
from arakis.utils import get_openai_rate_limiter, retry_with_exponential_backoff


class AnalysisRecommenderAgent:
    """LLM agent that recommends appropriate statistical tests."""

    def __init__(
        self, model: str = "gpt-4o", temperature: float = 0.3, max_tokens: int = 4000
    ):
        """Initialize the analysis recommender agent.

        Args:
            model: OpenAI model to use
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens in response
        """
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.rate_limiter = get_openai_rate_limiter()

    @retry_with_exponential_backoff(max_retries=8, initial_delay=2.0, max_delay=90.0, use_rate_limiter=True)
    async def _call_openai(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        tool_choice: dict[str, Any] | str = "auto",
        temperature: float | None = None,
    ):
        """Call OpenAI API with retry logic.

        Args:
            messages: Chat messages
            tools: Tool definitions
            tool_choice: Tool choice strategy
            temperature: Override default temperature

        Returns:
            OpenAI completion response
        """
        await self.rate_limiter.wait()

        return await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=self.max_tokens,
        )

    def _get_system_prompt(self) -> str:
        """Get system prompt for the recommender agent."""
        return """You are a statistical analysis expert helping researchers choose appropriate statistical tests for systematic reviews and meta-analyses.

Your task is to analyze the extracted data from research papers and recommend:
1. Appropriate statistical tests based on data characteristics
2. Whether meta-analysis is feasible and which method to use
3. Assumptions that need to be checked
4. Potential issues or warnings

Consider these factors:
- **Data type**: Continuous, binary/dichotomous, categorical, time-to-event
- **Study design**: RCT, cohort, case-control, cross-sectional
- **Number of studies**: Meta-analysis requires ≥2 studies, ideally ≥5
- **Sample sizes**: Small samples may require non-parametric tests
- **Outcome measures**: Mean difference, standardized mean difference, odds ratio, risk ratio
- **Heterogeneity expectations**: Clinical and methodological diversity
- **Data completeness**: Missing statistics may prevent meta-analysis

**Statistical Test Guidelines:**

For **continuous outcomes**:
- Independent groups (2 groups): t-test (if normal) or Mann-Whitney U (if non-normal/small n)
- Independent groups (≥3 groups): One-way ANOVA (if normal) or Kruskal-Wallis (if non-normal)
- Paired/matched data: Paired t-test (if normal) or Wilcoxon signed-rank (if non-normal)
- Meta-analysis: Mean difference or standardized mean difference

For **binary/dichotomous outcomes**:
- 2x2 contingency tables: Chi-square test or Fisher's exact test (if expected frequencies <5)
- Meta-analysis: Odds ratio, risk ratio, or risk difference

For **categorical outcomes** (>2 categories):
- Chi-square test of independence
- Consider collapsing categories if frequencies are low

For **meta-analysis**:
- ≥2 studies required (≥5 preferred for reliable heterogeneity assessment)
- Fixed-effects: Use when I² < 25% (low heterogeneity)
- Random-effects: Use when I² ≥ 25% or clinical heterogeneity expected
- Assess publication bias if ≥10 studies

**Assumptions to check:**
- Normality (Shapiro-Wilk test for n<50, Q-Q plots)
- Equal variances (Levene's test)
- Independence of observations
- Adequate sample size for parametric tests

Be conservative and prioritize robustness over statistical power."""

    def _get_recommendation_tool(self) -> dict[str, Any]:
        """Get tool definition for statistical test recommendation."""
        return {
            "type": "function",
            "function": {
                "name": "recommend_statistical_tests",
                "description": "Recommend appropriate statistical tests based on extracted data characteristics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recommended_tests": {
                            "type": "array",
                            "description": "List of recommended statistical tests",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "test_name": {
                                        "type": "string",
                                        "description": "Name of the statistical test (e.g., 'independent_t_test', 'mann_whitney_u', 'random_effects_meta_analysis')",
                                    },
                                    "test_type": {
                                        "type": "string",
                                        "enum": ["parametric", "non_parametric", "meta_analysis", "descriptive"],
                                        "description": "Type of statistical test",
                                    },
                                    "effect_measure": {
                                        "type": "string",
                                        "enum": [
                                            "mean_difference",
                                            "standardized_mean_difference",
                                            "odds_ratio",
                                            "risk_ratio",
                                            "risk_difference",
                                            "correlation",
                                        ],
                                        "description": "Effect measure for meta-analysis (if applicable)",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Brief explanation of when and why to use this test",
                                    },
                                    "priority": {
                                        "type": "string",
                                        "enum": ["primary", "secondary", "sensitivity"],
                                        "description": "Priority level of this test",
                                    },
                                },
                                "required": ["test_name", "test_type", "description", "priority"],
                            },
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Overall rationale for the recommendations, explaining the choice of tests based on data characteristics",
                        },
                        "data_characteristics": {
                            "type": "object",
                            "description": "Summary of key data characteristics that influenced recommendations",
                            "properties": {
                                "outcome_type": {
                                    "type": "string",
                                    "description": "Type of outcome (continuous, binary, categorical)",
                                },
                                "study_design": {
                                    "type": "string",
                                    "description": "Predominant study design",
                                },
                                "number_of_studies": {
                                    "type": "integer",
                                    "description": "Number of studies available for analysis",
                                },
                                "sample_size_range": {
                                    "type": "string",
                                    "description": "Range of sample sizes (e.g., '50-200')",
                                },
                                "meta_analysis_feasible": {
                                    "type": "boolean",
                                    "description": "Whether meta-analysis is feasible with available data",
                                },
                            },
                        },
                        "assumptions_to_check": {
                            "type": "array",
                            "description": "Statistical assumptions that should be checked before running tests",
                            "items": {"type": "string"},
                        },
                        "warnings": {
                            "type": "array",
                            "description": "Warnings about potential issues or limitations",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "recommended_tests",
                        "rationale",
                        "data_characteristics",
                        "assumptions_to_check",
                        "warnings",
                    ],
                },
            },
        }

    async def recommend_tests(
        self, extraction_result: ExtractionResult, outcome_of_interest: str | None = None
    ) -> AnalysisRecommendation:
        """Recommend statistical tests based on extracted data.

        Args:
            extraction_result: Result from data extraction
            outcome_of_interest: Specific outcome to analyze (optional)

        Returns:
            AnalysisRecommendation with suggested tests and rationale
        """
        # Prepare data summary for LLM
        data_summary = self._prepare_data_summary(extraction_result, outcome_of_interest)

        # Create prompt
        user_message = f"""Analyze the following extracted data from a systematic review and recommend appropriate statistical tests.

**Extraction Summary:**
{json.dumps(data_summary, indent=2)}

**Outcome of interest:** {outcome_of_interest or 'All available outcomes'}

Please recommend:
1. Primary statistical test(s) for analyzing the main outcome
2. Secondary tests for supporting analyses
3. Sensitivity analyses if applicable
4. Whether meta-analysis is feasible and which method to use

Consider the data type, study designs, sample sizes, and number of studies available."""

        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": user_message},
        ]

        # Call OpenAI with tool
        tools = [self._get_recommendation_tool()]
        response = await self._call_openai(messages, tools, tool_choice="auto")

        # Parse response
        recommendation = self._parse_recommendation_response(response)

        return recommendation

    def _prepare_data_summary(
        self, extraction_result: ExtractionResult, outcome_of_interest: str | None
    ) -> dict[str, Any]:
        """Prepare a summary of extracted data for the LLM.

        Args:
            extraction_result: Result from data extraction
            outcome_of_interest: Specific outcome to analyze

        Returns:
            Dictionary summarizing the data characteristics
        """
        papers = extraction_result.papers

        # Collect study designs
        study_designs = [p.data.get("study_design") for p in papers if "study_design" in p.data]

        # Collect sample sizes
        sample_sizes = []
        for p in papers:
            if "sample_size_total" in p.data and p.data["sample_size_total"]:
                sample_sizes.append(p.data["sample_size_total"])

        # Collect outcomes
        outcomes = []
        for p in papers:
            if "primary_outcome" in p.data and p.data["primary_outcome"]:
                outcomes.append(p.data["primary_outcome"])

        # Check for available statistics
        has_means = any(
            "intervention_mean" in p.data or "control_mean" in p.data for p in papers
        )
        has_events = any(
            "intervention_events" in p.data or "control_events" in p.data for p in papers
        )
        has_effect_sizes = any(
            "primary_outcome_result" in p.data and p.data["primary_outcome_result"]
            for p in papers
        )

        return {
            "number_of_studies": len(papers),
            "study_designs": study_designs,
            "sample_sizes": sample_sizes,
            "sample_size_range": f"{min(sample_sizes)}-{max(sample_sizes)}"
            if sample_sizes
            else "Unknown",
            "outcomes": outcomes[:5],  # First 5 outcomes
            "outcome_of_interest": outcome_of_interest,
            "available_statistics": {
                "has_means_and_sds": has_means,
                "has_event_counts": has_events,
                "has_effect_sizes": has_effect_sizes,
            },
            "average_confidence": extraction_result.average_confidence,
            "average_quality": extraction_result.average_quality,
        }

    def _parse_recommendation_response(self, response) -> AnalysisRecommendation:
        """Parse OpenAI response into AnalysisRecommendation.

        Args:
            response: OpenAI completion response

        Returns:
            AnalysisRecommendation object
        """
        # Extract tool call
        message = response.choices[0].message

        if not message.tool_calls:
            # Fallback: basic recommendation
            return AnalysisRecommendation(
                recommended_tests=[
                    StatisticalTest(
                        test_name="descriptive_statistics",
                        test_type=TestType.DESCRIPTIVE,
                        description="Calculate basic descriptive statistics",
                    )
                ],
                rationale="Unable to parse recommendation from LLM response",
                warnings=["LLM did not provide structured recommendation"],
            )

        # Parse tool call arguments
        tool_call = message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)

        # Build StatisticalTest objects
        recommended_tests = []
        for test_data in args["recommended_tests"]:
            test = StatisticalTest(
                test_name=test_data["test_name"],
                test_type=TestType(test_data["test_type"]),
                description=test_data.get("description", ""),
                parameters={
                    "priority": test_data.get("priority", "primary"),
                    "effect_measure": test_data.get("effect_measure"),
                },
            )
            recommended_tests.append(test)

        return AnalysisRecommendation(
            recommended_tests=recommended_tests,
            rationale=args["rationale"],
            data_characteristics=args["data_characteristics"],
            assumptions_checked=args["assumptions_to_check"],
            warnings=args["warnings"],
        )
