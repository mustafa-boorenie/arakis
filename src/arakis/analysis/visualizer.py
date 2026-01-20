"""Statistical visualization generator.

Creates publication-ready plots for systematic reviews and meta-analyses.
Uses matplotlib/seaborn (NO LLM COST).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from arakis.models.analysis import (
    AnalysisMethod,
    EffectMeasure,
    MetaAnalysisResult,
)

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
    """Generator for statistical visualizations."""

    def __init__(self, output_dir: str = "."):
        """Initialize visualization generator.

        Args:
            output_dir: Directory to save plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
        for i, (study, effect, y) in enumerate(zip(studies, effects, y_positions)):
            # Calculate CI
            if use_log_scale:
                study_ci_lower = np.exp(study.effect - 1.96 * study.standard_error)  # type: ignore
                study_ci_upper = np.exp(study.effect + 1.96 * study.standard_error)  # type: ignore
            else:
                study_ci_lower = study.effect - 1.96 * study.standard_error  # type: ignore
                study_ci_upper = study.effect + 1.96 * study.standard_error  # type: ignore

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
        # Heterogeneity statistics
        het = meta_result.heterogeneity
        het_text = (
            f"Heterogeneity: τ² = {het.tau_squared:.4f}; "
            f"χ² = {het.q_statistic:.2f}, df = {n_studies - 1} "
            f"(P = {het.q_p_value:.4f}); I² = {het.i_squared:.1f}%"
        )

        # I² interpretation
        if het.i_squared < 25:
            het_interp = "(low heterogeneity)"
        elif het.i_squared < 50:
            het_interp = "(moderate heterogeneity)"
        elif het.i_squared < 75:
            het_interp = "(substantial heterogeneity)"
        else:
            het_interp = "(considerable heterogeneity)"

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

        # Test for overall effect
        overall_test = (
            f"Test for overall effect: Z = {meta_result.z_statistic:.2f} "
            f"(P {'< 0.0001' if meta_result.p_value < 0.0001 else f'= {meta_result.p_value:.4f}'})"
        )
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
            sig_levels = [
                (1.0, "white", "p > 0.10"),
                (1.645, "#E8E8E8", "0.05 < p < 0.10"),
                (1.96, "#D0D0D0", "0.01 < p < 0.05"),
                (2.576, "#B8B8B8", "p < 0.01"),
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
            # Simple 95% CI funnel
            y_range = np.linspace(0.001, max_y * 1.2, 100)
            if y_axis == "precision":
                se_for_contours = 1 / y_range
            else:
                se_for_contours = y_range

            if use_log_scale:
                upper = np.exp(pooled_effect + 1.96 * se_for_contours)
                lower = np.exp(pooled_effect - 1.96 * se_for_contours)
            else:
                upper = pooled_effect + 1.96 * se_for_contours
                lower = pooled_effect - 1.96 * se_for_contours

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

        # Heterogeneity info (I², τ², Q)
        het = meta_result.heterogeneity
        stats_lines.append(f"Heterogeneity: I² = {het.i_squared:.1f}%")
        stats_lines.append(f"τ² = {het.tau_squared:.4f}, Q = {het.q_statistic:.2f} (p = {het.q_p_value:.4f})")

        # Egger's test
        if meta_result.egger_test_p_value is not None:
            egger_sig = (
                "significant" if meta_result.egger_test_p_value < 0.05 else "not significant"
            )
            if meta_result.egger_test_p_value < 0.0001:
                egger_p_str = "p < 0.0001"
            else:
                egger_p_str = f"p = {meta_result.egger_test_p_value:.4f}"
            stats_lines.append(f"Egger's test: {egger_p_str} ({egger_sig})")

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
