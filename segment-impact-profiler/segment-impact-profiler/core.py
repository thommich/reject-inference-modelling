"""Weighted, segment-level aggregation of additive SHAP model contributions.

The package performs no network operations or LLM calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

OVERALL = "__OVERALL__"


def _weighted_mean(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return np.dot(weights, matrix) / weights.sum()


@dataclass
class SegmentImpactReport:
    """Aggregated SHAP contributions, stored without row-level feature data.

    All signed SHAP values are oriented so that positive values mean higher
    modeled *risk*. With ``higher_output_is_riskier=False``, the raw model
    output and SHAP signs are negated consistently.

    ``score_col`` is reported as-is (it may be probability, scorecard score,
    etc.); it is NOT used in the additive SHAP decomposition.
    """

    impacts: pd.DataFrame
    segments: pd.DataFrame
    feature_names: list[str]
    segment_col: str
    score_col: str | None
    weighted: bool
    max_additivity_error: float | None
    higher_output_is_riskier: bool

    @classmethod
    def from_shap(
        cls,
        data: pd.DataFrame,
        shap_values: np.ndarray,
        feature_names: Sequence[str],
        segment_col: str,
        *,
        base_values: float | np.ndarray,
        score_col: str | None = None,
        weight_col: str | None = None,
        raw_margin_col: str | None = None,
        higher_output_is_riskier: bool = True,
        max_allowed_additivity_error: float = 1e-3,
    ) -> SegmentImpactReport:
        """Aggregate row-aligned SHAP values by segment.

        Args:
            data: Original row-aligned frame, containing segment and metadata.
            shap_values: Shape (rows, model features), in raw model space.
            feature_names: One name for every column of shap_values.
            segment_col: Population grouping field; can also be a risk group.
            base_values: Scalar or one baseline per row, in raw model space.
            score_col: Optional score for group reporting (no additivity claim).
            weight_col: Optional nonnegative sampling/frequency weight.
            raw_margin_col: Optional true raw prediction to validate additivity.
            higher_output_is_riskier: Flip SHAP and raw margins when False.
        """
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("data must be a nonempty pandas DataFrame")
        required = [segment_col] + [x for x in [score_col, weight_col, raw_margin_col] if x]
        for col in required:
            if col not in data.columns:
                raise ValueError(f"Missing data column: {col!r}")
        values = np.asarray(shap_values, dtype=np.float64)
        features = [str(x) for x in feature_names]
        if values.ndim != 2 or values.shape != (len(data), len(features)):
            raise ValueError("shap_values must have shape (len(data), len(feature_names))")
        if not np.isfinite(values).all():
            raise ValueError("SHAP values must be finite")
        if not features or len(set(features)) != len(features):
            raise ValueError("feature_names must be nonempty and unique")

        baselines = np.asarray(base_values, dtype=np.float64)
        if baselines.ndim == 0:
            baselines = np.full(len(data), float(baselines))
        if baselines.shape != (len(data),) or not np.isfinite(baselines).all():
            raise ValueError("base_values must be a finite scalar or one value per row")

        direction = 1.0 if higher_output_is_riskier else -1.0
        values = direction * values
        baselines = direction * baselines
        weights = (
            pd.to_numeric(data[weight_col], errors="raise").to_numpy(dtype=float)
            if weight_col is not None else np.ones(len(data), dtype=float)
        )
        if not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
            raise ValueError("Weights must be finite, nonnegative and have positive sum")

        scores = None
        if score_col:
            scores = pd.to_numeric(data[score_col], errors="raise").to_numpy(dtype=float)
            if not np.isfinite(scores).all():
                raise ValueError("Scores must be finite")
        raw_margin = baselines + values.sum(axis=1)
        max_error = None
        if raw_margin_col:
            expected = pd.to_numeric(data[raw_margin_col], errors="raise").to_numpy(dtype=float)
            max_error = float(np.max(np.abs(direction * expected - raw_margin)))
            if not np.isfinite(max_error) or max_error > max_allowed_additivity_error:
                raise ValueError(
                    f"Raw prediction and baseline + SHAP disagree: max error={max_error:.6g}"
                )

        # Nonzero-weight groups only; segments are labeled as strings for plotting.
        names = data[segment_col].astype("string").fillna("(missing)").astype(str).to_numpy()
        if (names == OVERALL).any():
            raise ValueError(f"Segment value {OVERALL!r} is reserved")
        groups = list(pd.unique(names))
        # preserve the categorical ordering if present, otherwise sort by label
        if isinstance(data[segment_col].dtype, pd.CategoricalDtype):
            ordered = [str(g) for g in data[segment_col].cat.categories]
            groups = [g for g in ordered if g in groups] + [g for g in groups if g not in ordered]
        else:
            # numeric segment labels get natural order; strings lexical order
            groups = sorted(groups, key=lambda s: (0, float(s)) if s.replace('.', '', 1).isdigit() else (1, s))

        total_weight = float(weights.sum())
        impact_records: list[dict] = []
        segment_records: list[dict] = []

        for group in [OVERALL, *groups]:
            ix = np.ones(len(data), dtype=bool) if group == OVERALL else names == group
            wx = weights[ix]
            wsum = float(wx.sum())
            if wsum == 0:
                continue
            vals = values[ix]
            means = _weighted_mean(vals, wx)
            means_abs = _weighted_mean(np.abs(vals), wx)
            means_pos = _weighted_mean(np.maximum(vals, 0.0), wx)
            means_neg = _weighted_mean(np.maximum(-vals, 0.0), wx)
            share_pos = _weighted_mean((vals > 0).astype(float), wx)
            share_neg = _weighted_mean((vals < 0).astype(float), wx)
            mean_base = float(np.dot(wx, baselines[ix]) / wsum)
            mean_raw = float(np.dot(wx, raw_margin[ix]) / wsum)
            mean_score = float(np.dot(wx, scores[ix]) / wsum) if scores is not None else np.nan
            segment_records.append({
                "segment": group, "n_rows": int(ix.sum()), "weight_sum": wsum,
                "population_share": wsum / total_weight,
                "mean_base": mean_base, "mean_raw_margin": mean_raw,
                "mean_score": mean_score,
            })
            for j, feature in enumerate(features):
                impact_records.append({
                    "segment": group, "feature": feature,
                    "mean_shap": float(means[j]),
                    "mean_abs_shap": float(means_abs[j]),
                    "mean_positive": float(means_pos[j]),
                    "mean_negative_magnitude": float(means_neg[j]),
                    "positive_share": float(share_pos[j]),
                    "negative_share": float(share_neg[j]),
                })

        impacts = pd.DataFrame(impact_records)
        overall_means = (
            impacts.loc[impacts.segment == OVERALL, ["feature", "mean_shap", "mean_abs_shap"]]
            .set_index("feature")
        )
        impacts["delta_vs_overall"] = (
            impacts["mean_shap"] - impacts["feature"].map(overall_means["mean_shap"])
        )
        denom = impacts["feature"].map(overall_means["mean_abs_shap"])
        impacts["relative_strength"] = np.where(denom > 0, impacts["mean_abs_shap"] / denom, np.nan)
        impacts["direction_consistency"] = np.where(
            impacts["mean_abs_shap"] > 0,
            np.abs(impacts["mean_shap"]) / impacts["mean_abs_shap"], 0.0,
        )
        return cls(
            impacts=impacts,
            segments=pd.DataFrame(segment_records),
            feature_names=features,
            segment_col=segment_col,
            score_col=score_col,
            weighted=(weight_col is not None),
            max_additivity_error=max_error,
            higher_output_is_riskier=higher_output_is_riskier,
        )

    @classmethod
    def from_model(
        cls,
        model: object,
        data: pd.DataFrame,
        feature_cols: Sequence[str],
        segment_col: str,
        *,
        score_col: str | None = None,
        weight_col: str | None = None,
        raw_margin_col: str | None = None,
        higher_output_is_riskier: bool = True,
        output_index: int = 1,
    ) -> SegmentImpactReport:
        """Calculate SHAP values for a tree model, then aggregate by segment.

        Uses SHAP TreeExplainer in raw model-output space. The optional
        ``output_index`` selects the modeled target when the explainer returns
        a multi-output array. Classifier wrappers may differ in output shape.
        """
        try:
            import shap
        except ImportError as ex:
            raise ImportError("Install the optional 'shap' package to use from_model") from ex
        cols = [str(x) for x in feature_cols]
        missing = [c for c in cols if c not in data.columns]
        if missing:
            raise ValueError(f"Missing model features: {missing}")
        exp = shap.TreeExplainer(model, model_output="raw")(data.loc[:, cols], check_additivity=False)
        values = np.asarray(exp.values)
        base = np.asarray(exp.base_values)
        if values.ndim == 3:
            if not (0 <= output_index < values.shape[-1]):
                raise ValueError("output_index out of range for multi-output SHAP values")
            values = values[:, :, output_index]
            if base.ndim == 2:
                base = base[:, output_index]
            elif base.ndim == 1:
                base = base[output_index]
        elif values.ndim != 2:
            raise ValueError("Unsupported SHAP shape (expected 2D or 3D)")
        return cls.from_shap(
            data, values, cols, segment_col, base_values=base,
            score_col=score_col, weight_col=weight_col,
            raw_margin_col=raw_margin_col,
            higher_output_is_riskier=higher_output_is_riskier,
        )

    @property
    def group_names(self) -> list[str]:
        return self.segments.loc[self.segments.segment != OVERALL, "segment"].tolist()

    def top_features(self, top_n: int = 10, strategy: str = "overall") -> list[str]:
        if top_n <= 0:
            raise ValueError("top_n must be positive")
        if strategy == "overall":
            rankings = self.impacts[self.impacts.segment == OVERALL].set_index("feature")["mean_abs_shap"]
        elif strategy == "max_segment":
            rankings = (self.impacts[self.impacts.segment != OVERALL]
                        .groupby("feature")["mean_abs_shap"].max())
        else:
            raise ValueError("strategy must be 'overall' or 'max_segment'")
        return rankings.sort_values(ascending=False).head(top_n).index.tolist()

    def impact_for(self, segment: str) -> pd.DataFrame:
        group = self.impacts.loc[self.impacts.segment == str(segment)].copy()
        if group.empty:
            raise KeyError(f"Unknown segment: {segment}")
        return group.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    def plot_impact_flow(self, *, top_n: int = 6, portfolio_weighted: bool = False):
        from .plots import impact_flow
        return impact_flow(self, top_n=top_n, portfolio_weighted=portfolio_weighted)

    def plot_comparative_atlas(self, *, top_n: int = 10,
                               features: Sequence[str] | None = None):
        from .plots import comparative_atlas
        return comparative_atlas(self, top_n=top_n, selected_features=features)

    def plot_segment_dashboard(self, *, top_n: int = 9, initial_segment: str | None = None):
        from .plots import segment_dashboard
        return segment_dashboard(self, top_n=top_n, initial_segment=initial_segment)

    def export(self, output_dir: str | Path, *, top_n: int = 9, flow_top_n: int = 6,
               prefix: str = "segment_impact") -> dict[str, Path]:
        """Save standalone, offline Plotly HTML charts and the analytic tables."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        outputs: dict[str, Path] = {}
        charts = {
            "01_impact_flow": self.plot_impact_flow(top_n=flow_top_n),
            "02_comparative_atlas": self.plot_comparative_atlas(top_n=top_n),
            "04_segment_dashboard": self.plot_segment_dashboard(top_n=top_n),
        }
        for key, fig in charts.items():
            target = out / f"{prefix}_{key}.html"
            fig.write_html(str(target), include_plotlyjs=True, full_html=True)
            outputs[key] = target
        for key, frame in {"feature_impacts": self.impacts, "segment_summary": self.segments}.items():
            target = out / f"{prefix}_{key}.csv"
            frame.to_csv(target, index=False)
            outputs[key] = target
        return outputs
