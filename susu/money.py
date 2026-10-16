"""Exact handling of GHS amounts.

Every amount in the program is a Decimal with exactly two decimal places
(cedis and pesewas). Floats never enter the system: 0.1 cannot be stored
exactly as a binary float, so 0.1 + 0.2 != 0.3. Amounts arrive as strings
(from the command line or the saved file) or as Decimal/int, and are checked
here before any rule sees them.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .errors import InvalidAmountError

# One pesewa: the smallest unit of the cedi, and the precision we keep.
PESEWA = Decimal("0.01")


def parse_amount(value: str | int | Decimal) -> Decimal:
    """Turn user input into a positive two-decimal amount, or raise.

    Accepts "50", "50.5", "50.00", 50 or Decimal("50.00"). Rejects floats,
    zero, negatives, NaN/Infinity, text that is not a number, and anything
    with more than two decimal places (e.g. "10.005"), rather than rounding
    it silently.
    """
    # bool is a subclass of int, so True would otherwise be read as 1.00.
    if isinstance(value, (bool, float)):
        raise InvalidAmountError(
            f"Amount {value!r} must be given as text or a Decimal, not a float, "
            "so it can be stored exactly."
        )

    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        try:
            amount = Decimal(value.strip())
        except InvalidOperation:
            raise InvalidAmountError(f"'{value}' is not a valid amount.") from None
    else:
        raise InvalidAmountError(f"'{value}' is not a valid amount.")

    if not amount.is_finite():
        raise InvalidAmountError(f"'{value}' is not a valid amount.")
    if amount <= 0:
        raise InvalidAmountError(f"Amount must be greater than zero (got {value}).")

    # Refuse fractions of a pesewa instead of rounding them away: rounding
    # someone's payment is exactly the kind of error we must not make.
    try:
        exact = amount.quantize(PESEWA)
    except InvalidOperation:
        raise InvalidAmountError(f"Amount {value} is too large.") from None
    if exact != amount:
        raise InvalidAmountError(
            f"Amount {value} has more than two decimal places; "
            "the smallest unit is one pesewa (0.01)."
        )
    return exact


def format_amount(amount: Decimal) -> str:
    """Show an amount the way people write it: 150.00, 20.50."""
    return f"{amount.quantize(PESEWA):.2f}"
