"""Generate three offline HTML prototypes from a synthetic credit-risk model.

Run at repository root:
    python examples/demo_lightgbm.py

The data and the model are completely synthetic; no connection to real bank data.
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from scipy.special import expit
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from segment_impact_profiler import SegmentImpactReport


def make_demo_data(n: int = 11000, seed: int = 42):
    rng = np.random.default_rng(seed)
    age = rng.integers(23, 90, size=n)
    income = np.exp(rng.normal(8.1, 0.62, n))
    income = np.clip(income, 1000, 28000)
    debt_ratio = rng.beta(2.7, 4.5, n)
    utilization = np.clip(rng.beta(2.2, 3.0, n) + 0.12 * (debt_ratio > .6), 0, 1)
    delinq = rng.poisson(0.22 + 0.75 * debt_ratio, n)
    missed_payments = rng.binomial(1, expit(-2.6 + 2.4 * utilization + 0.7 * (delinq > 0)), n)
    tenure_years = np.maximum(0, rng.gamma(3, 3.6, n) + (age-50)*.18)
    inquiries = rng.poisson(1.15 + 2.3 * utilization, n)
    num_products = 1 + rng.poisson(1.1, n)
    region_risk = rng.normal(0, 1, n)
    loan_amount = income * rng.uniform(.2, 3.0, n)
    contact_frequency = rng.poisson(2.8 + 2.5 * missed_payments, n)

    X = pd.DataFrame({
        "Age": age,
        "Monthly income": income,
        "Debt-to-income ratio": debt_ratio,
        "Credit utilization": utilization,
        "Past delinquencies": delinq,
        "Missed payments": missed_payments,
        "Account tenure": tenure_years,
        "Credit inquiries": inquiries,
        "Number of products": num_products,
        "Region risk index": region_risk,
        "Loan amount": loan_amount,
        "Collection contacts": contact_frequency,
    })
    # A plausible nonlinear credit-risk signal; not an empirical calibration.
    logit = (-3.35 + 0.55 * missed_payments + 0.4 * (delinq > 0)
             + 2.1 * debt_ratio + 1.3 * utilization + 0.04 * (age - 55)
             + 0.55 * (age > 78) - 0.000065 * income - 0.026 * tenure_years
             + 0.22 * (inquiries > 4) + 0.14 * region_risk
             + 0.26 * missed_payments * (utilization > .8))
    target = rng.binomial(1, expit(logit))
    return X, target


def main():
    X, y = make_demo_data()
    idx_train, idx_test = train_test_split(
        np.arange(len(X)), test_size=.28, random_state=12, stratify=y)
    model = LGBMClassifier(
        n_estimators=150, learning_rate=.05, num_leaves=15,
        max_depth=5, min_child_samples=90, colsample_bytree=.85,
        random_state=12, verbosity=-1,
    )
    model.fit(X.iloc[idx_train], y[idx_train])
    sample = X.iloc[idx_test].reset_index(drop=True).copy()
    rng = np.random.default_rng(101)
    sample["predicted_pd"] = model.predict_proba(sample[X.columns])[:, 1]
    sample["raw_margin"] = model.predict(sample[X.columns], raw_score=True)
    sample["sampling_weight"] = rng.uniform(.55, 2.1, size=len(sample)) * np.where(sample.Age >= 70, 1.8, 1.0)
    sample["age_band"] = pd.cut(sample.Age, bins=[0, 39, 59, 69, 110],
                                labels=["Under 40", "40–59", "60–69", "70+"])
    sample["risk_group"] = pd.qcut(sample["predicted_pd"].rank(method="first"),
                                    6, labels=[f"GH {i}" for i in range(1, 7)])

    report = SegmentImpactReport.from_model(
        model=model, data=sample, feature_cols=X.columns,
        segment_col="age_band", score_col="predicted_pd",
        weight_col="sampling_weight", raw_margin_col="raw_margin",
    )
    destination = Path(__file__).resolve().parents[1] / "demo_reports"
    paths = report.export(destination, prefix="age_band", top_n=9, flow_top_n=6)
    # Optional extra view: keep one dominant feature from flattening the scale.
    focus_features = [f for f in report.top_features(9) if f != "Age"][:8]
    focused_path = destination / "age_band_02_atlas_focus_excluding_age.html"
    report.plot_comparative_atlas(features=focus_features).write_html(
        str(focused_path), include_plotlyjs=True, full_html=True)
    paths["02_focus_excluding_age"] = focused_path
    print("Top 5 features for age 70+:")
    print(report.impact_for("70+")[
        ["feature", "mean_shap", "mean_abs_shap", "delta_vs_overall"]
    ].head().to_string(index=False))
    print("Maximum additivity error:", report.max_additivity_error)
    print("\nFiles created:")
    for label, path in paths.items():
        print(f"  {label}: {path}")

    # You can reuse the already-computed SHAP values across multiple segmentations:
    # explanation = shap.TreeExplainer(model, model_output='raw')(sample[X.columns])
    # risk_report = SegmentImpactReport.from_shap(
    #     sample, explanation.values, X.columns, segment_col='risk_group',
    #     base_values=explanation.base_values, score_col='predicted_pd',
    #     weight_col='sampling_weight')


if __name__ == "__main__":
    main()
