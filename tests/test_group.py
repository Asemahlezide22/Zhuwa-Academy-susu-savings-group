"""Tests for the group rules: members, contributions, closing weeks, payouts."""

import unittest
from decimal import Decimal

from susu.errors import (
    CycleCompleteError,
    DuplicateMemberError,
    InvalidAmountError,
    InvalidMemberNameError,
    MembershipLockedError,
    NotEnoughMembersError,
    OverpaymentError,
    UnknownMemberError,
    WeekNotOpenError,
)
from susu.group import SusuGroup


def make_group(*names, amount="50.00"):
    """A group with the given members, ready for week 1."""
    group = SusuGroup(amount)
    for name in names:
        group.add_member(name)
    return group


class MemberTests(unittest.TestCase):
    def test_members_keep_join_order(self):
        group = make_group("Ama", "Kofi", "Esi")
        self.assertEqual(group.members, ("Ama", "Kofi", "Esi"))

    def test_rejects_duplicate_member_ignoring_case_and_spaces(self):
        group = make_group("Ama")
        for dup in ("Ama", "ama", "  AMA "):
            with self.subTest(dup=dup):
                with self.assertRaises(DuplicateMemberError):
                    group.add_member(dup)

    def test_rejects_blank_name(self):
        with self.assertRaises(InvalidMemberNameError):
            make_group("   ")

    def test_cannot_add_member_after_week_1_has_started(self):
        group = make_group("Ama", "Kofi")
        group.contribute("Ama", 1, "10")
        with self.assertRaises(MembershipLockedError):
            group.add_member("Esi")


class ContributionTests(unittest.TestCase):
    def setUp(self):
        self.group = make_group("Ama", "Kofi", "Esi")

    def test_partial_payments_add_up(self):
        self.assertEqual(self.group.contribute("Esi", 1, "30"), Decimal("20.00"))
        self.assertEqual(self.group.owed("Esi"), Decimal("20.00"))
        self.assertEqual(self.group.contribute("Esi", 1, "20"), Decimal("0.00"))
        self.assertEqual(self.group.paid("Esi"), Decimal("50.00"))

    def test_member_lookup_is_case_insensitive(self):
        self.group.contribute("esi", 1, "50")
        self.assertEqual(self.group.paid("Esi"), Decimal("50.00"))

    def test_rejects_unknown_member(self):
        with self.assertRaises(UnknownMemberError):
            self.group.contribute("Yaw", 1, "50")

    def test_rejects_zero_and_negative_amounts(self):
        for bad in ("0", "-10"):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidAmountError):
                    self.group.contribute("Ama", 1, bad)

    def test_rejects_payment_above_amount_owed(self):
        with self.assertRaises(OverpaymentError):
            self.group.contribute("Ama", 1, "50.01")

    def test_rejects_overpayment_after_partial_payment(self):
        self.group.contribute("Esi", 1, "30")
        with self.assertRaises(OverpaymentError) as caught:
            self.group.contribute("Esi", 1, "25")
        self.assertIn("owes 20.00", str(caught.exception))
        # The refused payment changed nothing.
        self.assertEqual(self.group.paid("Esi"), Decimal("30.00"))

    def test_rejects_payment_once_paid_in_full(self):
        self.group.contribute("Ama", 1, "50")
        with self.assertRaises(OverpaymentError):
            self.group.contribute("Ama", 1, "1")

    def test_rejects_payment_for_a_week_that_is_not_open(self):
        for week in (0, 2, True):
            with self.subTest(week=week):
                with self.assertRaises(WeekNotOpenError):
                    self.group.contribute("Ama", week, "50")

    def test_needs_two_members_before_money_moves(self):
        group = make_group("Ama")
        with self.assertRaises(NotEnoughMembersError):
            group.contribute("Ama", 1, "50")


class CloseWeekTests(unittest.TestCase):
    def setUp(self):
        self.group = make_group("Ama", "Kofi", "Esi")

    def pay_all(self, week):
        for name in self.group.members:
            self.group.contribute(name, week, self.group.owed(name))

    def test_example_from_the_brief(self):
        # Week 1: Ama and Kofi pay 50, Esi pays 30.
        self.group.contribute("Ama", 1, "50")
        self.group.contribute("Kofi", 1, "50")
        self.group.contribute("Esi", 1, "30")

        # Closing week 1 pays nothing and reports "Esi owes 20.00".
        result = self.group.close_week()
        self.assertFalse(result.closed)
        self.assertEqual(result.outstanding, {"Esi": Decimal("20.00")})
        self.assertIn("Esi owes 20.00", result.message())
        self.assertEqual(self.group.payouts, ())
        self.assertEqual(self.group.current_week, 1)

        # Esi pays 20, week 1 closes, and Ama receives 150.00.
        self.group.contribute("Esi", 1, "20")
        result = self.group.close_week()
        self.assertTrue(result.closed)
        self.assertEqual(result.payout.member, "Ama")
        self.assertEqual(result.payout.amount, Decimal("150.00"))

        # Week 2 begins, and Kofi is next.
        self.assertEqual(self.group.current_week, 2)
        self.assertEqual(self.group.next_recipient, "Kofi")
        self.assertIn("Week 2 begins; Kofi is next", result.message())

    def test_week_cannot_close_lists_everyone_who_owes(self):
        self.group.contribute("Kofi", 1, "12.50")
        result = self.group.close_week()
        self.assertFalse(result.closed)
        self.assertEqual(
            result.outstanding,
            {"Ama": Decimal("50.00"), "Kofi": Decimal("37.50"), "Esi": Decimal("50.00")},
        )
        self.assertEqual(
            result.message(),
            "Week 1 cannot close: Ama owes 50.00; Kofi owes 37.50; Esi owes 50.00.",
        )

    def test_new_week_starts_with_everyone_owing_in_full(self):
        self.pay_all(1)
        self.group.close_week()
        for name in self.group.members:
            self.assertEqual(self.group.owed(name), Decimal("50.00"))

    def test_cannot_pay_into_a_closed_week(self):
        self.pay_all(1)
        self.group.close_week()
        with self.assertRaises(WeekNotOpenError):
            self.group.contribute("Ama", 1, "10")

    def test_pot_is_paid_in_join_order_then_cycle_completes(self):
        for week in (1, 2, 3):
            self.pay_all(week)
            self.group.close_week()
        self.assertEqual([p.member for p in self.group.payouts], ["Ama", "Kofi", "Esi"])
        self.assertEqual([p.week for p in self.group.payouts], [1, 2, 3])
        self.assertTrue(self.group.is_complete)
        self.assertIsNone(self.group.next_recipient)
        # Nothing more can happen once everyone has received the pot.
        with self.assertRaises(CycleCompleteError):
            self.group.close_week()
        with self.assertRaises(CycleCompleteError):
            self.group.contribute("Ama", 4, "50")

    def test_each_member_pays_in_exactly_what_they_receive(self):
        # Over a full cycle nobody gains or loses: each pays 3 x 50 and gets 150.
        for week in (1, 2, 3):
            self.pay_all(week)
            self.group.close_week()
        total_paid_out = sum((p.amount for p in self.group.payouts), Decimal("0"))
        self.assertEqual(total_paid_out, Decimal("450.00"))

    def test_odd_amounts_stay_exact(self):
        group = make_group("Ama", "Kofi", "Esi", amount="33.33")
        for name in group.members:
            group.contribute(name, 1, "11.11")
            group.contribute(name, 1, "22.22")
        result = group.close_week()
        self.assertEqual(result.payout.amount, Decimal("99.99"))


if __name__ == "__main__":
    unittest.main()
