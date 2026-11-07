# CS4263 Group 17: constrained travel planning

This repository contains the current Python implementation, executable prompts, regression tests, fixed synthetic benchmark inputs and recorded version-2 evidence for a comparison of classical constraint satisfaction search and direct language model reasoning.

The report, slide deck, proposal, legacy pilot, local guide, caches and build artifacts remain in the local submission workspace. The final measured outputs, scores, settings manifest and raw trial logs are included here so the report can link directly to its evidence.

## Requirements

- Python 3.9 or newer. The experiment code uses only the Python standard library.
- Checking the benchmark, running classical search and executing tests require no network or model account.
- Fresh LLM trials require either the Codex CLI with a working login, or an OpenAI API key and an available model.

## Quick start

From the repository root:

```bash
python3 check_benchmark.py
python3 -m unittest -v test_project.py
python3 run_all.py
```

The local rebuild regenerates the deterministic benchmark and label-free inputs, solves and scores all 72 classical cases, runs regression tests and generates analysis. It makes no model calls and does not regenerate the legacy pilot. Existing independent model records, when present locally, are scored and preserved.

A fresh clone includes all 432 recorded LLM trials. Scoring and analysing those saved responses requires no model account and makes no new model calls. Running the full rebuild measures classical latency again, so that timing may differ from the published snapshot. To reproduce the published aggregates from the saved scores, run `python3 analyze_results.py` without regenerating classical outputs.

## Code map

| File | Purpose |
|---|---|
| `generate_benchmark.py` | Construct the deterministic v2 synthetic dataset and its witnesses/proofs. |
| `benchmark.json` | Canonical 72-case benchmark with evaluation labels and witnesses. |
| `check_benchmark.py` | Verify crossed counts, witness validity, one-field mutations and infeasibility proofs. |
| `export_llm_inputs.py` | Remove ground truth, feasibility and construction metadata before model calls. |
| `llm_inputs.jsonl` | Frozen label-free model inputs, one case per line. |
| `csp_solver.py` | Finite backtracking CSP with dynamic MRV, forward checking and sound bounds. |
| `prompt_templates.py` | Exact executable B0/B1/B2 instructions. |
| `prompts.md` | Explanation of prompt conditions and their limitations. |
| `llm_runner.py` | Independent tool-free model trials, frozen manifests, raw preservation and resume. |
| `project_common.py` | Shared JSON helpers, time conversion and output schema. |
| `validator.py` | Post-generation, score-only constraint and arithmetic checking. |
| `analyze_results.py` | Aggregate/subgroup metrics, paired contrasts and descriptive cluster intervals. |
| `test_project.py` | Regression tests, including 80 small random exhaustive comparisons. |
| `run_all.py` | Rebuild and verify the local experiment without making model calls. |

## Benchmark composition

The suite crosses 3-, 5- and 7-day trips with low, medium and high intended constraint-load profiles. Each duration/load cell has two feasible base replicas. Each base also has separate impossible-budget, category-capacity and required-slot-conflict variants:

`3 durations × 3 profiles × 2 bases × (1 feasible + 3 infeasible) = 72 cases`

The suite contains 18 feasible and 54 infeasible cases. Every contradiction type occurs at every duration and load. Candidates include varied opening windows, duration traps, shared attraction choices, directed transfer overrides and tighter budgets. The checker verifies labels through feasible witnesses and short contradiction proofs.

Constraint-load labels describe intended requirements, not an empirically proven hardness ranking. Variants share a base. Always declaring infeasible scores 75% overall, so the analysis also reports feasible success, infeasible accuracy and balanced accuracy.

## Published result evidence

