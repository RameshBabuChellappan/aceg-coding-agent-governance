"""Reproduce the RQ1–RQ4 sample size calculations reported in the synopsis.

Run: python sample_size/sample_size.py
Common assumptions: alpha = .05 (two-sided, Z = 1.96), power = .80 (Z = 0.8416).
"""
import math

from scipy import optimize, stats

Z_A = 1.96
Z_B = 0.8416

# RQ1 — confidence interval for a proportion (framework coverage / FP prevalence)
p, e = 0.50, 0.07
n_rq1 = Z_A**2 * p * (1 - p) / e**2

# RQ2 — power of the chi-square test of independence (Cohen, 1988)
w, df, power = 0.25, 3, 0.80
crit = stats.chi2.ppf(0.95, df)
lam = optimize.brentq(lambda L: stats.ncx2.sf(crit, df, L) - power, 0.1, 100)
n_rq2 = lam / w**2

# RQ3 — logistic regression with a continuous predictor (Hsieh et al., 1998)
P, beta_star, r2 = 0.70, 0.50, 0.20  # P(high impact) observed in the frozen data; |log-OR| per SD (OR = 0.61, i.e., 1/1.65); R^2 of GCS with other predictors
n_rq3_simple = (Z_A + Z_B) ** 2 / (P * (1 - P) * beta_star**2)
n_rq3 = n_rq3_simple / (1 - r2)

# RQ4 — confidence interval for classification accuracy of the LLM pipeline
acc, e4 = 0.80, 0.06
n_rq4 = Z_A**2 * acc * (1 - acc) / e4**2

# RQ1 check — power of the one-sided exact test of coverage (H0: pi <= .80) against a true coverage of .88
z_one = stats.norm.ppf(0.95)
p0, p1 = 0.80, 0.88
n_rq1_test = ((z_one * math.sqrt(p0 * (1 - p0)) + Z_B * math.sqrt(p1 * (1 - p1))) / (p1 - p0)) ** 2

rows = [("RQ1", n_rq1), ("RQ2", n_rq2), ("RQ3", n_rq3), ("RQ4", n_rq4)]
for rq, n in rows:
    print(f"{rq}: n = {n:.2f} -> {math.ceil(n)}")
print(f"RQ1 check: one-sided test of .80 vs .88 needs n = {math.ceil(n_rq1_test)} (below the CI requirement)")
print(f"RQ3 check: events per predictor = 67 / 4 = {67 / 4:.1f}")
print(f"RQ2 detail: critical chi2 = {crit:.3f}, lambda = {lam:.3f}")
print(f"RQ3 detail: unadjusted n = {n_rq3_simple:.2f}")
N = max(math.ceil(n) for _, n in rows)
print(f"Final N = max = {N}; eligible cases in the frozen dataset = 223 (all are coded)")
print(f"Achieved power for RQ2 at n = 221 (cases with a CVSS user-interaction value): {stats.ncx2.sf(crit, df, 221 * w**2):.3f}")
print(f"Achieved margin for RQ1 at N = 223: ±{Z_A * math.sqrt(0.25 / 223):.3f}")
