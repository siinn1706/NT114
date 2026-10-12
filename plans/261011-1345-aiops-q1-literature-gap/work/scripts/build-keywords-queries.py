"""Write keywords.csv and queries.csv for the Q1 AIOps literature search."""
import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]

# group, term, variants (| separated), proposal paragraph ids / advisor note
KEYWORDS = [
    ("C1", "microservice", "microservices|micro-service|microservice architecture|microservice system", "P0003 P0008"),
    ("C1", "cloud-native", "cloud native|cloud-native application", "P0008"),
    ("C1", "Kubernetes", "container orchestration|containerized", "P0003 P0026"),
    ("C1", "cloud service", "online service system|cloud system|large-scale cloud|distributed system", "P0008"),
    ("C2", "multimodal telemetry", "multi-source data|multimodal data|metrics logs traces|heterogeneous monitoring data", "P0012 P0030-P0033"),
    ("C2", "metric", "KPI|time series|performance metric", "P0032"),
    ("C2", "log", "system log|log data", "P0031"),
    ("C2", "trace", "distributed tracing|span|call trace", "P0033"),
    ("C2", "observability", "OpenTelemetry|monitoring", "P0045"),
    ("C3", "anomaly detection", "outlier detection|Isolation Forest", "P0013 P0049-P0052"),
    ("C3", "incident detection", "failure detection|fault detection", "P0021"),
    ("C4", "root cause analysis", "RCA|root cause localization|root cause identification", "P0003 P0022"),
    ("C4", "fault localization", "failure localization|fault diagnosis|failure diagnosis", "P0016 P0022"),
    ("C4", "fault type classification", "failure type|failure classification|fault classification", "P0022 P0040"),
    ("C5", "large language model", "LLM|LLMs|language model", "P0009 P0016 P0076"),
    ("C5", "LLM agent", "agent|multi-agent|agentic", "P0009"),
    ("C5", "AIOps", "IT operations|incident management", "P0009"),
    ("C5", "fine-tuning", "LoRA|parameter-efficient fine-tuning|instruction tuning", "P0076"),
    ("C6", "retrieval-augmented generation", "RAG|retrieval augmented", "P0015 P0071"),
    ("C6", "hybrid retrieval", "BM25|dense retrieval|sparse retrieval|reciprocal rank fusion|hybrid search", "P0015 P0065-P0070"),
    ("C6", "historical incidents", "similar incidents|case-based reasoning|knowledge base|runbook|troubleshooting guide", "P0064"),
    ("C7", "log parsing", "log template|Drain|log parser", "P0056"),
    ("C7", "context compression", "summarization|token budget|context window|prompt compression", "P0014 P0054 P0059"),
    ("C7", "feature selection", "metric reduction|dimensionality reduction", "P0055 P0058"),
    ("C8", "explainability", "explainable|interpretable|interpretability|explanation", "P0017 P0023 P0119"),
    ("C8", "faithfulness", "hallucination|grounded|evidence|citation", "P0041 P0120"),
    ("C8", "LLM-as-a-judge", "LLM as a judge|LLM evaluator|human evaluation", "P0121"),
    ("C8", "uncertainty", "confidence|calibration|trustworthy", "note-29-9 line 9"),
    ("C9", "fault propagation", "failure propagation|anomaly propagation|error propagation", "P0057; note-29-9 line 4"),
    ("C9", "dependency graph", "call graph|service dependency|topology", "P0057"),
    ("C9", "causal inference", "causal discovery|causality|causal graph", "P0147"),
    ("C10", "MLOps", "reproducibility|continuous evaluation", "P0018 P0078"),
    ("C10", "benchmark", "dataset|empirical study|evaluation framework", "P0025"),
    ("C10", "chaos engineering", "fault injection", "P0026 P0082"),
]

