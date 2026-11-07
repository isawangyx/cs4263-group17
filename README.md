# CS4263 Group 17: constrained travel planning

This repository contains the current Python implementation, executable prompts, regression tests and fixed synthetic benchmark inputs for a comparison of classical constraint satisfaction search and direct language model reasoning.

The report, slide deck, proposal, recorded experiment outputs, legacy pilot, local guide, caches and build artifacts are intentionally excluded. The project authors retain those files in the submission workspace.

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

A fresh clone contains no recorded LLM outputs. Its initial analysis therefore contains classical results only and reports the independent experiment as incomplete. Generated outputs remain ignored by Git.

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

## Independent model trials

The recorded study's protocol requested `gpt-6.1-sol` with medium reasoning, two fresh repetitions per case and condition, fixed shuffled order seed 42632 and six workers. Its 432 actual responses remain in the authors' local evidence archive. Model availability and CLI features may change over time.

To run fresh trials using a compatible installed Codex CLI and its existing login:

```bash
python3 llm_runner.py --backend codex --model gpt-6.1-sol \
  --repetitions 2 --workers 6 --output experiments/v2_llm_outputs.jsonl
```

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
