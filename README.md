# Deal Underwriting

[![tests](https://github.com/WyGuy32/deal-underwriting/actions/workflows/tests.yml/badge.svg)](https://github.com/WyGuy32/deal-underwriting/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

Underwriting models for **rental real estate** and **leveraged buyouts**, written in plain Python with no dependencies, plus a browser calculator that runs the same math.

**[Try the live calculator →](https://wyguy32.github.io/deal-underwriting/)**

It answers the questions an acquisitions analyst asks of a deal:

- **Rental property:** What does it yield on day one (cap rate, cash-on-cash, DSCR)? What occupancy does it need to break even? What's the levered IRR after a sale, and how much does that depend on the price I pay and the cap rate I sell at?
- **Leveraged buyout:** How fast does free cash flow pay down the debt? What's the sponsor's MOIC and IRR? How much of the gain comes from growing EBITDA, how much from multiple expansion, and how much from paying down debt?

## Quick start

```bash
git clone https://github.com/WyGuy32/deal-underwriting.git
cd deal-underwriting
python -m underwrite rental examples/duplex.json --sensitivity
python -m underwrite lbo examples/lbo_industrial.json --sensitivity
```

<details>
<summary>Example output: LBO</summary>

```
LEVERAGED BUYOUT

  Entry EBITDA    $21,600,000
  Entry EV        $194,400,000 (9.0x)
  Debt raised     $108,000,000 (5.0x EBITDA)
  Fees            $3,888,000
  Sponsor equity  $90,288,000

Year       Revenue       EBITDA    Interest          FCF  Senior debt  Cash  Net lev.
----  ------------  -----------  ----------  -----------  -----------  ----  --------
1     $127,200,000  $23,532,000  $9,828,000   $6,060,000  $80,340,000    $0     4.33x
2     $134,832,000  $25,618,080  $9,312,900   $7,757,805  $72,582,195    $0     3.68x
3     $142,921,920  $27,869,774  $8,653,487   $9,672,871  $62,909,324    $0     3.03x
4     $151,497,235  $30,299,447  $7,831,293  $11,827,410  $51,081,914    $0     2.40x
5     $160,587,069  $32,920,349  $6,825,963  $14,245,662  $36,836,251    $0     1.78x

EXIT (year 5, 9.0x EBITDA)
  Exit EV          $296,283,143
  Net debt repaid  -$58,436,251
  Exit equity      $237,846,891
  MOIC             2.63x
  IRR              21.4%

VALUE CREATION BRIDGE
Driver                     Value   Share
------------------  ------------  ------
EBITDA growth       $101,883,143   69.0%
Multiple expansion            $0    0.0%
Debt paydown         $49,563,749   33.6%
Fees                 -$3,888,000   -2.6%
Equity gain         $147,558,891  100.0%

SPONSOR IRR: entry vs. exit multiple
entry_multiple \ exit_multiple  8.00x  8.50x  9.00x  9.50x  10.00x
------------------------------  -----  -----  -----  -----  ------
8.00x                           24.6%  26.5%  28.4%  30.1%   31.7%
8.50x                           20.9%  22.8%  24.6%  26.3%   27.8%
9.00x                           17.8%  19.6%  21.4%  23.0%   24.6%
9.50x                           15.1%  16.9%  18.6%  20.2%   21.7%
10.00x                          12.8%  14.5%  16.2%  17.8%   19.2%
```
</details>

<details>
<summary>Example output: rental sensitivity</summary>

```
LEVERED IRR: purchase price vs. exit cap
purchase_price \ exit_cap_rate  6.75%  7.00%  7.25%  7.50%  7.75%
------------------------------  -----  -----  -----  -----  -----
$283,000                        16.8%  15.1%  13.5%  11.8%  10.2%
$299,000                        13.5%  11.7%   9.9%   8.1%   6.3%
$315,000                        10.1%   8.2%   6.3%   4.4%   2.4%
$331,000                         6.8%   4.7%   2.6%   0.5%  -1.7%
$347,000                         3.3%   1.1%  -1.2%  -3.5%  -6.0%
```

At the asking price this duplex earns only 6.3%. Negotiating $16k off lifts that to 9.9%, and $32k off more than doubles it. A sensitivity table is built to show exactly this.
</details>

## Use it as a library

```python
from underwrite import RentalDeal, underwrite_rental, sensitivity, around

deal = RentalDeal(
    purchase_price=315_000, monthly_rent=3_000,
    property_tax_annual=5_200, insurance_annual=1_900,
    interest_rate=0.0675, exit_cap_rate=0.0725,
)
result = underwrite_rental(deal)
print(f"IRR {result.irr:.1%}, DSCR {result.dscr_year1:.2f}x")

grid = sensitivity(deal, underwrite_rental, lambda r: r.irr,
                   "purchase_price", around(315_000, 15_000),
                   "interest_rate", around(0.0675, 0.005))
```

Every model is a pure function from a dataclass of inputs to a dataclass of results, so `sensitivity` can flex any two inputs of any model. Add `--json` on the command line to get the full result as JSON.

## Modeling conventions

These follow standard acquisition-model practice. Each one is stated so the numbers can be checked:

| | Convention |
|---|---|
| NOI | Effective gross income minus operating expenses. Management and maintenance scale with income; taxes and insurance grow with inflation. |
| Reserves | Capital reserves are taken **below** NOI, so they reduce cash flow without distorting the cap rate. |
| Sale price | **Forward** (year N+1) NOI divided by the exit cap rate, because a buyer pays for the income they will receive. |
| Debt | Fully amortizing monthly mortgage. Balances use the closed-form formula and are cross-checked against a full amortization schedule in tests. |
| LBO interest | Charged on beginning-of-year balances, which avoids a circular reference. Free cash flow pays mandatory amortization, then a 100% sweep on senior debt. Subordinated debt is a bullet repaid at exit. |
| Value bridge | EBITDA growth × entry multiple, plus multiple change × exit EBITDA, plus net debt paydown, minus fees. The four parts sum **exactly** to the equity gain (tested). |
| IRR | Bisection rather than Newton's method: slower, but it can't diverge on unusual cash flows. Returns `None` when no IRR exists. |

## Tests

```bash
python -m unittest discover -s tests -t .
```

The suite checks results against known answers, not just "it runs":

- A $300k, 6%, 30-year mortgage pays **$1,798.65**, the textbook figure.
- IRR matches the spreadsheet documentation example (**8.66%**) and the exact solution of a quadratic.
- An all-cash rental bought and sold at the same cap rate with no growth earns **exactly its cap rate**.
- An all-equity, no-growth LBO returns exactly `1 + years × EBITDA / EV`.
- The value-creation bridge sums to the equity gain across growth, decline and multiple-expansion cases.
- Positive leverage raises IRR, costs lower it, and debt never goes negative.

CI runs the suite on Python 3.10 to 3.13 on every push.

## Project layout

```
underwrite/
  finance.py      PMT, amortization, NPV, IRR, equity multiple
  rental.py       rental pro forma, debt, sale, returns
  lbo.py          LBO operating model, debt schedule, value bridge
  sensitivity.py  two-way tables over any model input
  report.py       terminal formatting
  __main__.py     command line
docs/index.html   browser calculator (GitHub Pages), same formulas in JavaScript
examples/         sample deals as JSON
tests/            unittest suite
```

## Disclaimer

The example deals are illustrative. This is a modeling tool, not investment advice.

## License

MIT
