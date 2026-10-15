# Jev: verified API, capabilities, limits and cost (2026-10-15)

No live call was made. Sources are TypeSafe's documentation and two provider listings, read
on 2026-10-15. **[F]** = stated by TypeSafe docs; **[P]** = stated by a provider listing only;
**[A]** = our inference.

Sources: [TypeSafe API](https://docs.typesafe.ai/api.md),
[Models](https://docs.typesafe.ai/models.md), [Confidence](https://docs.typesafe.ai/confidence.md),
[Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md),
[Confidence-gated routing](https://docs.typesafe.ai/patterns/confidence-routing.md),
[Python SDK](https://docs.typesafe.ai/sdk/python.md),
[Cloudflare Workers AI: typesafe/jev](https://developers.cloudflare.com/ai/models/typesafe/jev/),
[OpenRouter Jev guide](https://openrouter.ai/docs/guides/community/jev.md).

## 1. What Jev is

A "System One" decision model: it takes a `state` (string, object or array) and typed
`questions`, and returns probabilities. It produces no free text, explanations or reasoning
traces **[F]**. TypeSafe says it is not a chat model and is meant for narrow typed decisions that
code acts on.

## 2. API contract (TypeSafe direct)

`POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer <key>` **[F]**.

Request:

```json
{
  "model": "jev-1.13.0",
  "state": {"...": "..."},
  "questions": {
    "action":    {"type": "choice", "instructions": "...",
                  "criteria": {"accept": "...", "retrieve": "...", "escalate": "...", "abstain": "..."}},
    "supported": {"type": "noul", "instructions": "...",
                  "criteria": {"true": "...", "false": "..."}}
  }
}
```

- Question types: `noul` (yes/no probability), `choice` (≤255 options, keys of `criteria`),
  `score` (2–10 ordered levels), `box` (images) **[F]**. Question keys are not sent to the model.
- Response: `model` (e.g. `jev-1.13.0`), `answers.<key>`, `usage.{input_tokens,output_tokens}`.
  A choice answer has `choice`, `probabilities` (sum to 1) and `confidence`. A noul answer has
  `noul` ∈ [0, 1] only **[F]**.
- Limits: body ≤32 MiB; nesting ≤64; finite numbers only; per-question context 32k tokens
  (state + one question), per-request 64k; an opt-in long-context header exists, which TypeSafe
  calls "slower and less accurate" **[F]**.
- Errors: 400 (rule / `max_tokens_exceeded`), 401, 413, 415, 422 (validation), 429 (rate),
  529 (overloaded) **[F]**.
- Determinism: no seed parameter is documented **[F]**. Repeat-call stability must be measured
  **[A]**.

Other routes: Cloudflare Workers AI (`typesafe/jev`, body `{"model", "input": {state, questions}}`,
listed as zero data retention) **[P]**, and OpenRouter (`typesafe/jev-1.13`,
`POST /api/alpha/decisions`) **[P]**. The provider routes do not document version pinning.

## 3. Versions and pinning

`jev-latest` → `jev-1.13.0` (stable); `jev-preview` → `jev-1.14.0`, available from
2026-10-14 **[F]**. Aliases move when a release ships. TypeSafe advises sending the versioned id
when thresholds were tuned against one version **[F]**. **Decision for this plan:** pin
`jev-1.13.0` for all reported runs, store the response `model` per row, and refuse rows whose
`model` differs from the pin. A one-off 1.14 rerun is an optional robustness check.

## 4. Cost and rate limits

$0.042 per million input tokens, output free **[F]**. Planned volume (architecture §6) is about
2.5×10⁸ input tokens in the worst case, about **$11** in total **[A]**. Cost is negligible. Rate
limits are set per organisation in the console and are not published **[F]**. They are the real
operational risk; the client must back off on 429/529 and cache every response.

## 5. Confidence semantics (critical for the research design)

- Choice `confidence` = (p_max − 1/n) / (1 − 1/n), from the top probability only **[F]**.
- TypeSafe does **not** claim that confidence or probabilities match observed accuracy; it calls
  the formula "one reasonable way to summarise a distribution" and says thresholds depend on the
  domain and must be tested on your own data **[F]**.
- Low confidence may mean the question suits the model poorly or the input lacks information **[F]**.

Consequences for this plan:

1. Jev probabilities are treated as an uncalibrated score. Their relation to RCA correctness is
   an empirical question (RQ3/RQ4), not an assumption.
2. Jev's `choice` (argmax) is the default decision. Any Jev-confidence floor is a tuned Jev
   variant, fitted on the dev split only, and reported separately.
3. Calibration of Jev's `supported` noul is measured (ECE, AUROC) like any other confidence
   signal.

## 6. Documented weaknesses and how the design responds

| Jaggedness item **[F]** | Risk for RCA | Design response |
|---|---|---|
| Counting and numbers are unreliable; numeric scales weak | Evidence z-scores and "confidence 0.83" may be ignored or misread | State encodes LLM agreement as a verbal band plus the raw value as a string; ablation removes numbers (architecture §4) |
| Accuracy drops as state grows with unrelated content | Long evidence text | Cap evidence at 6,000 chars in the state; ablation with a short state |
| First option is favoured | Systematic bias toward one action | Randomise option order per call (seeded, logged); position-bias test on dev |
| Literal reading; negations and indirection hurt | Mis-scoped instructions | Plain affirmative instructions; criteria never contradict instructions; frozen after dev |
| Injected instructions in state can shift answers | Log lines are untrusted text | Evidence is benchmark telemetry (low risk); note as a threat to validity |
| Weak on System Two tasks | Jev cannot redo the RCA | Jev decides whether to act on the LLM answer; it does not diagnose |

## 7. Data-handling constraint

The state carries evidence text derived from AgenticOpsEval data (AIOps2025 CC BY-NC 4.0, RCA100
CC BY-NC-SA 4.0), released "private transfer only". TypeSafe says it does not train on requests;
zero data retention is for enterprise customers **[F]**. Cloudflare lists ZDR **[P]**. Whether
sending NC evidence to a third-party processor is acceptable is an owner decision (plan.md, open
decision D3). Labels never enter the state (allowlist test).

## 8. Integration requirements

- A `jev.py` module: state builder (allowlist-checked), question builder, a TypeSafe client
  (other routes only if decision D1 requires one that can pin the version), SQLite cache, retry with backoff on 429/529, a version
  guard and a deterministic `mock` backend for offline tests.
- Secrets: `TYPESAFE_API_KEY` from the environment;
  never logged, never in configs or results.
- Raw responses stored verbatim in `jev_raw.jsonl` next to the decisions.
