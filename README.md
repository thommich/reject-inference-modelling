# denied-inference-modelling

df.columns

[
    "id",
    "reference_month", (sorted chronologically)
    "account_status",
    "lag",

    "supplier_general_score",
    "supplier_internal_score",
    "supplier_external_score",

    "target"
]




1. Data Preparation

def add_score_transitions(
    df,
    score_cols,
    id_col="id",
    time_col="reference_month"
):
    """
    Creates:

    score_prev
    score_change
    score_abs_change
    score_pct_change
    """

    df = df.sort_values([id_col, time_col]).copy()

    for score in score_cols:

        prev = f"{score}_prev"

        df[prev] = (
            df.groupby(id_col)[score]
            .shift(1)
        )

        df[f"{score}_change"] = (
            df[score] != df[prev]
        )

        df[f"{score}_abs_change"] = (
            df[score] - df[prev]
        ).abs()

    return df



2. Score Stability Analysis

def calculate_change_rate(
    df,
    score_cols
):
    results = []

    for score in score_cols:

        results.append({
            "score": score,
            "change_rate":
                df[f"{score}_change"].mean(),
            "avg_abs_change":
                df[f"{score}_abs_change"].mean(),
            "median_abs_change":
                df[f"{score}_abs_change"].median()
        })

    return pd.DataFrame(results)
    


def calculate_run_lengths(
    df,
    score_col,
    id_col="id"
):
    """
    Returns length of constant-score periods.
    """

    tmp = df.copy()

    change = (
        tmp.groupby(id_col)[score_col]
        .diff()
        .ne(0)
        .fillna(True)
    )

    tmp["run_group"] = (
        change.groupby(tmp[id_col])
        .cumsum()
    )

    runs = (
        tmp.groupby([id_col, "run_group"])
        .size()
        .reset_index(name="run_length")
    )

    return runs


def summarize_run_lengths(
    runs
):
    return {
        "mean": runs["run_length"].mean(),
        "median": runs["run_length"].median(),
        "p90": runs["run_length"].quantile(.9),
        "p95": runs["run_length"].quantile(.95)
    }



def stability_curve(
    runs,
    max_months=24
):
    curve = []

    for m in range(1, max_months + 1):

        prob = (
            runs["run_length"] >= m
        ).mean()

        curve.append({
            "months": m,
            "prob_unchanged": prob
        })

    return pd.DataFrame(curve)
    


3. Refresh Policy Simulation

def simulate_refresh_policy(
    df,
    score_col,
    refresh_every,
    id_col="id",
    time_col="reference_month"
):
    """
    refresh_every:
        1 = monthly
        3 = quarterly
        6 = semiannual
        12 = annual
    """

    df = df.sort_values([id_col, time_col]).copy()

    out_col = (
        f"{score_col}_refresh_{refresh_every}m"
    )

    def process_group(g):

        g = g.copy()

        refresh_idx = np.arange(
            0,
            len(g),
            refresh_every
        )

        values = g[score_col].iloc[
            refresh_idx
        ]

        g[out_col] = (
            values
            .reindex(g.index)
            .ffill()
        )

        return g

    return (
        df.groupby(id_col, group_keys=False)
        .apply(process_group)
    )


def create_refresh_grid(
    df,
    score_col,
    refreshes=(1,3,6,12)
):

    out = df.copy()

    for r in refreshes:

        out = simulate_refresh_policy(
            out,
            score_col,
            r
        )

    return out





4. Predictive Decay Analysis

from sklearn.metrics import roc_auc_score

def gini_score(
    y_true,
    y_pred
):
    auc = roc_auc_score(
        y_true,
        y_pred
    )

    return 2 * auc - 1


def evaluate_refresh_policies(
    df,
    target_col,
    score_col,
    refreshes=(1,3,6,12)
):

    results = []

    for r in refreshes:

        pred_col = (
            f"{score_col}_refresh_{r}m"
        )

        gini = gini_score(
            df[target_col],
            df[pred_col]
        )

        results.append({
            "refresh_months": r,
            "gini": gini
        })

    return pd.DataFrame(results)


def calculate_performance_decay(
    performance_df
):
    baseline = (
        performance_df
        .loc[
            performance_df.refresh_months == 1,
            "gini"
        ]
        .iloc[0]
    )

    performance_df = performance_df.copy()

    performance_df["gini_loss"] = (
        baseline
        - performance_df["gini"]
    )

    performance_df["relative_loss_pct"] = (
        performance_df["gini_loss"]
        / baseline
        * 100
    )

    return performance_df






5. Incremental Model Value Analysis


