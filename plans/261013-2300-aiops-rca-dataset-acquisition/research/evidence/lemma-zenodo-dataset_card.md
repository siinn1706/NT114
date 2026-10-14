# Dataset Card: LEMMA-RCA

## Dataset summary

LEMMA-RCA is a large multi-modal, multi-domain dataset for root cause analysis (RCA). It contains monitoring data from information technology (IT) and operational technology (OT) systems, including microservice systems and water treatment/distribution systems. The dataset is designed to support benchmarking and development of RCA methods under offline/online and single-/multi-modal settings.

## Modalities

The dataset includes, depending on the sub-dataset:

- time-series system metrics;
- system logs or processed log-derived features;
- key performance indicators (KPIs);
- fault timestamps;
- root-cause entity labels;
- benchmark configuration and preprocessing documentation.

## Sub-datasets

| Sub-dataset | Domain | Data type | Access note |
|---|---|---|---|
| Product Review | IT / microservices | metrics, logs, KPIs, labels | Available through the project website |
| Cloud Computing | IT / cloud systems | metrics, logs, KPIs, labels | Available through the project website |
| SWaT | OT / water treatment | sensor/actuator time series, labels | Access follows the original SWaT/iTrust terms and the instructions on the project website |
| WADI | OT / water distribution | sensor/actuator time series, labels | Access follows the original WADI/iTrust terms and the instructions on the project website |

## Access

The full dataset is large and is not directly uploaded to this Zenodo record. The canonical access point is:

https://www.lemmarca.info

This Zenodo record provides archival metadata and points to the maintained dataset access page.

## Intended uses

LEMMA-RCA is intended for academic and industrial research on:

- root cause analysis;
- AIOps;
- anomaly detection;
- time-series analysis;
- log analysis;
- multi-modal system diagnosis;
- online RCA benchmarking.

## Out-of-scope uses

The dataset is not intended for attacking, disrupting, or compromising real systems. Any security-related traces or fault scenarios are provided for research and benchmarking purposes only.

## Ethics, privacy, and responsible release

The dataset is based on system telemetry and benchmark/testbed monitoring data. It is not intended to contain human-subject data. Users should follow the access terms, licenses, and responsible-use instructions provided on the project website and by the original providers of third-party sub-datasets such as SWaT and WADI.

Before release, sensitive operational identifiers, secrets, credentials, and private deployment information should be removed or anonymized where applicable.

## Limitations

LEMMA-RCA does not cover all possible real-world system faults. Some scenarios are collected from controlled systems or testbeds and may not fully capture all operational conditions in production environments. Results on this benchmark should therefore be interpreted as evidence of performance on the released scenarios, not as a guarantee of general RCA performance in all systems.

## Maintenance

The project website provides the latest access instructions, documentation, and update information:

https://www.lemmarca.info
