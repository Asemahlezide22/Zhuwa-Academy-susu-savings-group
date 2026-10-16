"""Tests for exact money parsing and formatting."""

import unittest
from decimal import Decimal

from susu.errors import InvalidAmountError
from susu.money import format_amount, parse_amount


class ParseAmountTests(unittest.TestCase):
    def test_accepts_text_ints_and_decimals(self):
        self.assertEqual(parse_amount("50"), Decimal("50.00"))
        self.assertEqual(parse_amount(" 50.5 "), Decimal("50.50"))
        self.assertEqual(parse_amount(50), Decimal("50.00"))
        self.assertEqual(parse_amount(Decimal("0.01")), Decimal("0.01"))

    def test_rejects_zero_and_negative(self):
        for bad in ("0", "0.00", "-5", -1, Decimal("-0.01")):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidAmountError):
                    parse_amount(bad)

    def test_rejects_floats_and_bools(self):
        # A float has already lost exactness before we see it.
        for bad in (50.0, 0.1, True):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidAmountError):
                    parse_amount(bad)

    def test_rejects_fractions_of_a_pesewa_instead_of_rounding(self):
        with self.assertRaises(InvalidAmountError):
            parse_amount("10.005")

    def test_rejects_text_that_is_not_a_number(self):
        for bad in ("", "abc", "NaN", "Infinity", "1e999999"):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidAmountError):
                    parse_amount(bad)

    def test_sums_are_exact(self):
        # The classic float failure: 0.1 + 0.2 == 0.30000000000000004.
        total = parse_amount("0.10") + parse_amount("0.20")
        self.assertEqual(total, Decimal("0.30"))
        # Thirty partial payments of 1.67 plus one of 0.90 make exactly 51.00.
        total = sum((parse_amount("1.67") for _ in range(30)), Decimal("0")) + parse_amount("0.90")
        self.assertEqual(total, Decimal("51.00"))


class FormatAmountTests(unittest.TestCase):
    def test_always_two_decimal_places(self):
        self.assertEqual(format_amount(Decimal("150")), "150.00")
        self.assertEqual(format_amount(Decimal("20.5")), "20.50")


if __name__ == "__main__":
    unittest.main()
