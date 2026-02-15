"""
Basic unit tests for the HTML cleaner helpers.

These are small, fast unit tests that do not use the database or network.
They validate string parsing and normalization logic in isolation.
"""

import unittest
import pytest

from M2_material.clean import _normalize_decision, _extract_gpa

pytestmark = pytest.mark.analysis


class CleanerTests(unittest.TestCase):
    def test_normalize_decision(self):
        # Normalize common decision labels into consistent lowercase values.
        self.assertEqual(_normalize_decision("Accepted"), "accepted")
        self.assertEqual(_normalize_decision("Rejected"), "rejected")
        self.assertEqual(_normalize_decision("Wait listed"), "waitlisted")
        self.assertIsNone(_normalize_decision(None))

    def test_extract_gpa(self):
        # Extract GPA values from mixed text strings.
        sample = "Undergrad GPA: 3.8 GRE General: 165"
        self.assertEqual(_extract_gpa(sample), "3.8")


if __name__ == "__main__":
    unittest.main()
