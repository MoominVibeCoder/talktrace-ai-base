"""Intercoder – agreement metrics (two-rater and multi-rater)."""
import math

import numpy as np
import pandas as pd


# =====================================================================
# Two-rater helpers
# =====================================================================

def _percent_agreement(y_a, y_b):
    if not y_a:
        return float("nan")
    a = np.asarray(y_a)
    b = np.asarray(y_b)
    return float(np.mean(a == b))


def _krippendorff_alpha_nominal(y_a, y_b):
    """Krippendorff's α for nominal data with two raters.

    Coincidence-matrix formulation:
        α = 1 - D_o / D_e
    where D_o is observed and D_e expected disagreement.
    """
    if not y_a or len(y_a) < 2:
        return float("nan")
    a = np.asarray(y_a)
    b = np.asarray(y_b)
    labels = sorted(set(a.tolist()) | set(b.tolist()))
    idx = {c: i for i, c in enumerate(labels)}
    K = len(labels)
    if K < 2:
        # No variance → α undefined. Conventionally returned as 1.0
        # (all units in agreement on the single code).
        return 1.0

    # Coincidence matrix: each unit contributes 2 pairs (A↔B and B↔A) divided
    # by the number of values per unit (m=2) → effectively 1 each direction.
    coincidence = np.zeros((K, K), dtype=float)
    for ca, cb in zip(a, b):
        i, j = idx[ca], idx[cb]
        coincidence[i, j] += 1.0
        coincidence[j, i] += 1.0
    coincidence /= 1.0  # m - 1 = 1 for two raters

    n_c = coincidence.sum(axis=1)  # marginal totals per code
    n = float(n_c.sum())
    if n <= 1:
        return float("nan")

    # Observed disagreement
    d_o = (coincidence.sum() - np.trace(coincidence)) / n
    # Expected disagreement (nominal: δ = 1 for c≠c', 0 else)
    d_e = (n_c.sum() ** 2 - (n_c ** 2).sum()) / (n * (n - 1))

    if d_e == 0:
        return 1.0 if d_o == 0 else float("nan")
    return float(1.0 - d_o / d_e)


def _bootstrap_kappa_ci(y_a, y_b, labels, n_boot=1000, seed=42):
    """Non-parametric percentile bootstrap CI for Cohen's κ.

    Returns (low, high). NaN if too few units or no valid resamples.
    """
    from sklearn.metrics import cohen_kappa_score
    n = len(y_a)
    if n < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    a = np.asarray(y_a)
    b = np.asarray(y_b)
    samples = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        ya_s = a[idx]
        yb_s = b[idx]
        # Skip degenerate samples (only one class on either side)
        if len(set(ya_s.tolist())) < 2 and len(set(yb_s.tolist())) < 2:
            continue
        try:
            k = cohen_kappa_score(ya_s, yb_s, labels=labels)
            if not np.isnan(k):
                samples.append(float(k))
        except Exception:
            continue
    if not samples:
        return (float("nan"), float("nan"))
    return (
        float(np.percentile(samples, 2.5)),
        float(np.percentile(samples, 97.5)),
    )


def _gwet_ac1_two(y_a, y_b):
    """Gwet's AC1 for two coders, nominal categories.

    AC1 = (p_a - p_e) / (1 - p_e), where p_e = 1/(K-1) * sum(pi_k * (1 - pi_k))
    and pi_k is the marginal probability of category k. Robust against the
    "kappa paradox" with highly skewed prevalence. Gwet (2008).
    """
    if not y_a or len(y_a) < 2:
        return float("nan")
    a = np.asarray(y_a)
    b = np.asarray(y_b)
    n = len(a)
    labels = sorted(set(a.tolist()) | set(b.tolist()))
    K = len(labels)
    if K < 2:
        return 1.0
    p_a = float(np.mean(a == b))
    pi = np.array(
        [((a == c).sum() + (b == c).sum()) / (2.0 * n) for c in labels]
    )
    p_e = float(np.sum(pi * (1.0 - pi)) / (K - 1))
    if p_e >= 1.0 - 1e-12:
        return 1.0 if p_a >= 1.0 - 1e-12 else float("nan")
    return float((p_a - p_e) / (1.0 - p_e))


