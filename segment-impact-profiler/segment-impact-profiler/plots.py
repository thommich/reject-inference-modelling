"""Interactive Plotly prototypes: 1 Sankey, 2 lollipop atlas, 4 dashboard.

All visualizations have no server or LLM dependency. The offline HTML exports
embed Plotly JS. Red/coral = risk-increasing and teal = risk-reducing in the
risk-oriented raw-margin space (for binary GBMs: log-odds).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .core import OVERALL, SegmentImpactReport

CORAL = "#F87171"
TEAL = "#2DD4BF"
NAVY = "#111C33"
INDIGO = "#6855B7"
DARK = "#10182A"
DARK_PANEL = "#172339"
WHITE = "#F5F7FC"
LIGHT_TEXT = "#25344D"
MUTED = "#7A8CA7"


def _segment_display(s: str) -> str:
    return "Overall" if s == OVERALL else str(s)


def _impact_frame(report: SegmentImpactReport, segment: str, features: list[str]) -> pd.DataFrame:
    return (report.impacts.loc[(report.impacts.segment == segment) &
                               (report.impacts.feature.isin(features))]
            .set_index("feature").reindex(features).reset_index())


def impact_flow(report: SegmentImpactReport, *, top_n: int = 6,
                portfolio_weighted: bool = False) -> go.Figure:
    """Sankey: segments -> feature/sign channels -> effect direction.

    Link width is avg positive/negative SHAP *magnitude*, not the frequency of
    observations ending in a high- or low-risk outcome. It must never be read
    as an actual flow of clients to risk classes.
    """
    groups = report.group_names
    if not groups:
        raise ValueError("Need at least one nonempty group")
    features = report.top_features(top_n, strategy="max_segment")
    include_other = len(features) < len(report.feature_names)
    all_feats = features + (["Other features"] if include_other else [])

    left_nodes = [f"{g}  ·  {report.segments.set_index('segment').loc[g, 'population_share']:.0%}" for g in groups]
    mids: list[tuple[str, int]] = []
    effect_names = {1: "↑ Increases modeled risk", -1: "↓ Decreases modeled risk"}

    links_by_channel = []
    for gi, group in enumerate(groups):
        data = report.impacts[report.impacts.segment == group]
        sel = data[data.feature.isin(features)].set_index("feature")
        other = data[~data.feature.isin(features)]
        multiplier = (float(report.segments.set_index("segment").loc[group, "population_share"])
                      if portfolio_weighted else 1.0)
        for feat in all_feats:
            if feat == "Other features":
                pos = float(other.mean_positive.sum())
                neg = float(other.mean_negative_magnitude.sum())
            else:
                row = sel.loc[feat]
                pos = float(row.mean_positive)
                neg = float(row.mean_negative_magnitude)
            for side, strength in [(1, pos), (-1, neg)]:
                if strength > 1e-12:
                    links_by_channel.append((gi, feat, side, strength * multiplier))
                    if (feat, side) not in mids:
                        mids.append((feat, side))

    mid_offset = len(groups)
    dest_offset = mid_offset + len(mids)
    n_dest = 2
    node_labels = (left_nodes + [f"{f} {'(+)' if s == 1 else '(−)'}" for f, s in mids]
                   + [effect_names[1], effect_names[-1]])
    node_colors = (["#A3AEC4"] * len(groups) +
                   [("#FFD8D8" if s == 1 else "#CBF7EC") for _, s in mids] +
                   [CORAL, TEAL])
    middle_lookup = {key: mid_offset + i for i, key in enumerate(mids)}

    sources, targets, values, colors, hover = [], [], [], [], []
    end_totals = {}
    for gi, feature, side, strength in links_by_channel:
        m = middle_lookup[(feature, side)]
        sources.append(gi)
        targets.append(m)
        values.append(strength)
        colors.append("rgba(248,113,113,0.37)" if side == 1 else "rgba(45,212,191,0.36)")
        hover.append(f"{groups[gi]} → {feature}<br>{'Positive' if side == 1 else 'Negative'} risk-pressure component")
        end_totals[(feature, side)] = end_totals.get((feature, side), 0) + strength
    for (feature, side), strength in end_totals.items():
        sources.append(middle_lookup[(feature, side)])
        targets.append(dest_offset if side == 1 else dest_offset + 1)
        values.append(strength)
        colors.append("rgba(248,113,113,0.50)" if side == 1 else "rgba(45,212,191,0.48)")
        hover.append(f"{feature}: total {'risk-increasing' if side == 1 else 'risk-reducing'} pressure")

    if not values:
        raise ValueError("All contribution strengths are zero")
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=node_labels, color=node_colors, pad=17, thickness=16,
                  line=dict(color="rgba(85,105,135,0.2)", width=0.6)),
        link=dict(source=sources, target=targets, value=values, color=colors,
                  customdata=hover,
                  hovertemplate="%{customdata}<br>Magnitude: %{value:.4f} log-odds units<extra></extra>"),
    ))
    unit = "population-share weighted" if portfolio_weighted else "segment average"
    fig.update_layout(
        title=dict(text=f"<b>01 · Feature Impact Flow</b><br><sup>Positive and negative SHAP components · {unit}</sup>",
                   x=0.03, xanchor="left", font=dict(size=24, color=NAVY)),
        annotations=[dict(x=0.5, y=-0.06, xref="paper", yref="paper", xanchor="center",
                          text="Flow widths are SHAP magnitudes, NOT customer movements or observed default rates.",
                          showarrow=False, font=dict(color="#697A93", size=12))],
        margin=dict(l=28, r=30, t=100, b=74),
        font=dict(family="Arial, sans-serif", color=LIGHT_TEXT, size=12),
        paper_bgcolor="#F9FBFF", plot_bgcolor="#F9FBFF",
        height=max(640, 110 * len(groups), 36 * len(mids) + 240),
    )
    return fig


def comparative_atlas(report: SegmentImpactReport, *, top_n: int = 10,
                      selected_features=None) -> go.Figure:
    """Small-multiple signed impact lollipops with shared x-axis scaling.

    Pass selected_features to compare a focused subset on the same scale, e.g.
    when one dominant predictor masks smaller but important signed effects.
    """
    features = list(selected_features) if selected_features is not None else report.top_features(top_n)
    if not features or len(set(features)) != len(features) or any(f not in report.feature_names for f in features):
        raise ValueError("selected_features must be unique, valid model feature names")
    groups = [OVERALL, *report.group_names]
    gsum = report.segments.set_index("segment")
    titles = []
    for g in groups:
        stats = gsum.loc[g]
        label = _segment_display(g)
        if g == OVERALL:
            titles.append(f"<b>{label}</b><br><sup>n={int(stats.n_rows):,}</sup>")
        else:
            titles.append(f"<b>{label}</b><br><sup>{stats.population_share:.1%} · n={int(stats.n_rows):,}</sup>")

    fig = make_subplots(rows=1, cols=len(groups), subplot_titles=titles,
                        shared_yaxes=True, horizontal_spacing=0.022)
    m = report.impacts[report.impacts.feature.isin(features)]
    global_x = max(float(np.abs(m.mean_shap).max()), 0.05) * 1.24
    for col, group in enumerate(groups, 1):
        frame = _impact_frame(report, group, features[::-1])
        for _, r in frame.iterrows():
            x = float(r.mean_shap)
            fig.add_shape(type="line", x0=0, x1=x, y0=r.feature, y1=r.feature,
                          line=dict(color=CORAL if x > 0 else TEAL, width=2),
                          row=1, col=col)
        for positive, color in [(False, TEAL), (True, CORAL)]:
            rows = frame.loc[(frame.mean_shap >= 0) if positive else (frame.mean_shap < 0)]
            if rows.empty:
                continue
            sizes = 8 + 14 * np.sqrt(rows.mean_abs_shap.to_numpy() /
                                     max(float(m.mean_abs_shap.max()), 1e-12))
            custom = np.column_stack((rows.mean_abs_shap.to_numpy(),
                                      rows.delta_vs_overall.to_numpy(),
                                      rows.positive_share.to_numpy()))
            fig.add_trace(go.Scatter(
                x=rows.mean_shap, y=rows.feature, mode="markers", showlegend=False,
                marker=dict(size=sizes, color=color, line=dict(color="white", width=1.4)),
                customdata=custom,
                hovertemplate=("<b>%{y}</b><br>Mean signed SHAP: %{x:+.4f}"
                               "<br>Mean |SHAP|: %{customdata[0]:.4f}"
                               "<br>Δ vs overall: %{customdata[1]:+.4f}"
                               "<br>Share of positive contributions: %{customdata[2]:.1%}<extra></extra>"),
            ), row=1, col=col)
        fig.add_vline(x=0, line=dict(color="#98A5B9", dash="dot", width=1.1), row=1, col=col)
        fig.update_xaxes(range=[-global_x, global_x], zeroline=False,
                         showgrid=True, gridcolor="#E9ECF3", tickformat="+.2f",
                         ticks="outside", title_text="Mean SHAP", title_font=dict(size=10),
                         tickfont=dict(size=10), row=1, col=col)
        fig.update_yaxes(tickfont=dict(size=12, color=LIGHT_TEXT),
                         categoryorder="array", categoryarray=features[::-1], row=1, col=col)
    # Explicit labels on the first facet only.
    fig.update_yaxes(showticklabels=True, row=1, col=1)
    fig.update_layout(
        title=dict(text="<b>02 · Comparative Impact Atlas</b><br><sup>Signed risk contribution by segment · circle size = mean absolute SHAP · raw-margin units</sup>",
                   x=0.02, xanchor="left", font=dict(size=23, color=NAVY)),
        margin=dict(l=max(165, max(len(f) for f in features) * 7), r=35, t=118, b=135),
        font=dict(family="Arial, sans-serif", color=LIGHT_TEXT),
        height=max(620, 50 * len(features) + 260),
        width=max(1320, 260 * len(groups)),
        paper_bgcolor="#FFFCF8", plot_bgcolor="#FFFCF8",
        annotations=[*fig.layout.annotations,
                     dict(x=0.5, y=-0.18, xref="paper", yref="paper", text=(
                         "<span style='color:#F87171'>●</span> Increases modeled risk  ·  "
                         "<span style='color:#2DD4BF'>●</span> Decreases modeled risk  ·  "
                         "Signed averages can cancel even when absolute importance is high"),
                          showarrow=False, font=dict(size=11, color="#64718C"))],
    )
    return fig


def _waterfall_trace(report: SegmentImpactReport, group: str, top_n: int) -> go.Waterfall:
    summary = report.segments.set_index("segment")
    overall = summary.loc[OVERALL]
    this = summary.loc[group]
    changes = report.impacts[report.impacts.segment == group].copy()
    changes["abs_delta"] = changes.delta_vs_overall.abs()
    changes = changes.sort_values("abs_delta", ascending=False)
    selected = changes.head(top_n)
    other_delta = float(changes.iloc[top_n:].delta_vs_overall.sum())
    base_delta = float(this.mean_base - overall.mean_base)
    x = ["Overall"] + selected.feature.tolist()
    y = [float(overall.mean_raw_margin)] + selected.delta_vs_overall.tolist()
    measure = ["absolute"] + ["relative"] * len(selected)
    if len(changes) > top_n:
        x.append("Other features")
        y.append(other_delta)
        measure.append("relative")
    if abs(base_delta) > 1e-10:
        x.append("Baseline shift")
        y.append(base_delta)
        measure.append("relative")
    x.append(str(group))
    y.append(0.0)
    measure.append("total")
    return go.Waterfall(
        x=x, y=y, measure=measure,
        increasing=dict(marker=dict(color=CORAL)),
        decreasing=dict(marker=dict(color=TEAL)),
        totals=dict(marker=dict(color="#758BB6")),
        connector=dict(line=dict(color="#7B8AA2", dash="dot")),
        text=[f"{v:+.3f}" for v in y[:-1]] + [f"{this.mean_raw_margin:.3f}"],
        textposition="outside",
        hovertemplate="%{x}<br>SHAP raw-margin step: %{y:+.4f}<extra></extra>",
        showlegend=False,
    )


def segment_dashboard(report: SegmentImpactReport, *, top_n: int = 9,
                      initial_segment: str | None = None) -> go.Figure:
    """Interactive selected-segment analysis, built entirely in Plotly.

    Dropdown changes four panels together: signed SHAP bars, differential
    SHAP dots, an additive raw-margin waterfall, and overall group scores.
    """
    groups = report.group_names
    if not groups:
        raise ValueError("Need at least one group")
    selected = initial_segment or groups[0]
    if selected not in groups:
        raise KeyError(f"Unknown initial_segment: {selected}")
    features = report.top_features(top_n, strategy="max_segment")
    summary = report.segments.set_index("segment")
    has_score = report.score_col is not None
    metric = "mean_score" if has_score else "mean_raw_margin"
    metric_title = f"Average {report.score_col} (not additive)" if has_score else "Mean risk-oriented raw margin"

    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, {"type": "xy"}]],
        subplot_titles=("Signed impact · segment", "Δ SHAP · segment versus population",
                        "Decomposition of mean prediction (raw margin)", metric_title),
        vertical_spacing=0.19, horizontal_spacing=0.13,
    )
    group_trace_indices = {}
    for group in groups:
        visible = (group == selected)
        indices = []
        frame = _impact_frame(report, group, features[::-1])
        values = frame.mean_shap.to_numpy()
        colors = [CORAL if x >= 0 else TEAL for x in values]
        custom = np.column_stack([frame.mean_abs_shap.to_numpy(),
                                  frame.positive_share.to_numpy()])
        indices.append(len(fig.data))
        fig.add_trace(go.Bar(
            x=values, y=frame.feature, orientation="h", marker_color=colors,
            customdata=custom,
            hovertemplate=("<b>%{y}</b><br>Signed SHAP: %{x:+.4f}"
                           "<br>Mean |SHAP|: %{customdata[0]:.4f}"
                           "<br>Positive contribution share: %{customdata[1]:.1%}<extra></extra>"),
            showlegend=False, visible=visible,
        ), row=1, col=1)
        indices.append(len(fig.data))
        differences = frame.delta_vs_overall.to_numpy()
        fig.add_trace(go.Scatter(
            x=differences, y=frame.feature, mode="markers",
            marker=dict(color=[CORAL if x >= 0 else TEAL for x in differences],
                        size=12, line=dict(color=WHITE, width=1)),
            customdata=frame.mean_shap,
            hovertemplate=("<b>%{y}</b><br>Δ from overall: %{x:+.4f}"
                           "<br>Within-group signed SHAP: %{customdata:+.4f}<extra></extra>"),
            showlegend=False, visible=visible,
        ), row=1, col=2)
        indices.append(len(fig.data))
        wf = _waterfall_trace(report, group, min(top_n, len(report.feature_names)))
        wf.visible = visible
        fig.add_trace(wf, row=2, col=1)
        indices.append(len(fig.data))
        to_plot = summary.loc[groups]
        fig.add_trace(go.Bar(
            x=groups, y=to_plot[metric],
            marker_color=["#6E88B7" if g == group else "#31435D" for g in groups],
            customdata=np.column_stack([to_plot.population_share, to_plot.n_rows]),
            hovertemplate=("<b>%{x}</b><br>Average: %{y:.5f}"
                           "<br>Portfolio share: %{customdata[0]:.1%}"
                           "<br>Rows: %{customdata[1]:,.0f}<extra></extra>"),
            showlegend=False, visible=visible,
        ), row=2, col=2)
        group_trace_indices[group] = indices

    # The axes are shared between dropdown states; choose symmetric bounds.
    rangeval = float(report.impacts[report.impacts.feature.isin(features)].mean_shap.abs().max())
    delta_range = float(report.impacts[report.impacts.feature.isin(features)].delta_vs_overall.abs().max())
    fig.update_xaxes(range=[-max(rangeval * 1.2, 0.03), max(rangeval * 1.2, 0.03)],
                     gridcolor="#2D3D53", zeroline=True, zerolinecolor="#8796AF",
                     row=1, col=1)
    fig.update_xaxes(range=[-max(delta_range * 1.2, 0.03), max(delta_range * 1.2, 0.03)],
                     gridcolor="#2D3D53", zeroline=True, zerolinecolor="#8796AF",
                     row=1, col=2)
    fig.update_yaxes(categoryorder="array", categoryarray=features[::-1],
                     row=1, col=1)
    fig.update_yaxes(categoryorder="array", categoryarray=features[::-1],
                     row=1, col=2)
    fig.update_xaxes(tickangle=-40, row=2, col=1)
    fig.update_xaxes(tickangle=0, row=2, col=2)
    fig.update_yaxes(gridcolor="#293C54", row=2, col=2)

    def headline(group: str) -> str:
        s = summary.loc[group]
        delta = float(s.mean_raw_margin - summary.loc[OVERALL, "mean_raw_margin"])
        score_part = f" · mean {report.score_col}: {s.mean_score:.4f}" if has_score else ""
        return (f"<b>04 · Segment Diagnostic Dashboard</b>"
                f"<br><sup>{report.segment_col}: {group} · {s.population_share:.1%} of weighted population"
                f" · Δ average raw margin: {delta:+.4f}{score_part}</sup>")

    buttons = []
    for group in groups:
        indices = set(group_trace_indices[group])
        visible_mask = [j in indices for j in range(len(fig.data))]
        buttons.append(dict(
            label=str(group), method="update",
            args=[{"visible": visible_mask}, {"title.text": headline(group)}],
        ))
    fig.update_layout(
        updatemenus=[dict(type="dropdown", buttons=buttons, direction="down",
                          x=0.985, y=1.15, xanchor="right", yanchor="top",
                          bgcolor=DARK_PANEL, bordercolor="#5D6F91",
                          font=dict(color=WHITE, size=12), showactive=True)],
        title=dict(text=headline(selected), x=0.035, xanchor="left",
                   font=dict(color=WHITE, size=23)),
        font=dict(family="Arial, sans-serif", color=WHITE, size=12),
        paper_bgcolor=DARK, plot_bgcolor=DARK_PANEL,
        height=1030, width=1510,
        margin=dict(l=175, r=60, t=152, b=135),
        bargap=0.3,
        hoverlabel=dict(bgcolor="#F6F7FA", font_color=NAVY),
    )
    for annotation in fig.layout.annotations:
        annotation.font = dict(color="#C9D5EC", size=15)
    # These explanatory notes prevent interpreting the additive log-odds steps
    # as changes in average default probability.
    fig.add_annotation(
        x=0.5, y=-0.12, xref="paper", yref="paper", showarrow=False,
        text=("Coral = pushes modeled risk up · teal = pushes modeled risk down. "
              "Waterfall changes are additive in raw-margin space (not percentage points of PD)."),
        font=dict(color="#9CACCB", size=12),
    )
    fig.update_xaxes(tickfont=dict(color="#B9C6DB"), gridcolor="#2D3D53",
                     title_font=dict(color="#B9C6DB"))
    fig.update_yaxes(tickfont=dict(color="#B9C6DB"), gridcolor="#2D3D53")
    return fig
