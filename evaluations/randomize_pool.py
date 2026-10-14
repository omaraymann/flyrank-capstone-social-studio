"""Assemble labeled synthetic judge examples without a fixed good/bad pairing."""

import argparse
import json
import random
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent


def build_examples(seed=42):
    rng = random.Random(seed)
    sources = json.loads((DIRECTORY / "cases.json").read_text())
    pool = json.loads((DIRECTORY / "claim_pool.json").read_text())
    examples = []
    for source in sources:
        claims = pool[source["id"]]
        for claim in claims:
            assert claim["verdict"] in {"supported", "contradicted", "unsupported"}
            if claim["source_excerpt"] is not None:
                assert claim["source_excerpt"] in source["markdown"]
        target_count = rng.randint(2, 5)
        used = set()
        attempts = 0
        while len(used) < target_count:
            attempts += 1
            if attempts > 2000:
                raise ValueError(f"Not enough distinct valid drafts for source {source['id']}")
            selected = rng.sample(claims, rng.randint(1, min(3, len(claims))))
            # Reordering identical claims should not create another example.
            signature = tuple(sorted(claim["claim"] for claim in selected))
            if signature in used:
                continue
            draft = " ".join(claim["claim"] for claim in selected)
            draft += " " + source["call_to_action"]
            if len(draft) > 280:
                continue
            used.add(signature)
            supported = sum(claim["verdict"] == "supported" for claim in selected)
            examples.append({
                "id": f"example-{rng.getrandbits(64):016x}",
                "source_case_id": source["id"],
                "split": source["split"],
                "platform": "x",
                "draft": draft,
                "expected_requires_review": supported != len(selected),
                "expected_supported_claim_rate": supported / len(selected),
                "gold_claims": selected,
            })
    rng.shuffle(examples)
    return examples


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=DIRECTORY / "judge_examples.json")
    args = parser.parse_args()
    examples = build_examples(args.seed)
    args.output.write_text(json.dumps(examples, indent=2) + "\n")
    print(f"Saved {len(examples)} shuffled examples using seed {args.seed}.")
