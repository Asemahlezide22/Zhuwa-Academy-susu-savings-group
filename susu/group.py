"""The rotating savings group (susu) and its rules.

A group has a fixed weekly contribution. Each member pays that amount every
week, in one go or in parts. When every member has paid in full, the week can
close: the whole pot (weekly amount x number of members) goes to the next
member in join order and the next week opens. One full cycle is one payout
per member, so a group of N members runs for N weeks.

Rules that the brief left open, and the choice made for each, are listed in
NOTES.md. The short version:
- Members can be added only before week 1 starts (before the first payment),
  so everyone pays into every pot they might receive from.
- Names are unique ignoring case and surrounding spaces ("ama" == "Ama ").
- Payments are accepted only for the current open week: no back-dating into
  closed weeks and no prepaying future weeks.
- At least two members are needed before money can move.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .errors import (
    CycleCompleteError,
    DuplicateMemberError,
    InvalidMemberNameError,
    MembershipLockedError,
    NotEnoughMembersError,
    OverpaymentError,
    UnknownMemberError,
    WeekNotOpenError,
)
from .money import format_amount, parse_amount

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class Payout:
    """One week's pot paid to one member."""

    week: int
    member: str
    amount: Decimal


@dataclass(frozen=True)
class CloseResult:
    """What happened when someone tried to close a week.

    closed is False when somebody still owes money; outstanding then lists who
    owes what (in join order) and no payout was made.
    """

    week: int
    closed: bool
    payout: Payout | None = None
    outstanding: dict[str, Decimal] = field(default_factory=dict)
    next_member: str | None = None  # who receives next week's pot, if anyone

    def message(self) -> str:
        if not self.closed:
            owing = "; ".join(f"{name} owes {format_amount(amt)}" for name, amt in self.outstanding.items())
            return f"Week {self.week} cannot close: {owing}."
        assert self.payout is not None
        text = (
            f"Week {self.week} closed: {self.payout.member} receives "
            f"{format_amount(self.payout.amount)}."
        )
        if self.next_member is None:
            return text + " Cycle complete: every member has received the pot."
        return text + f" Week {self.week + 1} begins; {self.next_member} is next."