def _brennan_prediger_two(y_a, y_b):
    """Brennan-Prediger κ for two coders, nominal categories.

    BP = (p_a - 1/K) / (1 - 1/K). Treats expected agreement as uniform across
    K categories instead of estimating it from marginals — much less
    sensitive to rare codes than Cohen's κ. Brennan & Prediger (1981).
    """
    if not y_a or len(y_a) < 2:
        return float("nan")
    a = np.asarray(y_a)
    b = np.asarray(y_b)
    labels = sorted(set(a.tolist()) | set(b.tolist()))
    K = len(labels)
    if K < 2:
        return 1.0
    p_a = float(np.mean(a == b))
    p_e = 1.0 / K
    if p_e >= 1.0 - 1e-12:
        return 1.0 if p_a >= 1.0 - 1e-12 else float("nan")
    return float((p_a - p_e) / (1.0 - p_e))


def _per_code_metrics(y_a, y_b, labels):
    """Per-code F1 / precision / recall using A as reference, B as prediction.

    Returns DataFrame with columns: code, n_a, n_b, f1, precision, recall.
    """
    from sklearn.metrics import precision_recall_fscore_support
    if not y_a:
        return pd.DataFrame(columns=["Code", "n(A)", "n(B)", "F1", "Precision", "Recall"])
    a = np.asarray(y_a)
    b = np.asarray(y_b)
    precision, recall, f1, _ = precision_recall_fscore_support(
        a, b, labels=labels, zero_division=0
    )
    rows = []
    for i, code in enumerate(labels):
        rows.append({
            "Code": code,
            "n(A)": int((a == code).sum()),
            "n(B)": int((b == code).sum()),
            "F1": float(f1[i]),
            "Precision": float(precision[i]),
            "Recall": float(recall[i]),
        })
    return pd.DataFrame(rows)


def compute_intercoder_agreement(df_a, df_b, unmatched_label="—"):
    """Align two coded-impulse DataFrames by 'Impuls' text and compute
    Cohen's kappa, Krippendorff's α, percent agreement, bootstrap CI for κ
    and per-code F1 over the 'Shortcode' columns. Impulses present in
    only one report contribute as (code, unmatched_label) pairs.

    Returns dict with keys: kappa, n_pairs, n_both, n_only_a, n_only_b,
        confusion (pd.DataFrame), labels (list[str]),
        percent_agreement, krippendorff_alpha,
        kappa_ci_low, kappa_ci_high, per_code (pd.DataFrame).
    """
    from sklearn.metrics import cohen_kappa_score

    def _norm_series(df):
        s = df.copy()
        s["Impuls"] = s["Impuls"].astype(str).str.strip()
        s["Shortcode"] = s["Shortcode"].astype(str).str.strip()
        # If the same impulse appears multiple times in one report, keep
        # the first occurrence — kappa needs exactly one code per unit.
        s = s.drop_duplicates(subset=["Impuls"], keep="first")
        return s

    a = _norm_series(df_a)
    b = _norm_series(df_b)

    a_map = dict(zip(a["Impuls"], a["Shortcode"]))
    b_map = dict(zip(b["Impuls"], b["Shortcode"]))

    all_impulses = list(dict.fromkeys(list(a_map.keys()) + list(b_map.keys())))

    y_a, y_b = [], []
    n_both = n_only_a = n_only_b = 0
    pairs = []
    for imp in all_impulses:
        ca = a_map.get(imp)
        cb = b_map.get(imp)
        if ca and cb:
            n_both += 1
        elif ca and not cb:
            n_only_a += 1
        elif cb and not ca:
            n_only_b += 1
        code_a = ca if ca else unmatched_label
        code_b = cb if cb else unmatched_label
        y_a.append(code_a)
        y_b.append(code_b)
        pairs.append({"impuls": imp, "code_a": code_a, "code_b": code_b})

    labels = sorted(set(y_a) | set(y_b))
    try:
        kappa = float(cohen_kappa_score(y_a, y_b, labels=labels))
    except Exception:
        kappa = float("nan")

    confusion = pd.crosstab(
        pd.Series(y_a, name="A"),
        pd.Series(y_b, name="B"),
    ).reindex(index=labels, columns=labels, fill_value=0)

    percent_agreement = _percent_agreement(y_a, y_b)
    krippendorff_alpha = _krippendorff_alpha_nominal(y_a, y_b)
    ci_low, ci_high = _bootstrap_kappa_ci(y_a, y_b, labels)
    per_code = _per_code_metrics(y_a, y_b, labels)
    gwet_ac1 = _gwet_ac1_two(y_a, y_b)
    brennan_prediger = _brennan_prediger_two(y_a, y_b)

    return {
        "kappa": kappa,
        "n_pairs": len(all_impulses),
        "n_both": n_both,
        "n_only_a": n_only_a,
        "n_only_b": n_only_b,
        "confusion": confusion,
        "labels": labels,
        "percent_agreement": percent_agreement,
        "krippendorff_alpha": krippendorff_alpha,
        "kappa_ci_low": ci_low,
        "kappa_ci_high": ci_high,
        "per_code": per_code,
        "pairs": pairs,
        "gwet_ac1": gwet_ac1,
        "brennan_prediger": brennan_prediger,
    }


