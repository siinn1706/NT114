"""Compute weighted direction scores and a sensitivity check under alternative weightings.

Reads direction-scores.csv (one row per direction x criterion, scores 1-5) and writes direction-ranking.csv
(weighted total under the plan weights) and sensitivity.csv (rank under each weighting, and whether the
direction stays in the top 3 under all of them).
Usage: python -X utf8 score-directions.py
"""
import csv
from collections import defaultdict
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
CRITERIA = ["novelty", "feasibility", "evaluability", "proposal_reuse", "supervisor_fit", "q1_publishability"]
WEIGHTS = {
    "plan": [0.25, 0.20, 0.15, 0.15, 0.15, 0.10],
    "equal": [1 / 6] * 6,
    "feasibility_first": [0.15, 0.35, 0.20, 0.10, 0.10, 0.10],
    "novelty_first": [0.40, 0.15, 0.15, 0.05, 0.15, 0.10],
}


def main():
    scores = defaultdict(dict)
    for r in csv.DictReader(open(WORK / "direction-scores.csv", encoding="utf-8")):
        scores[r["direction_id"]][r["criterion"]] = int(r["score"])
    missing = [(d, c) for d in scores for c in CRITERIA if c not in scores[d]]
    if missing:
        raise SystemExit(f"missing scores: {missing}")
    totals = {name: {d: round(sum(w * s[c] for w, c in zip(ws, CRITERIA)), 3) for d, s in scores.items()}
              for name, ws in WEIGHTS.items()}
    ranks = {name: {d: i + 1 for i, d in enumerate(sorted(t, key=lambda d: (-t[d], d)))} for name, t in totals.items()}
    with open(WORK / "direction-ranking.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["direction_id"] + CRITERIA + ["weighted_total", "rank"])
        for d in sorted(scores, key=lambda d: ranks["plan"][d]):
            w.writerow([d] + [scores[d][c] for c in CRITERIA] + [totals["plan"][d], ranks["plan"][d]])
    with open(WORK / "sensitivity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["direction_id"] + [f"{n}_total" for n in WEIGHTS] + [f"{n}_rank" for n in WEIGHTS] + ["top3_in_all"])
        for d in sorted(scores, key=lambda d: ranks["plan"][d]):
            w.writerow([d] + [totals[n][d] for n in WEIGHTS] + [ranks[n][d] for n in WEIGHTS]
                       + [int(all(ranks[n][d] <= 3 for n in WEIGHTS))])
    for d in sorted(scores, key=lambda d: ranks["plan"][d]):
        print(d, " ".join(f"{n}={totals[n][d]:.3f}(#{ranks[n][d]})" for n in WEIGHTS))


if __name__ == "__main__":
    main()
