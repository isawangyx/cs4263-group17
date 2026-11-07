# Contemporary-AI conditions, prompt version 2.0

All conditions receive identical label-free instance data and the same JSON output requirements, with no tool, solver or validator access. `prompt_templates.py` is authoritative.

- **B0:** Direct reasoning to produce a complete valid itinerary or recognise infeasibility.
- **B1:** B0 plus explicit constraint coverage, an internal itemised budget ledger and a day-by-day timing table.
- **B2:** All B1 instructions plus a draft, separate checking questions, recalculation and one revision within the same response.

B2 is **single-response self-verification**, inspired by CoVe/Self-Refine. It does not demonstrate independent multi-call verification. Final notes cannot prove the hidden checking process occurred.

Independent evaluation uses fresh contexts for every case, condition and repetition. Complete prompts, raw responses, token usage and elapsed times are preserved under `experiments`. The manifest freezes prompt/input hashes and model settings. The scoring validator never repairs model plans. The original fixed-answer pilot is archived and excluded from independent analysis.