# =====================================================================
# Multi-rater intercoder agreement (Expert Mode)
# =====================================================================

def _align_n_reports(dfs, unmatched_label="—"):
    """Align N report DataFrames by 'Impuls' text into a coding matrix.

    Returns a tuple (matrix, pairs, all_impulses) where:
      - matrix is an ``np.ndarray`` of shape ``(n_units, n_raters)`` with
        Shortcode strings; missing impulses get ``unmatched_label``.
      - pairs is a list of dicts ``{impuls, code_1, code_2, ...}``.
      - all_impulses is the ordered list of unit identifiers.
    """
    normed_maps = []
    impuls_lists = []
    for df in dfs:
        s = df.copy()
        s["Impuls"] = s["Impuls"].astype(str).str.strip()
        s["Shortcode"] = s["Shortcode"].astype(str).str.strip()
        s = s.drop_duplicates(subset=["Impuls"], keep="first")
        normed_maps.append(dict(zip(s["Impuls"], s["Shortcode"])))
        impuls_lists.append(list(s["Impuls"]))

    seen = set()
    all_impulses = []
    for lst in impuls_lists:
        for imp in lst:
            if imp not in seen:
                seen.add(imp)
                all_impulses.append(imp)

    n_units = len(all_impulses)
    n_raters = len(dfs)
    matrix = np.empty((n_units, n_raters), dtype=object)
    pairs = []
    for i, imp in enumerate(all_impulses):
        row = {"impuls": imp}
        for j, m in enumerate(normed_maps):
            code = m.get(imp, unmatched_label)
            matrix[i, j] = code
            row[f"code_{j + 1}"] = code
        pairs.append(row)
    return matrix, pairs, all_impulses


def _cohen_kappa_value(matrix, labels=None):
    """Cohen's κ from a (n_units, 2) matrix."""
    from sklearn.metrics import cohen_kappa_score
    if matrix.shape[1] != 2 or len(matrix) < 2:
        return float("nan")
    y_a = list(matrix[:, 0])
    y_b = list(matrix[:, 1])
    if labels is None:
        labels = sorted(set(y_a) | set(y_b))
    try:
        return float(cohen_kappa_score(y_a, y_b, labels=labels))
    except Exception:
        return float("nan")


def _fleiss_kappa_value(matrix):
    """Fleiss' κ from a (n_units, n_raters) matrix; constant n_raters."""
    n_units, n_raters = matrix.shape
    if n_units < 2 or n_raters < 2:
        return float("nan")
    labels = sorted(set(matrix.flatten().tolist()))
    K = len(labels)
    if K < 2:
        return 1.0  # only one category in play → trivial agreement
    label_to_idx = {l: i for i, l in enumerate(labels)}
    counts = np.zeros((n_units, K), dtype=int)
    for i in range(n_units):
        for r in matrix[i]:
            counts[i, label_to_idx[r]] += 1
    p_j = counts.sum(axis=0) / float(n_units * n_raters)
    P_i = (np.sum(counts ** 2, axis=1) - n_raters) / float(n_raters * (n_raters - 1))
    P_bar = float(P_i.mean())
    P_e = float((p_j ** 2).sum())
    if P_e >= 1.0 - 1e-12:
        return 1.0 if P_bar >= 1.0 - 1e-12 else float("nan")
    return float((P_bar - P_e) / (1.0 - P_e))


