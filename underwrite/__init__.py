"""Deal underwriting: rental property and leveraged buyout models in plain Python."""

from .finance import amortization_schedule, equity_multiple, irr, npv, payment, remaining_balance
from .lbo import LBODeal, LBOResult, run_lbo
from .rental import RentalDeal, RentalResult, underwrite_rental
from .sensitivity import around, sensitivity

__all__ = [
    "LBODeal",
    "LBOResult",
    "RentalDeal",
    "RentalResult",
    "amortization_schedule",
    "around",
    "equity_multiple",
    "irr",
    "npv",
    "payment",
    "remaining_balance",
    "run_lbo",
    "sensitivity",
    "underwrite_rental",
]

__version__ = "1.0.0"
