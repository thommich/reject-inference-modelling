# denied-inference-modelling

import decimal
import numbers
import os
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
except ImportError:
    pa = None
    pc = None
    ds = None


# ==========================================================
# Legacy KBinsDiscretizer & categorizacao (backwards-compat)
# ==========================================================
def _get_base_classes():
    from sklearn.base import BaseEstimator, TransformerMixin

    return BaseEstimator, TransformerMixin


class KBinsDiscretizer:
    """Discretizer compatible with the original pytinela_v2 API."""

    def __init__(self, n_bins=5, encode='onehot', strategy='quantile'):
        self.n_bins = n_bins
        self.encode = encode
        self.strategy = strategy

    def get_params(self, deep=True):
        return {'n_bins': self.n_bins, 'encode': self.encode, 'strategy': self.strategy}

    def set_params(self, **params):
        for k, v in params.items():
            setattr(self, k, v)
        return self

    def fit(self, X, y=None):
        from sklearn.preprocessing import OneHotEncoder
        from sklearn.utils.validation import check_array

        X = check_array(X, dtype='numeric')

        valid_encode = ('onehot', 'onehot-dense', 'ordinal')
        if self.encode not in valid_encode:
            raise ValueError(
                "Valid options for 'encode' are {}. Got encode={!r} instead.".format(
                    valid_encode, self.encode
                )
            )
        valid_strategy = ('uniform', 'quantile', 'kmeans')
        if self.strategy not in valid_strategy:
            raise ValueError(
                "Valid options for 'strategy' are {}. Got strategy={!r} instead.".format(
                    valid_strategy, self.strategy
                )
            )

        n_features = X.shape[1]
        n_bins = self._validate_n_bins(n_features)

        bin_edges = np.zeros(n_features, dtype=object)
        for jj in range(n_features):
            column = X[:, jj]
            col_min, col_max = column.min(), column.max()

            if col_min == col_max:
                warnings.warn("Feature %d is constant and will be replaced with 0." % jj)
                n_bins[jj] = 1
                bin_edges[jj] = np.array([-np.inf, np.inf])
                continue

            if self.strategy == 'uniform':
                bin_edges[jj] = np.linspace(col_min, col_max, n_bins[jj] + 1)

            elif self.strategy == 'quantile':
                quantiles = np.linspace(0, 100, n_bins[jj] + 1)
                bin_edges[jj] = np.asarray(np.percentile(column, quantiles))

            elif self.strategy == 'kmeans':
                from sklearn.cluster import KMeans

                uniform_edges = np.linspace(col_min, col_max, n_bins[jj] + 1)
                init = (uniform_edges[1:] + uniform_edges[:-1])[:, None] * 0.5
                km = KMeans(n_clusters=n_bins[jj], init=init, n_init=1)
                centers = km.fit(column[:, None]).cluster_centers_[:, 0]
                centers.sort()
                bin_edges[jj] = (centers[1:] + centers[:-1]) * 0.5
                bin_edges[jj] = np.r_[col_min, bin_edges[jj], col_max]

            if self.strategy in ('quantile', 'kmeans'):
                mask = np.ediff1d(bin_edges[jj], to_begin=np.inf) > 1e-8
                bin_edges[jj] = bin_edges[jj][mask]
                if len(bin_edges[jj]) - 1 != n_bins[jj]:
                    warnings.warn(
                        'Bins whose width are too small (i.e., <= 1e-8) in feature %d '
                        'are removed. Consider decreasing the number of bins.' % jj
                    )
                    n_bins[jj] = len(bin_edges[jj]) - 1

        self.bin_edges_ = bin_edges
        self.n_bins_ = n_bins

        if 'onehot' in self.encode:
            cats = [np.arange(i) for i in self.n_bins_]
            try:
                self._encoder = OneHotEncoder(
                    categories=cats, sparse_output=(self.encode == 'onehot')
                )
            except TypeError:
                self._encoder = OneHotEncoder(
                    categories=cats, sparse=(self.encode == 'onehot')
                )
            self._encoder.fit(np.zeros((1, len(self.n_bins_)), dtype=int))

        return self

    def _validate_n_bins(self, n_features):
        from sklearn.utils.validation import check_array

        orig_bins = self.n_bins
        if isinstance(orig_bins, numbers.Number):
            if not isinstance(orig_bins, numbers.Integral):
                raise ValueError(
                    "{} received an invalid n_bins type. Received {}, expected int.".format(
                        KBinsDiscretizer.__name__, type(orig_bins).__name__
                    )
                )
            if orig_bins < 2:
                raise ValueError(
                    "{} received an invalid number of bins. Received {}, expected at least 2.".format(
                        KBinsDiscretizer.__name__, orig_bins
                    )
                )
            return np.full(n_features, orig_bins, dtype=int)

        n_bins = check_array(orig_bins, dtype=int, copy=True, ensure_2d=False)

        if n_bins.ndim > 1 or n_bins.shape[0] != n_features:
            raise ValueError("n_bins must be a scalar or array of shape (n_features,).")

        bad_nbins_value = (n_bins < 2) | (n_bins != orig_bins)
        violating_indices = np.where(bad_nbins_value)[0]
        if violating_indices.shape[0] > 0:
            indices = ", ".join(str(i) for i in violating_indices)
            raise ValueError(
                "{} received an invalid number of bins at indices {}. "
                "Number of bins must be at least 2, and must be an int.".format(
                    KBinsDiscretizer.__name__, indices
                )
            )
        return n_bins

    def transform(self, X):
        from sklearn.utils.validation import FLOAT_DTYPES, check_array, check_is_fitted

        check_is_fitted(self, ['n_bins', 'encode', 'strategy'])

        Xt = check_array(X, copy=True, dtype=FLOAT_DTYPES)
        n_features = self.n_bins_.shape[0]
        if Xt.shape[1] != n_features:
            raise ValueError(
                "Incorrect number of features. Expecting {}, received {}.".format(
                    n_features, Xt.shape[1]
                )
            )

        bin_edges = self.bin_edges_
        for jj in range(Xt.shape[1]):
            rtol = 1.0e-5
            atol = 1.0e-8
            eps = atol + rtol * np.abs(Xt[:, jj])
            Xt[:, jj] = np.digitize(Xt[:, jj] + eps, bin_edges[jj][1:])
        np.clip(Xt, 0, self.n_bins_ - 1, out=Xt)

        if self.encode == 'ordinal':
            return Xt

        return self._encoder.transform(Xt)

    def inverse_transform(self, Xt):
        from sklearn.utils.validation import FLOAT_DTYPES, check_array, check_is_fitted

        check_is_fitted(self, ['n_bins', 'encode', 'strategy'])

        if 'onehot' in self.encode:
            Xt = self._encoder.inverse_transform(Xt)

        Xinv = check_array(Xt, copy=True, dtype=FLOAT_DTYPES)
        n_features = self.n_bins_.shape[0]
        if Xinv.shape[1] != n_features:
            raise ValueError(
                "Incorrect number of features. Expecting {}, received {}.".format(
                    n_features, Xinv.shape[1]
                )
            )

        for jj in range(n_features):
            bin_edges = self.bin_edges_[jj]
            bin_centers = (bin_edges[1:] + bin_edges[:-1]) * 0.5
            Xinv[:, jj] = bin_centers[np.asarray(Xinv[:, jj], dtype=np.intp)]

        return Xinv


def categorizacao(
    serie_entrada,
    qtd_grupos=5,
    modo_categorizacao='quantile',
    interv_como_grupo=False,
):
    """Categorize a numeric Series into string bin labels using vectorized binning."""
    x = pd.to_numeric(serie_entrada, errors='coerce').to_numpy(dtype=np.float64, copy=False)
    valid = ~np.isnan(x)
    xv = x[valid]
    if len(xv) == 0:
        return pd.Series('nan', index=serie_entrada.index, dtype=object)

    edges = _compute_bin_edges(xv, qtd_grupos=qtd_grupos, modo_categorizacao=modo_categorizacao)
    inner = edges[1:-1]
    n_bins = max(len(edges) - 1, 1)

    codes = np.zeros(len(x), dtype=np.int32)
    if len(inner) > 0:
        if len(inner) <= 16:
            for e in inner:
                codes += x > e
        else:
            codes[valid] = np.searchsorted(inner, xv, side='left')

    if interv_como_grupo:
        labels = np.array(_format_interval_labels(inner, n_bins), dtype=object)
    else:
        labels = np.array([str(float(i)) for i in range(n_bins)], dtype=object)

    out = np.empty(len(x), dtype=object)
    out[valid] = labels[codes[valid]]
    out[~valid] = 'nan'
    return pd.Series(out, index=serie_entrada.index, dtype=object)


