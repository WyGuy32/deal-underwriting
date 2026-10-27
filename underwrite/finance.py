"""Time-value-of-money primitives: loan payments, amortization, NPV and IRR.

Everything here is plain Python with no dependencies, so the same math can be
checked by hand (or in a spreadsheet) line by line.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


def payment(principal: float, annual_rate: float, years: int, periods_per_year: int = 12) -> float:
    """Level payment that fully amortizes `principal` (the spreadsheet PMT function)."""
    n = years * periods_per_year
    if n <= 0:
        raise ValueError("loan term must be positive")
    r = annual_rate / periods_per_year
    if r == 0:
        return principal / n
    return principal * r / (1 - (1 + r) ** -n)


def remaining_balance(
    principal: float, annual_rate: float, years: int, periods_elapsed: int, periods_per_year: int = 12
) -> float:
    """Loan balance after `periods_elapsed` payments, in closed form."""
    n = years * periods_per_year
    k = min(max(periods_elapsed, 0), n)
    r = annual_rate / periods_per_year
    if r == 0:
        return principal * (1 - k / n)
    pmt = payment(principal, annual_rate, years, periods_per_year)
    growth = (1 + r) ** k
    return max(principal * growth - pmt * (growth - 1) / r, 0.0)


@dataclass(frozen=True)
class AmortizationRow:
    period: int
    payment: float
    interest: float
    principal: float
    balance: float


def amortization_schedule(
    principal: float, annual_rate: float, years: int, periods_per_year: int = 12
) -> list[AmortizationRow]:
    """Period-by-period split of each payment into interest and principal."""
    pmt = payment(principal, annual_rate, years, periods_per_year)
    r = annual_rate / periods_per_year
    balance = principal
    rows = []
    for period in range(1, years * periods_per_year + 1):
        interest = balance * r
        principal_paid = min(pmt - interest, balance)
        balance -= principal_paid
        rows.append(AmortizationRow(period, interest + principal_paid, interest, principal_paid, max(balance, 0.0)))
    return rows


def npv(rate: float, cashflows: Sequence[float]) -> float:
    """Net present value, with the first cash flow at t=0 (undiscounted)."""
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))


def irr(cashflows: Sequence[float], tol: float = 1e-10, max_iter: int = 500) -> float:
    """Internal rate of return by bisection.

    Bisection is slower than Newton's method but it cannot diverge, which
    matters when a calculator is fed odd inputs. Raises ValueError when the
    cash flows never change sign (no IRR exists).
    """
    if not any(cf < 0 for cf in cashflows) or not any(cf > 0 for cf in cashflows):
        raise ValueError("IRR needs at least one negative and one positive cash flow")

    lo, hi = -0.9999, 1.0
    f_lo = npv(lo, cashflows)
    f_hi = npv(hi, cashflows)
    while f_lo * f_hi > 0 and hi < 1e6:
        hi *= 2
        f_hi = npv(hi, cashflows)
    if f_lo * f_hi > 0:
        raise ValueError("could not bracket an IRR for these cash flows")

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = npv(mid, cashflows)
        if abs(f_mid) < tol or (hi - lo) / 2 < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def irr_or_none(cashflows: Sequence[float]) -> float | None:
    """IRR, or None when the deal never returns capital (or never needs any)."""
    try:
        return irr(cashflows)
    except ValueError:
        return None


def equity_multiple(cashflows: Sequence[float]) -> float:
    """Total cash returned divided by total cash invested (MOIC)."""
    invested = -sum(cf for cf in cashflows if cf < 0)
    returned = sum(cf for cf in cashflows if cf > 0)
    if invested == 0:
        raise ValueError("no invested capital in cash flows")
    return returned / invested