class SusuGroup:
    """One rotating savings group, held in memory."""

    # A one-person susu just pays the member back their own money.
    MIN_MEMBERS = 2

    def __init__(self, weekly_amount: str | int | Decimal) -> None:
        self.weekly_amount: Decimal = parse_amount(weekly_amount)
        self._members: list[str] = []  # join order = payout order
        self.current_week: int = 1
        # week number -> member name -> total paid for that week so far
        self._paid: dict[int, dict[str, Decimal]] = {}
        self._payouts: list[Payout] = []

    # ----- members -------------------------------------------------------

    @property
    def members(self) -> tuple[str, ...]:
        """Members in the order they joined (which is the payout order)."""
        return tuple(self._members)

    @property
    def has_started(self) -> bool:
        """True once any money has been recorded; membership is then locked."""
        return self.current_week > 1 or bool(self._paid.get(1))

    def add_member(self, name: str) -> str:
        """Add a member to the end of the payout order and return their name."""
        clean = " ".join(str(name).split())  # trim and collapse inner spaces
        if not clean:
            raise InvalidMemberNameError("Member name cannot be blank.")
        if self.has_started:
            raise MembershipLockedError(
                f"Cannot add {clean}: week 1 has started. Members can only be "
                "added before the first contribution is recorded."
            )
        if self._find_member(clean) is not None:
            raise DuplicateMemberError(f"{clean} is already a member.")
        self._members.append(clean)
        return clean

    def _find_member(self, name: str) -> str | None:
        """Return the stored spelling of a member, matching case-insensitively."""
        wanted = " ".join(str(name).split()).casefold()
        for member in self._members:
            if member.casefold() == wanted:
                return member
        return None

    def member_name(self, name: str) -> str:
        """The stored spelling of a member's name ("ama" -> "Ama"); raises if unknown."""
        return self._require_member(name)

    def _require_member(self, name: str) -> str:
        member = self._find_member(name)
        if member is None:
            raise UnknownMemberError(f"{name} is not a member of this group.")
        return member

    # ----- contributions ----------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """True once every member has received the pot (end of the cycle)."""
        return bool(self._members) and len(self._payouts) == len(self._members)

    def contribute(self, member: str, week: int, amount: str | int | Decimal) -> Decimal:
        """Record a (possibly partial) payment and return what is still owed.

        The week must be the current open week. The amount must be positive and
        no more than the member still owes for that week.
        """
        name = self._require_member(member)
        value = parse_amount(amount)
        self._require_open_week(week)
        self._require_enough_members()

        owed = self.owed(name)
        if owed == ZERO:
            raise OverpaymentError(f"{name} has already paid in full for week {week}.")
        if value > owed:
            raise OverpaymentError(
                f"{name} owes {format_amount(owed)} for week {week}; "
                f"cannot accept {format_amount(value)}."
            )

        week_paid = self._paid.setdefault(week, {})
        week_paid[name] = week_paid.get(name, ZERO) + value
        return owed - value

    def paid(self, member: str, week: int | None = None) -> Decimal:
        """Total a member has paid for a week (default: the current week)."""
        name = self._require_member(member)
        week = self.current_week if week is None else week
        return self._paid.get(week, {}).get(name, ZERO)

    def owed(self, member: str, week: int | None = None) -> Decimal:
        """What a member still owes for a week (default: the current week)."""
        return self.weekly_amount - self.paid(member, week)

    def _require_open_week(self, week: int) -> None:
        # bool is an int subclass; True must not be read as week 1.
        if isinstance(week, bool) or not isinstance(week, int):
            raise WeekNotOpenError(f"Week must be a whole number (got {week!r}).")
        if self.is_complete:
            raise CycleCompleteError("The cycle is complete: every member has received the pot.")
        if week < self.current_week:
            raise WeekNotOpenError(f"Week {week} is already closed; the open week is {self.current_week}.")
        if week > self.current_week:
            raise WeekNotOpenError(f"Week {week} has not opened yet; the open week is {self.current_week}.")

    def _require_enough_members(self) -> None:
        if len(self._members) < self.MIN_MEMBERS:
            raise NotEnoughMembersError(
                f"The group needs at least {self.MIN_MEMBERS} members before money can move "
                f"(it has {len(self._members)})."
            )

    # ----- closing weeks and payouts ----------------------------------------

    @property
    def pot(self) -> Decimal:
        """What one week pays out: every member's full contribution."""
        return self.weekly_amount * len(self._members)

    @property
    def payouts(self) -> tuple[Payout, ...]:
        """Payout history, oldest first."""
        return tuple(self._payouts)

    @property
    def next_recipient(self) -> str | None:
        """Who receives the pot when the current week closes (None if complete).

        Weeks only advance on a payout, so the k-th payout goes to the k-th
        member to join.
        """
        if self.is_complete or not self._members:
            return None
        return self._members[len(self._payouts)]

    def outstanding(self) -> dict[str, Decimal]:
        """Members who still owe for the current week, in join order."""
        return {m: self.owed(m) for m in self._members if self.owed(m) > ZERO}

    def close_week(self) -> CloseResult:
        """Try to close the current week.

        If everyone has paid in full, pay the pot to the next member, open the
        next week and return closed=True. Otherwise change nothing and return
        closed=False with who owes what.
        """
        if self.is_complete:
            raise CycleCompleteError("The cycle is complete: every member has received the pot.")
        self._require_enough_members()

        week = self.current_week
        owing = self.outstanding()
        if owing:
            return CloseResult(week=week, closed=False, outstanding=owing)

        payout = Payout(week=week, member=self.next_recipient, amount=self.pot)
        self._payouts.append(payout)
        self.current_week += 1
        return CloseResult(week=week, closed=True, payout=payout, next_member=self.next_recipient)
