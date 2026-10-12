"""Build the concept matrix (papers x coded dimensions) from extraction.csv and count 2- and 3-way combinations.

Each dimension is coded 0/1 by explicit regex rules over the extraction fields, so the matrix is reproducible and
the rules can be audited. Combination counts use primary studies only (surveys and benchmarks of other domains kept
in the matrix but excluded from counts).
Writes concept-matrix.csv (one row per paper) and concept-combos.csv (dimension combination, count, paper ids).
Usage: python -X utf8 build-concept-matrix.py
"""
import csv
import itertools
import re
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
SYSTEMS = {
    "TrainTicket": r"train ?-?ticket|\bTT\b",
    "OnlineBoutique": r"online ?boutique|hipster ?shop|\bOB\b",
    "SocialNetwork": r"social ?network",
    "SockShop": r"sock ?shop",
    "HotelReservation": r"hotel ?reservation",
    "GAIA": r"\bGAIA\b|MicroSS",
    "AIOpsChallenge": r"AIOps ?-?(20)?2[02]|AIOps Challenge|CCF AIOps",
    "RCAEval": r"RCAEval",
    "DejaVu": r"DejaVu",
}
API_LLM = r"qwen-?(2\.5-)?(plus|max)|qwenmax"  # hosted API models, not open weights
OPEN_LLM = r"llama|qwen|mistral|gemma|deepseek|gpt-oss|phi-4|baichuan|codellama|\b\d(\.\d)?B\b"


def nr(v):
    return v.strip().lower().startswith("not-reported") or not v.strip()


def code(r):
    j = lambda *k: " ".join(r[x] for x in k)
    survey = bool(re.match(r"\s*(survey|systematic literature review|multivocal|narrative)", r["method_family"], re.I))
    llm_gen = not nr(r["llm"]) and not re.search(r"no generative|not used as diagnoser|encoder", r["llm"], re.I)
    retr = not nr(r["retrieval"]) and not re.search(r"not used|diagnosed target|only in baselines|overview only|not text retrieval", r["retrieval"], re.I)
    conf_cal = bool(re.search(r"uncertaint|calibrat|\bECE\b|coverage", r["confidence"], re.I)) and \
        not re.search(r"^not-reported|no calibration|not tested|not quantified|no probabilistic", r["confidence"], re.I)
    systems = sorted(k for k, rx in SYSTEMS.items() if re.search(rx, j("datasets", "system_context"), re.I))
    mods = j("modalities")
    d = {
        "survey": survey,
        "microservice": bool(re.search(r"microservice|cloud-native|cloud native", j("problem", "system_context", "datasets"), re.I)) or bool(systems),
        "rca": bool(re.search(r"root cause|RCA|RCL|fault locali|failure locali|failure diagnosis|fault diagnosis|bug locali", j("problem", "method_family"), re.I)),
        "metrics": bool(re.search(r"metric|KPI|time.series|telemetry", mods, re.I)),
        "logs": bool(re.search(r"\blogs?\b|log template", mods, re.I)),
        "traces": bool(re.search(r"trace|span", mods, re.I)),
        "llm_generative": llm_gen,
        "open_weight_llm": llm_gen and bool(re.search(OPEN_LLM, re.sub(API_LLM, "", r["llm"], flags=re.I), re.I)),
        "retrieval": retr,
        "retrieval_variants_compared": retr and bool(re.search(r"BM25|sparse|lexical", r["retrieval"] + r["method_family"], re.I))
        and bool(re.search(r"dense|embed|hybrid", r["retrieval"] + r["method_family"], re.I)),
        "propagation": not nr(r["propagation"]) and not re.search(r"^not-reported", r["propagation"], re.I),
        "calibrated_confidence": conf_cal,
        "explanation_evaluated": bool(re.search(r"human evaluation|HEval|BLEU|BERTScore|rating|evidence correctness|factual support|Gwet|judge", r["explanation"] + r["metrics"], re.I)),
        "cost_reported": not nr(r["compression_cost"]),
        "public_artifact": bool(re.search(r"github|zenodo|replication package|code public|hugging ?face", r["artifacts"], re.I)),
    }
    d["multimodal"] = sum((d["metrics"], d["logs"], d["traces"])) >= 2
    d["multi_system_2plus"] = len(systems) >= 2
    d["rcaeval"] = "RCAEval" in systems
    return {k: int(v) for k, v in d.items()}, systems


DIMS = ["microservice", "rca", "multimodal", "llm_generative", "open_weight_llm", "retrieval", "retrieval_variants_compared",
        "propagation", "calibrated_confidence", "explanation_evaluated", "cost_reported", "multi_system_2plus", "rcaeval",
        "public_artifact"]


def main():
    rows = list(csv.DictReader(open(WORK / "extraction.csv", encoding="utf-8")))
    coded = []
    with open(WORK / "concept-matrix.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        head = ["id", "venue", "year", "read_level", "survey", "metrics", "logs", "traces"] + DIMS + ["systems"]
        w.writerow(head)
        for r in rows:
            c, systems = code(r)
            coded.append((r["id"], c))
            w.writerow([r["id"], r["venue"], r["year"], r["read_level"][:40]] + [c[k] for k in head[4:-1]] + ["|".join(systems)])
    primary = [(i, c) for i, c in coded if not c["survey"]]
    out = []
    for n in (1, 2, 3):
        for combo in itertools.combinations(DIMS, n):
            ids = [i for i, c in primary if all(c[k] for k in combo)]
            out.append([n, " & ".join(combo), len(ids), " ".join(ids)])
    with open(WORK / "concept-combos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arity", "combination", "n_primary_papers", "paper_ids"])
        w.writerows(out)
    print("papers", len(coded), "primary", len(primary), "combos", len(out))
    for k in DIMS:
        print(f"{k:28s}", sum(c[k] for _, c in primary))


if __name__ == "__main__":
    main()