# ==========================================================
# PyArrow & Input Helpers
# ==========================================================
def _is_arrow_table(data):
    return pa is not None and isinstance(data, pa.Table)


def _is_arrow_dataset(data):
    return ds is not None and isinstance(data, ds.Dataset)


def _resolve_n_jobs(n_jobs):
    if n_jobs is None or n_jobs == 0:
        return 1
    if n_jobs < 0:
        return max(1, (os.cpu_count() or 1) + 1 + n_jobs)
    return max(1, int(n_jobs))


def arrow_to_pandas_optimized(
    table,
    downcast_floats=False,
    dictionary_encode_strings=True,
    dict_max_cardinality_ratio=0.5,
    self_destruct=True,
    show_progress=True,
):
    """
    Convert a pyarrow.Table to a memory-efficient pandas DataFrame:
      - Casts decimal128/decimal256 to float64 (or float32) in C++ before to_pandas(),
        preventing Python Decimal object bloat.
      - Optionally dictionary-encodes low-cardinality string columns into pandas category.
      - Uses split_blocks=True and self_destruct=True to avoid 2x RAM spikes.
    """
    if pa is None or not isinstance(table, pa.Table):
        raise TypeError("Expected a pyarrow.Table instance.")

    n_rows = table.num_rows
    new_arrays = []
    target_float = pa.float32() if downcast_floats else pa.float64()

    iterator = zip(table.column_names, table.columns)
    for _, col in tqdm(
        iterator,
        total=table.num_columns,
        desc="PyArrow -> Pandas",
        unit="col",
        ncols=100,
        disable=not show_progress,
    ):
        t = col.type
        if pa.types.is_decimal(t):
            col = pc.cast(col, target_float)
        elif downcast_floats and pa.types.is_float64(t):
            col = pc.cast(col, pa.float32())
        elif dictionary_encode_strings and (
            pa.types.is_string(t) or pa.types.is_large_string(t)
        ):
            if n_rows > 0 and _classify_arrow_column(col) != 'numeric_object':
                n_uniq = pc.count_distinct(col).as_py()
                if n_uniq is not None and n_uniq <= n_rows * dict_max_cardinality_ratio:
                    col = pc.dictionary_encode(col)
        new_arrays.append(col)

    optimized = pa.Table.from_arrays(new_arrays, names=table.column_names)
    return optimized.to_pandas(
        split_blocks=True,
        self_destruct=self_destruct,
        ignore_metadata=True,
    )


# ==========================================================
# IEP Calculation (Symmetric inf when either period is 0)
# ==========================================================
def _calcula_iep_matrix(valores, eps=0.0):
    """
    Vectorized IEP (PSI) calculation over a (T, G) probability matrix.

    When eps == 0.0:
      - valores == 0 and linha_ref == 0 -> 0.0
      - valores > 0  and linha_ref == 0 -> +inf
      - valores == 0 and linha_ref > 0  -> +inf
      - valores > 0  and linha_ref > 0  -> (valores - linha_ref) * log(valores / linha_ref)
      - Period 0 always equals 0.0.
    """
    if valores.shape[0] == 0 or valores.shape[1] == 0:
        return np.zeros(valores.shape[0], dtype=np.float64)

    linha_ref = valores[0, :]

    if eps > 0.0:
        v = np.where(valores == 0.0, eps, valores)
        r = np.where(linha_ref == 0.0, eps, linha_ref)
        eixo_y = np.sum((v - r) * np.log(v / r), axis=1)
        eixo_y[0] = 0.0
        return eixo_y

    both_pos = (valores > 0.0) & (linha_ref > 0.0)
    one_zero = (valores > 0.0) ^ (linha_ref > 0.0)

    safe_v = np.where(both_pos, valores, 1.0)
    safe_r = np.where(both_pos, linha_ref, 1.0)
    contrib = np.where(both_pos, (safe_v - safe_r) * np.log(safe_v / safe_r), 0.0)
    contrib = np.where(one_zero, np.inf, contrib)

    eixo_y = np.sum(contrib, axis=1)
    eixo_y[0] = 0.0
    return eixo_y


def calcula_iep(pivotada, eps=0.0):
    """Compute IEP time series from a pivoted period-by-category DataFrame."""
    eixo_x = pivotada.index
    valores = pivotada.to_numpy(dtype=np.float64, copy=False)
    eixo_y = _calcula_iep_matrix(valores, eps=eps)
    return eixo_x, eixo_y.tolist()


# ==========================================================
# Zero-Copy Column Classification
# ==========================================================
def _classify_object_series(series, sample_size=100):
    """
    Inspect non-null values of an object/string Series without casting the full
    column. Returns one of: 'all_null', 'numeric_object', 'categorical'.
    """
    n = len(series)
    if n == 0:
        return 'all_null'

    non_null_vals = []
    # Scan progressively in positional slices to stay O(1) when early rows have data
    bounds = [(0, min(4096, n))]
    if n > 4096:
        bounds.append((4096, min(65536, n)))
    if n > 65536:
        step = 262144
        for start in range(65536, n, step):
            bounds.append((start, min(start + step, n)))

    for start, stop in bounds:
        chunk = series.iloc[start:stop]
        mask = pd.notna(chunk)
        if mask.any():
            vals = chunk[mask].iloc[: sample_size - len(non_null_vals)].tolist()
            non_null_vals.extend(vals)
            if len(non_null_vals) >= sample_size:
                break

    if not non_null_vals:
        return 'all_null'

    first_val = non_null_vals[0]
    if isinstance(first_val, (bool, np.bool_)):
        return 'categorical'
    if isinstance(first_val, (decimal.Decimal, numbers.Number)):
        return 'numeric_object'

    parsed = pd.to_numeric(pd.Series(non_null_vals, dtype=object), errors='coerce')
    if parsed.notna().sum() >= len(non_null_vals) * 0.9:
        return 'numeric_object'
    return 'categorical'


def _classify_arrow_column(pa_col, sample_size=100):
    """Classify a PyArrow Array/ChunkedArray using its schema and non-null probe."""
    t = pa_col.type
    if pa.types.is_null(t):
        return 'all_null'
    if pa.types.is_boolean(t) or pa.types.is_dictionary(t) or pa.types.is_temporal(t):
        return 'categorical'
    if pa.types.is_integer(t) or pa.types.is_floating(t) or pa.types.is_decimal(t):
        return 'numeric_native'
    if pa.types.is_string(t) or pa.types.is_large_string(t):
        if isinstance(pa_col, pa.ChunkedArray):
            chunks = pa_col.chunks
        else:
            chunks = [pa_col]
        non_null_vals = []
        for chunk in chunks:
            dropped = pc.drop_null(chunk)
            if len(dropped) > 0:
                need = sample_size - len(non_null_vals)
                non_null_vals.extend(dropped.slice(0, need).to_pylist())
                if len(non_null_vals) >= sample_size:
                    break
        if not non_null_vals:
            return 'all_null'
        parsed = pd.to_numeric(pd.Series(non_null_vals, dtype=object), errors='coerce')
        if parsed.notna().sum() >= len(non_null_vals) * 0.9:
            return 'numeric_object'
        return 'categorical'
    return 'categorical'


def _classify_pandas_column(series, dt, sample_size=100):
    """Classify a pandas Series without copying or scanning the full DataFrame."""
    if isinstance(dt, pd.CategoricalDtype):
        return 'categorical'
    if pd.api.types.is_bool_dtype(dt):
        return 'categorical'
    if pd.api.types.is_datetime64_any_dtype(dt) or pd.api.types.is_timedelta64_dtype(dt):
        return 'categorical'

    if pa is not None and isinstance(dt, pd.ArrowDtype):
        pa_type = dt.pyarrow_dtype
        if pa.types.is_null(pa_type):
            return 'all_null'
        if (
            pa.types.is_boolean(pa_type)
            or pa.types.is_dictionary(pa_type)
            or pa.types.is_temporal(pa_type)
        ):
            return 'categorical'
        if (
            pa.types.is_integer(pa_type)
            or pa.types.is_floating(pa_type)
            or pa.types.is_decimal(pa_type)
        ):
            return 'numeric_native'
        return _classify_object_series(series, sample_size=sample_size)

    if pd.api.types.is_numeric_dtype(dt):
        return 'numeric_native'

    return _classify_object_series(series, sample_size=sample_size)


