"""Run with: python -m pytest -q"""
import numpy as np
import pandas as pd
import pytest

from segment_impact_profiler import OVERALL, SegmentImpactReport


@pytest.fixture
def report():
    values = np.array([[1.0, -3.0], [-1.0, 1.0], [3.0, -2.0], [5.0, 0.0]])
    base = np.array([-0.1, -0.1, -0.1, -0.1])
    w = np.array([1.0, 3.0, 1.0, 2.0])
    df = pd.DataFrame({"cohort": ["A", "A", "B", "B"],
                       "weights": w, "probability": [.1, .2, .5, .9],
                       "raw": base + values.sum(axis=1)})
    return SegmentImpactReport.from_shap(
        df, values, ["f0", "f1"], "cohort", base_values=base,
        weight_col="weights", score_col="probability", raw_margin_col="raw")


def test_weighted_contributions(report):
    a = report.impact_for("A").set_index("feature")
    assert a.loc["f0", "mean_shap"] == pytest.approx(-.5)
    assert a.loc["f0", "mean_abs_shap"] == pytest.approx(1.)
    assert a.loc["f0", "positive_share"] == pytest.approx(.25)
    assert a.loc["f0", "mean_positive"] == pytest.approx(.25)
    assert a.loc["f0", "mean_negative_magnitude"] == pytest.approx(.75)
    assert report.max_additivity_error == pytest.approx(0.0)


def test_sign_and_magnitude_decompose(report):
    imp = report.impacts
    assert np.allclose(imp.mean_shap, imp.mean_positive - imp.mean_negative_magnitude)
    assert np.allclose(imp.mean_abs_shap, imp.mean_positive + imp.mean_negative_magnitude)
    assert ((imp.direction_consistency >= 0) & (imp.direction_consistency <= 1)).all()


def test_waterfall_reconciles(report):
    agg = report.segments.set_index("segment")
    for group in report.group_names:
        effects = report.impacts.loc[report.impacts.segment == group]
        lhs = agg.loc[OVERALL, "mean_raw_margin"] + effects.delta_vs_overall.sum()
        lhs += agg.loc[group, "mean_base"] - agg.loc[OVERALL, "mean_base"]
        assert lhs == pytest.approx(agg.loc[group, "mean_raw_margin"])


def test_reversed_target_sign():
    df = pd.DataFrame({"segment": ["A", "B"]})
    r = SegmentImpactReport.from_shap(df, np.array([[1.], [-2.]]), ["f"],
                                      "segment", base_values=-0.5,
                                      higher_output_is_riskier=False)
    assert r.impact_for("A").iloc[0].mean_shap == -1
    assert r.segments.loc[r.segments.segment == "A", "mean_raw_margin"].iloc[0] == -.5


def test_invalid_shape():
    with pytest.raises(ValueError, match="shape"):
        SegmentImpactReport.from_shap(pd.DataFrame({"segment": ["A"]}),
                                      np.zeros((2, 2)), ["x", "y"],
                                      "segment", base_values=0)


def test_figures_render(report):
    assert report.plot_impact_flow().data[0].type == "sankey"
    assert report.plot_comparative_atlas().data[0].type == "scatter"
    fig = report.plot_segment_dashboard(top_n=2)
    assert any(trace.type == "waterfall" for trace in fig.data)
    assert len(fig.layout.updatemenus[0].buttons) == len(report.group_names)


def test_exports_offline(tmp_path, report):
    out = report.export(tmp_path, top_n=2, flow_top_n=1)
    assert len(out) == 5
    for name, path in out.items():
        assert path.is_file()
        if name.startswith("0"):
            txt = path.read_text(encoding="utf8")
            assert "plotly.js" in txt


def test_from_lightgbm():
    pytest.importorskip("lightgbm")
    pytest.importorskip("shap")
    from lightgbm import LGBMClassifier
    from scipy.special import expit
    rng = np.random.default_rng(1234)
    x = pd.DataFrame({"x": rng.normal(size=300), "z": rng.normal(size=300)})
    y = rng.binomial(1, expit(x.x * .9 + x.z * -.8))
    model = LGBMClassifier(n_estimators=20, num_leaves=8, min_child_samples=10, verbosity=-1)
    model.fit(x, y)
    x["segment"] = np.where(x.x > 0, "positive", "negative")
    x["raw"] = model.predict(x[["x", "z"]], raw_score=True)
    r = SegmentImpactReport.from_model(model, x, ["x", "z"], "segment", raw_margin_col="raw")
    assert r.max_additivity_error < 1e-8


def test_from_xgboost():
    pytest.importorskip("xgboost")
    pytest.importorskip("shap")
    from xgboost import XGBClassifier
    rng = np.random.default_rng(456)
    X = pd.DataFrame({"x": rng.normal(size=180), "y": rng.normal(size=180)})
    target = (X.x + .7 * X.y + rng.normal(size=180) > 0).astype(int)
    model = XGBClassifier(n_estimators=15, max_depth=3, learning_rate=.1, n_jobs=2)
    model.fit(X, target)
    X["group"] = np.where(X.x > 0, "positive", "negative")
    X["raw"] = model.predict(X[["x", "y"]], output_margin=True)
    report = SegmentImpactReport.from_model(model, X, ["x", "y"], "group",
                                            raw_margin_col="raw")
    assert report.max_additivity_error < 1e-5
