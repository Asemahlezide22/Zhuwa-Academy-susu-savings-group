"""Command-line interface for one susu group.

Each command loads the group from a JSON file (default ./susu.json), applies
one action through SusuGroup, and saves only if the action succeeded. A
refused action prints the reason and exits with code 1, leaving the file
untouched.

    python -m susu create 50.00
    python -m susu add Ama Kofi Esi
    python -m susu pay Esi 30 --week 1
    python -m susu close
    python -m susu report
    python -m susu demo          # runs the example from the brief, saves nothing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

from .errors import SusuError
from .group import SusuGroup
from .money import format_amount, parse_amount
from .report import render_report
from .storage import load_state, new_state, replay, save_state

DEFAULT_STATE = "susu.json"


# ----- commands ---------------------------------------------------------------


def cmd_create(args: argparse.Namespace) -> int:
    path = Path(args.state)
    if path.exists() and not args.force:
        print(f"Error: {path} already holds a group. Use --force to replace it.", file=sys.stderr)
        return 1
    state = new_state(args.amount)
    save_state(path, state)
    print(f"Created a group with a weekly contribution of GHS {state['weekly_amount']} ({path}).")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    path = Path(args.state)
    state = load_state(path)
    group = replay(state)
    # Add every name before saving, so a duplicate in the list adds none of them.
    for name in args.names:
        added = group.add_member(name)
        state["events"].append({"action": "add_member", "name": added})
    save_state(path, state)
    print(f"Members (payout order): {', '.join(group.members)}")
    return 0


def cmd_pay(args: argparse.Namespace) -> int:
    path = Path(args.state)
    state = load_state(path)
    group = replay(state)
    week = group.current_week if args.week is None else args.week
    # Log the stored spelling and the two-decimal amount, not whatever was typed.
    member = group.member_name(args.member)
    amount = parse_amount(args.amount)
    remaining = group.contribute(member, week, amount)
    state["events"].append({"action": "contribute", "member": member, "week": week, "amount": format_amount(amount)})
    save_state(path, state)
    if remaining == 0:
        print(f"Recorded. {member} has paid in full for week {week}.")
    else:
        print(f"Recorded. {member} still owes {format_amount(remaining)} for week {week}.")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    path = Path(args.state)
    state = load_state(path)
    group = replay(state)
    result = group.close_week()
    if result.closed:
        state["events"].append({"action": "close_week"})
        save_state(path, state)
    print(result.message())
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    group = replay(load_state(Path(args.state)))
    print(render_report(group))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Walk through the example from the brief, entirely in memory."""
    group = SusuGroup("50.00")
    steps: list[tuple[str, Callable[[], Any]]] = [
        ("add Ama, Kofi, Esi", lambda: [group.add_member(n) for n in ("Ama", "Kofi", "Esi")]),
        ("Ama pays 50 for week 1", lambda: group.contribute("Ama", 1, "50")),
        ("Kofi pays 50 for week 1", lambda: group.contribute("Kofi", 1, "50")),
        ("Esi pays 30 for week 1", lambda: group.contribute("Esi", 1, "30")),
        ("close week 1", lambda: print("   ", group.close_week().message())),
        ("Esi pays 20 for week 1", lambda: group.contribute("Esi", 1, "20")),
        ("close week 1", lambda: print("   ", group.close_week().message())),
    ]
    for label, step in steps:
        print(f"> {label}")
        step()
    print()
    print(render_report(group))
    return 0


# ----- entry point --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="susu", description="Manage one rotating savings group (susu).")
    parser.add_argument("--state", default=DEFAULT_STATE, help=f"group file to use (default: {DEFAULT_STATE})")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="start a new group with a fixed weekly contribution in GHS")
    p.add_argument("amount", help="weekly contribution, e.g. 50.00")
    p.add_argument("--force", action="store_true", help="replace an existing group file")
    p.set_defaults(handler=cmd_create)

    p = sub.add_parser("add", help="add one or more members (before week 1 starts)")
    p.add_argument("names", nargs="+", metavar="NAME")
    p.set_defaults(handler=cmd_add)

    p = sub.add_parser("pay", help="record a full or partial contribution")
    p.add_argument("member")
    p.add_argument("amount", help="amount in GHS, e.g. 20 or 12.50")
    p.add_argument("--week", type=int, help="week number (default: the current open week)")
    p.set_defaults(handler=cmd_pay)

    p = sub.add_parser("close", help="close the current week and pay the pot if everyone has paid")
    p.set_defaults(handler=cmd_close)

    p = sub.add_parser("report", help="show the current week, balances and payout history")
    p.set_defaults(handler=cmd_report)

    p = sub.add_parser("demo", help="run the example from the brief in memory (saves nothing)")
    p.set_defaults(handler=cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except SusuError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
