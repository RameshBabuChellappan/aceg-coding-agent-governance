"""Statistics helpers written with NumPy/SciPy only (no statsmodels dependency)."""
import numpy as np
from scipy import stats


def wilson(k, n, z=1.959964):
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = k / n
    den = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return p, c - h, c + h


def logit_fit(X, y, names, cluster=None, max_iter=100):
    """Maximum-likelihood logistic regression (Newton-Raphson). X excludes the intercept."""
    X = np.column_stack([np.ones(len(y)), np.asarray(X, float)])
    y = np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(max_iter):
        p = 1 / (1 + np.exp(-X @ b))
        W = p * (1 - p)
        H = X.T @ (X * W[:, None])
        step = np.linalg.solve(H, X.T @ (y - p))
        b += step
        if np.max(np.abs(step)) < 1e-10:
            break
    p = 1 / (1 + np.exp(-X @ b))
    H = X.T @ (X * (p * (1 - p))[:, None])
    cov = np.linalg.inv(H)
    if cluster is not None:
        u = X * (y - p)[:, None]
        cl = np.asarray(cluster)
        meat = np.zeros_like(H)
        groups = np.unique(cl)
        for g in groups:
            s = u[cl == g].sum(0)
            meat += np.outer(s, s)
        G, n, k = len(groups), len(y), X.shape[1]
        cov = cov @ meat @ cov * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(cov))
    z = b / se
    pv = 2 * stats.norm.sf(np.abs(z))
    ll = np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    p0 = y.mean()
    ll0 = len(y) * (p0 * np.log(p0) + (1 - p0) * np.log(1 - p0))
    lr = 2 * (ll - ll0)
    df = X.shape[1] - 1
    return {"names": ["Intercept"] + list(names), "b": b, "se": se, "z": z, "p": pv,
            "or": np.exp(b), "lo": np.exp(b - 1.959964 * se), "hi": np.exp(b + 1.959964 * se),
            "ll": ll, "ll0": ll0, "lr": lr, "lr_df": df, "lr_p": stats.chi2.sf(lr, df),
            "mcfadden": 1 - ll / ll0, "pred": p, "n": len(y), "aic": -2 * ll + 2 * X.shape[1]}


def hosmer_lemeshow(y, p, g=10):
    y, p = np.asarray(y), np.asarray(p)
    order = np.argsort(p)
    bins = np.array_split(order, g)
    hl = 0
    for b in bins:
        o, e, n = y[b].sum(), p[b].sum(), len(b)
        hl += (o - e) ** 2 / (e * (1 - e / n)) if 0 < e < n else 0
    return hl, g - 2, stats.chi2.sf(hl, g - 2)


def vif(X):
    X = np.asarray(X, float)
    out = []
    for j in range(X.shape[1]):
        others = np.column_stack([np.ones(len(X)), np.delete(X, j, axis=1)])
        beta, *_ = np.linalg.lstsq(others, X[:, j], rcond=None)
        r = X[:, j] - others @ beta
        r2 = 1 - r.var() / X[:, j].var()
        out.append(1 / (1 - r2))
    return out


def kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    cats = np.union1d(a, b)
    po = np.mean(a == b)
    pe = sum(np.mean(a == c) * np.mean(b == c) for c in cats)
    return np.nan if pe == 1 else (po - pe) / (1 - pe)


def boot_ci(fn, *arrays, B=2000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(arrays[0])
    vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        v = fn(*[np.asarray(x)[idx] for x in arrays])
        if not np.isnan(v):
            vals.append(v)
    return np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan)


def fleiss(ratings, cats):
    """ratings: n x m array of category labels (m raters)."""
    R = np.asarray(ratings)
    n, m = R.shape
    counts = np.stack([(R == c).sum(1) for c in cats], 1)
    P_i = (np.sum(counts ** 2, 1) - m) / (m * (m - 1))
    p_j = counts.sum(0) / (n * m)
    Pe = np.sum(p_j ** 2)
    return np.nan if Pe == 1 else (P_i.mean() - Pe) / (1 - Pe)


def binclass(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    tp = np.sum((y == 1) & (yhat == 1)); tn = np.sum((y == 0) & (yhat == 0))
    fp = np.sum((y == 0) & (yhat == 1)); fn = np.sum((y == 1) & (yhat == 0))
    prec = tp / (tp + fp) if tp + fp else np.nan
    rec = tp / (tp + fn) if tp + fn else np.nan
    f1 = 2 * prec * rec / (prec + rec) if prec and rec and not np.isnan(prec + rec) else (0.0 if tp == 0 else np.nan)
    spec = tn / (tn + fp) if tn + fp else np.nan
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "acc": (tp + tn) / len(y), "prec": prec,
            "rec": rec, "f1": f1, "spec": spec,
            "bal_acc": np.nanmean([rec, spec])}
