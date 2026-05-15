# Solo 401(k) S-Corp Optimizer (2026)

Browser-based optimizer for splitting S-Corp net profit between W-2 wages,
401(k) employee deferral, employer profit-sharing, and K-1 distribution to
minimize current-year federal tax burden. Solves an 11-variable LP via YALPS.

**Live:** https://USERNAME.github.io/solo-401k-optimizer/ · **Tests:** [`?test=1`](https://USERNAME.github.io/solo-401k-optimizer/?test=1)

## Usage

Open `index.html` in any modern browser. No server required.

`dist/index.html` is the self-contained single-file build (vendor libs +
ground truth inlined, ~115 KB) suitable for direct distribution or hosting.

## Testing

Open `index.html?test=1` (or `dist/index.html?test=1`) to run the 13
ground-truth cases. All must pass.

## Design

See [DESIGN.md](./DESIGN.md) — LP model, UI layout, 2026 tax constant verification.

## Local dev

```bash
# 1. Fetch vendor libs
mkdir -p vendor
curl -fsSL https://unpkg.com/yalps@0.6.4/dist/index.min.js          -o vendor/yalps.min.js
curl -fsSL https://unpkg.com/d3-selection@3.0.0/dist/d3-selection.min.js -o vendor/d3-selection.min.js
curl -fsSL https://unpkg.com/d3-array@3.2.4/dist/d3-array.min.js     -o vendor/d3-array.min.js
curl -fsSL https://unpkg.com/d3-path@3.1.0/dist/d3-path.min.js       -o vendor/d3-path.min.js
curl -fsSL https://unpkg.com/d3-shape@3.2.0/dist/d3-shape.min.js     -o vendor/d3-shape.min.js
curl -fsSL https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js  -o vendor/d3-sankey.min.js
cat vendor/d3-{selection,array,path,shape,sankey}.min.js > vendor/d3-sankey-bundle.min.js

# 2. Re-generate ground truth (if LP changed)
python3 scripts/gen_test_ground_truth.py
bash   scripts/inject_ground_truth.sh

# 3. Build self-contained dist
bash scripts/build.sh

# 4. Open in browser
open index.html              # dev mode
open dist/index.html?test=1  # tests
```

Requires `python3` with `scipy>=1.6`.

## Deployment (GitHub Pages)

CI auto-deploys `dist/` on every push to `main` via
[`.github/workflows/deploy.yml`](./.github/workflows/deploy.yml).

One-time setup after pushing to GitHub:

1. Repo Settings → **Pages** → Source = **GitHub Actions**
2. (or via CLI) `gh api -X POST /repos/USERNAME/solo-401k-optimizer/pages -f build_type=workflow`

The workflow pins all vendor versions and verifies YALPS bundle size (9,910
bytes) before deploying.
