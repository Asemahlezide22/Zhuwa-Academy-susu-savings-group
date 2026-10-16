"""Errors raised when an action breaks a susu rule.

Every rule violation raises a subclass of SusuError, so callers (the CLI, tests)
can catch one type and show the message. The message is written for the person
running the group, not for a developer.
"""


class SusuError(Exception):
    """Base class for every rule the group refuses to break."""


class InvalidAmountError(SusuError):
    """Amount is zero, negative, not a number, or finer than one pesewa."""


class UnknownMemberError(SusuError):
    """The named member is not in the group."""


class DuplicateMemberError(SusuError):
    """A member with that name is already in the group."""


class InvalidMemberNameError(SusuError):
    """The member name is blank."""


class OverpaymentError(SusuError):
    """The payment is more than the member still owes for the week."""


class WeekNotOpenError(SusuError):
    """The payment is for a week that is already closed or not yet open."""


class MembershipLockedError(SusuError):
    """Members can no longer be added because week 1 has started."""


class NotEnoughMembersError(SusuError):
    """The group needs at least two members before money can move."""


class CycleCompleteError(SusuError):
    """Every member has already received the pot once."""