def _classify_columns(data, vars_list, sample_size=100):
    """Return a dict mapping each column name to its classification kind."""
    kinds = {}
    if _is_arrow_table(data):
        col_names = set(data.column_names)
        for v in vars_list:
            if v in col_names:
                kinds[v] = _classify_arrow_column(data.column(v), sample_size=sample_size)
        return kinds

    dtypes = data.dtypes
    for v in vars_list:
        if v in dtypes.index:
            kinds[v] = _classify_pandas_column(data[v], dtypes[v], sample_size=sample_size)
    return kinds


# ==========================================================
# Vectorized Temporal, Binning & Contingency Engine
# ==========================================================
def _encode_temporal(temporal_col):
    """
    Encode var_temporal once into:
      - t_codes: int32 array (0..T-1, or -1 for nulls)
      - period_labels: list[str] sorted lexicographically by str(period)
    """
    if pa is not None and isinstance(temporal_col, (pa.Array, pa.ChunkedArray)):
        series = temporal_col.to_pandas()
    elif isinstance(temporal_col, pd.Series):
        series = temporal_col
    else:
        series = pd.Series(temporal_col)

    raw_codes, uniques = pd.factorize(series, use_na_sentinel=True)
    if len(uniques) == 0:
        return np.full(len(series), -1, dtype=np.int32), []

    labels = [str(u) for u in uniques]
    order = np.argsort(labels, kind='mergesort')
    inv_order = np.empty(len(order), dtype=np.int32)
    inv_order[order] = np.arange(len(order), dtype=np.int32)

    valid = raw_codes >= 0
    t_codes = np.full(len(series), -1, dtype=np.int32)
    if valid.all():
        t_codes = inv_order[raw_codes]
    elif valid.any():
        t_codes[valid] = inv_order[raw_codes[valid]]

    period_labels = [labels[i] for i in order]
    return t_codes, period_labels


def _has_fewer_than_k_distinct(xv, k):
    """
    Short-circuiting check whether 1D array xv has strictly fewer than k distinct values.
    Returns (True, sorted_unique_values) or (False, None).
    """
    n = len(xv)
    if n == 0:
        return True, np.empty(0, dtype=xv.dtype)

    u = np.unique(xv[:8192])
    if len(u) >= k:
        return False, None

    if n > 8192:
        step = 262144
        for start in range(8192, n, step):
            u = np.union1d(u, np.unique(xv[start : min(start + step, n)]))
            if len(u) >= k:
                return False, None

    return True, u


