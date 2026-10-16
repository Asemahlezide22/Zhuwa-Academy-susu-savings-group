# Notes

## Assumptions (rules the brief left open)

| Situation | Rule I chose | Why |
|---|---|---|
| Adding a member after week 1 has started | **Refused.** Membership locks at the first recorded contribution. | A latecomer would receive a pot they did not pay into for the weeks they missed, or the pot sizes would differ week to week. Locking keeps every pot the same size and keeps the cycle fair. |
| Minimum group size | **At least 2 members** before any payment or close. | A one-person susu just hands the member their own money back. |
| Duplicate names | Names are compared **ignoring case and extra spaces**, so `Ama`, `ama` and ` AMA ` are the same person. The spelling used when they joined is kept. | Prevents two accounts for one person caused by typing. |
| Which week a payment is for | Only the **current open week** is accepted. Paying into a closed week or prepaying a future week is refused. | A closed week has already paid out, so money added later would have nowhere to go. Prepayment adds credit-tracking the brief did not ask for. |
| Paying more than owed | Refused, including a second payment once the member has paid in full. The message says how much is still owed. | As the brief says; the extra detail helps whoever is taking the money. |
| Amount precision | Amounts may have **at most two decimal places** (one pesewa). `10.005` is refused, not rounded. Floats are refused in code. | Rounding a payment silently is a money error; refusing it is not. |
| The pot | Weekly amount x number of members. | Everyone paid in full by definition, so the pot always equals that. |
| End of the cycle | After every member has received the pot once (N weeks for N members), the group is **complete**. Further payments or closes are refused. | One group, one rotation. Starting a new rotation is listed under improvements. |
| Closing a week that cannot close | Not an error (exit code 0). It reports who owes what and changes nothing. | Trying to close is a normal check, not a mistake. |
| Order of payout | Join order. Weeks advance only on a payout, so week k always pays the k-th member. | As the brief says. |

## Decisions

- **Exact money with `Decimal`.** Every amount is a `decimal.Decimal`
  quantised to 0.01, parsed from text. Floats are refused at the boundary
  because `0.1 + 0.2 != 0.3` in binary floating point. Amounts are saved as
  strings (`"12.50"`) so the JSON file is exact too. I considered integer
  pesewas, but Decimal reads more naturally in the code and is just as exact
  at this scale.
- **The rules live in one class (`SusuGroup`)** with no I/O. The CLI,
  storage and report all go through it, so each rule is enforced in exactly
  one place and is easy to test.
- **A refused action changes nothing.** Every check runs before any state
  is changed. The CLI saves only after the action succeeds, and `add A B C`
  is all-or-nothing.
- **Saved as an action log, not a snapshot.** The JSON file records each
  successful action. Loading replays them through the same rules, so a
  hand-edited file (say, closing a week that was not fully paid) is refused
  instead of trusted. It also gives a free audit trail of every payment.
  Writes go through a temporary file and a rename, so a crash cannot leave a
  half-written file.
- **CLI with one command per action**, rather than an interactive menu, so
  it is scriptable and easy to test end to end. A `demo` command runs the
  brief's example.
- **Standard library only** (`unittest`, `argparse`, `decimal`, `json`), so
  there is nothing to install.

## What I would improve with more time

- **Multiple cycles and groups:** start a new rotation when one completes,
  and manage several groups from one store.
- **A real database** (SQLite) with transactions, instead of a single JSON
  file, once more than one person records payments at the same time. The
  current file has no locking.
- **Payment details:** who received the money, date and time, and a
  reference, plus an `undo` for an entry recorded by mistake (as a reversing
  entry, so history is kept).
- **Late payments and penalties:** a policy for a member who never pays
  (skip their turn, a fine, or the group covers them). Today the week simply
  stays open.
- **Changing the payout order** by agreement (swap turns) before the cycle
  starts.
- **Stable member IDs** separate from display names, so a name can be
  corrected without changing history.
- **A small HTTP API** (e.g. FastAPI) over the same `SusuGroup` class, and
  property-based tests (Hypothesis) on the money and balance rules.
