"""Basic unit tests for the HTML cleaner helpers."""

import unittest

from M2_material.clean import _normalize_decision, _extract_gpa


class CleanerTests(unittest.TestCase):
    def test_normalize_decision(self):
        self.assertEqual(_normalize_decision("Accepted"), "accepted")
        self.assertEqual(_normalize_decision("Rejected"), "rejected")
        self.assertEqual(_normalize_decision("Wait listed"), "waitlisted")
        self.assertIsNone(_normalize_decision(None))

    def test_extract_gpa(self):
        sample = "Undergrad GPA: 3.8 GRE General: 165"
        self.assertEqual(_extract_gpa(sample), "3.8")


if __name__ == "__main__":
    unittest.main()
