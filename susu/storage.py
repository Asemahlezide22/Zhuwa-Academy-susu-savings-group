"""Saving a group to a JSON file between command-line runs.

The file stores the weekly amount and an ordered log of every successful
action (add member, contribution, week closed), not a snapshot of balances.
Loading replays that log through SusuGroup, so the same rules that guard
live input also check the file: a hand-edited file that, say, overpays a
member or closes a week that was not fully paid is refused on load instead
of being trusted. Amounts are stored as strings so they stay exact.

Example file:
    {"version": 1, "weekly_amount": "50.00",
     "events": [{"action": "add_member", "name": "Ama"},
                {"action": "contribute", "member": "Ama", "week": 1, "amount": "50.00"},
                {"action": "close_week"}]}
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .errors import SusuError
from .group import SusuGroup
from .money import format_amount

FORMAT_VERSION = 1


class StateFileError(SusuError):
    """The saved group file is missing, unreadable or breaks the rules."""


def new_state(weekly_amount: str) -> dict[str, Any]:
    """State for a brand-new group (validates the amount)."""
    group = SusuGroup(weekly_amount)
    return {"version": FORMAT_VERSION, "weekly_amount": format_amount(group.weekly_amount), "events": []}


def apply_event(group: SusuGroup, event: dict[str, Any]) -> None:
    """Apply one logged action to a group, using the normal rules."""
    action = event.get("action")
    if action == "add_member":
        group.add_member(event["name"])
    elif action == "contribute":
        group.contribute(event["member"], event["week"], event["amount"])
    elif action == "close_week":
        result = group.close_week()
        # Only successful closes are logged, so a failed one means tampering.
        if not result.closed:
            raise StateFileError(f"Saved file closes week {result.week}, but it was not fully paid.")
    else:
        raise StateFileError(f"Unknown action in saved file: {action!r}.")


def replay(state: dict[str, Any]) -> SusuGroup:
    """Rebuild the group from saved state, checking every step."""
    if state.get("version") != FORMAT_VERSION:
        raise StateFileError(f"Unsupported file version {state.get('version')!r}.")
    group = SusuGroup(state["weekly_amount"])
    for number, event in enumerate(state["events"], start=1):
        try:
            apply_event(group, event)
        except StateFileError:
            raise
        except (SusuError, KeyError, TypeError) as exc:
            raise StateFileError(f"Saved file is invalid at event {number}: {exc}") from None
    return group


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise StateFileError(f"No group found at {path}. Create one first with: susu create 50.00")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateFileError(f"Could not read {path}: {exc}") from None
    if not isinstance(state, dict) or "weekly_amount" not in state or not isinstance(state.get("events"), list):
        raise StateFileError(f"{path} is not a susu group file.")
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    """Write via a temporary file and rename, so a crash never leaves half a file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