| File | Evidence |
|---|---|
| [RESULTS_SUMMARY.md](RESULTS_SUMMARY.md) | Human-readable aggregate and subgroup results. |
| [analysis_summary.json](analysis_summary.json), [results.csv](results.csv) | Machine-readable aggregates and per-trial metrics. |
| [classical_outputs.jsonl](classical_outputs.jsonl), [classical_scores.jsonl](classical_scores.jsonl) | 72 classical outputs, measured timing samples and independent scores. |
| [experiments/v2_llm_outputs.jsonl](experiments/v2_llm_outputs.jsonl) | All 432 model outputs with model/settings metadata, latency, usage and raw-log links. |
| [experiments/v2_llm_scores.jsonl](experiments/v2_llm_scores.jsonl) | Independent scores for every recorded model trial. |
| [experiments/v2_llm_outputs.manifest.json](experiments/v2_llm_outputs.manifest.json) | Frozen protocol settings and input/prompt hashes. |
| [experiments/v2_llm_outputs_raw/](experiments/v2_llm_outputs_raw/) | 432 trial logs containing exact prompts, output text and CLI response events. |

Classical passed 72/72; B0 and B1 each passed 144/144; B2 passed 143/144. The failed `V2T050`, B2, trial 1 remains in the evidence: declared cost 1086 versus computed cost 1066. No answer was repaired or excluded.

For publication, the local username prefix in CLI warnings and diagnostic paths was replaced with `/Users/REDACTED`. Original unedited logs are retained locally. Prompts, model answer text, parsed answers, scores, timestamps, response identifiers, timing and token usage are unchanged. Configuration warning events are preserved; all trials completed with exit code zero, and these warnings are not generation failures.

## Independent model trials

The recorded study's protocol requested `gpt-6.1-sol` with medium reasoning, two fresh repetitions per case and condition, fixed shuffled order seed 42632 and six workers. Its 432 actual responses and their raw logs are published under `experiments/`. Model availability and CLI features may change over time.

To run fresh trials using a compatible installed Codex CLI and its existing login, choose a new output path:

```bash
python3 llm_runner.py --backend codex --model gpt-6.1-sol \
  --repetitions 2 --workers 6 --output experiments/new_run_outputs.jsonl
```

The published `experiments/v2_llm_outputs.jsonl` file is already complete. Using that path resumes the recorded run and skips its 432 existing trials. Keep fresh trials in a separate file. To analyse them, score that new file with `validator.py`, then pass the new score file to `analyze_results.py --llm PATH_TO_NEW_SCORES`.

Alternatively, configure `OPENAI_API_KEY` locally, choose an available API model and use `--backend api --model YOUR_MODEL` with a new output path. Fresh runs consume account allowance or incur API usage charges. Never commit credentials.

Score and analyse saved responses:

```bash
python3 validator.py --inputs experiments/v2_llm_outputs.jsonl \
  --output experiments/v2_llm_scores.jsonl
python3 analyze_results.py
```

The runner freezes input/prompt hashes and model settings in a manifest, resumes by `(instance_id, condition, trial_id)`, and refuses incompatible manifests or pilot provenance. Every trial uses a fresh context. Complete responses are saved before parsing. Failures remain failures; scoring never constructs, selects or repairs an LLM plan.

## Interpretation and scope

B0 requests direct reasoning. B1 adds a constraint checklist, internal ledger and timing table. B2 retains B1 and adds single-response draft/check/revision instructions. B2 is literature-inspired self-verification; final notes do not prove independent multi-call verification occurred.

The classical solver returns the first feasible assignment, not a certified utility optimum. Its correctness argument applies to the finite encoded model, including its explicit slot and transport assumptions. Raw CLI timings include startup, network and service overhead; token counts include system context. Descriptive uncertainty resamples shared-base clusters. Synthetic data, few base replicas, short contradiction proofs and one model configuration limit generalisation.

The code/data publication corresponds to benchmark v2.0. Ground truth is available for post-generation evaluation and must remain hidden from model inputs. Report and presentation sources remain local. The optional `run_all.py --compile-report` flag applies only to a workspace that also contains those local report sources and an installed Tectonic compiler.