def _compute_bin_edges(xv, qtd_grupos=5, modo_categorizacao='quantile', quantile_sample_size=None):
    """Compute sorted unique bin edges for non-null numeric 1D array xv."""
    if modo_categorizacao == 'quantile':
        if quantile_sample_size is not None and len(xv) > quantile_sample_size:
            step = max(1, len(xv) // int(quantile_sample_size))
            xv_q = xv[::step]
        else:
            xv_q = xv
        q = np.linspace(0.0, 1.0, qtd_grupos + 1)
        return np.unique(np.quantile(xv_q, q))

    if modo_categorizacao == 'uniform':
        col_min = float(np.min(xv))
        col_max = float(np.max(xv))
        if col_min == col_max:
            return np.array([col_min], dtype=np.float64)
        return np.unique(np.linspace(col_min, col_max, qtd_grupos + 1))

    if modo_categorizacao == 'kmeans':
        from sklearn.cluster import KMeans

        col_min = float(np.min(xv))
        col_max = float(np.max(xv))
        if col_min == col_max:
            return np.array([col_min], dtype=np.float64)
        uniform_edges = np.linspace(col_min, col_max, qtd_grupos + 1)
        init = (uniform_edges[1:] + uniform_edges[:-1])[:, None] * 0.5
        km = KMeans(n_clusters=qtd_grupos, init=init, n_init=1)
        centers = km.fit(xv[:, None]).cluster_centers_[:, 0]
        centers.sort()
        mid = (centers[1:] + centers[:-1]) * 0.5
        return np.unique(np.r_[col_min, mid, col_max])

    raise ValueError(f"Unsupported modo_categorizacao: {modo_categorizacao!r}")


def _format_interval_labels(inner_edges, n_bins):
    """Format interval labels matching categorizacao(..., interv_como_grupo=True)."""
    bordas = np.concatenate(([-np.inf], inner_edges, [np.inf]))
    labels = []
    for i in range(n_bins):
        left = str(bordas[i])
        right = str(bordas[i + 1])
        bracket = ')' if np.isinf(bordas[i + 1]) else ']'
        labels.append(f'({left}, {right}{bracket}')
    return labels


def _bin_numeric_array(
    x,
    qtd_grupos=5,
    modo_categorizacao='quantile',
    incluir_na=True,
    quantile_sample_size=None,
    return_labels=False,
):
    """
    Bin a 1D numeric NumPy array into int32 group codes (0..G_total-1).
    Returns (g_codes, G_total, valid_mask_or_None, group_labels_or_None).
    """
    n = len(x)
    if n == 0:
        return (
            np.empty(0, dtype=np.int32),
            0,
            None,
            ([] if return_labels else None),
        )

    if np.issubdtype(x.dtype, np.floating):
        valid = ~np.isnan(x)
        has_na = not bool(valid.all())
        xv = x[valid] if has_na else x
    else:
        valid = None
        has_na = False
        xv = x

    if len(xv) == 0:
        if incluir_na:
            return (
                np.zeros(n, dtype=np.int32),
                1,
                None,
                (['nan'] if return_labels else None),
            )
        return (
            np.empty(n, dtype=np.int32),
            0,
            np.zeros(n, dtype=bool),
            ([] if return_labels else None),
        )

    is_low_card, uniq_vals = _has_fewer_than_k_distinct(xv, qtd_grupos)

    if is_low_card:
        g_bins = len(uniq_vals)
        if has_na:
            g_codes = np.empty(n, dtype=np.int32)
            g_codes[valid] = np.searchsorted(uniq_vals, xv)
        else:
            g_codes = np.searchsorted(uniq_vals, xv).astype(np.int32, copy=False)
        labels = [str(v) for v in uniq_vals] if return_labels else None
    else:
        edges = _compute_bin_edges(
            xv,
            qtd_grupos=qtd_grupos,
            modo_categorizacao=modo_categorizacao,
            quantile_sample_size=quantile_sample_size,
        )
        inner = edges[1:-1]
        g_bins = max(len(edges) - 1, 1)

        if len(inner) == 0:
            g_codes = np.zeros(n, dtype=np.int32)
        elif len(inner) <= 16:
            g_codes = np.zeros(n, dtype=np.int32)
            if has_na:
                for e in inner:
                    g_codes += x > e
            else:
                for e in inner:
                    g_codes += x > e
        else:
            if has_na:
                g_codes = np.zeros(n, dtype=np.int32)
                g_codes[valid] = np.searchsorted(inner, xv, side='left')
            else:
                g_codes = np.searchsorted(inner, xv, side='left').astype(np.int32, copy=False)

        labels = _format_interval_labels(inner, g_bins) if return_labels else None

    if has_na and incluir_na:
        g_codes[~valid] = g_bins
        g_total = g_bins + 1
        mask_out = None
        if return_labels:
            labels.append('nan')
    elif has_na and not incluir_na:
        g_total = g_bins
        mask_out = valid
    else:
        g_total = g_bins
        mask_out = None

    return g_codes, g_total, mask_out, labels


def _extract_arrow_numeric(pa_col, kind):
    """Extract a 1D NumPy numeric array from a PyArrow Array or ChunkedArray."""
    if kind == 'numeric_object':
        return pd.to_numeric(pa_col.to_pandas(), errors='coerce').to_numpy(
            dtype=np.float64, copy=False
        )
    t = pa_col.type
    if pa.types.is_decimal(t):
        return pc.cast(pa_col, pa.float64()).to_numpy(zero_copy_only=False)
    if pa.types.is_floating(t):
        if pa_col.null_count > 0:
            return pc.fill_null(pa_col, np.nan).to_numpy(zero_copy_only=False)
        return pa_col.to_numpy(zero_copy_only=False)
    if pa.types.is_integer(t):
        if pa_col.null_count == 0:
            return pa_col.to_numpy(zero_copy_only=False)
        return pc.cast(pa_col, pa.float64()).to_numpy(zero_copy_only=False)
    return pd.to_numeric(pa_col.to_pandas(), errors='coerce').to_numpy(
        dtype=np.float64, copy=False
    )


def _extract_pandas_numeric(series, kind):
    """Extract a 1D NumPy numeric array from a pandas Series."""
    if kind == 'numeric_object':
        return pd.to_numeric(series, errors='coerce').to_numpy(dtype=np.float64, copy=False)

    dt = series.dtype
    if pa is not None and isinstance(dt, pd.ArrowDtype):
        return _extract_arrow_numeric(series.array._pa_array, kind)

    if isinstance(dt, pd.api.extensions.ExtensionDtype):
        return series.to_numpy(dtype=np.float64, na_value=np.nan)

    return series.to_numpy(copy=False)


def _encode_arrow_categorical(pa_col, incluir_na=True, return_labels=False):
    """Encode a PyArrow categorical/string/bool column into int32 codes without Python strings."""
    n = len(pa_col)
    if n == 0:
        return (
            np.empty(0, dtype=np.int32),
            0,
            None,
            ([] if return_labels else None),
        )

    t = pa_col.type
    if pa.types.is_null(t):
        if incluir_na:
            return (
                np.zeros(n, dtype=np.int32),
                1,
                None,
                (['nan'] if return_labels else None),
            )
        return (
            np.empty(n, dtype=np.int32),
            0,
            np.zeros(n, dtype=bool),
            ([] if return_labels else None),
        )

    enc = pa_col if pa.types.is_dictionary(t) else pc.dictionary_encode(pa_col)
    if isinstance(enc, pa.ChunkedArray):
        if enc.num_chunks == 0:
            return (
                np.empty(0, dtype=np.int32),
                0,
                None,
                ([] if return_labels else None),
            )
        enc = enc.unify_dictionaries().combine_chunks()

    n_uniq = len(enc.dictionary)
    indices = enc.indices
    has_na = indices.null_count > 0

    if has_na:
        raw_codes = indices.fill_null(-1).to_numpy(zero_copy_only=False).astype(
            np.int32, copy=False
        )
        na_mask = raw_codes < 0
        if incluir_na:
            g_codes = np.where(na_mask, n_uniq, raw_codes).astype(np.int32, copy=False)
            g_total = n_uniq + 1
            mask_out = None
        else:
            g_codes = raw_codes
            g_total = n_uniq
            mask_out = ~na_mask
    else:
        g_codes = indices.to_numpy(zero_copy_only=False).astype(np.int32, copy=False)
        g_total = n_uniq
        mask_out = None

    if return_labels:
        labels = [str(v) for v in enc.dictionary.to_pylist()]
        if has_na and incluir_na:
            labels.append('nan')
    else:
        labels = None

    return g_codes, g_total, mask_out, labels


def _encode_pandas_categorical(series, incluir_na=True, return_labels=False):
    """Encode a pandas categorical/object/bool Series into int32 codes."""
    dt = series.dtype
    if pa is not None and isinstance(dt, pd.ArrowDtype):
        return _encode_arrow_categorical(
            series.array._pa_array, incluir_na=incluir_na, return_labels=return_labels
        )

    if isinstance(dt, pd.CategoricalDtype):
        raw_codes = series.cat.codes.to_numpy(copy=False)
        uniques = series.cat.categories
    else:
        raw_codes, uniques = pd.factorize(series, use_na_sentinel=True)

    n_uniq = len(uniques)
    na_mask = raw_codes < 0
    has_na = bool(na_mask.any())

    if has_na and incluir_na:
        g_codes = np.where(na_mask, n_uniq, raw_codes).astype(np.int32, copy=False)
        g_total = n_uniq + 1
        mask_out = None
    elif has_na and not incluir_na:
        g_codes = raw_codes.astype(np.int32, copy=False)
        g_total = n_uniq
        mask_out = ~na_mask
    else:
        g_codes = raw_codes.astype(np.int32, copy=False)
        g_total = n_uniq
        mask_out = None

    if return_labels:
        labels = [str(u) for u in uniques]
        if has_na and incluir_na:
            labels.append('nan')
    else:
        labels = None

    return g_codes, g_total, mask_out, labels


def _compute_iep_from_codes(
    t_codes,
    period_labels,
    g_codes,
    G_total,
    valid_mask=None,
    eps=0.0,
    return_pivot=False,
    group_labels=None,
):
    """
    Compute IEP scores from integer temporal codes and integer group codes.
    Uses O(N) np.bincount for typical cardinalities and a sparse np.unique
    fallback when T * G_total > 10,000,000.
    """
    if len(period_labels) == 0 or G_total == 0:
        return 0.0, {}, None

    t_valid = t_codes >= 0
    if valid_mask is not None:
        keep = t_valid & valid_mask
    else:
        keep = t_valid

    if not keep.all():
        t_c = t_codes[keep]
        g_c = g_codes[keep]
    else:
        t_c = t_codes
        g_c = g_codes

    if len(t_c) == 0:
        return 0.0, {}, None

    T = len(period_labels)
    flat_size = int(T) * int(G_total)

    if flat_size <= 10_000_000 or return_pivot:
        flat_idx = (
            t_c.astype(np.int64, copy=False) * int(G_total)
            + g_c.astype(np.int64, copy=False)
        )
        counts = np.bincount(flat_idx, minlength=flat_size).reshape(T, G_total)
        row_sums = counts.sum(axis=1)
        active = row_sums > 0
        if not active.any():
            return 0.0, {}, None

        counts_active = counts[active]
        active_labels = [period_labels[i] for i in np.flatnonzero(active)]
        probs = counts_active / row_sums[active, None]
        eixo_y = _calcula_iep_matrix(probs, eps=eps)
        iep_por_periodo = {p: float(v) for p, v in zip(active_labels, eixo_y)}
        iep_max = float(np.max(eixo_y))

        if return_pivot:
            pivotada = pd.DataFrame(probs, index=active_labels, columns=group_labels)
        else:
            pivotada = None
        return iep_max, iep_por_periodo, pivotada

    # Sparse bounded-memory fallback for ultra-high-cardinality columns
    flat_idx = (
        t_c.astype(np.int64, copy=False) * int(G_total)
        + g_c.astype(np.int64, copy=False)
    )
    uniq, cnt = np.unique(flat_idx, return_counts=True)
    t_idx = (uniq // int(G_total)).astype(np.int32)
    g_idx = uniq % int(G_total)

    row_sums = np.bincount(t_idx, weights=cnt, minlength=T)
    active_t = np.flatnonzero(row_sums > 0)
    if len(active_t) == 0:
        return 0.0, {}, None

    t0 = active_t[0]
    m0 = t_idx == t0
    g0 = g_idx[m0]
    p0 = cnt[m0] / row_sums[t0]

    iep_por_periodo = {}
    for t in active_t:
        label = period_labels[t]
        if t == t0:
            iep_por_periodo[label] = 0.0
            continue
        mt = t_idx == t
        gt = g_idx[mt]
        pt = cnt[mt] / row_sums[t]

        if eps == 0.0:
            if len(gt) != len(g0):
                iep_por_periodo[label] = float(np.inf)
            else:
                pos = np.searchsorted(g0, gt)
                if np.any(pos >= len(g0)) or not np.array_equal(g0[pos], gt):
                    iep_por_periodo[label] = float(np.inf)
                else:
                    p0_aligned = p0[pos]
                    iep_por_periodo[label] = float(np.sum((pt - p0_aligned) * np.log(pt / p0_aligned)))
        else:
            g_all = np.union1d(g0, gt)
            v0 = np.full(len(g_all), eps, dtype=np.float64)
            vt = np.full(len(g_all), eps, dtype=np.float64)
            v0[np.searchsorted(g_all, g0)] = p0
            vt[np.searchsorted(g_all, gt)] = pt
            iep_por_periodo[label] = float(np.sum((vt - v0) * np.log(vt / v0)))

    iep_max = float(max(iep_por_periodo.values()))
    return iep_max, iep_por_periodo, None


def _all_null_result(t_codes, period_labels, incluir_na, return_pivot=False):
    active_t = np.unique(t_codes[t_codes >= 0])
    if len(active_t) == 0 or not incluir_na:
        return 0.0, {}, None
    active_labels = [period_labels[i] for i in active_t]
    iep_por_periodo = {p: 0.0 for p in active_labels}
    pivotada = (
        pd.DataFrame(np.ones((len(active_labels), 1), dtype=np.float64), index=active_labels, columns=['nan'])
        if return_pivot
        else None
    )
    return 0.0, iep_por_periodo, pivotada


def _evaluate_column_from_source(
    source,
    col_name,
    kind,
    t_codes,
    period_labels,
    qtd_grupos=5,
    modo_categorizacao='quantile',
    incluir_na=True,
    eps=0.0,
    quantile_sample_size=None,
    return_pivot=False,
):
    """Compute IEP for one column from a DataFrame or pyarrow.Table."""
    if kind == 'all_null':
        return _all_null_result(t_codes, period_labels, incluir_na, return_pivot=return_pivot)

    is_arrow = _is_arrow_table(source)

    if kind in ('numeric_native', 'numeric_object'):
        x = (
            _extract_arrow_numeric(source.column(col_name), kind)
            if is_arrow
            else _extract_pandas_numeric(source[col_name], kind)
        )
        g_codes, g_total, valid_mask, labels = _bin_numeric_array(
            x,
            qtd_grupos=qtd_grupos,
            modo_categorizacao=modo_categorizacao,
            incluir_na=incluir_na,
            quantile_sample_size=quantile_sample_size,
            return_labels=return_pivot,
        )
    else:
        if is_arrow:
            g_codes, g_total, valid_mask, labels = _encode_arrow_categorical(
                source.column(col_name),
                incluir_na=incluir_na,
                return_labels=return_pivot,
            )
        else:
            g_codes, g_total, valid_mask, labels = _encode_pandas_categorical(
                source[col_name],
                incluir_na=incluir_na,
                return_labels=return_pivot,
            )

    return _compute_iep_from_codes(
        t_codes,
        period_labels,
        g_codes,
        g_total,
        valid_mask=valid_mask,
        eps=eps,
        return_pivot=return_pivot,
        group_labels=labels,
    )


# ==========================================================
# Plotting & PDF Helpers
# ==========================================================
def _ensure_parent_dir(path):
    """Ensure parent directory exists for an explicit file path (str or PathLike)."""
    parent = os.path.dirname(os.fspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def _render_plot(pivotada, var_analisada, iep_por_periodo, figsize, salvar, mostrar):
    if salvar is True:
        raise ValueError("salvar must be False or an explicit output file path.")

    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "monospace"

    eixo_x = list(iep_por_periodo.keys())
    eixo_y = list(iep_por_periodo.values())

    fig, axes = plt.subplots(
        nrows=2,
        ncols=1,
        sharex=True,
        figsize=figsize,
        gridspec_kw={'height_ratios': [1, 3]},
    )
    fig.set_dpi(150)
    fig.suptitle(var_analisada, fontsize="x-large")

    axes[0].set_title('Índice de Estabilidade Populacional')
    axes[0].plot(list(range(len(eixo_x))), eixo_y, '.-')

    axes[1].set_title('Distribuição das categorias ao longo do tempo')
    pivotada.plot(kind='bar', stacked=True, colormap='Paired', legend='reverse', ax=axes[1])

    for i in range(2):
        tick_vals = axes[i].get_yticks()
        axes[i].set_yticklabels(['{:.0%}'.format(tv) for tv in tick_vals])

    plt.legend(frameon=True, loc='center left', bbox_to_anchor=(1, 0.5))

    if salvar is not False:
        nome = os.fspath(salvar)
        _ensure_parent_dir(nome)
        plt.savefig(nome, transparent=False, bbox_inches='tight', pad_inches=0.2)
        plt.close(fig)
        return nome

    if mostrar:
        plt.show()

    plt.close(fig)
    return None


def cria_pdf(saida, lista_entrada, dir=None):
    from fpdf import FPDF
    from PIL import Image

    dir_path = os.fspath(dir) if dir else None
    img_paths = [
        os.path.join(dir_path, str(page)) if dir_path else os.fspath(page)
        for page in lista_entrada
    ]

    cover = Image.open(img_paths[0])
    width, height = cover.size

    pdf = FPDF(unit="pt", format=[width, height])

    for img_path in img_paths:
        pdf.add_page()
        pdf.image(img_path, 0, 0)

    out_name = os.fspath(saida)
    if not out_name.lower().endswith(".pdf"):
        out_name += ".pdf"
    out_path = (
        os.path.join(dir_path, out_name)
        if (dir_path and not os.path.isabs(out_name))
        else out_name
    )
    _ensure_parent_dir(out_path)
    pdf.output(out_path, "F")


# ==========================================================
# Public Single & Multi-Variable APIs
# ==========================================================
def pytinela(
    df,
    var_temporal,
    var_analisada,
    qtd_grupos=5,
    modo_categorizacao='quantile',
    incluir_na=True,
    salvar=False,
    mostrar=True,
    figsize=(8, 4),
    eps=0.0,
    quantile_sample_size=None,
):
    """Compute IEP for a single variable (DataFrame or pyarrow.Table)."""
    if salvar is True:
        raise ValueError("salvar must be False or an explicit output file path.")

    sem_plot = (salvar is False) and (not mostrar)

    t_col = df.column(var_temporal) if _is_arrow_table(df) else df[var_temporal]
    t_codes, period_labels = _encode_temporal(t_col)
    kinds = _classify_columns(df, [var_analisada])
    kind = kinds[var_analisada]

    iep_max, iep_por_periodo, pivotada = _evaluate_column_from_source(
        df,
        var_analisada,
        kind,
        t_codes,
        period_labels,
        qtd_grupos=qtd_grupos,
        modo_categorizacao=modo_categorizacao,
        incluir_na=incluir_na,
        eps=eps,
        quantile_sample_size=quantile_sample_size,
        return_pivot=not sem_plot,
    )

    if sem_plot or pivotada is None:
        return iep_max, iep_por_periodo, None

    nome = _render_plot(pivotada, var_analisada, iep_por_periodo, figsize, salvar, mostrar)
    return iep_max, iep_por_periodo, nome


def _run_threaded_batch(
    source,
    vars_batch,
    kinds,
    t_codes,
    period_labels,
    qtd_grupos,
    modo_categorizacao,
    incluir_na,
    eps,
    quantile_sample_size,
    max_workers,
    pbar,
):
    results = []
    if max_workers == 1 or len(vars_batch) <= 1:
        for var in vars_batch:
            iep_max, iep_por_periodo, _ = _evaluate_column_from_source(
                source,
                var,
                kinds[var],
                t_codes,
                period_labels,
                qtd_grupos=qtd_grupos,
                modo_categorizacao=modo_categorizacao,
                incluir_na=incluir_na,
                eps=eps,
                quantile_sample_size=quantile_sample_size,
                return_pivot=False,
            )
            dados = {'variavel': var, 'iep_max': iep_max}
            dados.update(iep_por_periodo)
            results.append(dados)
            pbar.update(1)
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                _evaluate_column_from_source,
                source,
                var,
                kinds[var],
                t_codes,
                period_labels,
                qtd_grupos,
                modo_categorizacao,
                incluir_na,
                eps,
                quantile_sample_size,
                False,
            ): var
            for var in vars_batch
        }
        for fut in as_completed(future_map):
            var = future_map[fut]
            iep_max, iep_por_periodo, _ = fut.result()
            dados = {'variavel': var, 'iep_max': iep_max}
            dados.update(iep_por_periodo)
            results.append(dados)
            pbar.update(1)
    return results


def Pytinela(
    df,
    var_temporal,
    vars_analisadas,
    qtd_grupos=5,
    modo_categorizacao='quantile',
    incluir_na=True,
    dir_imagens=None,
    arq_pdf=None,
    salvar_imagens=False,
    salvar_pdf=False,
    mostrar_imagens=False,
    completo_csv=None,
    excluir_csv=None,
    iep_threshold=0.1,
    n_jobs=-1,
    eps=0.0,
    quantile_sample_size=None,
    arrow_col_batch_size=128,
    show_progress=True,
):
    """
    Compute IEP across all vars_analisadas using vectorized NumPy/PyArrow operations
    and GIL-free multithreading. Accepts pd.DataFrame, pyarrow.Table, or pyarrow.dataset.Dataset.
    All file/directory output paths are passed explicitly as parameters (no hardcoded paths).
    """
    if salvar_imagens and not dir_imagens:
        raise ValueError("dir_imagens must be provided when salvar_imagens=True.")
    if salvar_imagens and salvar_pdf and not arq_pdf:
        raise ValueError("arq_pdf must be provided when salvar_pdf=True.")

    vars_list = list(vars_analisadas)
    sem_plot = (not salvar_imagens) and (not mostrar_imagens)

    dir_imagens_str = os.fspath(dir_imagens) if dir_imagens else None
    if salvar_imagens and dir_imagens_str:
        os.makedirs(dir_imagens_str, exist_ok=True)

    meta = {
        'qtd_grupos': qtd_grupos,
        'modo_categorizacao': modo_categorizacao,
        'incluir_na': incluir_na,
    }
    if not vars_list:
        empty_df = pd.DataFrame(columns=['variavel', 'iep_max'])
        if completo_csv is not None:
            _ensure_parent_dir(completo_csv)
            empty_df.to_csv(os.fspath(completo_csv), index=False)
        if excluir_csv is not None:
            _ensure_parent_dir(excluir_csv)
            empty_df.to_csv(os.fspath(excluir_csv), index=False)
        return meta, empty_df

    is_dataset = _is_arrow_dataset(df)
    if is_dataset:
        t_table = df.to_table(columns=[var_temporal])
        t_codes, period_labels = _encode_temporal(t_table.column(var_temporal))
        del t_table
    elif _is_arrow_table(df):
        t_codes, period_labels = _encode_temporal(df.column(var_temporal))
    else:
        t_codes, period_labels = _encode_temporal(df[var_temporal])

    max_workers = _resolve_n_jobs(n_jobs)
    results = []
    image_files = []

    if sem_plot:
        with tqdm(
            total=len(vars_list),
            desc="Pytinela",
            unit="var",
            ncols=100,
            disable=not show_progress,
        ) as pbar:
            if is_dataset:
                available = set(df.schema.names)
                valid_vars = [v for v in vars_list if v in available]
                for start in range(0, len(valid_vars), arrow_col_batch_size):
                    batch_vars = valid_vars[start : start + arrow_col_batch_size]
                    batch_table = df.to_table(columns=batch_vars)
                    kinds = _classify_columns(batch_table, batch_vars)
                    results.extend(
                        _run_threaded_batch(
                            batch_table,
                            batch_vars,
                            kinds,
                            t_codes,
                            period_labels,
                            qtd_grupos,
                            modo_categorizacao,
                            incluir_na,
                            eps,
                            quantile_sample_size,
                            max_workers,
                            pbar,
                        )
                    )
                    del batch_table
            else:
                kinds = _classify_columns(df, vars_list)
                valid_vars = [v for v in vars_list if v in kinds]
                results.extend(
                    _run_threaded_batch(
                        df,
                        valid_vars,
                        kinds,
                        t_codes,
                        period_labels,
                        qtd_grupos,
                        modo_categorizacao,
                        incluir_na,
                        eps,
                        quantile_sample_size,
                        max_workers,
                        pbar,
                    )
                )
    else:
        # Plotting mode (matplotlib is not thread-safe, so render sequentially)
        with tqdm(
            total=len(vars_list),
            desc="Pytinela (plot)",
            unit="var",
            ncols=100,
            disable=not show_progress,
        ) as pbar:
            if is_dataset:
                available = set(df.schema.names)
                batches = [
                    vars_list[i : i + arrow_col_batch_size]
                    for i in range(0, len(vars_list), arrow_col_batch_size)
                ]
                idx_offset = 0
                for batch_vars in batches:
                    present = [v for v in batch_vars if v in available]
                    batch_table = df.to_table(columns=present)
                    kinds = _classify_columns(batch_table, present)
                    for var in batch_vars:
                        idx_offset += 1
                        if var not in kinds:
                            pbar.update(1)
                            continue
                        iep_max, iep_por_periodo, pivotada = _evaluate_column_from_source(
                            batch_table,
                            var,
                            kinds[var],
                            t_codes,
                            period_labels,
                            qtd_grupos=qtd_grupos,
                            modo_categorizacao=modo_categorizacao,
                            incluir_na=incluir_na,
                            eps=eps,
                            quantile_sample_size=quantile_sample_size,
                            return_pivot=True,
                        )
                        if pivotada is not None:
                            salvar_path = (
                                os.path.join(dir_imagens_str, f"{str(idx_offset).zfill(3)}_{var}.jpeg")
                                if salvar_imagens
                                else False
                            )
                            nome = _render_plot(
                                pivotada, var, iep_por_periodo, (8, 4), salvar_path, mostrar_imagens
                            )
                            if nome:
                                image_files.append(os.path.basename(nome))
                        dados = {'variavel': var, 'iep_max': iep_max}
                        dados.update(iep_por_periodo)
                        results.append(dados)
                        pbar.update(1)
                    del batch_table
            else:
                kinds = _classify_columns(df, vars_list)
                for idx, var in enumerate(vars_list, start=1):
                    if var not in kinds:
                        pbar.update(1)
                        continue
                    iep_max, iep_por_periodo, pivotada = _evaluate_column_from_source(
                        df,
                        var,
                        kinds[var],
                        t_codes,
                        period_labels,
                        qtd_grupos=qtd_grupos,
                        modo_categorizacao=modo_categorizacao,
                        incluir_na=incluir_na,
                        eps=eps,
                        quantile_sample_size=quantile_sample_size,
                        return_pivot=True,
                    )
                    if pivotada is not None:
                        salvar_path = (
                            os.path.join(dir_imagens_str, f"{str(idx).zfill(3)}_{var}.jpeg")
                            if salvar_imagens
                            else False
                        )
                        nome = _render_plot(
                            pivotada, var, iep_por_periodo, (8, 4), salvar_path, mostrar_imagens
                        )
                        if nome:
                            image_files.append(os.path.basename(nome))
                    dados = {'variavel': var, 'iep_max': iep_max}
                    dados.update(iep_por_periodo)
                    results.append(dados)
                    pbar.update(1)

        if salvar_imagens and salvar_pdf and image_files:
            cria_pdf(arq_pdf, image_files, dir=dir_imagens_str)

    arq_ordenados = pd.DataFrame(results)
    if len(arq_ordenados) > 0 and 'iep_max' in arq_ordenados.columns:
        arq_ordenados = arq_ordenados.sort_values('iep_max', ascending=False).reset_index(drop=True)
    else:
        arq_ordenados = pd.DataFrame(columns=['variavel', 'iep_max'])

    if completo_csv is not None:
        _ensure_parent_dir(completo_csv)
        arq_ordenados.to_csv(os.fspath(completo_csv), index=False)
    if excluir_csv is not None:
        _ensure_parent_dir(excluir_csv)
        excluir_df = arq_ordenados[arq_ordenados['iep_max'] > iep_threshold].reset_index(drop=True)
        excluir_df.to_csv(os.fspath(excluir_csv), index=False)

    return meta, arq_ordenados


def _evaluate_column_all_subpops(
    source,
    col_name,
    kind,
    subpop_slices,
    period_labels,
    qtd_grupos,
    modo_categorizacao,
    incluir_na,
    eps,
    quantile_sample_size,
):
    """Evaluate one column across all subpopulations in a single pass."""
    rows = []
    if kind == 'all_null':
        for subpop, _, t_sub in subpop_slices:
            iep_max, iep_por_periodo, _ = _all_null_result(
                t_sub, period_labels, incluir_na, return_pivot=False
            )
            dados = {'variavel': col_name, 'iep_max': iep_max}
            dados.update(iep_por_periodo)
            dados['subpop'] = subpop
            rows.append(dados)
        return rows

    is_arrow = _is_arrow_table(source)

    if kind in ('numeric_native', 'numeric_object'):
        x = (
            _extract_arrow_numeric(source.column(col_name), kind)
            if is_arrow
            else _extract_pandas_numeric(source[col_name], kind)
        )
        for subpop, idx_arr, t_sub in subpop_slices:
            x_sub = x[idx_arr]
            g_codes, g_total, valid_mask, _ = _bin_numeric_array(
                x_sub,
                qtd_grupos=qtd_grupos,
                modo_categorizacao=modo_categorizacao,
                incluir_na=incluir_na,
                quantile_sample_size=quantile_sample_size,
                return_labels=False,
            )
            iep_max, iep_por_periodo, _ = _compute_iep_from_codes(
                t_sub,
                period_labels,
                g_codes,
                g_total,
                valid_mask=valid_mask,
                eps=eps,
                return_pivot=False,
            )
            dados = {'variavel': col_name, 'iep_max': iep_max}
            dados.update(iep_por_periodo)
            dados['subpop'] = subpop
            rows.append(dados)
        return rows

    # Categorical: encode once globally, then slice codes per subpop
    if is_arrow:
        g_codes, g_total, valid_mask, _ = _encode_arrow_categorical(
            source.column(col_name), incluir_na=incluir_na, return_labels=False
        )
    else:
        g_codes, g_total, valid_mask, _ = _encode_pandas_categorical(
            source[col_name], incluir_na=incluir_na, return_labels=False
        )

    for subpop, idx_arr, t_sub in subpop_slices:
        g_sub = g_codes[idx_arr]
        mask_sub = valid_mask[idx_arr] if valid_mask is not None else None
        iep_max, iep_por_periodo, _ = _compute_iep_from_codes(
            t_sub,
            period_labels,
            g_sub,
            g_total,
            valid_mask=mask_sub,
            eps=eps,
            return_pivot=False,
        )
        dados = {'variavel': col_name, 'iep_max': iep_max}
        dados.update(iep_por_periodo)
        dados['subpop'] = subpop
        rows.append(dados)
    return rows


def Pytinela_parallel(
    segment_col,
    df_full,
    var_temporal,
    vars_finalistas,
    qtd_grupos=5,
    modo_categorizacao='quantile',
    incluir_na=True,
    excluir_csv=None,
    completo_csv=None,
    n_jobs=-1,
    eps=0.0,
    iep_threshold=0.1,
    quantile_sample_size=None,
    arrow_col_batch_size=128,
    show_progress=True,
):
    """
    Column-major multithreaded IEP across all subpopulations.
    Eliminates SharedMemory/pickle/DataFrame copies so working RAM stays < ~1 GB
    even at 2M rows x 7,000 columns. Accepts pd.DataFrame, pyarrow.Table, or pyarrow.dataset.Dataset.
    All output CSV paths are passed explicitly via excluir_csv / completo_csv (no hardcoded paths).
    """
    vars_list = list(vars_finalistas)
    is_dataset = _is_arrow_dataset(df_full)

    if is_dataset:
        meta_table = df_full.to_table(columns=[segment_col, var_temporal])
        t_codes, period_labels = _encode_temporal(meta_table.column(var_temporal))
        seg_series = meta_table.column(segment_col).to_pandas()
        del meta_table
    elif _is_arrow_table(df_full):
        t_codes, period_labels = _encode_temporal(df_full.column(var_temporal))
        seg_series = df_full.column(segment_col).to_pandas()
    else:
        t_codes, period_labels = _encode_temporal(df_full[var_temporal])
        seg_series = df_full[segment_col]

    seg_codes, seg_uniques = pd.factorize(seg_series, use_na_sentinel=True)
    del seg_series

    # Sort subpopulations deterministically (matching sorted(df[segment_col].unique()))
    valid_seg_indices = [(i, u) for i, u in enumerate(seg_uniques)]
    valid_seg_indices.sort(key=lambda item: item[1])

    subpop_slices = []
    for seg_id, subpop in valid_seg_indices:
        idx_arr = np.flatnonzero(seg_codes == seg_id)
        if len(idx_arr) > 0:
            subpop_slices.append((subpop, idx_arr, t_codes[idx_arr]))

    del seg_codes

    max_workers = _resolve_n_jobs(n_jobs)
    all_rows = []

    def _run_batch(source, batch_vars, kinds, pbar):
        if max_workers == 1 or len(batch_vars) <= 1:
            for var in batch_vars:
                all_rows.extend(
                    _evaluate_column_all_subpops(
                        source,
                        var,
                        kinds[var],
                        subpop_slices,
                        period_labels,
                        qtd_grupos,
                        modo_categorizacao,
                        incluir_na,
                        eps,
                        quantile_sample_size,
                    )
                )
                pbar.update(1)
            return

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _evaluate_column_all_subpops,
                    source,
                    var,
                    kinds[var],
                    subpop_slices,
                    period_labels,
                    qtd_grupos,
                    modo_categorizacao,
                    incluir_na,
                    eps,
                    quantile_sample_size,
                )
                for var in batch_vars
            ]
            for fut in as_completed(futures):
                all_rows.extend(fut.result())
                pbar.update(1)

    with tqdm(
        total=len(vars_list),
        desc="Pytinela_parallel",
        unit="var",
        ncols=100,
        disable=not show_progress,
    ) as pbar:
        if is_dataset:
            available = set(df_full.schema.names)
            valid_vars = [v for v in vars_list if v in available]
            for start in range(0, len(valid_vars), arrow_col_batch_size):
                batch_vars = valid_vars[start : start + arrow_col_batch_size]
                batch_table = df_full.to_table(columns=batch_vars)
                kinds = _classify_columns(batch_table, batch_vars)
                _run_batch(batch_table, batch_vars, kinds, pbar)
                del batch_table
        else:
            kinds = _classify_columns(df_full, vars_list)
            valid_vars = [v for v in vars_list if v in kinds]
            _run_batch(df_full, valid_vars, kinds, pbar)

    completo_df = pd.DataFrame(all_rows)
    if len(completo_df) > 0:
        completo_df = completo_df.sort_values(
            ['subpop', 'iep_max'], ascending=[True, False]
        ).reset_index(drop=True)
        excluir_df = completo_df[completo_df['iep_max'] > iep_threshold].reset_index(drop=True)
    else:
        completo_df = pd.DataFrame(columns=['variavel', 'iep_max', 'subpop'])
        excluir_df = completo_df.copy()

    if completo_csv is not None:
        _ensure_parent_dir(completo_csv)
        completo_df.to_csv(os.fspath(completo_csv), index=False)
    if excluir_csv is not None:
        _ensure_parent_dir(excluir_csv)
        excluir_df.to_csv(os.fspath(excluir_csv), index=False)
    return completo_df










































    from __future__ import annotations

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from scipy.linalg.blas import ssyrk
from scipy.stats import rankdata


