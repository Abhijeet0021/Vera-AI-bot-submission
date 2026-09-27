#!/usr/bin/env python3
"""
Generate canonical submission.jsonl from expanded test_pairs.json
"""

import json
from pathlib import Path
from engine.composer import EngagementComposer
from engine.grounding_validator import GroundingValidator

BASE_DIR = Path(__file__).parent.parent
EXPANDED_DIR = BASE_DIR / "dataset" / "expanded"
OUTPUT_FILE = BASE_DIR / "submission.jsonl"


def main():
    print("[*] Loading expanded dataset...")
    categories = {}
    for f in (EXPANDED_DIR / "categories").glob("*.json"):
        with open(f) as fp:
            d = json.load(fp)
            categories[d["slug"]] = d

    merchants = {}
    for f in (EXPANDED_DIR / "merchants").glob("*.json"):
        with open(f) as fp:
            d = json.load(fp)
            merchants[d["merchant_id"]] = d

    customers = {}
    for f in (EXPANDED_DIR / "customers").glob("*.json"):
        with open(f) as fp:
            d = json.load(fp)
            customers[d["customer_id"]] = d

    triggers = {}
    for f in (EXPANDED_DIR / "triggers").glob("*.json"):
        with open(f) as fp:
            d = json.load(fp)
            triggers[d["id"]] = d

    with open(EXPANDED_DIR / "test_pairs.json") as fp:
        pairs = json.load(fp)["pairs"]

    print(f"[*] Processing {len(pairs)} canonical test pairs...")
    lines = []

    for pair in pairs:
        test_id = pair["test_id"]
        trg_id = pair["trigger_id"]
        m_id = pair["merchant_id"]
        c_id = pair.get("customer_id")

        trg = triggers.get(trg_id)
        m = merchants.get(m_id)
        if not (trg and m):
            print(f"[!] Warning: missing data for test {test_id} (trigger: {trg_id}, merchant: {m_id})")
            continue

        cat_slug = m.get("category_slug")
        cat = categories.get(cat_slug)
        cust = customers.get(c_id) if c_id else None

        composed = EngagementComposer.compose(
            category=cat,
            merchant=m,
            trigger=trg,
            customer=cust
        )

        # Output schema compliance
        entry = {
            "test_id": test_id,
            "body": composed.body,
            "cta": composed.cta,
            "send_as": composed.send_as,
            "suppression_key": composed.suppression_key,
            "rationale": composed.rationale
        }
        lines.append(json.dumps(entry, ensure_ascii=False))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")

    print(f"[SUCCESS] Wrote {len(lines)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
