# Measured results, dataset v2.0

Independent trials saved and scored: 432/432. Complete: True.

| Condition | Passes | Pass rate | Feasible pass | Infeasible accuracy | Balanced accuracy | Mean seconds |
|---|---:|---:|---:|---:|---:|---:|
| classical | 72/72 | 100.0% | 100.0% | 100.0% | 100.0% | 0.0002 |
| B0 | 144/144 | 100.0% | 100.0% | 100.0% | 100.0% | 11.2067 |
| B1 | 144/144 | 100.0% | 100.0% | 100.0% | 100.0% | 12.7299 |
| B2 | 143/144 | 99.3% | 97.2% | 100.0% | 98.6% | 12.8950 |

## Interpretation boundaries

The suite has 18 feasible and 54 infeasible cases. Always declaring infeasible scores 75% overall, so report feasible success and balanced accuracy alongside the overall rate. Variants share their base, and repetitions share an instance. Confidence intervals resample the 18 base clusters, not 432 independent problems. They are descriptive and have limited resolution. Classical times average 10 local runs per case. LLM elapsed times include process, service and network overhead; token totals include the CLI system context. No cost in dollars is inferred.

B1-B0: paired pass-rate difference +0.000; 95% base-cluster interval [0.0, 0.0].
B2-B0: paired pass-rate difference -0.007; 95% base-cluster interval [-0.020833333333333332, 0.0].

## Violation categories

- classical: {}; generation errors 0.
- B0: {}; generation errors 0.
- B1: {}; generation errors 0.
- B2: {'arithmetic_error': 1}; generation errors 0.

## Results by duration_days

| Group | Condition | Passes | Mean seconds |
|---|---|---:|---:|
| 3 | classical | 24/24 | 0.0001 |
| 3 | B0 | 48/48 | 9.8235 |
| 3 | B1 | 48/48 | 11.3704 |
| 3 | B2 | 48/48 | 11.3779 |
| 5 | classical | 24/24 | 0.0002 |
| 5 | B0 | 48/48 | 11.2359 |
| 5 | B1 | 48/48 | 13.1712 |
| 5 | B2 | 48/48 | 13.2456 |
| 7 | classical | 24/24 | 0.0003 |
| 7 | B0 | 48/48 | 12.5607 |
| 7 | B1 | 48/48 | 13.6482 |
| 7 | B2 | 47/48 | 14.0615 |

## Results by difficulty

| Group | Condition | Passes | Mean seconds |
|---|---|---:|---:|
| high | classical | 24/24 | 0.0002 |
| high | B0 | 48/48 | 10.9620 |
| high | B1 | 48/48 | 12.4418 |
| high | B2 | 48/48 | 12.8961 |
| low | classical | 24/24 | 0.0002 |
| low | B0 | 48/48 | 11.4679 |
| low | B1 | 48/48 | 12.9108 |
| low | B2 | 48/48 | 12.9758 |
| medium | classical | 24/24 | 0.0002 |
| medium | B0 | 48/48 | 11.1902 |
| medium | B1 | 48/48 | 12.8373 |
| medium | B2 | 47/48 | 12.8131 |

## Results by variant

| Group | Condition | Passes | Mean seconds |
|---|---|---:|---:|
| budget | classical | 18/18 | 0.0002 |
| budget | B0 | 36/36 | 11.7380 |
| budget | B1 | 36/36 | 13.7410 |
| budget | B2 | 36/36 | 14.1122 |
| category | classical | 18/18 | 0.0001 |
| category | B0 | 36/36 | 9.0945 |
| category | B1 | 36/36 | 9.4182 |
| category | B2 | 36/36 | 9.5028 |
| feasible | classical | 18/18 | 0.0003 |
| feasible | B0 | 36/36 | 16.2897 |
| feasible | B1 | 36/36 | 19.9075 |
| feasible | B2 | 35/36 | 19.8547 |
| required_slot | classical | 18/18 | 0.0001 |
| required_slot | B0 | 36/36 | 7.7045 |
| required_slot | B1 | 36/36 | 7.8531 |
| required_slot | B2 | 36/36 | 8.1105 |
