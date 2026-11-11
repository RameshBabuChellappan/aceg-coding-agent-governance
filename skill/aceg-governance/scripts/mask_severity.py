#!/usr/bin/env python3
"""Mask CVSS scores, vectors and severity wording in advisory text before ACEG coding.
Usage: python mask_severity.py advisory.txt > masked.txt   (or pipe text on stdin)"""
import re
import sys

PAT = re.compile(r"(CVSS:\d\.\d(/[A-Z]{1,2}:[A-Z])+|CVSS[^.;\n]*|\b(critical|high|medium|moderate|low)[- ]severity\b|\bseverity\b[^.;\n]*|"
                 r"\b\d{1,2}\.\d\s*\((critical|high|medium|low)\)|\bscore of \d+(\.\d+)?|"
                 r"\b(AV|AC|PR|UI|S|C|I|A|AT|VC|VI|VA|SC|SI|SA):[NLHRPACU]\b)", re.I)


def mask(text: str) -> str:
    return PAT.sub("[masked]", text)


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else sys.stdin.read()
    sys.stdout.write(mask(src))
