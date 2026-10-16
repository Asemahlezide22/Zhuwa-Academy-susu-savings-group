# Susu savings group

A small command-line program that manages one rotating savings group (susu).
Every member pays the same fixed amount in GHS each week; each week the whole
pot goes to one member, in the order they joined.

Pure Python 3.10+ with no third-party dependencies.

## Run it

From the project folder:

```bash
python -m susu demo
```

`demo` runs the worked example from the brief (Ama, Kofi, Esi at 50.00) in
memory and prints each step and the final report. It saves nothing.

To run your own group, use one command per action. The group is saved to
`susu.json` in the current folder; pass `--state other.json` to use a
different file.

```bash
python -m susu create 50.00              # new group, weekly contribution GHS 50.00
python -m susu add Ama Kofi Esi          # members, in payout order
python -m susu pay Ama 50 --week 1       # full payment
python -m susu pay Esi 30 --week 1       # partial payment
python -m susu close                     # pays out only if everyone has paid in full
python -m susu report                    # current week, who paid, who owes, payout history
```

`--week` defaults to the current open week. Run `python -m susu --help` or
`python -m susu pay --help` for every option.

Example session:

```text
$ python -m susu pay Esi 30 --week 1
Recorded. Esi still owes 20.00 for week 1.
$ python -m susu close
Week 1 cannot close: Esi owes 20.00.
$ python -m susu pay Esi 20 --week 1
Recorded. Esi has paid in full for week 1.
$ python -m susu close
Week 1 closed: Ama receives 150.00. Week 2 begins; Kofi is next.
```

A refused action (unknown member, duplicate member, zero or negative amount,
paying more than is owed, a closed week) prints `Error: ...` and exits with
code 1. The saved file is not changed.

Optionally, `pip install -e .` adds a `susu` command, so `susu report` works
from anywhere.

## Run the tests

```bash
python -m unittest -v
```

The tests use only the standard library. `pytest` also finds and runs them
if you have it installed. They cover money handling, every validation rule,
partial payments, a week that cannot close, payout order, the full cycle, the
report, and the CLI end to end against a temporary file.

## Layout

```text
susu/
  money.py    exact GHS amounts (Decimal, two decimal places, no floats)
  group.py    the group and its rules: members, contributions, closing weeks
  report.py   the plain-text report
  storage.py  JSON save/load (an action log replayed through the rules)
  cli.py      command-line interface
tests/        unittest suites, one per module
NOTES.md      assumptions, decisions, and what I would improve
```
