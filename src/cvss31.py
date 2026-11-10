"""CVSS v3.x base-score calculator (FIRST specification), used to recover missing scores."""
import math

W = {"AV": {"N": .85, "A": .62, "L": .55, "P": .2}, "AC": {"L": .77, "H": .44},
     "UI": {"N": .85, "R": .62}, "CIA": {"H": .56, "L": .22, "N": 0}}


def roundup(x):
    i = int(round(x * 100000))
    return i / 100000.0 if i % 10000 == 0 else (math.floor(i / 10000) + 1) / 10.0


def base_score(vector):
    if not isinstance(vector, str) or not vector.startswith("CVSS:3"):
        return None
    m = dict(p.split(":") for p in vector.split("/")[1:])
    s = m["S"]
    pr = {"N": .85, "L": .68 if s == "C" else .62, "H": .5 if s == "C" else .27}[m["PR"]]
    iss = 1 - (1 - W["CIA"][m["C"]]) * (1 - W["CIA"][m["I"]]) * (1 - W["CIA"][m["A"]])
    imp = 6.42 * iss if s == "U" else 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    ex = 8.22 * W["AV"][m["AV"]] * W["AC"][m["AC"]] * pr * W["UI"][m["UI"]]
    if imp <= 0:
        return 0.0
    return roundup(min(imp + ex, 10)) if s == "U" else roundup(min(1.08 * (imp + ex), 10))


def band(score):
    return None if score is None else ("NONE" if score == 0 else "LOW" if score < 4 else
                                       "MEDIUM" if score < 7 else "HIGH" if score < 9 else "CRITICAL")
