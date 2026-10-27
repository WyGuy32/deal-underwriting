"""Two-way sensitivity tables: flex two inputs, read one output."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class SensitivityTable:
    row_field: str
    col_field: str
    row_values: list[float]
    col_values: list[float]
    cells: list[list[float | None]]


def sensitivity(
    deal: Any,
    model: Callable[[Any], Any],
    metric: Callable[[Any], float | None],
    row_field: str,
    row_values: Sequence[float],
    col_field: str,
    col_values: Sequence[float],
) -> SensitivityTable:
    """Rerun `model` for every (row, col) pair of input values.

    Cells where the model rejects the inputs (for example, debt larger than
    the purchase price) are left as None rather than aborting the table.
    """
    cells = []
    for rv in row_values:
        row = []
        for cv in col_values:
            try:
                row.append(metric(model(replace(deal, **{row_field: rv, col_field: cv}))))
            except ValueError:
                row.append(None)
        cells.append(row)
    return SensitivityTable(row_field, col_field, list(row_values), list(col_values), cells)


def around(center: float, step: float, n: int = 2) -> list[float]:
    """`center` plus `n` steps either side, e.g. around(0.065, 0.005) -> 5 cap rates."""
    return [round(center + step * k, 10) for k in range(-n, n + 1)]