def _gwet_ac1_value(matrix):
    """Gwet's AC1 generalised to N raters via the per-unit subject-counts
    formulation (Gwet 2008, eq. 9). Treats expected agreement using the
    chance probability ``pi_k * (1 - pi_k) / (K - 1)`` averaged over
    categories, where pi_k is the overall marginal of category k.
    """
    n_units, n_raters = matrix.shape
    if n_units < 2 or n_raters < 2:
        return float("nan")
    labels = sorted(set(matrix.flatten().tolist()))
    K = len(labels)
    if K < 2:
        return 1.0
    label_to_idx = {l: i for i, l in enumerate(labels)}
    counts = np.zeros((n_units, K), dtype=int)
    for i in range(n_units):
        for r in matrix[i]:
            counts[i, label_to_idx[r]] += 1
    # Per-unit observed agreement (probability two raters chosen at random
    # within a unit agree).
    P_i = (np.sum(counts ** 2, axis=1) - n_raters) / float(n_raters * (n_raters - 1))
    P_a = float(P_i.mean())
    pi = counts.sum(axis=0) / float(n_units * n_raters)
    P_e = float(np.sum(pi * (1.0 - pi)) / (K - 1))
    if P_e >= 1.0 - 1e-12:
        return 1.0 if P_a >= 1.0 - 1e-12 else float("nan")
    return float((P_a - P_e) / (1.0 - P_e))


def _brennan_prediger_value(matrix):
    """Brennan-Prediger κ generalised to N raters: same observed agreement
    estimator as Fleiss/AC1 but expected agreement is the uniform 1/K.
    """
    n_units, n_raters = matrix.shape
    if n_units < 2 or n_raters < 2:
        return float("nan")
    labels = sorted(set(matrix.flatten().tolist()))
    K = len(labels)
    if K < 2:
        return 1.0
    label_to_idx = {l: i for i, l in enumerate(labels)}
    counts = np.zeros((n_units, K), dtype=int)
    for i in range(n_units):
        for r in matrix[i]:
            counts[i, label_to_idx[r]] += 1
    P_i = (np.sum(counts ** 2, axis=1) - n_raters) / float(n_raters * (n_raters - 1))
    P_a = float(P_i.mean())
    P_e = 1.0 / K
    if P_e >= 1.0 - 1e-12:
        return 1.0 if P_a >= 1.0 - 1e-12 else float("nan")
    return float((P_a - P_e) / (1.0 - P_e))


def _krippendorff_alpha_value(matrix):
    """Krippendorff's α (nominal) for an (n_units, n_raters) matrix.

    Uses the coincidence-matrix formulation generalised to m raters per
    unit. For m=2 reduces to the same expected value as
    :func:`_krippendorff_alpha_nominal`.
    """
    n_units, n_raters = matrix.shape
    if n_units < 2 or n_raters < 2:
        return float("nan")
    labels = sorted(set(matrix.flatten().tolist()))
    K = len(labels)
    if K < 2:
        return 1.0
    label_to_idx = {l: i for i, l in enumerate(labels)}
    m = n_raters
    coincidence = np.zeros((K, K), dtype=float)
    for i in range(n_units):
        n_u = np.zeros(K, dtype=int)
        for r in matrix[i]:
            n_u[label_to_idx[r]] += 1
        # diagonal: pairs of same code within unit
        for c in range(K):
            if n_u[c] >= 2:
                coincidence[c, c] += n_u[c] * (n_u[c] - 1) / (m - 1)
        # off-diagonal: pairs of different codes within unit
        for c in range(K):
            for k in range(K):
                if c == k:
                    continue
                if n_u[c] and n_u[k]:
                    coincidence[c, k] += n_u[c] * n_u[k] / (m - 1)

    n_c = coincidence.sum(axis=1)
    n = float(n_c.sum())
    if n <= 1:
        return float("nan")
    d_o = (coincidence.sum() - np.trace(coincidence)) / n
    d_e = (n_c.sum() ** 2 - (n_c ** 2).sum()) / (n * (n - 1))
    if d_e == 0:
        return 1.0 if d_o == 0 else float("nan")
    return float(1.0 - d_o / d_e)


def _two_sided_p_from_z(z):
    """Two-sided p-value from a standard-normal z-statistic, no scipy."""
    if z != z:  # NaN
        return float("nan")
    upper = 1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))
    return float(2.0 * upper)


