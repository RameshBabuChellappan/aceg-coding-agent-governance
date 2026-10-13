# Raw data — how to download

Both sources are public GitHub repositories. No account, API key or permission is needed. About 6 GB of disk space is required.

```bash
git clone --depth 1 https://github.com/github/advisory-database.git data/raw/advisory-database
git clone --depth 1 --filter=blob:none --sparse https://github.com/CVEProject/cvelistV5.git data/raw/cvelistV5
git -C data/raw/cvelistV5 sparse-checkout set cves/2023 cves/2024 cves/2025 cves/2026
```

Use the frozen commits listed in `docs/data_freeze.md` to reproduce the study dataset exactly. The raw clones are not committed to this repository because of their size. The derived files are committed:

- `data/interim/candidates.csv`: 239 records identified;
- `data/processed/cases_to_code.csv`: 223 eligible cases.

Attribution: GitHub Advisory Database (CC BY 4.0) and the CVE Program's CVE List (CVE® is a registered trademark of The MITRE Corporation).
