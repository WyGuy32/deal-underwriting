import unittest
from dataclasses import replace

from underwrite.lbo import LBODeal, run_lbo
from underwrite.sensitivity import around, sensitivity

BASE = LBODeal(
    ltm_revenue=100_000_000,
    ebitda_margin=0.20,
    entry_multiple=8.0,
    exit_multiple=8.0,
    revenue_growth=0.05,
)


class LBOTests(unittest.TestCase):
    def test_sources_and_uses(self):
        r = run_lbo(BASE)
        self.assertAlmostEqual(r.entry_ebitda, 20_000_000)
        self.assertAlmostEqual(r.entry_ev, 160_000_000)
        self.assertAlmostEqual(r.entry_debt, 100_000_000)
        self.assertAlmostEqual(r.sponsor_equity + r.entry_debt, r.entry_ev + r.fees)

    def test_bridge_sums_to_equity_gain(self):
        for deal in (BASE, replace(BASE, exit_multiple=9.5, margin_change_per_year=0.01), replace(BASE, revenue_growth=-0.03)):
            r = run_lbo(deal)
            self.assertAlmostEqual(r.bridge.total, r.exit_equity - r.sponsor_equity, places=2)

    def test_all_equity_no_growth(self):
        # No debt, growth, fees, taxes or reinvestment: equity grows only by
        # the cash the business throws off, i.e. EBITDA each year.
        deal = replace(
            BASE,
            revenue_growth=0.0,
            senior_debt_multiple=0.0,
            sub_debt_multiple=0.0,
            transaction_fee_rate=0.0,
            da_pct_revenue=0.0,
            capex_pct_revenue=0.0,
            tax_rate=0.0,
        )
        r = run_lbo(deal)
        self.assertAlmostEqual(r.moic, 1 + 5 * 20_000_000 / 160_000_000)

    def test_debt_never_goes_negative(self):
        r = run_lbo(replace(BASE, revenue_growth=0.15, hold_years=10))
        for year in r.years:
            self.assertGreaterEqual(year.senior_balance, 0.0)
        self.assertGreater(r.years[-1].cash, 0.0)

    def test_multiple_expansion_raises_returns(self):
        flat = run_lbo(BASE)
        expanded = run_lbo(replace(BASE, exit_multiple=9.0))
        self.assertGreater(expanded.irr, flat.irr)
        self.assertGreater(expanded.bridge.multiple_expansion, 0)

    def test_overlevered_deal_rejected(self):
        with self.assertRaises(ValueError):
            run_lbo(replace(BASE, senior_debt_multiple=8.0, sub_debt_multiple=1.0))

    def test_sensitivity_grid(self):
        t = sensitivity(BASE, run_lbo, lambda r: r.irr, "entry_multiple", around(8.0, 0.5), "exit_multiple", around(8.0, 0.5))
        self.assertEqual(len(t.cells), 5)
        self.assertEqual(len(t.cells[0]), 5)
        # Paying less (top rows) and selling for more (right columns) both help.
        self.assertGreater(t.cells[0][2], t.cells[4][2])
        self.assertGreater(t.cells[2][4], t.cells[2][0])
        self.assertAlmostEqual(t.cells[2][2], run_lbo(BASE).irr)


if __name__ == "__main__":
    unittest.main()