def _bootstrap_ci_and_p(metric_fn, matrix, n_boot=1000, seed=42):
    """Resample units (rows), return (ci_low, ci_high, p_value).

    p-value is the two-sided z-test ``z = κ_obs / SE_boot`` against H0 κ=0.
    Falls back to NaN where the bootstrap distribution is degenerate.
    """
    n_units = len(matrix)
    if n_units < 2:
        return (float("nan"), float("nan"), float("nan"))
    obs = metric_fn(matrix)
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_units, size=n_units)
        try:
            v = metric_fn(matrix[idx])
        except Exception:
            continue
        if v == v:  # not NaN
            samples.append(float(v))
    if len(samples) < 2:
        return (float("nan"), float("nan"), float("nan"))
    arr = np.asarray(samples, dtype=float)
    ci_low = float(np.percentile(arr, 2.5))
    ci_high = float(np.percentile(arr, 97.5))
    se = float(arr.std(ddof=1))
    if obs != obs or se == 0.0:
        p_value = float("nan")
    else:
        z = obs / se
        p_value = _two_sided_p_from_z(z)
    return (ci_low, ci_high, p_value)


def compute_intercoder_agreement_multi(dfs, metric, unmatched_label="—",
                                       n_boot=1000, seed=42):
    """Compute Cohen's κ / Krippendorff's α / Fleiss' κ across N coders.

    Args:
        dfs: list of pandas DataFrames with 'Impuls' and 'Shortcode' columns.
        metric: one of ``"cohen"`` (N=2), ``"krippendorff"`` (N≥2),
            ``"fleiss"`` (N≥3).
        unmatched_label: code used for impulses missing in a report.

    Returns dict with ``metric, value, ci_low, ci_high, p_value, n_units,
    n_raters, n_only_each, pairs, rater_labels, labels``.
    """
    if metric not in ("cohen", "krippendorff", "fleiss", "gwet", "brennan_prediger"):
        raise ValueError(f"unsupported_metric: {metric}")
    n_raters = len(dfs)
    if metric == "cohen" and n_raters != 2:
        raise ValueError("cohen_requires_two_raters")
    if metric == "fleiss" and n_raters < 3:
        raise ValueError("fleiss_requires_three_raters")
    if metric == "krippendorff" and n_raters < 2:
        raise ValueError("krippendorff_requires_two_raters")
    if metric in ("gwet", "brennan_prediger") and n_raters < 2:
        raise ValueError("requires_two_raters")

    matrix, pairs, all_impulses = _align_n_reports(dfs, unmatched_label)
    labels = sorted(set(matrix.flatten().tolist()))

    if metric == "cohen":
        def _fn(m):
            return _cohen_kappa_value(m, labels=labels)
    elif metric == "fleiss":
        _fn = _fleiss_kappa_value
    elif metric == "gwet":
        _fn = _gwet_ac1_value
    elif metric == "brennan_prediger":
        _fn = _brennan_prediger_value
    else:  # krippendorff
        _fn = _krippendorff_alpha_value

    value = _fn(matrix)
    ci_low, ci_high, p_value = _bootstrap_ci_and_p(_fn, matrix,
                                                   n_boot=n_boot, seed=seed)

    # Per-rater "only-in-this-coder" counts (coded here, missing elsewhere
    # via the unmatched_label sentinel).
    n_only_each = []
    for j in range(n_raters):
        col = matrix[:, j]
        coded_here = sum(1 for c in col if c != unmatched_label)
        only_here = 0
        for i, c in enumerate(col):
            if c == unmatched_label:
                continue
            others = [matrix[i, k] for k in range(n_raters) if k != j]
            if all(o == unmatched_label for o in others):
                only_here += 1
        n_only_each.append({"coded": int(coded_here), "only_here": int(only_here)})

    rater_labels = [f"Coder {i + 1}" for i in range(n_raters)]

    return {
        "metric": metric,
        "value": value,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_value": p_value,
        "n_units": len(all_impulses),
        "n_raters": n_raters,
        "n_only_each": n_only_each,
        "pairs": pairs,
        "rater_labels": rater_labels,
        "labels": labels,
    }


def p_value_stars(p):
    """Return significance-stars notation for a p-value (or 'n.s.')."""
    if p is None or p != p:
        return "n.s."
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."
