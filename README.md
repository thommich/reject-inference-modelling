# denied-inference-modelling

from __future__ import annotations

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

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
    row_chunk_size: int = 50_000,
    n_jobs: int | None = None,
    use_memmap: bool = True,
    memmap_dir: str | None = None,
    filter_invalid_cols: bool = True,
    nan_policy: Literal["pairwise", "midrank"] = "pairwise",
    min_periods: int = 2,
    return_dataframe: bool = True,
) -> pd.DataFrame | np.ndarray:
    """
    Compute the Spearman correlation matrix on CPU for very large DataFrames
    (e.g., 2M rows x 7K columns) with bounded memory usage and internal NaN
    handling.

    Supports numeric, boolean, ordered categorical, and binary categorical
    columns (including missing values / NaNs).

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    row_chunk_size : int, default 50_000
        Rows processed per BLAS chunk (~5 GB peak extra RAM in "pairwise" mode
        or ~2.5 GB in "midrank"/NaN-free mode for 7K columns).
    n_jobs : int | None, default None
        Worker threads for Phase 1 ranking. Defaults to min(cpu_count, 16).
    use_memmap : bool, default True
        Store the (n_cols, n_rows) float32 standardized rank matrix on disk
        (~56 GB for 7K x 2M). Set False if you have >64 GB free RAM.
    memmap_dir : str | None, default None
        Directory for the temporary memmap file (point to a fast NVMe SSD).
    filter_invalid_cols : bool, default True
        If True, automatically skip non-numeric and unordered multi-class
        categorical columns without copying `df`. If False, raise TypeError
        when such a column is encountered.
    nan_policy : {"pairwise", "midrank"}, default "pairwise"
        - "pairwise": Exact pairwise-masked Pearson correlation over jointly
          valid rows of globally-ranked columns (no attenuation bias; supports
          `min_periods`; automatically uses the 1x SSYRK fast path if no NaNs
          exist).
        - "midrank": Fast 1x SSYRK pass treating missing values as each
          column's mid-rank (centered rank 0).
    min_periods : int, default 2
        Minimum number of jointly valid observations required per pair
        (used in "pairwise" mode and for per-column validity checks).
    return_dataframe : bool, default True
        Return a labeled pd.DataFrame if True, else a raw float64 np.ndarray.
    """
    if nan_policy not in ("pairwise", "midrank"):
        raise ValueError(f"nan_policy must be 'pairwise' or 'midrank', got {nan_policy!r}")

    effective_min_periods = max(2, int(min_periods))
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
    if n_rows < effective_min_periods:
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
        # Shape (n_cols, n_rows) C-contiguous (~56 GB for 7K x 2M float32)
        if use_memmap:
            tmpdir_obj = tempfile.TemporaryDirectory(dir=memmap_dir)
            mmap_path = os.path.join(tmpdir_obj.name, "ranks_f32.dat")
            z_mat = np.memmap(
                mmap_path, dtype=np.float32, mode="w+", shape=(n_cols, n_rows)
            )
        else:
            z_mat = np.empty((n_cols, n_rows), dtype=np.float32)

        const_cols = np.zeros(n_cols, dtype=bool)
        has_nan_cols = np.zeros(n_cols, dtype=bool)

        # Phase 1: Parallel column ranking & standardization
        def _rank_column(out_j: int) -> None:
            orig_j = valid_idx[out_j]
            s = df.iloc[:, orig_j]
            col_name = df.columns[orig_j]

            nan_mask: np.ndarray | None = None

            if isinstance(s.dtype, pd.CategoricalDtype):
                if not s.cat.ordered and len(s.cat.categories) > 2:
                    raise TypeError(
                        f"Column {orig_j} ({col_name!r}) is an unordered "
                        f"categorical with {len(s.cat.categories)} levels. "
                        "Spearman requires ordered or binary categories."
                    )
                codes = s.cat.codes.to_numpy(copy=False)
                missing = codes == -1
                if missing.any():
                    nan_mask = missing
                    valid_codes = codes[~missing]
                else:
                    valid_codes = codes

                if valid_codes.size < effective_min_periods:
                    const_cols[out_j] = True
                    z_mat[out_j, :] = 0.0
                    return

                # O(N) exact average-tie ranking via category counts
                counts = np.bincount(valid_codes, minlength=len(s.cat.categories))
                avg_ranks = np.cumsum(counts) - 0.5 * (counts - 1)
                r_valid = avg_ranks[valid_codes]
            else:
                if not pd.api.types.is_numeric_dtype(s.dtype) or pd.api.types.is_complex_dtype(s.dtype):
                    raise TypeError(
                        f"Column {orig_j} ({col_name!r}) has unsupported dtype {s.dtype}."
                    )
                if pd.api.types.is_extension_array_dtype(s.dtype):
                    col = s.to_numpy(dtype=np.float64, na_value=np.nan)
                else:
                    col = s.to_numpy(copy=False)

                if np.issubdtype(col.dtype, np.floating):
                    missing = np.isnan(col)
                    if missing.any():
                        nan_mask = missing
                        col_valid = col[~missing]
                    else:
                        col_valid = col
                else:
                    col_valid = col

                if col_valid.size < effective_min_periods:
                    const_cols[out_j] = True
                    z_mat[out_j, :] = 0.0
                    return

                r_valid = rankdata(col_valid, method="average")

            # Standardize valid ranks in float64 to preserve accuracy
            r_valid -= r_valid.mean()

            if nan_policy == "midrank":
                norm = np.linalg.norm(r_valid)
                if norm == 0.0:
                    const_cols[out_j] = True
                    z_mat[out_j, :] = 0.0
                    return
                r_valid /= norm
                if nan_mask is not None:
                    row = np.zeros(n_rows, dtype=np.float32)
                    row[~nan_mask] = r_valid.astype(np.float32)
                    z_mat[out_j, :] = row
                else:
                    z_mat[out_j, :] = r_valid.astype(np.float32)
            else:
                # "pairwise": store unit-std centered ranks with NaN at missing entries
                std = np.sqrt(np.mean(r_valid * r_valid))
                if std == 0.0:
                    const_cols[out_j] = True
                    z_mat[out_j, :] = 0.0
                    return
                r_valid /= std
                if nan_mask is not None:
                    has_nan_cols[out_j] = True
                    row = np.full(n_rows, np.nan, dtype=np.float32)
                    row[~nan_mask] = r_valid.astype(np.float32)
                    z_mat[out_j, :] = row
                else:
                    z_mat[out_j, :] = r_valid.astype(np.float32)

        with ThreadPoolExecutor(max_workers=n_jobs) as pool:
            for _ in pool.map(_rank_column, range(n_cols)):
                pass

        if isinstance(z_mat, np.memmap):
            z_mat.flush()

        # Phase 2: Row-chunked correlation accumulation
        use_pairwise_mask = (nan_policy == "pairwise") and bool(has_nan_cols.any())

        if not use_pairwise_mask:
            # Fast 1x SSYRK path (used for "midrank" and NaN-free "pairwise")
            corr = np.zeros((n_cols, n_cols), dtype=np.float64)

            for start in range(0, n_rows, row_chunk_size):
                end = min(start + row_chunk_size, n_rows)
                chunk = np.ascontiguousarray(z_mat[:, start:end], dtype=np.float32)
                partial = ssyrk(alpha=1.0, a=chunk.T, trans=1, lower=0)
                corr += partial

            if nan_policy == "pairwise":
                # Columns were unit-std (not unit-L2), so divide by n_rows
                corr /= float(n_rows)

            for i in range(1, n_cols):
                corr[i, :i] = corr[:i, i]
        else:
            # Pairwise-masked path: accumulate sufficient statistics over
            # jointly non-missing entries for every column pair (i, j)
            sum_xy = np.zeros((n_cols, n_cols), dtype=np.float64)
            count = np.zeros((n_cols, n_cols), dtype=np.float64)
            sum_x = np.zeros((n_cols, n_cols), dtype=np.float64)
            sum_x2 = np.zeros((n_cols, n_cols), dtype=np.float64)

            for start in range(0, n_rows, row_chunk_size):
                end = min(start + row_chunk_size, n_rows)
                chunk = np.array(z_mat[:, start:end], dtype=np.float32, copy=True, order="C")
                valid = ~np.isnan(chunk)
                m_chunk = valid.astype(np.float32)
                chunk[~valid] = 0.0
                del valid

                sum_xy += ssyrk(alpha=1.0, a=chunk.T, trans=1, lower=0)
                count += ssyrk(alpha=1.0, a=m_chunk.T, trans=1, lower=0)
                sum_x += chunk @ m_chunk.T
                np.square(chunk, out=chunk)  # in-place u^2 to avoid extra buffer
                sum_x2 += chunk @ m_chunk.T
                del chunk, m_chunk

            for i in range(1, n_cols):
                sum_xy[i, :i] = sum_xy[:i, i]
                count[i, :i] = count[:i, i]

            with np.errstate(divide="ignore", invalid="ignore"):
                inv_n = np.where(count >= effective_min_periods, 1.0 / count, np.nan)
                del count
                corr = sum_xy - (sum_x * sum_x.T) * inv_n
                del sum_xy
                var_i = sum_x2 - (sum_x * sum_x) * inv_n
                del sum_x, inv_n
                # Guard against float32 rounding noise when a column is constant on overlap
                var_i = np.where((var_i > 0.0) & (var_i > 1e-6 * sum_x2), var_i, np.nan)
                del sum_x2
                corr /= np.sqrt(var_i * var_i.T)
                del var_i

        # Clamp tiny float32 rounding drift and enforce exact diagonal / invalid NaNs
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
    rng = np.random.default_rng(42)
    n = 50_000
    x = rng.normal(size=n).astype(np.float32)

    a = x.copy()
    b = (x * 2.0 + rng.normal(scale=0.5, size=n)).astype(np.float32)
    a[rng.random(n) < 0.15] = np.nan  # 15% missing
    b[rng.random(n) < 0.20] = np.nan  # 20% missing

    ord_vals = pd.qcut(x + rng.normal(scale=0.3, size=n), 3, labels=["low", "med", "high"])
    ord_cat = pd.Categorical(ord_vals, categories=["low", "med", "high"], ordered=True)
    ord_cat[rng.random(n) < 0.10] = np.nan  # 10% missing categories

    sample_df = pd.DataFrame(
        {
            "num_a": a,
            "num_b": b,
            "ordinal": ord_cat,
            "binary_cat": pd.Categorical(np.where(x > 0, "yes", "no")),
            "nominal_skip": pd.Categorical(rng.choice(["red", "green", "blue"], size=n)),
            "text_skip": rng.choice(["a", "b", "c"], size=n),
            "all_nan": np.full(n, np.nan, dtype=np.float32),
            "const_col": np.ones(n, dtype=np.float32),
        }
    )

    corr_pairwise = fast_spearman_corr(
        sample_df, row_chunk_size=10_000, nan_policy="pairwise", use_memmap=True
    )

    # Reference pandas Spearman (exact pairwise re-ranking)
    ref_df = sample_df[get_valid_spearman_columns(sample_df)].copy()
    for c in ref_df.columns:
        if isinstance(ref_df[c].dtype, pd.CategoricalDtype):
            ref_df[c] = ref_df[c].cat.codes.astype(np.float64).replace(-1, np.nan)
    corr_ref = ref_df.corr(method="spearman")

    max_diff = np.nanmax(np.abs(corr_pairwise.to_numpy() - corr_ref.to_numpy()))
    print(f"Max diff vs pandas exact pairwise Spearman (with 10-20% NaNs): {max_diff:.6f}")
    print(corr_pairwise.round(4))
