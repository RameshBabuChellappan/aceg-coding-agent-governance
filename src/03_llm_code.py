"""Step 3 — apply the framework to every case with an LLM (the automated pipeline).

The full ACEG codebook (docs/codebook.md) is sent as instructions; for each case the model
returns JSON with governance domains, primary domain and control status. Results are
written to data/processed/llm_codes.csv. The pipeline is blind to the human gold labels.

Requires: pip install anthropic ; environment variable ANTHROPIC_API_KEY.
Optional: CLAUDE_MODEL (default below). Every call is logged to outputs/llm_log.jsonl.
Run: python src/03_llm_code.py
"""
import json
import os
from pathlib import Path

import anthropic
import pandas as pd

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
CASES = Path("data/processed/cases_to_code.csv")
OUT = Path("data/processed/llm_codes.csv")
LOG = Path("outputs/llm_log.jsonl")
CODEBOOK = Path("docs/codebook.md").read_text()

SYSTEM = (
    "You are a careful research coder. Apply the codebook below exactly. Use only the case "
    "text provided; do not use outside knowledge.\n\n" + CODEBOOK
)
SCHEMA_HINT = (
    "Return only a JSON object with keys: d1..d8 (0 or 1), primary_domain (1-8), "
    "c01..c20 (1 = breached, 0 = not breached, \"NA\" = not applicable), covered (0 or 1), "
    "rationale (max 60 words)."
)


def code_case(client: anthropic.Anthropic, row: pd.Series) -> dict:
    case_text = (f"Title: {row['title']}\nProduct: {row['product']}\nPublished: {row['published']}\n"
                 f"Source: {row['url']}\n\n{row['description']}")
    kwargs = dict(model=MODEL, max_tokens=1200, system=SYSTEM,
                  messages=[{"role": "user", "content": case_text + "\n\n" + SCHEMA_HINT}])
    try:
        msg = client.messages.create(temperature=0, **kwargs)
    except anthropic.BadRequestError:  # some models fix sampling parameters
        msg = client.messages.create(**kwargs)
    text = "".join(b.text for b in msg.content if b.type == "text")
    start, end = text.find("{"), text.rfind("}")
    out = json.loads(text[start:end + 1])
    with LOG.open("a") as f:
        f.write(json.dumps({"case_id": row["case_id"], "model": MODEL, "response": text}) + "\n")
    return out


def main() -> None:
    client = anthropic.Anthropic()
    cases = pd.read_csv(CASES)
    LOG.parent.mkdir(exist_ok=True)
    done = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["case_id"])
    rows = done.to_dict("records")
    for _, row in cases[~cases["case_id"].isin(done["case_id"])].iterrows():
        res = code_case(client, row)
        rec = {"case_id": row["case_id"], "llm_model": MODEL}
        rec.update({f"llm_{k}": v for k, v in res.items()})
        rows.append(rec)
        pd.DataFrame(rows).to_csv(OUT, index=False)  # checkpoint after every case
        print(row["case_id"], "coded")


if __name__ == "__main__":
    main()
