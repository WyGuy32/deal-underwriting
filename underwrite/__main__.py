"""Command line: python -m underwrite {rental,lbo} deal.json [--sensitivity] [--json]"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from .lbo import LBODeal, run_lbo
from .report import money, multiple, pct, render_lbo, render_rental, render_sensitivity
from .rental import RentalDeal, underwrite_rental
from .sensitivity import around, sensitivity


def _load(path: str, cls):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data.pop("_comment", None)
    fields = {f.name for f in dataclasses.fields(cls)}
    unknown = set(data) - fields
    if unknown:
        raise SystemExit(f"unknown field(s) in {path}: {', '.join(sorted(unknown))}")
    return cls(**data)


def _as_json(result) -> str:
    def default(o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        raise TypeError(type(o))

    return json.dumps(dataclasses.asdict(result), indent=2, default=default)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="underwrite", description="Underwrite a rental property or an LBO.")
    parser.add_argument("model", choices=["rental", "lbo"])
    parser.add_argument("deal", help="path to a deal JSON file (see examples/)")
    parser.add_argument("--sensitivity", action="store_true", help="add a two-way IRR sensitivity table")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args(argv)

    if args.model == "rental":
        deal = _load(args.deal, RentalDeal)
        result = underwrite_rental(deal)
        text = render_rental(result)
        if args.sensitivity:
            price_step = round(deal.purchase_price * 0.05, -3)
            t = sensitivity(
                deal,
                underwrite_rental,
                lambda r: r.irr,
                "purchase_price",
                around(deal.purchase_price, price_step),
                "exit_cap_rate",
                around(deal.exit_cap_rate, 0.0025),
            )
            text += "\n\n" + render_sensitivity(t, "LEVERED IRR: purchase price vs. exit cap", money, lambda x: pct(x, 2), pct)
    else:
        deal = _load(args.deal, LBODeal)
        result = run_lbo(deal)
        text = render_lbo(result)
        if args.sensitivity:
            t = sensitivity(
                deal,
                run_lbo,
                lambda r: r.irr,
                "entry_multiple",
                around(deal.entry_multiple, 0.5),
                "exit_multiple",
                around(deal.exit_multiple, 0.5),
            )
            text += "\n\n" + render_sensitivity(t, "SPONSOR IRR: entry vs. exit multiple", multiple, multiple, pct)

    print(_as_json(result) if args.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
