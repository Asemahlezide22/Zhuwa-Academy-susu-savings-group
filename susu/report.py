"""Plain-text report of where a group stands.

Shows the current week, who has paid in full, who still owes what, and the
payout history. It only reads the group; it never changes it.
"""

from __future__ import annotations

from .group import SusuGroup
from .money import format_amount


def render_report(group: SusuGroup) -> str:
    """Build the report as lines of plain ASCII text (safe on any console)."""
    lines = [
        f"Weekly contribution: GHS {format_amount(group.weekly_amount)}",
        f"Members (payout order): {', '.join(group.members) or 'none yet'}",
        f"Pot per week: GHS {format_amount(group.pot)}",
    ]

    if group.is_complete:
        lines.append(f"Cycle complete after week {group.current_week - 1}: every member has received the pot.")
    else:
        lines.append(f"Current week: {group.current_week}")
        lines.append(f"Next to receive the pot: {group.next_recipient or 'nobody (add members first)'}")

        paid_in_full = [m for m in group.members if group.owed(m) == 0]
        lines.append(f"Paid in full: {', '.join(paid_in_full) or 'nobody yet'}")

        owing = group.outstanding()
        if owing:
            lines.append("Still owes:")
            for name, amount in owing.items():
                paid = group.paid(name)
                lines.append(f"  {name}: {format_amount(amount)} (paid {format_amount(paid)} so far)")
        else:
            lines.append("Still owes: nobody")

    lines.append("Payout history:")
    if group.payouts:
        for payout in group.payouts:
            lines.append(f"  Week {payout.week}: {payout.member} received GHS {format_amount(payout.amount)}")
    else:
        lines.append("  none yet")

    return "\n".join(lines)
