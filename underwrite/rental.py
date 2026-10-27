"""Rental property underwriting: a multi-year pro forma, debt, and a sale.

Conventions (the same ones used in most acquisition models):

* Net operating income (NOI) is income less operating expenses, before debt
  service and before capital reserves.
* Capital reserves are taken below NOI, so cap rates are not distorted.
* The sale price is the *following* year's NOI divided by the exit cap rate,
  because a buyer prices the income they will receive, not the income already
  received.
"""

from __future__ import annotations

from dataclasses import dataclass

from .finance import equity_multiple, irr_or_none, payment, remaining_balance


@dataclass(kw_only=True)
class RentalDeal:
    purchase_price: float
    monthly_rent: float
    property_tax_annual: float
    insurance_annual: float

    closing_costs: float = 0.0
    rehab: float = 0.0
    other_income_monthly: float = 0.0
    vacancy_rate: float = 0.05
    rent_growth: float = 0.03

    management_rate: float = 0.08  # share of effective gross income
    maintenance_rate: float = 0.05  # share of effective gross income
    capex_reserve_rate: float = 0.05  # share of effective gross income, below NOI
    other_expenses_annual: float = 0.0
    expense_growth: float = 0.03

    down_payment_rate: float = 0.25
    interest_rate: float = 0.07
    amortization_years: int = 30

    hold_years: int = 5
    exit_cap_rate: float = 0.065
    selling_cost_rate: float = 0.06

    def __post_init__(self) -> None:
        if self.purchase_price <= 0:
            raise ValueError("purchase_price must be positive")
        if not 0 < self.down_payment_rate <= 1:
            raise ValueError("down_payment_rate must be in (0, 1]")
        if self.hold_years < 1:
            raise ValueError("hold_years must be at least 1")
        if self.exit_cap_rate <= 0:
            raise ValueError("exit_cap_rate must be positive")


@dataclass(frozen=True)
class RentalYear:
    year: int
    gross_potential_income: float
    vacancy_loss: float
    effective_gross_income: float
    operating_expenses: float
    noi: float
    capex_reserve: float
    debt_service: float
    cash_flow: float
    dscr: float | None
    loan_balance: float


@dataclass(frozen=True)
class RentalResult:
    deal: RentalDeal
    loan_amount: float
    equity_invested: float
    annual_debt_service: float
    years: list[RentalYear]
    going_in_cap_rate: float
    cash_on_cash_year1: float
    dscr_year1: float | None
    break_even_occupancy: float
    rent_to_price: float
    sale_price: float
    selling_costs: float
    loan_payoff: float
    net_sale_proceeds: float
    cashflows: list[float]
    irr: float | None
    equity_multiple: float


def _operating_year(deal: RentalDeal, year: int) -> tuple[float, float, float, float, float]:
    """Income and expense lines for one year (year 1 = first year of ownership)."""
    rent_factor = (1 + deal.rent_growth) ** (year - 1)
    expense_factor = (1 + deal.expense_growth) ** (year - 1)

    gpi = 12 * (deal.monthly_rent + deal.other_income_monthly) * rent_factor
    vacancy = gpi * deal.vacancy_rate
    egi = gpi - vacancy

    fixed = (deal.property_tax_annual + deal.insurance_annual + deal.other_expenses_annual) * expense_factor
    variable = egi * (deal.management_rate + deal.maintenance_rate)
    opex = fixed + variable
    return gpi, vacancy, egi, opex, egi - opex


def underwrite_rental(deal: RentalDeal) -> RentalResult:
    loan = deal.purchase_price * (1 - deal.down_payment_rate)
    equity = deal.purchase_price - loan + deal.closing_costs + deal.rehab
    monthly_pmt = payment(loan, deal.interest_rate, deal.amortization_years) if loan > 0 else 0.0
    debt_service = 12 * monthly_pmt

    years = []
    for y in range(1, deal.hold_years + 1):
        gpi, vacancy, egi, opex, noi = _operating_year(deal, y)
        reserve = egi * deal.capex_reserve_rate
        balance = (
            remaining_balance(loan, deal.interest_rate, deal.amortization_years, 12 * y) if loan > 0 else 0.0
        )
        years.append(
            RentalYear(
                year=y,
                gross_potential_income=gpi,
                vacancy_loss=vacancy,
                effective_gross_income=egi,
                operating_expenses=opex,
                noi=noi,
                capex_reserve=reserve,
                debt_service=debt_service,
                cash_flow=noi - reserve - debt_service,
                dscr=noi / debt_service if debt_service else None,
                loan_balance=balance,
            )
        )

    forward_noi = _operating_year(deal, deal.hold_years + 1)[4]
    sale_price = forward_noi / deal.exit_cap_rate
    selling_costs = sale_price * deal.selling_cost_rate
    payoff = years[-1].loan_balance
    net_proceeds = sale_price - selling_costs - payoff

    cashflows = [-equity] + [yr.cash_flow for yr in years]
    cashflows[-1] += net_proceeds

    y1 = years[0]
    return RentalResult(
        deal=deal,
        loan_amount=loan,
        equity_invested=equity,
        annual_debt_service=debt_service,
        years=years,
        going_in_cap_rate=y1.noi / deal.purchase_price,
        cash_on_cash_year1=y1.cash_flow / equity,
        dscr_year1=y1.dscr,
        break_even_occupancy=(y1.operating_expenses + y1.capex_reserve + debt_service) / y1.gross_potential_income,
        rent_to_price=deal.monthly_rent / deal.purchase_price,
        sale_price=sale_price,
        selling_costs=selling_costs,
        loan_payoff=payoff,
        net_sale_proceeds=net_proceeds,
        cashflows=cashflows,
        irr=irr_or_none(cashflows),
        equity_multiple=equity_multiple(cashflows),
    )
