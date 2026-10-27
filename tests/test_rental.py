import unittest
from dataclasses import replace

from underwrite.rental import RentalDeal, underwrite_rental


def flat_all_cash(**overrides) -> RentalDeal:
    """No growth, no debt, no frictions: the simplest deal there is."""
    base = dict(
        purchase_price=200_000,
        monthly_rent=1_500,
        property_tax_annual=2_400,
        insurance_annual=1_200,
        vacancy_rate=0.0,
        rent_growth=0.0,
        management_rate=0.0,
        maintenance_rate=0.0,
        capex_reserve_rate=0.0,
        expense_growth=0.0,
        down_payment_rate=1.0,
        hold_years=5,
        exit_cap_rate=0.072,
        selling_cost_rate=0.0,
    )
    base.update(overrides)
    return RentalDeal(**base)


class RentalTests(unittest.TestCase):
    def test_noi_and_cap_rate_by_hand(self):
        r = underwrite_rental(flat_all_cash())
        # 18,000 rent - 3,600 fixed costs = 14,400 NOI on 200,000 = 7.2%.
        self.assertAlmostEqual(r.years[0].noi, 14_400)
        self.assertAlmostEqual(r.going_in_cap_rate, 0.072)

    def test_all_cash_flat_deal_irr_equals_cap_rate(self):
        # Buy and sell at the same cap rate with no growth, debt or costs:
        # the investor earns exactly the cap rate every year.
        r = underwrite_rental(flat_all_cash())
        self.assertAlmostEqual(r.sale_price, 200_000)
        self.assertAlmostEqual(r.irr, 0.072, places=8)

    def test_sale_uses_forward_noi(self):
        r = underwrite_rental(flat_all_cash(rent_growth=0.03, exit_cap_rate=0.07))
        year6_gpi = 18_000 * 1.03**5
        self.assertAlmostEqual(r.sale_price, (year6_gpi - 3_600) / 0.07, places=4)

    def test_leverage_and_dscr(self):
        deal = flat_all_cash(down_payment_rate=0.25, interest_rate=0.07)
        r = underwrite_rental(deal)
        self.assertAlmostEqual(r.loan_amount, 150_000)
        self.assertAlmostEqual(r.equity_invested, 50_000)
        self.assertAlmostEqual(r.dscr_year1, r.years[0].noi / r.annual_debt_service)
        self.assertLess(r.years[-1].loan_balance, 150_000)

    def test_positive_leverage_raises_irr(self):
        # Borrowing at 5% to buy a 7.2% yield should lift equity returns.
        unlevered = underwrite_rental(flat_all_cash())
        levered = underwrite_rental(flat_all_cash(down_payment_rate=0.3, interest_rate=0.05))
        self.assertGreater(levered.irr, unlevered.irr)

    def test_costs_lower_returns(self):
        base = flat_all_cash(down_payment_rate=0.25)
        cheap = underwrite_rental(base)
        costly = underwrite_rental(replace(base, closing_costs=8_000, selling_cost_rate=0.06))
        self.assertLess(costly.irr, cheap.irr)
        self.assertAlmostEqual(costly.equity_invested - cheap.equity_invested, 8_000)

    def test_reserves_sit_below_noi(self):
        with_reserve = underwrite_rental(flat_all_cash(capex_reserve_rate=0.05))
        without = underwrite_rental(flat_all_cash())
        self.assertAlmostEqual(with_reserve.years[0].noi, without.years[0].noi)
        self.assertAlmostEqual(without.years[0].cash_flow - with_reserve.years[0].cash_flow, 900)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            flat_all_cash(purchase_price=0)
        with self.assertRaises(ValueError):
            flat_all_cash(down_payment_rate=0)


if __name__ == "__main__":
    unittest.main()
