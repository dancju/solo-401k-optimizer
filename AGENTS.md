# AGENTS.md

Agent workflow guide for the Solo 401(k) S-Corp Optimizer. For *what* the system does and *why*, read [DESIGN.md](./DESIGN.md). For end-user usage, read [README.md](./README.md).

## Commands

```bash
# Dev (no build — single-file app)
open index.html

# Run tests (13 ground-truth cases; all must pass)
open index.html?test=1

# After ANY change to the LP model in index.html: regenerate ground truth
python3 scripts/gen_test_ground_truth.py && bash scripts/inject_ground_truth.sh

# Build self-contained dist/index.html
bash scripts/build.sh
```

One-time vendor fetch: see README "Local dev" step 1.

## Ironclad rules

1. **Single-file architecture.** `index.html` must remain openable via `file://` with no build step. No npm, no Vite, no ES modules. IIFE namespacing only. (DESIGN.md §4.1, §4.4)

2. **All deps inlined.** No runtime CDN fetches in either `index.html` or `dist/index.html`. `dist/` must be fully self-contained.

3. **LP changes require ground-truth regen.** Any edit to LP variables, constraints, or objective in `index.html` must be followed by `gen_test_ground_truth.py` + `inject_ground_truth.sh`, then a passing `?test=1` run. The 13 cases are the LP's correctness contract — never hand-edit `tests/ground_truth.json`.

4. **YALPS bundle size is enforced.** `vendor/yalps.min.js` must stay exactly 9,910 bytes; CI fails otherwise (`.github/workflows/deploy.yml`). Don't upgrade YALPS without updating both the workflow check and DESIGN.md §4.3.

5. **Respect scope.** Do not add catch-up contributions, state tax, NIIT, Roth split, FEIE, multi-year, second S-Corp, or HSA without explicit user approval. These are documented as v1.1+ in DESIGN.md §1.3 / §7 / §8.

## Where to look

- LP model (vars, constraints, objective): DESIGN.md §2
- 2026 tax constants + IRS source citations: DESIGN.md §6
- Sankey node/edge structure: DESIGN.md §3.3
- Resolved design questions (don't relitigate): DESIGN.md §11
