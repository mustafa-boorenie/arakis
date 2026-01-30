"""Statistical visualization generator.

Creates publication-ready plots for systematic reviews and meta-analyses.
Uses matplotlib/seaborn (NO LLM COST).

All numerical values displayed use centralized precision settings
to ensure consistency and traceability.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from arakis.models.analysis import (
    AnalysisMethod,
    EffectMeasure,
    MetaAnalysisResult,
)
from arakis.traceability import DEFAULT_PRECISION

if TYPE_CHECKING:
    from arakis.models.risk_of_bias import RiskOfBiasSummary

# Set publication-quality defaults
sns.set_style("whitegrid")
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 13,
        "figure.dpi": 300,
    }
)


class VisualizationGenerator:
    """Generator for statistical visualizations.

    Uses centralized precision configuration to ensure all numbers
    displayed in plots are consistent and traceable.
    """

    def __init__(self, output_dir: str = "."):
        """Initialize visualization generator.

        Args:
            output_dir: Directory to save plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.precision = DEFAULT_PRECISION

    def create_forest_plot(
        self,
        meta_result: MetaAnalysisResult,
        output_filename: str | None = None,
        figsize: tuple[float, float] | None = None,
        show_prediction_interval: bool = True,
        favors_labels: tuple[str, str] | None = None,
    ) -> str:
        """Create a forest plot for meta-analysis results with all required statistics.

        Args:
            meta_result: Meta-analysis result with study data
            output_filename: Output filename (default: forest_plot.png)
            figsize: Figure size in inches (width, height)
            show_prediction_interval: Whether to show prediction interval for random effects
            favors_labels: Custom labels for favors (left, right), e.g., ("Favors Treatment", "Favors Control")

        Returns:
            Path to saved plot
        """
        if output_filename is None:
            output_filename = "forest_plot.png"

        studies = meta_result.studies
        n_studies = len(studies)

        # Calculate figure height based on number of studies
        # Add extra space for statistics panel at bottom
        if figsize is None:
            height = max(8, 4 + n_studies * 0.5)
            figsize = (12, height)

        fig, ax = plt.subplots(figsize=figsize)

        # Determine if we're using log scale (for ORs, RRs)
        use_log_scale = meta_result.effect_measure in [
            EffectMeasure.ODDS_RATIO,
            EffectMeasure.RISK_RATIO,
        ]

        # Transform effects if using log scale
        if use_log_scale:
            # Effects are already in log scale from meta-analysis
            # Need to exponentiate for display
            effects = [np.exp(s.effect) for s in studies]  # type: ignore
            pooled_effect = np.exp(meta_result.pooled_effect)
            ci_lower = np.exp(meta_result.confidence_interval.lower)
            ci_upper = np.exp(meta_result.confidence_interval.upper)
            null_value = 1.0
            # Prediction interval
            if meta_result.heterogeneity.prediction_interval:
                pred_lower = np.exp(meta_result.heterogeneity.prediction_interval.lower)
                pred_upper = np.exp(meta_result.heterogeneity.prediction_interval.upper)
            else:
                pred_lower = pred_upper = None
        else:
            effects = [s.effect for s in studies]
            pooled_effect = meta_result.pooled_effect
            ci_lower = meta_result.confidence_interval.lower
            ci_upper = meta_result.confidence_interval.upper
            null_value = 0.0
            # Prediction interval
            if meta_result.heterogeneity.prediction_interval:
                pred_lower = meta_result.heterogeneity.prediction_interval.lower
                pred_upper = meta_result.heterogeneity.prediction_interval.upper
            else:
                pred_lower = pred_upper = None

        # Y-axis positions - leave space for headers and statistics
        header_y = n_studies + 2
        y_positions = list(range(n_studies, 0, -1))
        pooled_y = -0.5
        stats_y = -2.5

        # Collect all CI values for axis scaling
        all_ci_lowers = []
        all_ci_uppers = []

        # ===== COLUMN HEADERS =====
        ax.text(
            -0.02,
            header_y,
            "Study",
            ha="right",
            va="center",
            transform=ax.get_yaxis_transform(),
            fontweight="bold",
            fontsize=10,
        )
        ax.text(
            1.02,
            header_y,
            "Effect [95% CI]",
            ha="left",
            va="center",
            transform=ax.get_yaxis_transform(),
            fontweight="bold",
            fontsize=10,
        )
        ax.text(
            1.35,
            header_y,
            "Weight",
            ha="left",
            va="center",
            transform=ax.get_yaxis_transform(),
            fontweight="bold",
            fontsize=10,
        )

        # Separator line below headers
        ax.axhline(y=header_y - 0.5, color="black", linewidth=0.5, alpha=0.5)

        # ===== INDIVIDUAL STUDIES =====
        # Use z-critical value from precision config for consistency
        # Reference: Rosner, B. (2015). Fundamentals of Biostatistics
        z_crit = self.precision.Z_CRITICAL_95  # 1.96 for 95% CI

        for i, (study, effect, y) in enumerate(zip(studies, effects, y_positions)):
            # Calculate CI using centralized z-critical value
            if use_log_scale:
                study_ci_lower = np.exp(study.effect - z_crit * study.standard_error)  # type: ignore
                study_ci_upper = np.exp(study.effect + z_crit * study.standard_error)  # type: ignore
            else:
                study_ci_lower = study.effect - z_crit * study.standard_error  # type: ignore
                study_ci_upper = study.effect + z_crit * study.standard_error  # type: ignore

            all_ci_lowers.append(study_ci_lower)
            all_ci_uppers.append(study_ci_upper)

            # Box size proportional to weight
            weight = study.weight or 1.0
            box_size = max(weight * 300, 30)  # Scale factor for visibility with minimum size

            # Plot CI line
            ax.plot([study_ci_lower, study_ci_upper], [y, y], "k-", linewidth=1)

            # Plot effect estimate as square
            ax.scatter(
                [effect],
                [y],
                s=box_size,
                marker="s",
                color="steelblue",
                edgecolors="black",
                zorder=3,
            )

            # Add study label
            label = study.study_name or study.study_id
            if study.year:
                label = f"{label} ({study.year})"
            ax.text(
                -0.02,
                y,
                label,
                ha="right",
                va="center",
                transform=ax.get_yaxis_transform(),
                fontsize=9,
            )

            # Add effect and CI text
            effect_text = f"{effect:.2f} [{study_ci_lower:.2f}, {study_ci_upper:.2f}]"
            ax.text(
                1.02,
                y,
                effect_text,
                ha="left",
                va="center",
                transform=ax.get_yaxis_transform(),
                fontsize=9,
                family="monospace",
            )

            # Weight column
            weight_text = f"{weight * 100:.1f}%" if weight else ""
            ax.text(
                1.35,
                y,
                weight_text,
                ha="left",
                va="center",
                transform=ax.get_yaxis_transform(),
                fontsize=9,
            )

        # Separator line above pooled effect
        ax.axhline(y=0.3, color="black", linewidth=0.5, alpha=0.5)

        # ===== POOLED EFFECT (DIAMOND) =====
        diamond_height = 0.25

        diamond = [
            (ci_lower, pooled_y),
            (pooled_effect, pooled_y + diamond_height),
            (ci_upper, pooled_y),
            (pooled_effect, pooled_y - diamond_height),
        ]
        diamond_patch = plt.Polygon(
            diamond, closed=True, facecolor="crimson", edgecolor="darkred", linewidth=1.5
        )
        ax.add_patch(diamond_patch)

        # Add prediction interval line (if random effects and available)
        if (
            show_prediction_interval
            and meta_result.analysis_method == AnalysisMethod.RANDOM_EFFECTS
            and pred_lower is not None
            and pred_upper is not None
        ):
            ax.plot(
                [pred_lower, pred_upper],
                [pooled_y, pooled_y],
                color="crimson",
                linewidth=1.5,
                linestyle="--",
                alpha=0.7,
            )
            all_ci_lowers.append(pred_lower)
            all_ci_uppers.append(pred_upper)

        all_ci_lowers.extend([ci_lower, null_value])
        all_ci_uppers.extend([ci_upper, null_value])

        # Add pooled effect label
        method_label = meta_result.analysis_method.value.replace("_", " ").title()
        ax.text(
            -0.02,
            pooled_y,
            f"Overall ({method_label})",
            ha="right",
            va="center",
            fontweight="bold",
            transform=ax.get_yaxis_transform(),
            fontsize=9,
        )

        # Add pooled effect text
        pooled_text = f"{pooled_effect:.2f} [{ci_lower:.2f}, {ci_upper:.2f}]"
        ax.text(
            1.02,
            pooled_y,
            pooled_text,
            ha="left",
            va="center",
            fontweight="bold",
            transform=ax.get_yaxis_transform(),
            fontsize=9,
            family="monospace",
        )

        # Total weight (100%)
        ax.text(
            1.35,
            pooled_y,
            "100.0%",
            ha="left",
            va="center",
            fontweight="bold",
            transform=ax.get_yaxis_transform(),
            fontsize=9,
        )

        # ===== VERTICAL NULL LINE =====
        ax.axvline(null_value, color="black", linestyle="--", linewidth=1, alpha=0.7)

        # ===== AXIS LIMITS =====
        x_range = max(all_ci_uppers) - min(all_ci_lowers)
        x_padding = x_range * 0.15
        x_min = min(all_ci_lowers) - x_padding
        x_max = max(all_ci_uppers) + x_padding

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(stats_y - 1.5, header_y + 0.5)

        # ===== X-AXIS LABEL WITH FAVORS LABELS =====
        effect_label = self._get_effect_measure_label(meta_result.effect_measure)
        ax.set_xlabel(effect_label, fontweight="bold", fontsize=11)

        # Add favors labels
        if favors_labels is None:
            if use_log_scale:
                favors_labels = ("Favors Treatment", "Favors Control")
            else:
                favors_labels = ("Favors Treatment", "Favors Control")

        # Position favors labels below the x-axis
        ax.text(
            x_min + x_range * 0.15,
            stats_y - 0.5,
            f"← {favors_labels[0]}",
            ha="center",
            va="top",
            fontsize=9,
            style="italic",
        )
        ax.text(
            x_max - x_range * 0.15,
            stats_y - 0.5,
            f"{favors_labels[1]} →",
            ha="center",
            va="top",
            fontsize=9,
            style="italic",
        )

        # ===== STATISTICS PANEL =====
        # Heterogeneity statistics with consistent precision
        het = meta_result.heterogeneity

        # Format values using centralized precision settings
        tau_sq = f"{het.tau_squared:.{self.precision.tau_squared_decimals}f}"
        q_stat = f"{het.q_statistic:.{self.precision.q_statistic_decimals}f}"
        q_p = self.precision.format_p_value(het.q_p_value)
        i_sq = self.precision.format_i_squared(het.i_squared)

        het_text = (
            f"Heterogeneity: τ² = {tau_sq}; "
            f"χ² = {q_stat}, df = {n_studies - 1} "
            f"(P {q_p}); I² = {i_sq}"
        )

        # I² interpretation using centralized thresholds
        # Reference: Higgins JPT, Thompson SG. BMJ 2002;327:557-560
        het_interp = f"({self.precision.interpret_i_squared(het.i_squared)})"

        ax.text(
            0.5,
            stats_y + 0.8,
            het_text,
            ha="center",
            va="center",
            transform=ax.get_yaxis_transform(),
            fontsize=8,
        )
        ax.text(
            0.5,
            stats_y + 0.3,
            het_interp,
            ha="center",
            va="center",
            transform=ax.get_yaxis_transform(),
            fontsize=8,
            style="italic",
        )

        # Test for overall effect with consistent precision
        z_stat = f"{meta_result.z_statistic:.{self.precision.z_statistic_decimals}f}"
        p_val = self.precision.format_p_value(meta_result.p_value)
        overall_test = f"Test for overall effect: Z = {z_stat} (P {p_val})"
        ax.text(
            0.5,
            stats_y - 0.2,
            overall_test,
            ha="center",
            va="center",
            transform=ax.get_yaxis_transform(),
            fontsize=8,
        )

        # Prediction interval (if available)
        if (
            show_prediction_interval
            and meta_result.analysis_method == AnalysisMethod.RANDOM_EFFECTS
            and pred_lower is not None
            and pred_upper is not None
        ):
            pred_text = f"Prediction interval: [{pred_lower:.2f}, {pred_upper:.2f}]"
            ax.text(
                0.5,
                stats_y - 0.7,
                pred_text,
                ha="center",
                va="center",
                transform=ax.get_yaxis_transform(),
                fontsize=8,
            )

        # ===== TITLE =====
        title = f"Forest Plot: {meta_result.outcome_name}"
        subtitle = f"k = {n_studies} studies, N = {meta_result.total_sample_size:,}"
        ax.set_title(f"{title}\n{subtitle}", fontweight="bold", pad=15, fontsize=12)

        # ===== STYLING =====
        # Remove y-axis ticks and labels (we have custom labels)
        ax.set_yticks([])
        ax.set_yticklabels([])

        # Remove top and right spines
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Add light gridlines
        ax.grid(True, axis="x", alpha=0.3, linestyle="-", linewidth=0.5)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close()

        return str(output_path)

    def create_funnel_plot(
        self,
        meta_result: MetaAnalysisResult,
        output_filename: str | None = None,
        figsize: tuple[float, float] = (10, 8),
        show_contours: bool = True,
        show_study_labels: bool = False,
        y_axis: str = "se",  # "se" for standard error, "precision" for 1/SE
    ) -> str:
        """Create a publication-quality funnel plot for publication bias assessment.

        Args:
            meta_result: Meta-analysis result with study data
            output_filename: Output filename (default: funnel_plot.png)
            figsize: Figure size in inches
            show_contours: Whether to show significance contours (p < 0.01, 0.05, 0.10)
            show_study_labels: Whether to label individual studies
            y_axis: Y-axis metric - "se" for standard error or "precision" for 1/SE

        Returns:
            Path to saved plot
        """
        if output_filename is None:
            output_filename = "funnel_plot.png"

        studies = meta_result.studies
        n_studies = len(studies)
        pooled_effect = meta_result.pooled_effect

        # Determine if we're using log scale (for ORs, RRs)
        use_log_scale = meta_result.effect_measure in [
            EffectMeasure.ODDS_RATIO,
            EffectMeasure.RISK_RATIO,
        ]

        # Extract effects and standard errors
        effects = np.array([s.effect for s in studies])
        ses = np.array([s.standard_error for s in studies])

        # Transform for display if using log scale
        if use_log_scale:
            display_effects = np.exp(effects)
            display_pooled = np.exp(pooled_effect)
            null_value = 1.0
        else:
            display_effects = effects
            display_pooled = pooled_effect
            null_value = 0.0

        # Create figure with space for statistics
        fig, ax = plt.subplots(figsize=figsize)

        # Y-axis values
        if y_axis == "precision":
            y_values = 1 / ses
            y_label = "Precision (1/SE)"
            max_y = max(y_values) * 1.1
            min_y = min(y_values) * 0.5
        else:  # Standard error (default for funnel plots)
            y_values = ses
            y_label = "Standard Error"
            max_y = max(ses) * 1.2
            min_y = 0

        # ===== SIGNIFICANCE CONTOURS =====
        if show_contours:
            # Create y range for contours
            y_range = np.linspace(0.001, max_y * 1.2, 200)

            if y_axis == "precision":
                se_for_contours = 1 / y_range
            else:
                se_for_contours = y_range

            # Significance levels and their colors
            # Z-values from precision config for traceability
            # Reference: Rosner, B. (2015). Fundamentals of Biostatistics
            sig_levels = [
                (1.0, "white", "p > 0.10"),
                (self.precision.Z_CRITICAL_90, "#E8E8E8", "0.05 < p < 0.10"),  # 1.645
                (self.precision.Z_CRITICAL_95, "#D0D0D0", "0.01 < p < 0.05"),  # 1.96
                (self.precision.Z_CRITICAL_99, "#B8B8B8", "p < 0.01"),  # 2.576
            ]

            # Draw contours from outside in
            for z_value, color, label in reversed(sig_levels):
                if use_log_scale:
                    upper = np.exp(pooled_effect + z_value * se_for_contours)
                    lower = np.exp(pooled_effect - z_value * se_for_contours)
                else:
                    upper = pooled_effect + z_value * se_for_contours
                    lower = pooled_effect - z_value * se_for_contours

                ax.fill_betweenx(
                    y_range, lower, upper, alpha=1.0, color=color, linewidth=0, zorder=1
                )

            # Add contour legend
            from matplotlib.patches import Patch

            contour_handles = [
                Patch(facecolor="#B8B8B8", label="p < 0.01"),
                Patch(facecolor="#D0D0D0", label="0.01 < p < 0.05"),
                Patch(facecolor="#E8E8E8", label="0.05 < p < 0.10"),
                Patch(facecolor="white", edgecolor="gray", label="p > 0.10"),
            ]
        else:
            # Simple 95% CI funnel using z-critical from precision config
            y_range = np.linspace(0.001, max_y * 1.2, 100)
            if y_axis == "precision":
                se_for_contours = 1 / y_range
            else:
                se_for_contours = y_range

            z_crit = self.precision.Z_CRITICAL_95  # 1.96 for 95% CI
            if use_log_scale:
                upper = np.exp(pooled_effect + z_crit * se_for_contours)
                lower = np.exp(pooled_effect - z_crit * se_for_contours)
            else:
                upper = pooled_effect + z_crit * se_for_contours
                lower = pooled_effect - z_crit * se_for_contours

            ax.fill_betweenx(y_range, lower, upper, alpha=0.15, color="gray", linewidth=0, zorder=1)
            ax.plot(upper, y_range, "k--", alpha=0.5, linewidth=1, zorder=2)
            ax.plot(lower, y_range, "k--", alpha=0.5, linewidth=1, zorder=2)
            contour_handles = []

        # ===== POOLED EFFECT LINE =====
        ax.axvline(
            display_pooled,
            color="black",
            linestyle="-",
            linewidth=1.5,
            label=f"Pooled effect = {display_pooled:.3f}",
            zorder=3,
        )

        # ===== NULL EFFECT LINE =====
        ax.axvline(
            null_value,
            color="red",
            linestyle="--",
            linewidth=1,
            alpha=0.7,
            label=f"Null effect = {null_value}",
            zorder=3,
        )

        # ===== PLOT STUDIES =====
        ax.scatter(
            display_effects,
            y_values,
            s=80,
            alpha=0.8,
            color="steelblue",
            edgecolors="black",
            linewidth=1,
            zorder=4,
        )

        # Add study labels if requested
        if show_study_labels:
            for study, effect, y in zip(studies, display_effects, y_values):
                label = study.study_name or study.study_id
                if study.year:
                    label = f"{label} ({study.year})"
                ax.annotate(
                    label,
                    (effect, y),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=7,
                    alpha=0.8,
                )

        # ===== AXIS SETUP =====
        if y_axis != "precision":
            ax.invert_yaxis()  # For SE: low values at top

        # Set axis limits with padding
        x_range = max(display_effects) - min(display_effects)
        x_padding = max(x_range * 0.3, abs(display_pooled - null_value) * 0.5)
        ax.set_xlim(
            min(min(display_effects), null_value) - x_padding,
            max(max(display_effects), null_value) + x_padding,
        )

        if y_axis == "precision":
            ax.set_ylim(min_y, max_y)
        else:
            ax.set_ylim(max_y, min_y)  # Inverted for SE

        # ===== LABELS =====
        effect_label = self._get_effect_measure_label(meta_result.effect_measure)
        ax.set_xlabel(effect_label, fontweight="bold", fontsize=11)
        ax.set_ylabel(y_label, fontweight="bold", fontsize=11)

        # ===== TITLE =====
        title = f"Funnel Plot: {meta_result.outcome_name}"
        subtitle = f"k = {n_studies} studies"
        ax.set_title(f"{title}\n{subtitle}", fontweight="bold", pad=15, fontsize=12)

        # ===== STATISTICS BOX =====
        stats_lines = []

        # Heterogeneity info (I², τ², Q) with consistent precision
        het = meta_result.heterogeneity
        i_sq = self.precision.format_i_squared(het.i_squared)
        tau_sq = f"{het.tau_squared:.{self.precision.tau_squared_decimals}f}"
        q_stat = f"{het.q_statistic:.{self.precision.q_statistic_decimals}f}"
        q_p = self.precision.format_p_value(het.q_p_value)

        stats_lines.append(f"Heterogeneity: I² = {i_sq}")
        stats_lines.append(f"τ² = {tau_sq}, Q = {q_stat} (p {q_p})")

        # Egger's test with consistent p-value formatting
        if meta_result.egger_test_p_value is not None:
            egger_sig = (
                "significant" if meta_result.egger_test_p_value < 0.05 else "not significant"
            )
            egger_p_str = self.precision.format_p_value(meta_result.egger_test_p_value)
            stats_lines.append(f"Egger's test: p {egger_p_str} ({egger_sig})")

        # Asymmetry interpretation
        if meta_result.egger_test_p_value is not None:
            if meta_result.egger_test_p_value < 0.05:
                stats_lines.append("* Evidence of funnel plot asymmetry")
            elif meta_result.egger_test_p_value < 0.10:
                stats_lines.append("* Possible funnel plot asymmetry")
            else:
                stats_lines.append("No evidence of asymmetry")

        # Study count note
        if n_studies < 10:
            stats_lines.append(f"Note: With k={n_studies} studies, tests have low power")

        stats_text = "\n".join(stats_lines)
        ax.text(
            0.02,
            0.98,
            stats_text,
            transform=ax.transAxes,
            verticalalignment="top",
            fontsize=9,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="gray", alpha=0.9),
            zorder=5,
        )

        # ===== LEGEND =====
        # Combine contour legend with other elements
        handles, labels = ax.get_legend_handles_labels()
        if contour_handles:
            handles.extend(contour_handles)  # type: ignore[arg-type]
            labels.extend([h.get_label() for h in contour_handles])

        ax.legend(handles, labels, loc="upper right", fontsize=8, framealpha=0.9)

        # ===== STYLING =====
        ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close()

        return str(output_path)

    def create_box_plot(
        self,
        data: dict[str, list[float]],
        title: str = "Distribution Comparison",
        xlabel: str = "Groups",
        ylabel: str = "Values",
        output_filename: str | None = None,
        figsize: tuple[float, float] = (8, 6),
    ) -> str:
        """Create a box plot for comparing distributions.

        Args:
            data: Dictionary mapping group names to values
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            output_filename: Output filename (default: box_plot.png)
            figsize: Figure size in inches

        Returns:
            Path to saved plot
        """
        if output_filename is None:
            output_filename = "box_plot.png"

        fig, ax = plt.subplots(figsize=figsize)

        # Prepare data
        groups = list(data.keys())
        values = [data[group] for group in groups]

        # Create box plot
        bp = ax.boxplot(values, labels=groups, patch_artist=True, notch=True)

        # Customize colors
        colors = sns.color_palette("Set2", len(groups))
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        # Add scatter of individual points
        for i, (group_values, x_pos) in enumerate(zip(values, range(1, len(groups) + 1))):
            # Add jitter to x-position
            x_jitter = np.random.normal(x_pos, 0.04, len(group_values))
            ax.scatter(x_jitter, group_values, alpha=0.3, s=20, color="black")

        # Labels and title
        ax.set_xlabel(xlabel, fontweight="bold")
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_title(title, fontweight="bold", pad=15)

        ax.grid(True, axis="y", alpha=0.3)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return str(output_path)

    def create_bar_chart(
        self,
        data: dict[str, float],
        title: str = "Comparison",
        xlabel: str = "Groups",
        ylabel: str = "Values",
        output_filename: str | None = None,
        figsize: tuple[float, float] = (8, 6),
        errors: dict[str, float] | None = None,
    ) -> str:
        """Create a bar chart for categorical comparisons.

        Args:
            data: Dictionary mapping categories to values
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            output_filename: Output filename (default: bar_chart.png)
            figsize: Figure size in inches
            errors: Optional error bars (dictionary mapping categories to error values)

        Returns:
            Path to saved plot
        """
        if output_filename is None:
            output_filename = "bar_chart.png"

        fig, ax = plt.subplots(figsize=figsize)

        # Prepare data
        categories = list(data.keys())
        values = [data[cat] for cat in categories]
        x_pos = np.arange(len(categories))

        # Error bars
        error_values = [errors[cat] if errors else 0 for cat in categories]

        # Create bar chart
        colors = sns.color_palette("Set2", len(categories))
        bars = ax.bar(x_pos, values, color=colors, alpha=0.7, yerr=error_values, capsize=5)

        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        # Labels and title
        ax.set_xlabel(xlabel, fontweight="bold")
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_title(title, fontweight="bold", pad=15)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(categories)

        ax.grid(True, axis="y", alpha=0.3)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return str(output_path)

    def create_scatter_plot(
        self,
        x: list[float] | np.ndarray,
        y: list[float] | np.ndarray,
        title: str = "Scatter Plot",
        xlabel: str = "X",
        ylabel: str = "Y",
        output_filename: str | None = None,
        figsize: tuple[float, float] = (8, 6),
        add_regression: bool = True,
    ) -> str:
        """Create a scatter plot with optional regression line.

        Args:
            x: X-axis values
            y: Y-axis values
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            output_filename: Output filename (default: scatter_plot.png)
            figsize: Figure size in inches
            add_regression: Whether to add regression line

        Returns:
            Path to saved plot
        """
        if output_filename is None:
            output_filename = "scatter_plot.png"

        x = np.array(x)
        y = np.array(y)

        fig, ax = plt.subplots(figsize=figsize)

        # Scatter plot
        ax.scatter(x, y, alpha=0.6, s=50, color="steelblue", edgecolors="black")

        # Add regression line
        if add_regression:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            ax.plot(x, p(x), "r--", alpha=0.8, linewidth=2, label=f"y = {z[0]:.2f}x + {z[1]:.2f}")

            # Calculate R²
            y_pred = p(x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            ax.text(
                0.05,
                0.95,
                f"R² = {r_squared:.3f}",
                transform=ax.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

            ax.legend()

        # Labels and title
        ax.set_xlabel(xlabel, fontweight="bold")
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_title(title, fontweight="bold", pad=15)

        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return str(output_path)

    def _get_effect_measure_label(self, effect_measure: EffectMeasure) -> str:
        """Get display label for effect measure."""
        labels = {
            EffectMeasure.MEAN_DIFFERENCE: "Mean Difference",
            EffectMeasure.STANDARDIZED_MEAN_DIFFERENCE: "Standardized Mean Difference (Hedges' g)",
            EffectMeasure.ODDS_RATIO: "Odds Ratio",
            EffectMeasure.RISK_RATIO: "Risk Ratio",
            EffectMeasure.RISK_DIFFERENCE: "Risk Difference",
            EffectMeasure.CORRELATION: "Correlation Coefficient",
        }
        return labels.get(effect_measure, str(effect_measure))

    def create_risk_of_bias_summary(
        self,
        summary: "RiskOfBiasSummary",
        output_filename: str | None = None,
        figsize: tuple[float, float] = (12, 8),
        show_domains: bool = True,
    ) -> str:
        """Create a risk of bias summary plot.

        Generates a horizontal stacked bar chart showing the distribution
        of risk of bias judgments across studies for each domain.

        Args:
            summary: RiskOfBiasSummary from RiskOfBiasAssessor
            output_filename: Output filename (default: rob_summary.png)
            figsize: Figure size in inches
            show_domains: Whether to show domain-level breakdown

        Returns:
            Path to saved plot
        """
        from arakis.models.risk_of_bias import RiskLevel

        if output_filename is None:
            output_filename = "rob_summary.png"

        if not summary.studies:
            # Create empty plot
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, "No studies to assess", ha="center", va="center", fontsize=14)
            ax.axis("off")
            output_path = self.output_dir / output_filename
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()
            return str(output_path)

        n_studies = summary.n_studies
        domain_names = summary.get_domain_names()
        domain_distributions = summary.domain_distributions

        # Colors for risk levels
        colors = {
            RiskLevel.LOW: "#00a65a",  # Green
            RiskLevel.SOME_CONCERNS: "#f39c12",  # Yellow/Orange
            RiskLevel.HIGH: "#dd4b39",  # Red
            RiskLevel.UNCLEAR: "#f39c12",  # Yellow
            RiskLevel.NOT_APPLICABLE: "#d2d6de",  # Gray
        }

        # Prepare data - domains + overall
        categories = domain_names + ["Overall"] if show_domains else ["Overall"]
        y_positions = np.arange(len(categories))

        # Calculate percentages for each category
        data_low = []
        data_concerns = []
        data_high = []

        if show_domains:
            for domain_id, dist in domain_distributions.items():
                low_count = dist.get(RiskLevel.LOW, 0)
                concerns_count = dist.get(RiskLevel.SOME_CONCERNS, 0) + dist.get(
                    RiskLevel.UNCLEAR, 0
                )
                high_count = dist.get(RiskLevel.HIGH, 0)

                data_low.append(low_count / n_studies * 100)
                data_concerns.append(concerns_count / n_studies * 100)
                data_high.append(high_count / n_studies * 100)

        # Add overall
        overall_dist = summary.overall_distribution
        data_low.append(overall_dist.get(RiskLevel.LOW, 0) / n_studies * 100)
        data_concerns.append(
            (overall_dist.get(RiskLevel.SOME_CONCERNS, 0) + overall_dist.get(RiskLevel.UNCLEAR, 0))
            / n_studies
            * 100
        )
        data_high.append(overall_dist.get(RiskLevel.HIGH, 0) / n_studies * 100)

        # Create figure
        fig, ax = plt.subplots(figsize=figsize)

        # Create stacked horizontal bar chart
        bar_height = 0.6

        # Plot bars (stacked)
        ax.barh(
            y_positions,
            data_low,
            height=bar_height,
            color=colors[RiskLevel.LOW],
            label="Low risk",
            edgecolor="white",
            linewidth=0.5,
        )
        ax.barh(
            y_positions,
            data_concerns,
            height=bar_height,
            left=data_low,
            color=colors[RiskLevel.SOME_CONCERNS],
            label="Some concerns",
            edgecolor="white",
            linewidth=0.5,
        )
        ax.barh(
            y_positions,
            data_high,
            height=bar_height,
            left=[low + concern for low, concern in zip(data_low, data_concerns)],
            color=colors[RiskLevel.HIGH],
            label="High risk",
            edgecolor="white",
            linewidth=0.5,
        )

        # Add percentage labels inside bars (if segment > 10%)
        for i, (low, concerns, high) in enumerate(zip(data_low, data_concerns, data_high)):
            # Low risk label
            if low > 10:
                ax.text(
                    low / 2,
                    i,
                    f"{low:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                )

            # Some concerns label
            if concerns > 10:
                ax.text(
                    low + concerns / 2,
                    i,
                    f"{concerns:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="black",
                    fontweight="bold",
                )

            # High risk label
            if high > 10:
                ax.text(
                    low + concerns + high / 2,
                    i,
                    f"{high:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                )

        # Customize axes
        ax.set_yticks(y_positions)
        ax.set_yticklabels(categories, fontsize=10)
        ax.set_xlabel("Percentage of studies", fontweight="bold", fontsize=11)
        ax.set_xlim(0, 100)

        # Add grid
        ax.xaxis.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
        ax.set_axisbelow(True)

        # Style
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # Legend
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.08),
            ncol=3,
            frameon=False,
            fontsize=10,
        )

        # Title
        tool_names = {
            "rob_2": "RoB 2",
            "robins_i": "ROBINS-I",
            "quadas_2": "QUADAS-2",
        }
        tool_name = tool_names.get(summary.tool.value, summary.tool.value)
        title = f"Risk of Bias Summary ({tool_name})"
        subtitle = f"k = {n_studies} studies"
        ax.set_title(f"{title}\n{subtitle}", fontweight="bold", pad=15, fontsize=12)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close()

        return str(output_path)

    def create_risk_of_bias_traffic_light(
        self,
        summary: "RiskOfBiasSummary",
        output_filename: str | None = None,
        figsize: tuple[float, float] | None = None,
        cell_size: float = 0.8,
    ) -> str:
        """Create a traffic light plot for risk of bias.

        Shows individual study assessments across domains as a color-coded matrix.

        Args:
            summary: RiskOfBiasSummary from RiskOfBiasAssessor
            output_filename: Output filename (default: rob_traffic_light.png)
            figsize: Figure size (auto-calculated if None)
            cell_size: Size of each cell in the matrix

        Returns:
            Path to saved plot
        """
        from arakis.models.risk_of_bias import RiskLevel

        if output_filename is None:
            output_filename = "rob_traffic_light.png"

        if not summary.studies:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, "No studies to assess", ha="center", va="center", fontsize=14)
            ax.axis("off")
            output_path = self.output_dir / output_filename
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()
            return str(output_path)

        n_studies = len(summary.studies)
        domain_names = summary.get_domain_names() + ["Overall"]
        n_domains = len(domain_names)

        # Auto-calculate figure size
        if figsize is None:
            width = max(8, n_domains * 1.2 + 3)
            height = max(6, n_studies * 0.5 + 2)
            figsize = (width, height)

        # Colors
        colors = {
            RiskLevel.LOW: "#00a65a",
            RiskLevel.SOME_CONCERNS: "#f39c12",
            RiskLevel.HIGH: "#dd4b39",
            RiskLevel.UNCLEAR: "#f39c12",
            RiskLevel.NOT_APPLICABLE: "#d2d6de",
        }

        # Symbols
        symbols = {
            RiskLevel.LOW: "+",
            RiskLevel.SOME_CONCERNS: "?",
            RiskLevel.HIGH: "-",
            RiskLevel.UNCLEAR: "?",
            RiskLevel.NOT_APPLICABLE: "NA",
        }

        fig, ax = plt.subplots(figsize=figsize)

        # Draw cells
        for i, study in enumerate(summary.studies):
            y_pos = n_studies - i - 1  # Reverse order (first study at top)

            # Draw domain cells
            for j, domain in enumerate(study.domains):
                color = colors[domain.judgment]
                symbol = symbols[domain.judgment]

                # Draw cell
                rect = plt.Rectangle(
                    (j, y_pos),
                    cell_size,
                    cell_size,
                    facecolor=color,
                    edgecolor="white",
                    linewidth=1,
                )
                ax.add_patch(rect)

                # Add symbol
                ax.text(
                    j + cell_size / 2,
                    y_pos + cell_size / 2,
                    symbol,
                    ha="center",
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                    color="white",
                )

            # Draw overall cell
            j = len(study.domains)
            color = colors[study.overall_judgment]
            symbol = symbols[study.overall_judgment]

            rect = plt.Rectangle(
                (j, y_pos),
                cell_size,
                cell_size,
                facecolor=color,
                edgecolor="white",
                linewidth=2,
            )
            ax.add_patch(rect)
            ax.text(
                j + cell_size / 2,
                y_pos + cell_size / 2,
                symbol,
                ha="center",
                va="center",
                fontsize=12,
                fontweight="bold",
                color="white",
            )

        # Add study labels
        for i, study in enumerate(summary.studies):
            y_pos = n_studies - i - 1
            ax.text(
                -0.1,
                y_pos + cell_size / 2,
                study.study_name,
                ha="right",
                va="center",
                fontsize=9,
            )

        # Add domain labels at top
        for j, domain_name in enumerate(domain_names):
            ax.text(
                j + cell_size / 2,
                n_studies + 0.1,
                domain_name,
                ha="center",
                va="bottom",
                fontsize=9,
                rotation=45,
            )

        # Set axis limits
        ax.set_xlim(-0.5, n_domains)
        ax.set_ylim(-0.5, n_studies + 1)
        ax.set_aspect("equal")
        ax.axis("off")

        # Add legend
        from matplotlib.patches import Patch

        legend_elements = [
            Patch(facecolor=colors[RiskLevel.LOW], edgecolor="white", label="Low risk (+)"),
            Patch(
                facecolor=colors[RiskLevel.SOME_CONCERNS],
                edgecolor="white",
                label="Some concerns (?)",
            ),
            Patch(facecolor=colors[RiskLevel.HIGH], edgecolor="white", label="High risk (-)"),
        ]
        ax.legend(
            handles=legend_elements,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=3,
            frameon=False,
            fontsize=9,
        )

        # Title
        tool_names = {
            "rob_2": "RoB 2",
            "robins_i": "ROBINS-I",
            "quadas_2": "QUADAS-2",
        }
        tool_name = tool_names.get(summary.tool.value, summary.tool.value)
        ax.set_title(
            f"Risk of Bias Traffic Light Plot ({tool_name})",
            fontweight="bold",
            pad=20,
            fontsize=12,
        )

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close()

        return str(output_path)
