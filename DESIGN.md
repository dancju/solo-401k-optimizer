# Solo 401(k) S-Corp Optimizer — Design

> Single-page tool for optimizing the split of S-Corp net profit between W-2 wages, Solo 401(k) contributions (employee deferral + employer profit-sharing), and K-1 distribution to minimize total federal current-year tax burden, subject to 2026 IRS limits.
>
> Status: v2 design locked 2026-05-14 (post-audit revisions). Implementation pending.

---

## 1. Purpose & Scope

### 1.1 What this tool does

Given the user's S-Corp net profit (before owner compensation), filing status, and optional reasonable-compensation lower bound, the tool computes the **optimal allocation** of that profit across:

- W-2 wages (single S-Corp owner)
- 401(k) employee deferral (traditional pre-tax)
- 401(k) employer profit-sharing
- K-1 distribution

… that minimizes the **current-year federal tax burden** = federal income tax + employee FICA + employer FICA (both halves count, since both come out of household economic pie) + SE tax on any Schedule C income parameter.

**⚠️ Important caveat — current-year vs lifetime tax:** This tool minimizes **current-year tax**. 401(k) contributions (`ED` + `PS`) are **tax-deferred, not tax-saved** — they reduce 2026 taxable income but will be taxed upon withdrawal at retirement-era marginal rates. If your expected retirement marginal rate is **higher** than your current marginal rate (e.g., you're in 12% today due to deductions but expect 22%+ in retirement), over-deferring increases lifetime tax. Interpret the "optimal" output as the **current-year tax minimum**, not the lifetime tax minimum.

**Scope: single S-Corp owner.** The LP models one S-Corp owner's allocation. For households where two spouses each run their own S-Corp with separate Solo 401(k)s, run the tool twice independently and aggregate manually (per-individual §402(g) / §415(c) caps cannot legally be "doubled" inside a single LP).

### 1.2 In scope

- Single Solo 401(k) participant (S-Corp owner-employee)
- 2026 tax year
- Filing status: MFJ (default), Single, HoH, QW (Qualifying Widow) — affects standard deduction + tax brackets
- §402(g)(1) ED limit, §415(c)(1)(A) dollar cap, §415(c)(1)(B) 100%-of-comp cap, §401(a)(17) W-2 comp cap (not binding in stated range)
- Federal income tax (progressive brackets, piecewise-linear)
- FICA (SS + Medicare, both employee and employer halves)
- §199A QBI deduction on Schedule C net profit **and** S-Corp K-1 portion (assumes household TI < §199A MFJ threshold $403,500, so non-SSTB W-2 wage/UBIA limits don't apply)
- Other passive / W-2 income parameter (joint household; not QBI-eligible; FICA/withholding already paid externally)
- Schedule C net profit parameter (joint household; subject to SE tax; QBI-eligible)
- Standard deduction (filing-status-dependent)
- Optional reasonable comp lower bound (default $30,000 with IRS disclaimer)

### 1.3 Out of scope (intentional)

- FEIE Form 2555 / foreign earned income exclusion — tool assumes 100% US-source earned income
- Catch-up contributions: age 50+ §414(v), age 60-63 SECURE 2.0 §109 super catch-up
- State income tax — tool assumes 0% state rate
- NIIT 3.8% (only triggers above $250k MFJ MAGI on net investment income; S-Corp active business income excluded per §1411(c)(2)(A))
- Additional Medicare 0.9% (only triggers above $250k MFJ wages; out of typical range)
- Two S-Corp owners in same household sharing one LP (run tool twice)
- HSA / cafeteria plans / other §125 deductions
- Roth 401(k) split (ED treated as traditional pre-tax only)
- Self-employed health insurance / SE retirement deduction adjustments to QBI base
- Multi-year planning
- SS wage base interaction with SE tax / FICA when `W + 0.9235·SchedC > $184,500` (tool assumes sum below cap; see §7 for boundary note)

---

## 2. LP Model

### 2.1 Decision variables (all continuous, ≥ 0)

| Var | Type | Meaning |
|---|---|---|
| `W` | $ | S-Corp owner W-2 gross wages |
| `ED` | $ | 401(k) employee deferral (traditional pre-tax) |
| `PS` | $ | Employer profit-sharing contribution |
| `K1` | $ | K-1 distribution to owner |
| `QBI` | $ | §199A QBI deduction taken (LP maximizes to minimize tax) |
| `TI` | $ | Federal taxable income (post std ded + post QBI ded) |
| `t1`, `t2`, `t3`, `t4` | $ | Tax-bracket segment fillers (piecewise-linear federal tax) |
| `TI_pre` | $ | Pre-QBI taxable income floor: `max(0, AGI − StdDed)` (LP-ified via `TI_pre ≥ AGI − StdDed` + `TI_pre ≥ 0`) |

Total: **11 decision variables**.

### 2.2 Parameters (user inputs + constants)

**User inputs:**

| Param | Type | Range / Default | Meaning |
|---|---|---|---|
| `X` | $ | 0–200,000 (step 1,000), default 100,000 | S-Corp net profit *before owner comp* (the "pie") |
| `OtherIncome_passive` | $ | 0–500,000, default 0 | Joint passive / W-2 income from other sources; not QBI-eligible |
| `SchedC_NetProfit` | $ | 0–500,000, default 0 | Joint Schedule C net profit; subject to SE tax; QBI-eligible |
| `FilingStatus` | enum | MFJ / Single / HoH / QW, default MFJ | Determines std deduction + bracket widths |
| `W_min` | $ | 0–200,000, default 30,000 | Reasonable comp lower bound |

> **Note on slider top X = $200k**: Chosen to keep `W ≤ $184,500` SS wage base in worst-case (`W = X/1.0765 ≈ $185,800` at X=$200k, marginally over; ≤ $80 FICA overestimate). For larger X scenarios, see §7 boundary note.

**2026 tax-year constants (all verified ✅; see §6 for sources):**

| Const | Value | Reference |
|---|---|---|
| `ED_MAX` | $24,500 | §402(g)(1) |
| `SEC415_CAP` | $72,000 | §415(c)(1)(A) dollar limit |
| `COMP_CAP_401A17` | $360,000 | §401(a)(17); not binding in stated range |
| `PS_RATE` | 0.25 | Employer profit-sharing rate cap (S-Corp owner-employee) |
| `FICA_RATE` | 0.0765 | One side (6.2% SS + 1.45% Medicare) |
| `SE_TAX_RATE` | 0.153 | Self-employment tax combined rate |
| `SE_INCOME_FACTOR` | 0.9235 | = 1 − 0.0765; multiplier to SchedC for SE income base |
| `SS_WAGE_BASE` | $184,500 | OASDI taxable maximum 2026 |
| `QBI_RATE` | 0.20 | §199A(a)(1) |
| `QBI_TI_THRESHOLD_MFJ` | $403,500 | §199A non-SSTB phase-in start (MFJ) |

**Standard deduction (2026, by filing status):**

| FilingStatus | Std Deduction |
|---|---:|
| MFJ / QW | $32,200 |
| HoH | $24,150 |
| Single | $16,100 |

**Federal tax brackets (2026 MFJ; widths used by LP):**

| Rate | Bracket top | Width |
|---|---:|---:|
| 10% | $24,800 | $24,800 |
| 12% | $100,800 | $76,000 |
| 22% | $211,400 | $110,600 |
| 24% | $403,550 | $192,150 |

Single + HoH bracket lookup tables maintained in `TaxConstants.BRACKETS` (see §4.2). Tool restricts to first 4 brackets [10/12/22/24%]; in stated X range, TI cannot reach the 32% bracket.

### 2.3 Pre-computed quantities (derived from parameters, not LP variables)

```
SE_base    = 0.9235 · SchedC_NetProfit                  # SE income base
SE_tax     = 0.153  · SE_base                           # = 0.14130 · SchedC
SE_ded     = 0.5    · SE_tax                            # above-line deduction for 1/2 SE tax
StdDed     = lookup(FilingStatus)                       # from §2.2 table
[brkw1, brkw2, brkw3, brkw4] = bracket_widths(FilingStatus)
```

SE tax formula assumes `W + SE_base < $184,500` (SS wage base). For boundary cases where the sum approaches the cap, SE_tax overestimates the SS portion of SchedC; see §7.

### 2.4 Constraints

```
budget:        1.0765 · W + PS + K1 = X
                 # 1.0765·W = W + employer FICA (7.65%); both are S-Corp expenses
                 # PS contribution is also S-Corp expense → reduces K1

ED_legal:      ED ≤ 24500                                  # §402(g)(1)
ED_comp:       ED ≤ W                                       # §402(g) 100%-of-comp
ED_paycheck:   ED ≤ 0.9235 · W                              # clean-paycheck (take-home ≥ 0); toggleable

PS_max:        PS ≤ 0.25 · W                                # §404(a) 25% of W (S-Corp owner-employee)

sec415_dollar: ED + PS ≤ 72000                              # §415(c)(1)(A) dollar limit
sec415_comp:   ED + PS ≤ W                                  # §415(c)(1)(B) 100%-of-comp limit
                                                            # §415 comp = W-2 wages for S-Corp owner;
                                                            # includes ED per §415(c)(3)(D)

QBI_base:      QBI ≤ 0.20 · (K1 + SchedC_NetProfit - SE_ded)
                                                            # K1 and SchedC are QBI;
                                                            # SchedC QBI reduced by 1/2 SE tax per Reg §1.199A-3(b)(1)(vi)

TI_pre_def:    TI_pre ≥ AGI - StdDed                        # combined with TI_pre ≥ 0 →
                                                            # TI_pre = max(0, AGI - StdDed) at optimum
QBI_TI_cap:    QBI ≤ 0.20 · TI_pre                          # §199A(a)(1)(B) taxable income limit
                                                            # (handles AGI ≤ StdDed case correctly:
                                                            #  TI_pre = 0 → QBI = 0; net cap gains assumed 0)

TI_def:        TI ≥ TI_pre - QBI                            # post-QBI TI; LP forces equality at optimum
TI_nonneg:     TI ≥ 0

brackets:      t1 + t2 + t3 + t4 = TI
               t1 ≤ brkw1                                   # depends on FilingStatus
               t2 ≤ brkw2
               t3 ≤ brkw3
               t4 ≤ brkw4

rsbl_comp:     W ≥ W_min                                    # default $30,000

non-negativity: all variables ≥ 0
```

Expanding `AGI` inline:

```
AGI = (W - ED) + K1 + OtherIncome_passive + SchedC_NetProfit - SE_ded

TI_pre_def rewritten:
  TI_pre ≥ W - ED + K1 + OtherIncome_passive + SchedC_NetProfit - SE_ded - StdDed
  (combined with TI_pre ≥ 0) → TI_pre = max(0, AGI - StdDed) at LP optimum

TI_def rewritten:
  TI ≥ TI_pre - QBI
```

### 2.5 Objective: minimize total current-year tax

```
min:  FedTax + 2 · 0.0765 · W + SE_tax
    = (0.10·t1 + 0.12·t2 + 0.22·t3 + 0.24·t4)        ← federal income tax (piecewise)
    + 2 · 0.0765 · W                                  ← total FICA (employee + employer)
    + SE_tax                                          ← SE tax on SchedC (constant)

Simplified (drop SE_tax as it's a constant in LP):
  min  0.10·t1 + 0.12·t2 + 0.22·t3 + 0.24·t4 + 0.153·W
```

`SE_tax` doesn't influence the LP optimum (it's a parameter-derived constant), but the **displayed** tax breakdown includes it.

### 2.6 What's *not* in the LP (but conceptually present)

- **K-1 is owner-only**: LP models a single S-Corp owner-employee, so K1 attribution is unambiguous.
- **Box 1 = W − ED**: traditional 401(k) deferral reduces W-2 Box 1 but **not** SS/Medicare wages (FICA always on full W; §3401(a) vs §3121(a)).
- **SE tax doesn't affect ED/PS optimization** since SchedC is exogenous, but reduces AGI via `SE_ded` and contributes to total displayed tax.
- **SchedC SE rate simplification**: assumes `W + SE_base < $184,500`; above SS wage base, SE rate falls from 15.3% to 2.9% (Medicare only). Out of scope for v1.

---

## 3. UI Design

### 3.1 Input controls (left panel)

| Control | Type | Range / options | Default |
|---|---|---|---|
| S-Corp net profit `X` | Slider + number | 0–200,000 (step 1,000) | 100,000 |
| Other passive / W-2 income | Number | 0–500,000 | 0 |
| Schedule C net profit | Number | 0–500,000 | 0 |
| Filing status | Selector | MFJ / Single / HoH / QW | MFJ |
| Reasonable comp lower bound `W_min` | Number | 0–200,000 | 30,000 |
| ⚙️ Advanced toggle | Disclosure | — | collapsed |

**Disclaimer under `W_min` input:**
> IRS requires reasonable compensation for active S-Corp owner-employees performing services for the corporation. The default $30,000 is a generic placeholder — actual reasonable comp depends on your role, hours, industry, and geography. Setting `W_min = 0` is legal but creates IRS audit risk. See [IRS S Corporation Compensation guidance](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues).

**Disclaimer under header (top of page):**
> ⚠️ This tool minimizes **current-year federal tax burden**. 401(k) contributions are **tax-deferred, not tax-free** — they'll be taxed upon withdrawal at retirement-era marginal rates. Optimal allocation here ≠ lifetime tax minimum.

Advanced section (collapsed by default):
- Clean-paycheck constraint (toggle, default on; if off, allows `ED > 0.9235·W` with FICA shortfall covered from K1)
- Year override (default 2026; placeholder for when 2027+ limits are announced)
- Show LP solver diagnostics (toggle; shows YALPS solver output for debugging)

### 3.2 Output panels (right side)

**Panel A — Optimal allocation table:**

| Row | Amount |
|---|---:|
| W-2 gross wages | W |
| ↳ ED (pre-tax 401k) | ED |
| ↳ Box 1 (taxable) | W − ED |
| Employer profit-sharing → 401k | PS |
| Employer FICA paid by S-Corp | 0.0765·W |
| K-1 distribution to owner | K1 |
| **Sum (= X)** | **X** |

**Panel B — Tax breakdown:**

| Item | Amount |
|---|---:|
| AGI | (W − ED) + K1 + OtherIncome_passive + SchedC − SE_ded |
| Standard deduction | StdDed (by FilingStatus) |
| §199A QBI deduction | QBI |
| Taxable income | TI |
| Federal income tax | 10%·t1 + 12%·t2 + 22%·t3 + 24%·t4 |
| Employee FICA | 0.0765·W |
| Employer FICA (S-Corp cost) | 0.0765·W |
| SE tax (on SchedC) | SE_tax |
| **Total tax burden** | **(sum above)** |
| Effective tax rate (vs gross income) | Total / (X + OtherIncome_passive + SchedC) |
| Effective tax rate (vs taxable income) | Total / TI |

**Panel C — Retirement deferred:**

| Item | Amount |
|---|---:|
| Employee deferral (ED) | ED |
| Profit-sharing (PS) | PS |
| **Total tax-deferred (Solo 401k contributions)** | **ED + PS** |
| % of pre-comp profit | (ED + PS) / X |

Footer note under Panel C: "Tax-deferred ≠ tax-saved. Withdrawals are ordinary income at retirement-era marginal rates."

### 3.3 Sankey diagram

Sankey shows the flow of money from sources → sinks. Designed so every node satisfies **inflow = outflow**.

**Nodes:**

| ID | Label | Type | Value |
|---|---|---|---|
| `src_x` | S-Corp profit (X) | source | X |
| `src_ext_passive` | Other passive income | source | OtherIncome_passive |
| `src_schedc` | Schedule C net profit | source | SchedC |
| `mid_w` | W-2 gross wages (paid to owner) | flow-through | W |
| `mid_erfica` | Employer FICA pool | flow-through | 0.0765·W |
| `mid_ps` | Employer profit-sharing pool | flow-through | PS |
| `mid_k1` | K-1 distribution | flow-through | K1 |
| `sink_401k_ed` | 401(k) ED (pre-tax) | sink | ED |
| `sink_401k_ps` | 401(k) PS | sink | PS |
| `sink_box1` | Box 1 taxable income | flow-through | W − ED |
| `sink_fed_tax` | Federal income tax | sink | FedTax |
| `sink_emp_fica` | Employee FICA | sink | 0.0765·W |
| `sink_employer_fica` | Employer FICA (to IRS) | sink | 0.0765·W |
| `sink_se_tax` | SE tax (to IRS) | sink | SE_tax |
| `sink_takehome` | Take-home (post-tax cash) | sink | (residual) |

**Edges (every flow-through node balances):**

```
src_x              → mid_w              : W
src_x              → mid_erfica         : 0.0765·W
src_x              → mid_ps             : PS
src_x              → mid_k1             : K1
                     # src_x balance: W + 0.0765·W + PS + K1 = 1.0765·W + PS + K1 = X ✓

mid_erfica         → sink_employer_fica : 0.0765·W

mid_w              → sink_401k_ed       : ED
mid_w              → sink_box1          : W − ED              ✓ balance: W in = ED + (W−ED) out

mid_ps             → sink_401k_ps       : PS

sink_box1          → sink_emp_fica      : 0.0765·W
sink_box1          → sink_fed_tax       : (Box 1's share of fed tax via proportional allocation)
sink_box1          → sink_takehome      : W − ED − 0.0765·W − fed_tax_share

mid_k1              → sink_fed_tax       : (K1's share of fed tax)
mid_k1              → sink_takehome      : K1 − fed_tax_share

src_ext_passive    → sink_fed_tax       : (Passive's share of fed tax)
src_ext_passive    → sink_takehome      : Passive − fed_tax_share

src_schedc         → sink_se_tax        : SE_tax
src_schedc         → sink_fed_tax       : (SchedC's share of fed tax, on SchedC − SE_ded portion)
src_schedc         → sink_takehome      : SchedC − SE_tax − fed_tax_share
```

**Why `src_x` balances**: outflows sum to `W + 0.0765·W + PS + K1 = 1.0765·W + PS + K1 = X` (the budget constraint).

**Why `sink_box1` balances**: Inflow = `W − ED`. Outflow includes employee FICA `0.0765·W`. For balance, need `W − ED ≥ 0.0765·W`, i.e., `ED ≤ 0.9235·W` — exactly the clean-paycheck constraint. When clean-paycheck is off, take-home can go negative (covered from K1 elsewhere) — Sankey then shows an explicit "FICA shortfall from K1" edge.

**Note on fed tax allocation**: Federal tax is computed jointly across all income sources, so attributing it to individual streams is fundamentally ambiguous. We use **proportional allocation**: each source's contribution to TI is multiplied by the effective federal tax rate on TI. Visual aid only; not strictly "correct" (joint progressive tax cannot be split cleanly).

Colors:
- Sources: gray
- Retirement sinks: green (tax-deferred wealth)
- Tax sinks: red (cost)
- Take-home: blue (cash)

### 3.4 Layout

Single-page, two columns on desktop, stacked on mobile.

**Desktop (≥ 768px):**

```
┌─────────────────────────────────────────────────────────────┐
│  Solo 401(k) S-Corp Optimizer (2026)                        │
│  ⚠️ Current-year tax minimum, not lifetime minimum           │
├──────────────────┬──────────────────────────────────────────┤
│  Inputs          │  Sankey diagram                          │
│                  │  (full-width, ~400px tall)               │
│  X: ___________  │                                          │
│  Other Inc: ___  │                                          │
│  SchedC: ______  │                                          │
│  Filing: [MFJ▾]  │                                          │
│  W_min: _______  │                                          │
│  ⚙ Advanced      │                                          │
│                  ├──────────────────────────────────────────┤
│                  │  Outputs                                 │
│                  │  ┌─────────┬─────────┬─────────┐         │
│                  │  │ Alloc   │ Tax     │ Retire  │         │
│                  │  │ table   │ table   │ table   │         │
│                  │  └─────────┴─────────┴─────────┘         │
└──────────────────┴──────────────────────────────────────────┘
```

**Mobile (< 768px), stacked top-to-bottom in this order:**

1. Header (with current-year-tax-only disclaimer)
2. Inputs panel
3. Sankey diagram (full width, ~300px tall)
4. Tax breakdown (Panel B — most informative)
5. Allocation table (Panel A)
6. Retirement table (Panel C)

Style: minimalist, monospace numeric, semantic colors (green retirement, red tax, blue cash).

---

## 4. Architecture

### 4.1 Single HTML file

One `index.html` containing everything:

- HTML structure (~3 KB)
- Inline CSS (~4 KB)
- Inline minified YALPS solver (~10 KB)
- Inline minified d3-sankey + d3-array + d3-shape (~25 KB — trimmed to what's needed)
- App logic (~12 KB — handles SchedC + filing status + infeasibility branches)
- **Total estimate: ~55 KB single file**

Why single file:
- Zero build, zero install, zero server
- Double-click `index.html` → runs in browser via `file://`
- Avoids ES-module CORS issues on `file://` protocol
- Trivial to email / USB / fork

### 4.2 Internal module organization (within the file)

Use IIFE (immediately-invoked function expression) pattern to namespace each "module":

```javascript
const SolverModule = (function() {
  // YALPS library (inlined, IIFE-style; exposes global YALPS)
  return { solve: function(model) { return YALPS.solve(model); } };
})();

const TaxConstants = (function() {
  return {
    YEAR: 2026,
    ED_MAX: 24500,
    SEC415_CAP: 72000,
    COMP_CAP_401A17: 360000,
    PS_RATE: 0.25,
    FICA_RATE: 0.0765,
    SE_TAX_RATE: 0.153,
    SE_INCOME_FACTOR: 0.9235,
    SS_WAGE_BASE: 184500,
    QBI_RATE: 0.20,
    QBI_TI_THRESHOLD_MFJ: 403500,
    STD_DED: { MFJ: 32200, QW: 32200, HoH: 24150, Single: 16100 },
    BRACKETS: {
      MFJ: [
        { top: 24800,  rate: 0.10 },
        { top: 100800, rate: 0.12 },
        { top: 211400, rate: 0.22 },
        { top: 403550, rate: 0.24 },
      ],
      Single: [/* ... */],
      HoH:    [/* ... */],
      // QW uses MFJ
    },
  };
})();

const LPModel = (function() {
  function buildModel(inputs) { /* construct YALPS model object */ }
  function extractSolution(solverResult) { /* parse + derive AGI, FedTax, etc. */ }
  return { buildModel, extractSolution };
})();

const SankeyRenderer = (function() {
  function render(svgEl, nodes, links) { /* D3 sankey rendering */ }
  return { render };
})();

const App = (function() {
  function init() { /* wire inputs, run initial solve */ }
  function onInputChange() {
    const inputs = readInputs();
    const model = LPModel.buildModel(inputs);
    const result = SolverModule.solve(model);
    if (result.status !== 'optimal') {
      renderInfeasibility(result.status, inputs);  // see §5.1
      return;
    }
    const solution = LPModel.extractSolution(result);
    renderOutputs(solution);
    SankeyRenderer.render(svgEl, buildSankey(solution));
  }
  return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
```

### 4.3 Dependencies (all bundled, no runtime fetch)

- **YALPS v0.6.4** (https://github.com/IanManske/YALPS) — pure-TS LP solver
  - License: **MIT**
  - Build format: **IIFE** with global `YALPS` (ships `dist/index.min.js` at **9,910 bytes**)
  - Solver: primal simplex (Phase 1 + Phase 2); branch-and-cut only triggered if integer vars exist
  - API: `YALPS.solve(model)` returns `{ status, result, variables }`
  - Status values: `"optimal"`, `"infeasible"`, `"unbounded"`, `"cycled"`, `"timedout"` — UI must handle all non-optimal cases
  - Infeasible returns `{ status: "infeasible", result: NaN, variables: [] }` (no exception thrown)
  - Performance: ~0.011 ms/solve for our 10-variable / ~14-constraint LP (well under 50 ms target)

- **d3-sankey** (https://github.com/d3/d3-sankey) + minimal deps (`d3-array`, `d3-shape`, `d3-path`)
  - License: **ISC**
  - Inline trimmed bundle (~25 KB)

**Fallback solvers** (in case YALPS becomes unmaintained):

| Solver | JS size | Wasm size | License | Type |
|---|---:|---:|---|---|
| **YALPS v0.6.4 (chosen)** | 9.9 KB | — | MIT | Pure-JS simplex |
| javascript-lp-solver | 172 KB | — | Unlicense | Pure-JS simplex |
| glpk.js | 210 KB | 294 KB | GPL-3.0 | wasm GLPK |
| highs-js | 27 KB | 2.68 MB | MIT | wasm HiGHS |

YALPS is the chosen solver due to its tiny bundle, MIT license, and sufficient correctness + performance for this problem size. If correctness issues arise, escalate to `highs-js` (same MIT license, more robust solver, but ~280× larger bundle).

### 4.4 Why not ES modules

Browsers (Chrome especially) restrict ES module `import` from `file://` for security. Using classic `<script>` tags + IIFE namespacing avoids this entirely. Trade-off: no `import` syntax — fine for a single-file app.

---

## 5. Real-time Update Flow

```
User adjusts slider (e.g., X = 100k → 120k)
    ↓
'input' event fires
    ↓
App.onInputChange()
    ↓
readInputs()                          ~0.1 ms
    ↓
LPModel.buildModel(inputs)            ~0.5 ms (object construction)
    ↓
SolverModule.solve(model)             ~0.01–2 ms (YALPS simplex)
    ↓
[branch on result.status]:
    "optimal"     → continue ↓
    "infeasible"  → renderInfeasibility(reason); return
    "unbounded"   → renderError("LP unbounded — check inputs"); return
    "cycled"      → retry once with larger maxPivots; if still cycled, renderError
    "timedout"    → renderError("Solver timeout")
    ↓
LPModel.extractSolution(result)       ~0.1 ms
    ↓
renderOutputs(solution)               ~5–10 ms (DOM table updates)
    ↓
SankeyRenderer.render(svgEl, sankey)  ~10–20 ms (D3 SVG update with transition)
    ↓
[end] — total: ~20–35 ms per slider tick for the "optimal" path
```

Target: < 50 ms total per input change → comfortable real-time feel.

### 5.1 Infeasibility handling

The most common infeasibility cause: `W_min × 1.0765 > X` (reasonable comp floor exceeds the available pie). When YALPS returns `status="infeasible"`:

```
┌─────────────────────────────────────────┐
│ ⚠️  Allocation infeasible               │
│                                         │
│ Reason: W_min ($50,000) requires more   │
│   than available X ($30,000).           │
│   Minimum X needed = $53,825            │
│   (= W_min × 1.0765).                   │
│                                         │
│ Fix: lower W_min, raise X, or both.     │
└─────────────────────────────────────────┘
```

While infeasibility banner is shown:
- Sankey is hidden (or rendered grayed-out with last valid solution + "(stale)" label)
- Output tables show "—" for all numbers
- Input panel highlights `W_min` and `X` fields

---

## 6. Tax constants (2026) — verification complete ✅

| Constant | Value | Source | Verified |
|---|---:|---|---|
| ED limit §402(g)(1) | $24,500 | [IRS Notice 2025-67](https://www.irs.gov/pub/irs-drop/n-25-67.pdf) | ✅ |
| §415(c)(1)(A) dollar cap | $72,000 | [IRS Notice 2025-67](https://www.irs.gov/pub/irs-drop/n-25-67.pdf) | ✅ |
| §415(c)(1)(B) 100%-of-comp | (formula `ED + PS ≤ W`; no dollar value) | IRC §415(c)(1)(B), §415(c)(3)(D) | ✅ |
| §401(a)(17) W comp cap | $360,000 | [IRS Notice 2025-67](https://www.irs.gov/pub/irs-drop/n-25-67.pdf) | ✅ |
| Std deduction MFJ / QW | $32,200 | [Rev. Proc. 2025-32 / IR-2025-103](https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill) | ✅ |
| Std deduction Single | $16,100 | Rev. Proc. 2025-32 | ✅ |
| Std deduction HoH | $24,150 | Rev. Proc. 2025-32 | ✅ |
| MFJ bracket tops [10/12/22/24%] | [24,800; 100,800; 211,400; 403,550] | Rev. Proc. 2025-32 | ✅ |
| §199A QBI threshold MFJ | $403,500 (phase-in to $553,500) | Rev. Proc. 2025-32 | ✅ |
| SS wage base | $184,500 | [SSA 2025-10-24](https://www.ssa.gov/news/en/press/releases/2025-10-24.html) | ✅ |
| FICA rates | 7.65% (each side) | IRC §3101 / §3111 (statutory) | ✅ |
| SE tax rate | 15.3% | IRC §1401 (statutory) | ✅ |
| QBI deduction rate | 20% | §199A(a)(1) (statutory) | ✅ |

Single + HoH bracket lookup tables to be populated in `TaxConstants.BRACKETS` from Rev. Proc. 2025-32 before locking implementation.

---

## 7. Out of scope (consolidated; not bugs)

Repeated for emphasis. If user requests any of these, treat as v1.1+ extension (see §8), not a v1 patch.

- **FEIE Form 2555** — tool assumes 100% US-source earned income. Users with foreign-source W-2 should compute FEIE separately and subtract from `OtherIncome_passive`.
- **Catch-up contributions** — age 50+ §414(v), age 60-63 SECURE 2.0 §109.
- **State income tax** — assume 0%. Add manually for IL / CA / NY / etc.
- **NIIT 3.8%** — not modeled. S-Corp active K-1 is excluded per §1411(c)(2)(A); only triggers on net investment income above $250k MFJ.
- **Additional Medicare 0.9%** — not modeled. Only triggers on wages > $250k MFJ.
- **Two S-Corp owners in same household** — run tool twice.
- **HSA / §125 / SE health insurance / SE retirement adjustments to QBI** — not modeled.
- **Roth ED split** — ED treated as fully traditional pre-tax.
- **Multi-year planning** — single-year snapshot only.
- **SS wage base interaction**: tool assumes `W ≤ $184,500` and `W + 0.9235·SchedC ≤ $184,500`. For boundary cases (`X` near $200k slider top → `W` up to ~$185,800 in all-W solution), FICA may overestimate by ~$80 (≤ 0.062 × $1,300 excess). Acceptable error for v1. For accurate handling above wage base, see §8 item 6.

---

## 8. Future extensions

(Documented for plan continuity; not implemented in v1.)

1. **Age 50+ catch-up**: add `CATCHUP` variable, `CATCHUP ≤ CATCHUP_LIMIT`, `CATCHUP ≤ W − ED`. Catch-up doesn't count toward §415(c) cap per current IRS guidance. UI gains age input.

2. **State tax**: add user input for state marginal rate; multiply by TI in objective. Trivial (~5 lines).

3. **Multi-year**: solve LP for each year independently with year-specific constants; show stacked allocations over time. UI adds year selector.

4. **Roth split**: bifurcate ED into `ED_traditional` + `ED_roth`. Only traditional reduces AGI. Total `ED_t + ED_r ≤ ED_MAX`. Adds 1 var, 1 constraint. **Especially valuable for users in low brackets (e.g., 10–12%) who expect higher retirement brackets.**

5. **FEIE Form 2555 for foreign-source earned income**: add `FEIE` variable with `FEIE ≤ FEIE_CAP × (days_abroad / 365)` and `FEIE ≤ (days_abroad / 365) × (W − ED)`. Subtract from AGI. Adds 1 var + 2 constraints + `days_abroad` parameter.

6. **SS wage base cap**: piecewise-linearize FICA above $184,500 as Medicare-only (1.45%). Adds 2 vars (`W_below_base`, `W_above_base`) + 2 constraints. Necessary for X > ~$200k.

7. **Self-employed health insurance**: subtract from SchedC for QBI base + AGI. 1 parameter.

8. **Two-S-Corp household integrated mode**: add second S-Corp as additional decision-var block (~5 more vars + ~6 more constraints). Caveat: still per-individual §402(g) / §415(c) caps; LP must track per-person.

---

## 9. Testing strategy

Single-file app: companion `tests.html` (or `?test=1` URL param) runs unit tests in-browser.

**Test cases (ground truth to be regenerated with verified 2026 constants before locking):**

| # | Scenario | Expected behavior |
|---|---|---|
| 1 | X = 0, all other defaults | All decision vars = 0, total tax = 0 |
| 2 | X = 50k, MFJ, W_min = 0 | Verify against Python ground truth (TBD) |
| 3 | X = 100k, MFJ, W_min = 30k | Verify against Python ground truth (TBD) |
| 4 | X = 200k, MFJ, W_min = 0 | §415(c) cap saturates |
| 5 | X = 100k, W_min = 50k (binding) | Solution has W = 50k |
| 6 | OtherIncome_passive = 50k, X = 50k | Passive pushes joint into 22% bracket |
| 7 | §415(c) dollar binding (X large) | ED + PS = $72k |
| 8 | §415(c) comp binding (W small) | ED + PS = W (new constraint) |
| 9 | Clean-paycheck off, low W | ED = W (Box 1 = 0) |
| 10 | K1 large, AGI − StdDed small | QBI capped by TI cap, not by 20% of K1+SchedC |
| 11 | SchedC = 30k, no S-Corp (X = 0) | SE tax + SE_ded + QBI on SchedC all kick in |
| 12 | W_min = 80k, X = 30k | Solver returns `infeasible`; UI shows error |
| 13 | FilingStatus = Single, X = 100k | Std deduction = $16,100; brackets narrower → higher tax than MFJ |

Each test: run LP, assert solution variables within $1 tolerance of pre-computed ground truth.

**Ground truth generation**: a one-off Python script (`scripts/gen_test_ground_truth.py`) using `scipy.optimize.linprog` or `pulp` to independently solve each case → emit JSON consumed by `tests.html`.

---

## 10. References

### IRS sources
- [IRS Notice 2025-67](https://www.irs.gov/pub/irs-drop/n-25-67.pdf) — 2026 401(k) / §415(c) / §401(a)(17) limits
- [Rev. Proc. 2025-32](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf) / [IR-2025-103](https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill) — 2026 inflation adjustments (std deduction, brackets, §199A threshold)
- [SSA Press Release 2025-10-24](https://www.ssa.gov/news/en/press/releases/2025-10-24.html) — 2026 SS wage base $184,500
- IRC §402(g)(1) / §402(g)(3) — elective deferral limit + comp def
- IRC §415(c)(1)(A) — annual addition dollar limit
- IRC §415(c)(1)(B) — annual addition 100%-of-comp limit
- IRC §415(c)(3)(D) — §415 comp includes elective deferrals
- IRC §401(a)(17) — comp cap
- IRC §199A — QBI deduction
- IRC §3101, §3111, §1401 — FICA / SE tax rates
- IRC §1411(c)(2)(A) — NIIT active trade/business exclusion
- Reg §1.199A-3(b)(1)(vi) — 1/2 SE tax reduces QBI base
- IRS Publication 560 — Retirement Plans for Small Business
- IRS [S Corporation Compensation and Medical Insurance Issues](https://www.irs.gov/businesses/small-businesses-self-employed/s-corporation-compensation-and-medical-insurance-issues) — reasonable comp guidance

### Tools
- [YALPS](https://github.com/IanManske/YALPS) v0.6.4 — pure-JS LP solver (~10 KB IIFE, MIT)
- [d3-sankey](https://github.com/d3/d3-sankey) — Sankey diagram (ISC license)

---

## 11. Open questions (resolved during design + audit)

- ✅ Should the tool include a spouse-on-payroll toggle? **No.** Tool models single S-Corp owner. For 2-S-Corp households, run twice independently (§1.1).
- ✅ Should FEIE Form 2555 be in v1? **No.** Tool assumes 100% US-source earned income. Users with foreign-source income compute FEIE separately and adjust `OtherIncome_passive`. (§1.3, §8 item 5)
- ✅ Should Schedule C income be handled? **Yes.** Added as parameter with SE tax + QBI eligibility (§2.2, §2.3).
- ✅ Should the §415(c) 100%-of-comp constraint be added? **Yes** — `ED + PS ≤ W` (§2.4). Confirmed via IRC §415(c)(1)(B) + IRS S-Corp FAQ.
- ✅ Should filing status be configurable? **Yes** — selector affects std deduction + brackets (§2.2, §3.1).
- ✅ Should `W_min` default be 0? **No** — default $30,000 with IRS reasonable comp disclaimer (§3.1).
- ✅ Should the objective minimize lifetime tax? **No** — tool explicitly minimizes current-year tax; user-facing disclaimer warns about the difference (§1.1, §3.1).
- ✅ Should `OtherIncome` be a single bucket? **No** — split into `OtherIncome_passive` (non-QBI, FICA-paid) and `SchedC_NetProfit` (QBI-eligible, SE-taxed) (§2.2).
- ✅ Should ETR have one denominator or two? **Two** — vs gross income + vs taxable income (§3.2).
- ✅ WebAssembly solver needed? **No** — YALPS IIFE bundle sufficient (§4.3).
- ✅ Build pipeline? **No build** — single inline HTML (§4.1).
- ✅ Sankey balance for `mid_w`? **Reframe**: `src_x → mid_w_with_erfica` carries `1.0765·W`, then splits into `mid_w (W) + mid_erfica (0.0765·W)`. Every node balances (§3.3).
- ✅ Handle YALPS `infeasible` / `unbounded` returns? **Yes** — explicit UI branches in §5.1.

---

*Design v2 locked 2026-05-14 post-audit. Audit findings + decisions integrated. Implementation pending.*
