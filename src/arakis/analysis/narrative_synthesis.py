"""Narrative synthesis for systematic reviews when meta-analysis is not feasible.

This module provides tools for qualitative synthesis of study findings
following established narrative synthesis methods.
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from arakis.models.analysis import (
    NarrativeSynthesisResult,
    StudySummary,
    VoteCount,
)
from arakis.models.extraction import ExtractedData, ExtractionResult


@dataclass
class SynthesisConfig:
    """Configuration for narrative synthesis."""

    # Thresholds for effect direction classification
    positive_threshold: float = 0.0  # Effect > threshold is positive
    negative_threshold: float = 0.0  # Effect < -threshold is negative

    # Quality assessment thresholds
    high_quality_threshold: float = 0.8
    moderate_quality_threshold: float = 0.6

    # Output settings
    output_dir: str = "./figures"
    dpi: int = 300


class NarrativeSynthesizer:
    """Performs narrative synthesis of study findings.

    Implements structured narrative synthesis methods including:
    - Vote counting for effect direction
    - Study characteristic tabulation
    - Pattern identification
    - Evidence quality assessment
    - Effect direction visualization
    """

    def __init__(self, config: SynthesisConfig | None = None):
        """Initialize the narrative synthesizer.

        Args:
            config: Configuration for synthesis. Uses defaults if not provided.
        """
        self.config = config or SynthesisConfig()

    def synthesize(
        self,
        extraction_result: ExtractionResult,
        outcome: str | None = None,
        meta_analysis_barriers: list[str] | None = None,
    ) -> NarrativeSynthesisResult:
        """Perform narrative synthesis on extracted data.

        Args:
            extraction_result: Results from data extraction
            outcome: Name of the outcome being analyzed
            meta_analysis_barriers: Reasons why meta-analysis wasn't feasible

        Returns:
            NarrativeSynthesisResult with qualitative synthesis
        """
        start_time = datetime.now(timezone.utc)

        # Create study summaries
        study_summaries = self._create_study_summaries(extraction_result)

        # Perform vote counting
        vote_count = self._perform_vote_counting(study_summaries)

        # Calculate total sample size
        total_sample_size = sum(s.sample_size for s in study_summaries if s.sample_size is not None)

        # Identify patterns and inconsistencies
        patterns = self._identify_patterns(study_summaries)
        inconsistencies = self._identify_inconsistencies(study_summaries, vote_count)

        # Assess evidence quality
        quality_assessment, confidence = self._assess_evidence_quality(study_summaries, vote_count)

        # Identify gaps in evidence
        gaps = self._identify_gaps(extraction_result, study_summaries)

        # Generate summary of findings
        summary = self._generate_summary_of_findings(study_summaries, vote_count, patterns, outcome)

        # Explain heterogeneity
        heterogeneity_explanation = self._explain_heterogeneity(study_summaries, extraction_result)

        # Create subgroups if applicable
        subgroups = self._create_subgroups(extraction_result)

        # Generate visualizations
        effect_chart_path = None
        summary_table_path = None
        if len(study_summaries) >= 2:
            effect_chart_path = self._generate_effect_direction_chart(
                study_summaries, outcome or "primary outcome"
            )

        # Calculate timing
        end_time = datetime.now(timezone.utc)
        analysis_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return NarrativeSynthesisResult(
            outcome_name=outcome or "primary outcome",
            studies_included=len(study_summaries),
            total_sample_size=total_sample_size,
            study_summaries=study_summaries,
            vote_count=vote_count,
            summary_of_findings=summary,
            heterogeneity_explanation=heterogeneity_explanation,
            evidence_quality_assessment=quality_assessment,
            confidence_in_evidence=confidence,
            patterns_identified=patterns,
            inconsistencies=inconsistencies,
            gaps_in_evidence=gaps,
            meta_analysis_barriers=meta_analysis_barriers or [],
            subgroups=subgroups,
            summary_table_path=summary_table_path,
            effect_direction_chart_path=effect_chart_path,
            synthesis_method="narrative",
            timestamp=end_time.isoformat(),
            analysis_time_ms=analysis_time_ms,
        )

    def _create_study_summaries(self, extraction_result: ExtractionResult) -> list[StudySummary]:
        """Create summaries for each study from extraction data."""
        summaries = []

        for paper in extraction_result.papers:
            summary = self._create_single_study_summary(paper)
            summaries.append(summary)

        return summaries

    def _create_single_study_summary(self, paper: ExtractedData) -> StudySummary:
        """Create a summary for a single study."""
        data = paper.data

        # Determine effect direction from available data
        effect_direction = self._determine_effect_direction(data)
        effect_magnitude = self._determine_effect_magnitude(data)

        # Extract key limitations
        limitations = self._extract_limitations(data)

        return StudySummary(
            study_id=paper.paper_id,
            study_name=data.get("study_name", paper.paper_id),
            sample_size=data.get("sample_size_total"),
            study_design=data.get("study_design"),
            population=data.get("population_description", data.get("population")),
            intervention=data.get("intervention_description", data.get("intervention")),
            comparator=data.get(
                "control_description", data.get("comparator", data.get("control_type"))
            ),
            outcome_description=data.get(
                "primary_outcome_description", data.get("primary_outcome")
            ),
            main_finding=data.get("primary_outcome_result", data.get("main_finding")),
            effect_direction=effect_direction,
            effect_magnitude=effect_magnitude,
            quality_score=paper.extraction_quality,
            key_limitations=limitations,
        )

    def _determine_effect_direction(self, data: dict[str, Any]) -> str:
        """Determine the direction of effect from study data.

        Effect direction is classified as:
        - "positive": Beneficial effect (intervention better than control)
        - "negative": Harmful effect (intervention worse than control)
        - "null": No significant effect
        - "mixed": Unclear or conflicting results

        We prioritize text-based inference (which uses semantic cues like
        "beneficial", "harmful") over pure numeric differences, since numeric
        differences alone cannot tell us if lower or higher values are better.
        """
        # First, try to infer from text fields (most reliable for direction)
        result_text = str(data.get("primary_outcome_result", "")).lower()
        conclusion = str(data.get("conclusion", data.get("authors_conclusion", ""))).lower()
        combined_text = f"{result_text} {conclusion}"

        positive_indicators = [
            "significant reduction",
            "significantly reduced",
            "significant decrease",
            "beneficial",
            "improved",
            "improvement",
            "effective",
            "positive effect",
            "significantly lower",
            "protective",
            "associated with lower",
            "favored intervention",
            "favored treatment",
            "superior",
            "better outcomes",
            "reduced risk",
            "lower risk",
        ]
        negative_indicators = [
            "significant increase",
            "significantly increased",
            "harmful",
            "worse",
            "worsened",
            "negative effect",
            "significantly higher",
            "associated with higher",
            "adverse",
            "increased risk",
            "higher risk",
            "favored control",
            "inferior",
            "detrimental",
        ]
        null_indicators = [
            "no significant",
            "not significant",
            "no difference",
            "no effect",
            "non-significant",
            "ns",
            "p>0.05",
            "p > 0.05",
            "similar between",
            "comparable",
            "no association",
        ]

        for indicator in positive_indicators:
            if indicator in combined_text:
                return "positive"

        for indicator in negative_indicators:
            if indicator in combined_text:
                return "negative"

        for indicator in null_indicators:
            if indicator in combined_text:
                return "null"

        # If no text-based inference, try binary outcomes (events are typically adverse)
        # For events (deaths, adverse events), fewer is usually better
        intervention_events = data.get("intervention_events")
        control_events = data.get("control_events")
        intervention_n = data.get("sample_size_intervention")
        control_n = data.get("sample_size_control")

        if all(
            v is not None for v in [intervention_events, control_events, intervention_n, control_n]
        ):
            try:
                # Calculate proportions (type narrowing via explicit cast)
                int_events = float(intervention_events)  # type: ignore[arg-type]
                int_n = float(intervention_n)  # type: ignore[arg-type]
                ctrl_events = float(control_events)  # type: ignore[arg-type]
                ctrl_n = float(control_n)  # type: ignore[arg-type]
                intervention_prop = int_events / int_n
                control_prop = ctrl_events / ctrl_n
                diff = intervention_prop - control_prop

                # For events, lower is typically better (positive effect)
                # Use a 5% absolute difference threshold
                if diff < -0.05:
                    return "positive"  # Fewer events in intervention = beneficial
                elif diff > 0.05:
                    return "negative"  # More events in intervention = harmful
                else:
                    return "null"
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        # For continuous outcomes without text cues, we cannot determine direction
        # without knowing if higher or lower is better - mark as mixed
        intervention_mean = data.get("intervention_mean")
        control_mean = data.get("control_mean")

        if intervention_mean is not None and control_mean is not None:
            try:
                diff = abs(float(intervention_mean) - float(control_mean))
                # If there's a substantial difference but we don't know direction interpretation
                if diff > self.config.positive_threshold:
                    return "mixed"  # There's a difference but unclear if good or bad
                else:
                    return "null"  # Essentially no difference
            except (TypeError, ValueError):
                pass

        return "mixed"

    def _determine_effect_magnitude(self, data: dict[str, Any]) -> str:
        """Determine the magnitude of effect."""
        # Try to get effect size if available
        effect_size = data.get("effect_size", data.get("cohens_d", data.get("odds_ratio")))

        if effect_size is not None:
            try:
                es = abs(float(effect_size))

                # For odds ratio / risk ratio
                if data.get("effect_measure") in ["odds_ratio", "risk_ratio", "OR", "RR"]:
                    # Larger deviation from 1 = larger effect
                    deviation = max(es, 1 / es if es > 0 else 1) - 1
                    if deviation >= 0.5:
                        return "large"
                    elif deviation >= 0.2:
                        return "moderate"
                    elif deviation >= 0.1:
                        return "small"
                    else:
                        return "negligible"
                else:
                    # For standardized mean difference (Cohen's d-like)
                    if es >= 0.8:
                        return "large"
                    elif es >= 0.5:
                        return "moderate"
                    elif es >= 0.2:
                        return "small"
                    else:
                        return "negligible"
            except (TypeError, ValueError):
                pass

        return "unknown"

    def _extract_limitations(self, data: dict[str, Any]) -> list[str]:
        """Extract key limitations from study data."""
        limitations = []

        # Check for common limitation indicators
        if data.get("allocation_concealment") in ["unclear", "high risk", "inadequate"]:
            limitations.append("Unclear allocation concealment")

        if data.get("blinding") in ["none", "single", "open-label"]:
            limitations.append("Lack of blinding")

        if data.get("attrition_rate") and float(data.get("attrition_rate", 0)) > 20:
            limitations.append("High attrition rate")

        sample_size = data.get("sample_size_total")
        if sample_size and int(sample_size) < 100:
            limitations.append("Small sample size")

        if data.get("funding_source", "").lower() in ["industry", "pharmaceutical"]:
            limitations.append("Industry funding")

        # Add any explicitly stated limitations
        explicit_limitations = data.get("limitations", data.get("study_limitations", []))
        if isinstance(explicit_limitations, list):
            limitations.extend(explicit_limitations[:3])  # Limit to 3
        elif isinstance(explicit_limitations, str) and explicit_limitations:
            limitations.append(explicit_limitations)

        return limitations[:5]  # Return top 5 limitations

    def _perform_vote_counting(self, summaries: list[StudySummary]) -> VoteCount:
        """Perform vote counting for effect direction."""
        vote_count = VoteCount()

        for summary in summaries:
            direction = summary.effect_direction
            if direction == "positive":
                vote_count.positive += 1
            elif direction == "negative":
                vote_count.negative += 1
            elif direction == "null":
                vote_count.null += 1
            else:
                vote_count.mixed += 1

        return vote_count

    def _identify_patterns(self, summaries: list[StudySummary]) -> list[str]:
        """Identify patterns across studies."""
        patterns: list[str] = []

        if len(summaries) < 2:
            return patterns

        # Check for patterns by study design
        designs = [s.study_design for s in summaries if s.study_design]
        if designs:
            design_effects: dict[str, list[str | None]] = {}
            for summary in summaries:
                if summary.study_design:
                    if summary.study_design not in design_effects:
                        design_effects[summary.study_design] = []
                    design_effects[summary.study_design].append(summary.effect_direction)

            for design, effects in design_effects.items():
                if len(effects) >= 2:
                    counter = Counter(effects)
                    most_common = counter.most_common(1)[0]
                    if most_common[1] >= len(effects) * 0.75:
                        patterns.append(
                            f"{design} studies predominantly show {most_common[0]} effects "
                            f"({most_common[1]}/{len(effects)})"
                        )

        # Check for sample size patterns
        large_studies = [s for s in summaries if s.sample_size and s.sample_size >= 500]
        small_studies = [s for s in summaries if s.sample_size and s.sample_size < 100]

        if large_studies and small_studies:
            large_positive = sum(1 for s in large_studies if s.effect_direction == "positive")
            small_positive = sum(1 for s in small_studies if s.effect_direction == "positive")

            if large_studies and small_studies:
                large_prop = large_positive / len(large_studies)
                small_prop = small_positive / len(small_studies)
                if abs(large_prop - small_prop) > 0.3:
                    if small_prop > large_prop:
                        patterns.append(
                            "Smaller studies tend to show more positive effects than larger studies "
                            "(potential small-study bias)"
                        )
                    else:
                        patterns.append(
                            "Larger studies tend to show more positive effects than smaller studies"
                        )

        # Check for quality patterns
        high_quality = [s for s in summaries if s.quality_score and s.quality_score >= 0.8]
        low_quality = [s for s in summaries if s.quality_score and s.quality_score < 0.6]

        if len(high_quality) >= 2 and len(low_quality) >= 2:
            hq_positive = sum(1 for s in high_quality if s.effect_direction == "positive")
            lq_positive = sum(1 for s in low_quality if s.effect_direction == "positive")

            hq_prop = hq_positive / len(high_quality)
            lq_prop = lq_positive / len(low_quality)

            if abs(hq_prop - lq_prop) > 0.3:
                if lq_prop > hq_prop:
                    patterns.append("Lower quality studies tend to show more favorable effects")
                else:
                    patterns.append("Higher quality studies tend to show more favorable effects")

        return patterns

    def _identify_inconsistencies(
        self, summaries: list[StudySummary], vote_count: VoteCount
    ) -> list[str]:
        """Identify inconsistencies across studies."""
        inconsistencies = []

        if vote_count.consistency == "inconsistent":
            inconsistencies.append(
                f"Effect directions were inconsistent: {vote_count.positive} positive, "
                f"{vote_count.negative} negative, {vote_count.null} null, {vote_count.mixed} mixed"
            )

        # Check for similar studies with different results
        design_groups: dict[str, list[StudySummary]] = {}
        for summary in summaries:
            if summary.study_design:
                if summary.study_design not in design_groups:
                    design_groups[summary.study_design] = []
                design_groups[summary.study_design].append(summary)

        for design, group in design_groups.items():
            if len(group) >= 2:
                directions = set(s.effect_direction for s in group)
                if len(directions) > 1 and "positive" in directions and "negative" in directions:
                    inconsistencies.append(
                        f"{design} studies show conflicting results "
                        f"(both positive and negative effects reported)"
                    )

        # Check for magnitude inconsistencies among same-direction studies
        positive_studies = [s for s in summaries if s.effect_direction == "positive"]
        if len(positive_studies) >= 2:
            magnitudes = [
                s.effect_magnitude for s in positive_studies if s.effect_magnitude != "unknown"
            ]
            if magnitudes and "large" in magnitudes and "negligible" in magnitudes:
                inconsistencies.append(
                    "Among studies showing positive effects, magnitude varies from negligible to large"
                )

        return inconsistencies

    def _assess_evidence_quality(
        self, summaries: list[StudySummary], vote_count: VoteCount
    ) -> tuple[str, str]:
        """Assess overall evidence quality and generate confidence rating.

        Returns:
            Tuple of (quality assessment text, confidence level)
        """
        if len(summaries) == 0:
            return "No studies available for quality assessment.", "very low"

        # Calculate average quality score
        quality_scores = [s.quality_score for s in summaries if s.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5

        # Count studies by quality tier
        high_quality_count = sum(
            1
            for s in summaries
            if s.quality_score and s.quality_score >= self.config.high_quality_threshold
        )
        moderate_quality_count = sum(
            1
            for s in summaries
            if s.quality_score
            and self.config.moderate_quality_threshold
            <= s.quality_score
            < self.config.high_quality_threshold
        )
        low_quality_count = len(summaries) - high_quality_count - moderate_quality_count

        # Determine confidence based on multiple factors
        confidence_score = 0

        # Study quality contributes up to 3 points
        if avg_quality >= 0.8:
            confidence_score += 3
        elif avg_quality >= 0.6:
            confidence_score += 2
        elif avg_quality >= 0.4:
            confidence_score += 1

        # Consistency contributes up to 2 points
        if vote_count.consistency == "consistent":
            confidence_score += 2
        elif vote_count.consistency == "moderately consistent":
            confidence_score += 1

        # Number of studies contributes up to 2 points
        if len(summaries) >= 5:
            confidence_score += 2
        elif len(summaries) >= 3:
            confidence_score += 1

        # Total sample size contributes up to 1 point
        total_n = sum(s.sample_size for s in summaries if s.sample_size)
        if total_n >= 1000:
            confidence_score += 1

        # Map score to confidence level
        if confidence_score >= 7:
            confidence = "high"
        elif confidence_score >= 5:
            confidence = "moderate"
        elif confidence_score >= 3:
            confidence = "low"
        else:
            confidence = "very low"

        # Generate assessment text
        assessment_parts = []

        assessment_parts.append(
            f"Evidence is based on {len(summaries)} studies with "
            f"{high_quality_count} high quality, {moderate_quality_count} moderate quality, "
            f"and {low_quality_count} lower quality studies."
        )

        if total_n > 0:
            assessment_parts.append(f"Total sample size across studies: {total_n}.")

        assessment_parts.append(f"Findings are {vote_count.consistency} across studies.")

        # Add specific concerns
        concerns = []
        if high_quality_count < len(summaries) / 2:
            concerns.append("limited high-quality evidence")
        if vote_count.consistency != "consistent":
            concerns.append("inconsistent findings")
        if len(summaries) < 3:
            concerns.append("small number of studies")
        if total_n < 500:
            concerns.append("limited total sample size")

        if concerns:
            assessment_parts.append(f"Key concerns: {', '.join(concerns)}.")

        assessment = " ".join(assessment_parts)

        return assessment, confidence

    def _identify_gaps(
        self, extraction_result: ExtractionResult, summaries: list[StudySummary]
    ) -> list[str]:
        """Identify gaps in the evidence base."""
        gaps = []

        # Check for missing study designs
        designs = {s.study_design for s in summaries if s.study_design}
        designs_lower = {d.lower() for d in designs}
        has_rct = "rct" in designs_lower or "randomized controlled trial" in designs_lower
        if not has_rct:
            gaps.append("No randomized controlled trials identified")

        # Check for limited populations
        populations = [s.population for s in summaries if s.population]
        if populations:
            # Look for diversity in populations
            unique_populations = len(set(populations))
            if unique_populations == 1:
                gaps.append(f"All studies conducted in similar population: {populations[0]}")

        # Check for missing outcome data
        missing_outcome_count = sum(
            1
            for s in summaries
            if not s.main_finding or s.main_finding.lower() in ["not reported", "nr", "n/a"]
        )
        if missing_outcome_count > 0:
            gaps.append(f"{missing_outcome_count} studies with unclear or missing outcome data")

        # Check for small total sample size
        total_n = sum(s.sample_size for s in summaries if s.sample_size)
        if total_n < 500 and len(summaries) >= 2:
            gaps.append(f"Limited total sample size ({total_n}) across all studies")

        # Check for limited follow-up information
        follow_up_data = [
            p.data.get("follow_up_duration")
            for p in extraction_result.papers
            if p.data.get("follow_up_duration")
        ]
        if len(follow_up_data) < len(summaries) / 2:
            gaps.append("Limited information on follow-up duration")

        return gaps

    def _generate_summary_of_findings(
        self,
        summaries: list[StudySummary],
        vote_count: VoteCount,
        patterns: list[str],
        outcome: str | None,
    ) -> str:
        """Generate a narrative summary of findings."""
        if len(summaries) == 0:
            return "No studies were available for synthesis."

        outcome_name = outcome or "the outcome of interest"
        parts = []

        # Opening sentence
        parts.append(
            f"This narrative synthesis includes {len(summaries)} studies examining {outcome_name}."
        )

        # Sample size information
        total_n = sum(s.sample_size for s in summaries if s.sample_size)
        if total_n > 0:
            parts.append(f"The combined sample size across studies was {total_n} participants.")

        # Vote counting summary
        if vote_count.total > 0:
            parts.append(vote_count_to_narrative(vote_count))

        # Key patterns
        if patterns:
            parts.append(f"Notable patterns include: {patterns[0].lower()}")

        # Conclusion based on evidence
        if (
            vote_count.consistency == "consistent"
            and vote_count.predominant_direction == "positive"
        ):
            parts.append(
                "Overall, the evidence consistently suggests a beneficial effect, "
                "though the inability to pool results quantitatively limits the precision of this conclusion."
            )
        elif (
            vote_count.consistency == "consistent"
            and vote_count.predominant_direction == "negative"
        ):
            parts.append(
                "Overall, the evidence consistently suggests a harmful effect, "
                "though the inability to pool results quantitatively limits the precision of this conclusion."
            )
        elif vote_count.consistency == "consistent" and vote_count.predominant_direction == "null":
            parts.append("Overall, the evidence consistently suggests no significant effect.")
        else:
            parts.append(
                "The evidence is mixed, with studies showing varying directions of effect. "
                "This heterogeneity precludes drawing firm conclusions."
            )

        return " ".join(parts)

    def _explain_heterogeneity(
        self, summaries: list[StudySummary], extraction_result: ExtractionResult
    ) -> str:
        """Generate explanation for heterogeneity across studies."""
        if len(summaries) < 2:
            return "Insufficient studies to assess heterogeneity."

        factors = []

        # Check study design variation
        designs = [s.study_design for s in summaries if s.study_design]
        unique_designs = set(designs)
        if len(unique_designs) > 1:
            factors.append(f"variation in study designs ({', '.join(unique_designs)})")

        # Check population variation
        populations = [s.population for s in summaries if s.population]
        if len(set(populations)) > 1:
            factors.append("differences in study populations")

        # Check intervention variation
        interventions = [s.intervention for s in summaries if s.intervention]
        if len(set(interventions)) > 1:
            factors.append("variation in interventions")

        # Check comparator variation
        comparators = [s.comparator for s in summaries if s.comparator]
        if len(set(comparators)) > 1:
            factors.append("different comparators used")

        # Check outcome measurement variation
        outcomes = [s.outcome_description for s in summaries if s.outcome_description]
        if len(set(outcomes)) > 1:
            factors.append("differences in outcome definitions or measurement")

        # Check sample size variation
        sample_sizes = [s.sample_size for s in summaries if s.sample_size]
        if sample_sizes:
            max_n, min_n = max(sample_sizes), min(sample_sizes)
            if max_n > min_n * 5:
                factors.append(f"large variation in sample sizes ({min_n} to {max_n})")

        if factors:
            return "Heterogeneity across studies may be explained by: " + "; ".join(factors) + "."
        else:
            return "Sources of heterogeneity could not be clearly identified from available data."

    def _create_subgroups(self, extraction_result: ExtractionResult) -> dict[str, list[str]]:
        """Create subgroups based on study characteristics."""
        subgroups: dict[str, list[str]] = {}

        # Group by study design
        design_groups: dict[str, list[str]] = {}
        for paper in extraction_result.papers:
            design = paper.data.get("study_design")
            if design:
                if design not in design_groups:
                    design_groups[design] = []
                design_groups[design].append(paper.paper_id)

        # Only include subgroups with 2+ studies
        for design, study_ids in design_groups.items():
            if len(study_ids) >= 2:
                subgroups[f"study_design_{design}"] = study_ids

        return subgroups

    def _generate_effect_direction_chart(
        self, summaries: list[StudySummary], outcome_name: str
    ) -> str | None:
        """Generate a bar chart showing effect directions across studies."""
        try:
            # Count effect directions
            directions = ["positive", "negative", "null", "mixed"]
            counts = [sum(1 for s in summaries if s.effect_direction == d) for d in directions]

            # Create figure
            fig, ax = plt.subplots(figsize=(8, 5))

            # Colors for each direction
            colors = ["#2ecc71", "#e74c3c", "#95a5a6", "#f39c12"]  # green, red, gray, orange

            bars = ax.bar(directions, counts, color=colors, edgecolor="black", linewidth=1)

            # Add count labels on bars
            for bar, count in zip(bars, counts):
                if count > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.1,
                        str(count),
                        ha="center",
                        va="bottom",
                        fontsize=12,
                        fontweight="bold",
                    )

            # Styling
            ax.set_xlabel("Effect Direction", fontsize=12)
            ax.set_ylabel("Number of Studies", fontsize=12)
            ax.set_title(
                f"Effect Direction Summary for {outcome_name}", fontsize=14, fontweight="bold"
            )
            ax.set_ylim(0, max(counts) + 1 if max(counts) > 0 else 1)

            # Add legend explaining directions
            legend_text = (
                "Positive: Beneficial effect\n"
                "Negative: Harmful effect\n"
                "Null: No significant effect\n"
                "Mixed: Unclear/mixed results"
            )
            ax.text(
                0.98,
                0.98,
                legend_text,
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="top",
                horizontalalignment="right",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            )

            plt.tight_layout()

            # Save figure
            os.makedirs(self.config.output_dir, exist_ok=True)
            filename = f"effect_direction_{outcome_name.replace(' ', '_').lower()}.png"
            filepath = str(Path(self.config.output_dir) / filename)
            fig.savefig(filepath, dpi=self.config.dpi, bbox_inches="tight")
            plt.close(fig)

            return filepath

        except Exception as e:
            # Don't fail synthesis if visualization fails
            print(f"Warning: Could not generate effect direction chart: {e}")
            return None


def vote_count_to_narrative(vote_count: VoteCount) -> str:
    """Convert vote count to narrative sentence."""
    parts = []

    if vote_count.positive > 0:
        parts.append(
            f"{vote_count.positive} {'study' if vote_count.positive == 1 else 'studies'} "
            f"showed beneficial effects"
        )

    if vote_count.negative > 0:
        parts.append(
            f"{vote_count.negative} {'study' if vote_count.negative == 1 else 'studies'} "
            f"showed harmful effects"
        )

    if vote_count.null > 0:
        parts.append(
            f"{vote_count.null} {'study' if vote_count.null == 1 else 'studies'} "
            f"showed no significant effect"
        )

    if vote_count.mixed > 0:
        parts.append(
            f"{vote_count.mixed} {'study' if vote_count.mixed == 1 else 'studies'} "
            f"had mixed or unclear results"
        )

    if len(parts) == 0:
        return "No effect direction data available."
    elif len(parts) == 1:
        return parts[0] + "."
    elif len(parts) == 2:
        return f"{parts[0]}, while {parts[1]}."
    else:
        return f"{', '.join(parts[:-1])}, and {parts[-1]}."