def refresh_policy_gain_table(
    model_factory,
    X_base_train,
    X_base_test,
    y_train,
    y_test,
    supplier_cols #['general_1m','general_3m','internal_1m']
):
    results = []

    for col in supplier_cols:

        model = model_factory()

        model.fit(
            X_base_train[[*X_base_train.columns]],
            y_train
        )

        pred = model.predict_proba(
            X_base_test
        )[:,1]

        base_gini = gini_score(
            y_test,
            pred
        )

        model2 = model_factory()

        train2 = X_base_train.copy()
        test2 = X_base_test.copy()

        train2[col] = supplier_cols[col]["train"]
        test2[col] = supplier_cols[col]["test"]

        model2.fit(train2, y_train)

        pred2 = model2.predict_proba(
            test2
        )[:,1]

        enhanced_gini = gini_score(
            y_test,
            pred2
        )

        results.append({
            "supplier_feature": col,
            "baseline_gini": base_gini,
            "enhanced_gini": enhanced_gini,
            "delta_gini":
                enhanced_gini -
                base_gini
        })

    return pd.DataFrame(results)







6. Reporting Layer

def build_cost_frontier(
    gain_df
):
    gain_df = gain_df.copy()

    gain_df["refreshes_year"] = (
        12 /
        gain_df["refresh_months"]
    )

    gain_df["gain_per_refresh"] = (
        gain_df["delta_gini"]
        /
        gain_df["refreshes_year"]
    )

    return gain_df


df = add_score_transitions(...)

change_stats = calculate_change_rate(...)

runs_general = calculate_run_lengths(...)
runs_internal = calculate_run_lengths(...)
runs_external = calculate_run_lengths(...)

stability_general = stability_curve(...)
stability_internal = stability_curve(...)
stability_external = stability_curve(...)

df = create_refresh_grid(
    df,
    "supplier_general_score"
)

general_decay = (
    evaluate_refresh_policies(...)
)

general_decay = (
    calculate_performance_decay(
        general_decay
    )
)

incremental_table = (
    refresh_policy_gain_table(...)
)

frontier = (
    build_cost_frontier(
        incremental_table
    )
)


















def build_refresh_calendar(
    months,
    refresh_every
):
    """
    months:
        sorted list of YYYY-MM values

    refresh_every:
        1,3,6,12
    """

    months = sorted(months)

    refresh_months = months[::refresh_every]

    return refresh_months






def simulate_calendar_refresh(
    df,
    score_col,
    refresh_every,
    time_col="reference_month"
):

    df = df.copy()

    months = (
        sorted(
            df[time_col]
            .unique()
        )
    )

    refresh_months = (
        build_refresh_calendar(
            months,
            refresh_every
        )
    )

    out_col = (
        f"{score_col}_refresh_{refresh_every}m"
    )

    df["_refresh"] = (
        df[time_col]
        .isin(refresh_months)
    )

    df.loc[
        ~df["_refresh"],
        score_col
    ] = np.nan

    df[out_col] = (
        df.groupby("id")[score_col]
        .ffill()
    )

    return (
        df
        .drop(columns="_refresh")
    )







def add_score_age(
    df,
    refresh_col,
    id_col="id"
):
    """
    Number of months since last refresh.
    """

    df = df.copy()

    age_col = (
        refresh_col +
        "_age"
    )

    refresh_event = (
        df[refresh_col]
        !=
        df.groupby(id_col)[refresh_col]
          .shift()
    )

    df[age_col] = (
        refresh_event
        .groupby(df[id_col])
        .cumsum()
    )

    return df











def deduplicate_current_status(
    df,
    id_col="id",
    time_col="reference_month",
    status_col="account_status",
    priority=("client", "external")
):
    """
    Keeps one row per ID-month.

    If multiple statuses exist for the same ID-month,
    keeps the status with highest priority.
    """

    df = df.copy()

    priority_map = {
        status: rank
        for rank, status in enumerate(priority)
    }

    df["_priority"] = df[status_col].map(priority_map)

    df = (
        df.sort_values("_priority")
          .drop_duplicates(
              subset=[id_col, time_col],
              keep="first"
          )
          .drop(columns="_priority")
    )

    return df

df_model = deduplicate_current_status(df)






def deduplicate_smallest_lag(
    df,
    id_col="id",
    time_col="reference_month",
    lag_col="lag"
):
    """
    Keeps the row with the smallest lag
    for each ID-month.
    """

    return (
        df.sort_values(lag_col)
          .drop_duplicates(
              subset=[id_col, time_col],
              keep="first"
          )
    )










def investigate_duplicates(
    df,
    id_col="id",
    time_col="reference_month"
):
    dup = (
        df.groupby([id_col, time_col])
          .size()
          .reset_index(name="n_rows")
    )

    dup = dup.loc[
        dup["n_rows"] > 1
    ]

    return dup


dup_cases = investigate_duplicates(df)

print(len(dup_cases))
print(
    dup_cases["n_rows"]
    .value_counts()
)



