"""A compact leveraged buyout (LBO) model with a value-creation bridge.

Mechanics:

* The sponsor buys the company at `entry_multiple` x LTM EBITDA, funds part of
  the price with senior and subordinated debt, and pays transaction fees.
* Each year, free cash flow first covers mandatory senior amortization, then
  is swept against the remaining senior balance. Once senior debt is repaid,
  cash builds on the balance sheet. A shortfall shows up as negative cash (a
  revolver draw).
* Interest is charged on beginning-of-year balances, which keeps the model
  free of circular references (the usual simplification in a paper LBO).
* At exit the company is sold at `exit_multiple` x final-year EBITDA, net debt
  is repaid, and the rest goes to the sponsor.

The bridge splits the sponsor's gain into EBITDA growth, multiple expansion,
debt paydown, and fees. The four parts sum exactly to the equity gain, which
the test suite checks.
"""

from __future__ import annotations

from dataclasses import dataclass

from .finance import irr_or_none


@dataclass(kw_only=True)
class LBODeal:
    ltm_revenue: float
    ebitda_margin: float
    entry_multiple: float
    exit_multiple: float
    revenue_growth: float = 0.05
    margin_change_per_year: float = 0.0

    senior_debt_multiple: float = 4.0  # x entry EBITDA
    senior_rate: float = 0.085
    senior_amortization: float = 0.01  # mandatory, share of original senior per year
    sub_debt_multiple: float = 1.0  # x entry EBITDA, bullet at exit
    sub_rate: float = 0.115

    transaction_fee_rate: float = 0.02  # share of enterprise value
    da_pct_revenue: float = 0.03
    capex_pct_revenue: float = 0.035
    nwc_pct_revenue: float = 0.10
    tax_rate: float = 0.25
    hold_years: int = 5

    def __post_init__(self) -> None:
        if self.ltm_revenue <= 0 or self.ebitda_margin <= 0:
            raise ValueError("revenue and EBITDA margin must be positive")
        if self.hold_years < 1:
            raise ValueError("hold_years must be at least 1")


@dataclass(frozen=True)
class LBOYear:
    year: int
    revenue: float
    ebitda: float
    interest: float
    taxes: float
    net_income: float
    free_cash_flow: float
    senior_paydown: float
    senior_balance: float
    sub_balance: float
    cash: float
    leverage: float  # net debt / EBITDA


@dataclass(frozen=True)
class Bridge:
    ebitda_growth: float
    multiple_expansion: float
    debt_paydown: float
    fees: float

    @property
    def total(self) -> float:
        return self.ebitda_growth + self.multiple_expansion + self.debt_paydown + self.fees


@dataclass(frozen=True)
class LBOResult:
    deal: LBODeal
    entry_ebitda: float
    entry_ev: float
    fees: float
    entry_debt: float
    sponsor_equity: float
    years: list[LBOYear]
    exit_ebitda: float
    exit_ev: float
    exit_net_debt: float
    exit_equity: float
    moic: float
    irr: float | None
    bridge: Bridge


def run_lbo(deal: LBODeal) -> LBOResult:
    entry_ebitda = deal.ltm_revenue * deal.ebitda_margin
    entry_ev = deal.entry_multiple * entry_ebitda
    fees = entry_ev * deal.transaction_fee_rate
    senior0 = deal.senior_debt_multiple * entry_ebitda
    sub0 = deal.sub_debt_multiple * entry_ebitda
    equity = entry_ev + fees - senior0 - sub0
    if equity <= 0:
        raise ValueError("debt exceeds the purchase price; sponsor equity must be positive")

    senior, sub, cash = senior0, sub0, 0.0
    revenue, margin = deal.ltm_revenue, deal.ebitda_margin
    years = []
    for y in range(1, deal.hold_years + 1):
        prior_revenue = revenue
        revenue *= 1 + deal.revenue_growth
        margin += deal.margin_change_per_year
        ebitda = revenue * margin

        interest = senior * deal.senior_rate + sub * deal.sub_rate
        ebit = ebitda - revenue * deal.da_pct_revenue
        pretax = ebit - interest
        taxes = max(pretax, 0.0) * deal.tax_rate
        net_income = pretax - taxes
        fcf = (
            net_income
            + revenue * deal.da_pct_revenue
            - revenue * deal.capex_pct_revenue
            - (revenue - prior_revenue) * deal.nwc_pct_revenue
        )

        mandatory = min(senior, senior0 * deal.senior_amortization)
        sweep = min(senior - mandatory, max(fcf - mandatory, 0.0))
        paydown = mandatory + sweep
        senior -= paydown
        cash += fcf - paydown

        years.append(
            LBOYear(
                year=y,
                revenue=revenue,
                ebitda=ebitda,
                interest=interest,
                taxes=taxes,
                net_income=net_income,
                free_cash_flow=fcf,
                senior_paydown=paydown,
                senior_balance=senior,
                sub_balance=sub,
                cash=cash,
                leverage=(senior + sub - cash) / ebitda,
            )
        )

    exit_ebitda = years[-1].ebitda
    exit_ev = deal.exit_multiple * exit_ebitda
    exit_net_debt = senior + sub - cash
    exit_equity = exit_ev - exit_net_debt

    bridge = Bridge(
        ebitda_growth=(exit_ebitda - entry_ebitda) * deal.entry_multiple,
        multiple_expansion=(deal.exit_multiple - deal.entry_multiple) * exit_ebitda,
        debt_paydown=(senior0 + sub0) - exit_net_debt,
        fees=-fees,
    )

    cashflows = [-equity] + [0.0] * (deal.hold_years - 1) + [exit_equity]
    return LBOResult(
        deal=deal,
        entry_ebitda=entry_ebitda,
        entry_ev=entry_ev,
        fees=fees,
        entry_debt=senior0 + sub0,
        sponsor_equity=equity,
        years=years,
        exit_ebitda=exit_ebitda,
        exit_ev=exit_ev,
        exit_net_debt=exit_net_debt,
        exit_equity=exit_equity,
        moic=exit_equity / equity,
        irr=irr_or_none(cashflows),
        bridge=bridge,
    )
