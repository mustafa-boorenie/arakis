"""Statistical visualization generator.

Creates publication-ready plots for systematic reviews and meta-analyses.
Uses matplotlib/seaborn (NO LLM COST).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from arakis.models.analysis import (
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
    ) -> str:
        """Create a forest plot for meta-analysis results.

        Args:
            meta_result: Meta-analysis result with study data
            output_filename: Output filename (default: forest_plot.png)
            figsize: Figure size in inches (width, height)

        Returns:
            Path to saved plot
        """
        if output_filename is None:
            output_filename = "forest_plot.png"

        studies = meta_result.studies
        n_studies = len(studies)

        # Calculate figure height based on number of studies
        if figsize is None:
            height = max(6, 2 + n_studies * 0.4)
            figsize = (10, height)

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
        else:
            effects = [s.effect for s in studies]
            pooled_effect = meta_result.pooled_effect
            ci_lower = meta_result.confidence_interval.lower
            ci_upper = meta_result.confidence_interval.upper
            null_value = 0.0

        # Y-axis positions
        y_positions = list(range(n_studies, 0, -1))
        pooled_y = 0

        # Plot individual studies
        for i, (study, effect, y) in enumerate(zip(studies, effects, y_positions)):
            # Calculate CI
            if use_log_scale:
                study_ci_lower = np.exp(study.effect - 1.96 * study.standard_error)  # type: ignore
                study_ci_upper = np.exp(study.effect + 1.96 * study.standard_error)  # type: ignore
            else:
                study_ci_lower = study.effect - 1.96 * study.standard_error  # type: ignore
                study_ci_upper = study.effect + 1.96 * study.standard_error  # type: ignore

            # Box size proportional to weight
            weight = study.weight or 1.0
            box_size = weight * 200  # Scale factor for visibility

            # Plot CI line
            ax.plot([study_ci_lower, study_ci_upper], [y, y], "k-", linewidth=1)

            # Plot effect estimate as square
            ax.scatter([effect], [y], s=box_size, marker="s", color="black", zorder=3)

            # Add study label
            label = study.study_name or study.study_id
            if study.year:
                label = f"{label} ({study.year})"
            ax.text(-0.02, y, label, ha="right", va="center", transform=ax.get_yaxis_transform())

            # Add effect and CI text
            if use_log_scale:
                effect_text = f"{effect:.2f} [{study_ci_lower:.2f}, {study_ci_upper:.2f}]"
            else:
                effect_text = f"{effect:.2f} [{study_ci_lower:.2f}, {study_ci_upper:.2f}]"

            weight_text = f"{weight * 100:.1f}%" if weight else ""
            ax.text(
                1.02,
                y,
                f"{effect_text}  {weight_text}",
                ha="left",
                va="center",
                transform=ax.get_yaxis_transform(),
                fontsize=8,
            )

        # Plot pooled effect (diamond)
        (ci_upper - ci_lower) / 2
        diamond_height = 0.3

        diamond = [
            (ci_lower, pooled_y),
            (pooled_effect, pooled_y + diamond_height),
            (ci_upper, pooled_y),
            (pooled_effect, pooled_y - diamond_height),
        ]
        diamond_patch = plt.Polygon(diamond, closed=True, facecolor="black", edgecolor="black")
        ax.add_patch(diamond_patch)

        # Add pooled effect label
        ax.text(
            -0.02,
            pooled_y,
            "Pooled Effect",
            ha="right",
            va="center",
            fontweight="bold",
            transform=ax.get_yaxis_transform(),
        )

        # Add pooled effect text
        if use_log_scale:
            pooled_text = f"{pooled_effect:.2f} [{ci_lower:.2f}, {ci_upper:.2f}]"
        else:
            pooled_text = f"{pooled_effect:.2f} [{ci_lower:.2f}, {ci_upper:.2f}]"

        ax.text(
            1.02,
            pooled_y,
            pooled_text,
            ha="left",
            va="center",
            fontweight="bold",
            transform=ax.get_yaxis_transform(),
            fontsize=8,
        )

        # Add vertical line at null effect
        ax.axvline(null_value, color="black", linestyle="--", linewidth=1, alpha=0.5)

        # Set axis limits and labels
        all_values = effects + [pooled_effect, ci_lower, ci_upper, null_value]
        x_min = min(all_values) - (max(all_values) - min(all_values)) * 0.1
        x_max = max(all_values) + (max(all_values) - min(all_values)) * 0.1

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(-1, n_studies + 1)

        # Labels
        effect_label = self._get_effect_measure_label(meta_result.effect_measure)
        ax.set_xlabel(effect_label, fontweight="bold")
        ax.set_title(
            f"Forest Plot: {meta_result.outcome_name}\n"
            f"({meta_result.analysis_method.value.replace('_', ' ').title()}, "
            f"I² = {meta_result.heterogeneity.i_squared:.1f}%)",
            fontweight="bold",
            pad=15,
        )

        # Remove y-axis ticks and labels (we have custom labels)
        ax.set_yticks([])
        ax.set_yticklabels([])

        # Remove top and right spines
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Add gridlines
        ax.grid(True, axis="x", alpha=0.3)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        return str(output_path)

    def create_funnel_plot(
        self,
        meta_result: MetaAnalysisResult,
        output_filename: str | None = None,
        figsize: tuple[float, float] = (8, 6),
    ) -> str:
        """Create a funnel plot for publication bias assessment.

        Args:
            meta_result: Meta-analysis result with study data
            output_filename: Output filename (default: funnel_plot.png)
            figsize: Figure size in inches

        Returns:
            Path to saved plot
        """
        if output_filename is None:
            output_filename = "funnel_plot.png"

        studies = meta_result.studies
        pooled_effect = meta_result.pooled_effect

        # Extract effects and standard errors
        effects = np.array([s.effect for s in studies])
        ses = np.array([s.standard_error for s in studies])
        precisions = 1 / ses

        # Create figure
        fig, ax = plt.subplots(figsize=figsize)

        # Plot studies
        ax.scatter(effects, precisions, s=50, alpha=0.6, color="steelblue", edgecolors="black")

        # Add pooled effect line
        ax.axvline(
            pooled_effect, color="black", linestyle="--", linewidth=1.5, label="Pooled Effect"
        )

        # Add funnel (pseudo confidence limits)
        max_precision = max(precisions)
        min_precision = min(precisions)

        # Calculate funnel boundaries (±1.96 SE)
        precision_range = np.linspace(min_precision * 0.5, max_precision * 1.1, 100)
        se_range = 1 / precision_range

        upper_bound = pooled_effect + 1.96 * se_range
        lower_bound = pooled_effect - 1.96 * se_range

        ax.plot(upper_bound, precision_range, "k--", alpha=0.3, linewidth=1)
        ax.plot(lower_bound, precision_range, "k--", alpha=0.3, linewidth=1)
        ax.fill_betweenx(
            precision_range, lower_bound, upper_bound, alpha=0.1, color="gray", label="95% CI"
        )

        # Invert y-axis (high precision at top)
        ax.invert_yaxis()

        # Labels
        effect_label = self._get_effect_measure_label(meta_result.effect_measure)
        ax.set_xlabel(effect_label, fontweight="bold")
        ax.set_ylabel("Precision (1/SE)", fontweight="bold")
        ax.set_title(f"Funnel Plot: {meta_result.outcome_name}", fontweight="bold", pad=15)

        # Add Egger's test result if available
        if meta_result.egger_test_p_value is not None:
            egger_text = f"Egger's test: p = {meta_result.egger_test_p_value:.3f}"
            ax.text(
                0.05,
                0.95,
                egger_text,
                transform=ax.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save
        output_path = self.output_dir / output_filename
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
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
