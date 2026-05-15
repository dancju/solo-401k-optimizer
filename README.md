# Solo 401(k) S-Corp Optimizer (2026)

Browser-based optimizer for splitting S-Corp net profit between W-2 wages,
401(k) employee deferral, employer profit-sharing, and K-1 distribution to
minimize current-year federal tax burden. Solves an 11-variable LP via YALPS.

**Live:** https://dancju.github.io/solo-401k-optimizer/ · **Tests:** [`?test=1`](https://dancju.github.io/solo-401k-optimizer/?test=1)

## Usage

Open `index.html` in any modern browser. No server required.

`dist/index.html` is the self-contained single-file build (vendor libs +
ground truth inlined, ~115 KB) suitable for direct distribution or hosting.

## Testing

Open `index.html?test=1` (or `dist/index.html?test=1`) to run the 13
ground-truth cases. All must pass.

## Limitations

This is a **current-year federal tax minimizer**, not a financial advisor. It
computes one well-defined number: the tax-minimizing W-2 / 401(k) / K-1 split
given 2026 IRS limits. Have a CPA review the output before filing.

### Not modeled (v1 scope)

- **Catch-up contributions** — age 50+ §414(v) and age 60–63 SECURE 2.0 §109
- **Roth 401(k) split** — all employee deferral treated as traditional pre-tax
- **State income tax** — assumes 0%
- **NIIT 3.8%** / **Additional Medicare 0.9%** — only relevant above $250k MFJ
- **FEIE (Form 2555)** — assumes 100% US-source earned income
- **HSA / §125 cafeteria / self-employed health insurance**
- **Multi-year planning** — 2026 only
- **Two separate S-Corps in one household** — run the tool twice independently

### Important caveats

- **Tax-deferred ≠ tax-saved.** 401(k) contributions reduce 2026 tax but are
  taxed at retirement-era marginal rates on withdrawal. If your future bracket
  exceeds today's, over-deferring increases lifetime tax.
- **Reasonable compensation is your responsibility.** The default
  `W_min = $30,000` is a placeholder; the IRS requires reasonable comp based on
  your actual role, hours, industry, and geography.
- **§199A QBI assumes household TI < $403,500 (MFJ).** Above that threshold,
  SSTB / W-2 wage / UBIA limits apply and are not modeled.
- **SS wage base.** Reliable for S-Corp profit ≤ ~$200k; FICA may overestimate
  by ≤ $80 near the boundary, and results become unreliable above the wage base.

See [DESIGN.md §1.3 / §7 / §8](./DESIGN.md) for the full out-of-scope list and
planned v1.1+ extensions.

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
2. (or via CLI) `gh api -X POST /repos/dancju/solo-401k-optimizer/pages -f build_type=workflow`

The workflow pins all vendor versions and verifies YALPS bundle size (9,910
bytes) before deploying.