G = {
    "C1": '("microservice" OR "microservices" OR "cloud-native" OR "cloud native" OR "Kubernetes")',
    "C1x": '("microservice" OR "microservices" OR "cloud-native" OR "cloud native" OR "Kubernetes" OR "cloud system" OR "online service system" OR "cloud service" OR "distributed system")',
    "C2": '("multimodal" OR "multi-source" OR "metrics" OR "logs" OR "traces" OR "tracing" OR "telemetry")',
    "C3": '("anomaly detection" OR "failure detection" OR "fault detection" OR "incident detection")',
    "C4": '("root cause" OR "fault localization" OR "failure localization" OR "fault diagnosis" OR "failure diagnosis")',
    "C5": '("large language model" OR "large language models" OR "LLM" OR "LLMs" OR "language model")',
    "C5a": '("AIOps" OR "IT operations" OR "incident management")',
    "C6": '("retrieval-augmented" OR "retrieval augmented" OR "RAG" OR "BM25" OR "dense retrieval" OR "hybrid retrieval" OR "rank fusion")',
    "C6b": '("historical incidents" OR "similar incidents" OR "case-based reasoning" OR "knowledge base" OR "troubleshooting")',
    "C7": '("log parsing" OR "log template" OR "summarization" OR "compression" OR "token")',
    "C8": '("explainable" OR "interpretable" OR "interpretability" OR "explanation")',
    "C8b": '("uncertainty" OR "confidence" OR "calibration" OR "trustworthy")',
    "C8c": '("hallucination" OR "faithfulness" OR "LLM-as-a-judge" OR "LLM as a judge")',
    "C9": '("propagation" OR "call graph" OR "dependency graph" OR "topology")',
    "C9b": '("causal" OR "causality")',
    "C10": '("benchmark" OR "empirical study" OR "evaluation")',
    "C10b": '("fault injection" OR "chaos engineering")',
    "C5o": '("AIOps" OR "artificial intelligence for IT operations")',
    "C5r": '("AIOps" OR "incident management" OR "root cause" OR "failure diagnosis")',
    "C5m": '("large language model" OR "large language models" OR "LLM")',
    "Cops": '("AIOps" OR "incident" OR "log analysis" OR "root cause")',
    "C6r": '("retrieval-augmented" OR "retrieval augmented" OR "RAG")',
    "C8h": '("hallucination" OR "faithfulness")',
    "C7l": '("log parsing" OR "log analysis" OR "telemetry")',
    "SV2": '("survey" OR "systematic literature review" OR "systematic mapping")',
    "SV": '("survey" OR "systematic literature review" OR "systematic mapping" OR "review")',
}

QUERIES = [
    ("Q01", ["C1", "C4"], "core: RCA in microservices/cloud-native"),
    ("Q02", ["C1", "C3", "C2"], "anomaly detection on multimodal telemetry"),
    ("Q03", ["C1x", "C4", "C5"], "LLM for RCA"),
    ("Q04", ["C1x", "C3", "C5"], "LLM for anomaly detection in systems"),
    ("Q05", ["C5r", "C5m"], "LLM for AIOps/incident management"),
    ("Q06", ["C1x", "C4", "C6"], "retrieval/RAG for RCA"),
    ("Q07", ["C5a", "C6"], "retrieval/RAG for AIOps"),
    ("Q08", ["C1x", "C4", "C6b"], "historical incidents / CBR for diagnosis"),
    ("Q09", ["C1", "C4", "C9"], "propagation-aware RCA"),
    ("Q10", ["C1", "C4", "C9b"], "causal RCA"),
    ("Q11", ["C1x", "C4", "C8"], "explainable RCA"),
    ("Q12", ["C1x", "C4", "C8b"], "uncertainty/confidence in RCA"),
    ("Q13", ["C1x", "C3", "C8b"], "uncertainty in anomaly detection"),
    ("Q14", ["C6r", "C8h", "Cops"], "RAG faithfulness/hallucination evaluation"),
    ("Q15", ["C1x", "C3", "C7"], "log parsing/compression for detection"),
    ("Q16", ["C5m", "C7l"], "LLM + telemetry/log compression"),
    ("Q17", ["C1", "C4", "C10"], "RCA benchmarks/empirical studies"),
    ("Q18", ["C1", "C10b"], "fault injection / chaos in microservices"),
    ("Q19", ["C1x", "C4", "SV"], "surveys on RCA"),
    ("Q20", ["C5o", "SV2"], "surveys on AIOps"),
    ("Q21", ["C1", "C3", "SV"], "surveys on anomaly detection in microservices"),
    ("Q22", ["C1x", "C4", "C2"], "multimodal/multi-source RCA"),
]

FILTERS = "type:article|review,primary_location.source.type:journal,from_publication_date:2020-01-01"


def main():
    with open(OUT / "keywords.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group", "term", "variants", "proposal_source"])
        w.writerows(KEYWORDS)
    with open(OUT / "queries.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "groups", "purpose", "boolean", "filters"])
        for qid, groups, purpose in QUERIES:
            w.writerow([qid, "openalex:title_and_abstract.search", "+".join(groups), purpose,
                        " AND ".join(G[g] for g in groups), FILTERS])
    print(len(KEYWORDS), "keywords;", len(QUERIES), "queries")


if __name__ == "__main__":
    main()