def _is_valid_spearman_column(s: pd.Series) -> bool:
    """Return True if a Series is valid for Spearman correlation."""
    if isinstance(s.dtype, pd.CategoricalDtype):
        return bool(s.cat.ordered or len(s.cat.categories) <= 2)
    return bool(
        pd.api.types.is_numeric_dtype(s.dtype)
        and not pd.api.types.is_complex_dtype(s.dtype)
    )


def get_valid_spearman_columns(df: pd.DataFrame) -> list:
    """Return column names eligible for Spearman correlation."""
    return [
        df.columns[j]
        for j in range(df.shape[1])
        if _is_valid_spearman_column(df.iloc[:, j])
    ]


def fast_spearman_corr(
    df: pd.DataFrame,
    row_chunk_size: int = 100_000,
    n_jobs: int | None = None,
    use_memmap: bool = True,
    memmap_dir: str | None = None,
    filter_invalid_cols: bool = True,
    return_dataframe: bool = True,
) -> pd.DataFrame | np.ndarray:
    """
    Compute the exact Spearman correlation matrix on CPU for very large
    DataFrames (e.g., 2M rows x 7K columns) with bounded memory usage.

    Supports numeric, boolean, ordered categorical, and binary categorical
    columns. Requires NaN-free values in the included columns.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    row_chunk_size : int, default 100_000
        Rows processed per BLAS SSYRK chunk (~2.8 GB for 7K cols x 100K rows).
    n_jobs : int | None, default None
        Worker threads for Phase 1 ranking. Defaults to min(cpu_count, 16).
    use_memmap : bool, default True
        Store the (n_cols, n_rows) float32 standardized rank matrix on disk
        (~56 GB for 7K x 2M) to keep extra RAM usage ~4 GB. Set False if you
        have >64 GB free RAM.
    memmap_dir : str | None, default None
        Directory for the temporary memmap file (point to a fast NVMe SSD).
    filter_invalid_cols : bool, default True
        If True, automatically skip non-numeric and unordered multi-class
        categorical columns without copying `df`. If False, raise TypeError
        when such a column is encountered.
    return_dataframe : bool, default True
        Return a labeled pd.DataFrame if True, else a raw float64 np.ndarray.
    """
    n_rows = df.shape[0]

    if filter_invalid_cols:
        valid_idx = [
            j
            for j in range(df.shape[1])
            if _is_valid_spearman_column(df.iloc[:, j])
        ]
    else:
        valid_idx = list(range(df.shape[1]))

    out_columns = df.columns[valid_idx]
    n_cols = len(valid_idx)

    if n_cols == 0:
        empty = np.empty((0, 0), dtype=np.float64)
        return (
            pd.DataFrame(empty, index=out_columns, columns=out_columns)
            if return_dataframe
            else empty
        )
    if n_rows < 2:
        nans = np.full((n_cols, n_cols), np.nan, dtype=np.float64)
        return (
            pd.DataFrame(nans, index=out_columns, columns=out_columns)
            if return_dataframe
            else nans
        )

    if n_jobs is None:
        n_jobs = min(os.cpu_count() or 4, 16)

    tmpdir_obj = None
    z_mat = None

    try:
        # Shape (n_cols, n_rows) C-contiguous (~56 GB for 7K x 2M float32):
        # - Phase 1 writes each ranked column sequentially (8 MB contiguous).
        # - Phase 2 reads row chunks cleanly across all columns.
        if use_memmap:
            tmpdir_obj = tempfile.TemporaryDirectory(dir=memmap_dir)
            mmap_path = os.path.join(tmpdir_obj.name, "ranks_f32.dat")
            z_mat = np.memmap(
                mmap_path, dtype=np.float32, mode="w+", shape=(n_cols, n_rows)
            )
        else:
            z_mat = np.empty((n_cols, n_rows), dtype=np.float32)

        const_cols = np.zeros(n_cols, dtype=bool)

        # Phase 1: Parallel column ranking & L2 normalization
        # NumPy/SciPy C loops release the GIL, avoiding DataFrame copies.
        def _rank_column(out_j: int) -> None:
            orig_j = valid_idx[out_j]
            s = df.iloc[:, orig_j]
            col_name = df.columns[orig_j]

            if isinstance(s.dtype, pd.CategoricalDtype):
                if not s.cat.ordered and len(s.cat.categories) > 2:
                    raise TypeError(
                        f"Column {orig_j} ({col_name!r}) is an unordered "
                        f"categorical with {len(s.cat.categories)} levels. "
                        "Spearman requires ordered or binary categories."
                    )
                codes = s.cat.codes.to_numpy(copy=False)
                if (codes == -1).any():  # pandas encodes missing categories as -1
                    raise ValueError(
                        f"Column {orig_j} ({col_name!r}) contains missing categories."
                    )
                # O(N) exact average-tie ranking via category counts
                counts = np.bincount(codes, minlength=len(s.cat.categories))
                avg_ranks = np.cumsum(counts) - 0.5 * (counts - 1)
                r = avg_ranks[codes]
            else:
                if not pd.api.types.is_numeric_dtype(s.dtype) or pd.api.types.is_complex_dtype(s.dtype):
                    raise TypeError(
                        f"Column {orig_j} ({col_name!r}) has unsupported dtype {s.dtype}."
                    )
                if pd.api.types.is_extension_array_dtype(s.dtype):
                    col = s.to_numpy(dtype=np.float64, na_value=np.nan)
                else:
                    col = s.to_numpy(copy=False)

                if np.issubdtype(col.dtype, np.floating) and np.isnan(col).any():
                    raise ValueError(
                        f"Column {orig_j} ({col_name!r}) contains NaNs. "
                        "Drop or impute missing values before calling fast_spearman_corr."
                    )
                r = rankdata(col, method="average")

            # Standardize in float64 to preserve numerical accuracy
            r -= r.mean()
            norm = np.linalg.norm(r)
            if norm == 0.0:
                const_cols[out_j] = True
                z_mat[out_j, :] = 0.0
            else:
                r /= norm
                z_mat[out_j, :] = r.astype(np.float32)

        with ThreadPoolExecutor(max_workers=n_jobs) as pool:
            for _ in pool.map(_rank_column, range(n_cols)):
                pass

        if isinstance(z_mat, np.memmap):
            z_mat.flush()

        # Phase 2: Row-chunked Z @ Z.T via BLAS SSYRK (~2.8 GB per 100K-row chunk)
        corr = np.zeros((n_cols, n_cols), dtype=np.float64)

        for start in range(0, n_rows, row_chunk_size):
            end = min(start + row_chunk_size, n_rows)
            chunk = np.ascontiguousarray(z_mat[:, start:end], dtype=np.float32)
            # chunk.T is Fortran-contiguous (chunk_len, n_cols) -> zero-copy in BLAS
            partial = ssyrk(alpha=1.0, a=chunk.T, trans=1, lower=0)
            corr += partial

        # Mirror upper triangle to lower triangle in-place (zero extra memory)
        for i in range(1, n_cols):
            corr[i, :i] = corr[:i, i]

        # Clamp tiny float32 rounding drift and enforce exact diagonal / constant NaNs
        np.clip(corr, -1.0, 1.0, out=corr)
        np.fill_diagonal(corr, 1.0)
        if const_cols.any():
            corr[const_cols, :] = np.nan
            corr[:, const_cols] = np.nan

        if return_dataframe:
            return pd.DataFrame(corr, index=out_columns, columns=out_columns)
        return corr

    finally:
        # Release memmap handle before deleting temp directory (required on Windows)
        if isinstance(z_mat, np.memmap):
            z_mat._mmap.close()
        del z_mat
        if tmpdir_obj is not None:
            tmpdir_obj.cleanup()


