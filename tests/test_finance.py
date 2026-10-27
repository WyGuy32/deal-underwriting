import unittest

from underwrite.finance import amortization_schedule, equity_multiple, irr, irr_or_none, npv, payment, remaining_balance


class PaymentTests(unittest.TestCase):
    def test_textbook_mortgage(self):
        # $300k, 6%, 30 years: the standard textbook answer is $1,798.65/month.
        self.assertAlmostEqual(payment(300_000, 0.06, 30), 1798.65, places=2)

    def test_zero_rate_is_straight_line(self):
        self.assertAlmostEqual(payment(120_000, 0.0, 10), 1000.0)

    def test_balance_matches_schedule(self):
        schedule = amortization_schedule(250_000, 0.07, 30)
        for k in (1, 12, 60, 180, 359):
            self.assertAlmostEqual(remaining_balance(250_000, 0.07, 30, k), schedule[k - 1].balance, places=4)

    def test_schedule_repays_exactly(self):
        schedule = amortization_schedule(250_000, 0.07, 30)
        self.assertEqual(len(schedule), 360)
        self.assertAlmostEqual(sum(r.principal for r in schedule), 250_000, places=4)
        self.assertAlmostEqual(schedule[-1].balance, 0.0, places=4)
        self.assertAlmostEqual(remaining_balance(250_000, 0.07, 30, 360), 0.0, places=4)


class IRRTests(unittest.TestCase):
    def test_one_period(self):
        self.assertAlmostEqual(irr([-100, 110]), 0.10, places=8)

    def test_spreadsheet_documentation_example(self):
        # The cash flows used in common spreadsheet IRR documentation: 8.66%.
        self.assertAlmostEqual(irr([-70_000, 12_000, 15_000, 18_000, 21_000, 26_000]), 0.086631, places=6)

    def test_npv_is_zero_at_irr(self):
        flows = [-1_000, 250, 300, 350, 400, 150]
        self.assertAlmostEqual(npv(irr(flows), flows), 0.0, places=6)

    def test_negative_irr_matches_closed_form(self):
        # -100 + 50x + 40x^2 = 0 with x = 1/(1+r): solve the quadratic exactly.
        x = (-50 + (50**2 + 4 * 40 * 100) ** 0.5) / (2 * 40)
        self.assertAlmostEqual(irr([-100, 50, 40]), 1 / x - 1, places=8)

    def test_no_sign_change(self):
        with self.assertRaises(ValueError):
            irr([-100, -50])
        self.assertIsNone(irr_or_none([100, 50]))

    def test_npv_by_hand(self):
        self.assertAlmostEqual(npv(0.10, [-100, 60, 60]), -100 + 60 / 1.1 + 60 / 1.21, places=10)

    def test_equity_multiple(self):
        self.assertAlmostEqual(equity_multiple([-100, 10, 10, 130]), 1.5)


if __name__ == "__main__":
    unittest.main()
