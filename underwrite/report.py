"""Plain-text reports for the terminal."""

from __future__ import annotations

from typing import Sequence

from .lbo import LBOResult
from .rental import RentalResult
from .sensitivity import SensitivityTable


def money(x: float) -> str:
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def pct(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{x * 100:.{digits}f}%"


def multiple(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.2f}x"


def table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    first = lambda i: str.ljust if i == 0 else str.rjust  # noqa: E731
    lines = ["  ".join(first(i)(h, widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * w for w in widths))
    for r in rows:
        lines.append("  ".join(first(i)(c, widths[i]) for i, c in enumerate(r)))
    return "\n".join(lines)


def kv(pairs: Sequence[tuple[str, str]]) -> str:
    width = max(len(k) for k, _ in pairs)
    return "\n".join(f"  {k.ljust(width)}  {v}" for k, v in pairs)


def render_rental(r: RentalResult) -> str:
    d = r.deal
    out = [
        "RENTAL UNDERWRITING",
        "",
        kv(
            [
                ("Purchase price", money(d.purchase_price)),
                ("Loan", f"{money(r.loan_amount)} at {pct(d.interest_rate, 2)}, {d.amortization_years}-yr amortization"),
                ("Equity invested", money(r.equity_invested)),
                ("Going-in cap rate", pct(r.going_in_cap_rate, 2)),
                ("Year-1 cash-on-cash", pct(r.cash_on_cash_year1)),
                ("Year-1 DSCR", multiple(r.dscr_year1)),
                ("Break-even occupancy", pct(r.break_even_occupancy)),
                ("Rent / price (monthly)", pct(r.rent_to_price, 2)),
            ]
        ),
        "",
        table(
            ["Year", "EGI", "OpEx", "NOI", "Reserves", "Debt svc", "Cash flow", "DSCR"],
            [
                [
                    str(y.year),
                    money(y.effective_gross_income),
                    money(y.operating_expenses),
                    money(y.noi),
                    money(y.capex_reserve),
                    money(y.debt_service),
                    money(y.cash_flow),
                    multiple(y.dscr),
                ]
                for y in r.years
            ],
        ),
        "",
        f"EXIT (year {d.hold_years}, {pct(d.exit_cap_rate, 2)} cap on forward NOI)",
        kv(
            [
                ("Sale price", money(r.sale_price)),
                ("Selling costs", money(-r.selling_costs)),
                ("Loan payoff", money(-r.loan_payoff)),
                ("Net proceeds", money(r.net_sale_proceeds)),
            ]
        ),
        "",
        "RETURNS",
        kv([("Levered IRR", pct(r.irr)), ("Equity multiple", multiple(r.equity_multiple))]),
    ]
    return "\n".join(out)


def render_lbo(r: LBOResult) -> str:
    d = r.deal
    b = r.bridge
    gain = r.exit_equity - r.sponsor_equity
    share = lambda x: pct(x / gain) if gain else "n/a"  # noqa: E731
    out = [
        "LEVERAGED BUYOUT",
        "",
        kv(
            [
                ("Entry EBITDA", money(r.entry_ebitda)),
                ("Entry EV", f"{money(r.entry_ev)} ({d.entry_multiple:.1f}x)"),
                ("Debt raised", f"{money(r.entry_debt)} ({r.entry_debt / r.entry_ebitda:.1f}x EBITDA)"),
                ("Fees", money(r.fees)),
                ("Sponsor equity", money(r.sponsor_equity)),
            ]
        ),
        "",
        table(
            ["Year", "Revenue", "EBITDA", "Interest", "FCF", "Senior debt", "Cash", "Net lev."],
            [
                [
                    str(y.year),
                    money(y.revenue),
                    money(y.ebitda),
                    money(y.interest),
                    money(y.free_cash_flow),
                    money(y.senior_balance),
                    money(y.cash),
                    multiple(y.leverage),
                ]
                for y in r.years
            ],
        ),
        "",
        f"EXIT (year {d.hold_years}, {d.exit_multiple:.1f}x EBITDA)",
        kv(
            [
                ("Exit EV", money(r.exit_ev)),
                ("Net debt repaid", money(-r.exit_net_debt)),
                ("Exit equity", money(r.exit_equity)),
                ("MOIC", multiple(r.moic)),
                ("IRR", pct(r.irr)),
            ]
        ),
        "",
        "VALUE CREATION BRIDGE",
        table(
            ["Driver", "Value", "Share"],
            [
                ["EBITDA growth", money(b.ebitda_growth), share(b.ebitda_growth)],
                ["Multiple expansion", money(b.multiple_expansion), share(b.multiple_expansion)],
                ["Debt paydown", money(b.debt_paydown), share(b.debt_paydown)],
                ["Fees", money(b.fees), share(b.fees)],
                ["Equity gain", money(b.total), share(b.total)],
            ],
        ),
    ]
    return "\n".join(out)


def render_sensitivity(t: SensitivityTable, title: str, row_fmt, col_fmt, cell_fmt) -> str:
    headers = [f"{t.row_field} \\ {t.col_field}"] + [col_fmt(c) for c in t.col_values]
    rows = [[row_fmt(rv)] + [cell_fmt(c) for c in cells] for rv, cells in zip(t.row_values, t.cells)]
    return f"{title}\n{table(headers, rows)}"