if __name__ == "__main__":
    # Quick correctness check against pandas on mixed column types
    rng = np.random.default_rng(42)
    n = 50_000
    x = rng.normal(size=n).astype(np.float32)

    sample_df = pd.DataFrame(
        {
            "num_a": x,
            "num_b": (x * 2.0 + rng.normal(scale=0.5, size=n)).astype(np.float32),
            "ordinal": pd.Categorical(
                pd.qcut(x + rng.normal(scale=0.3, size=n), 3, labels=["low", "med", "high"]),
                categories=["low", "med", "high"],
                ordered=True,
            ),
            "binary_cat": pd.Categorical(np.where(x > 0, "yes", "no")),
            "nominal_skip": pd.Categorical(rng.choice(["red", "green", "blue"], size=n)),
            "text_skip": rng.choice(["a", "b", "c"], size=n),
            "const_col": np.ones(n, dtype=np.float32),
        }
    )

    corr_fast = fast_spearman_corr(sample_df, row_chunk_size=10_000, use_memmap=True)

    # Compare against pandas after manually encoding the valid categoricals
    ref_df = sample_df[get_valid_spearman_columns(sample_df)].copy()
    for c in ref_df.columns:
        if isinstance(ref_df[c].dtype, pd.CategoricalDtype):
            ref_df[c] = ref_df[c].cat.codes
    corr_ref = ref_df.corr(method="spearman")

    assert np.allclose(corr_fast.to_numpy(), corr_ref.to_numpy(), atol=1e-5, equal_nan=True)
    print("Matched pandas Spearman correlation within 1e-5!")
    print(corr_fast.round(4))



corr = fast_spearman_corr(
    df,
    row_chunk_size=100_000,
    use_memmap=True,
    memmap_dir="/path/to/fast_nvme_tmp",  # ~56 GB temporary space
    filter_invalid_cols=True,             # skips nominal/text cols without copying df
)
