"""
Unit tests for query_data helper filters.

These tests validate the SQL filter builder without executing queries.
"""

import unittest
import pytest

from M3_material import query_data

pytestmark = pytest.mark.analysis


class QueryFilterTests(unittest.TestCase):
    def test_term_filter_on(self):
        # Verify the 2026 cohort filter includes term and year bounds.
        clause, params = query_data._term_filter(True)
        self.assertIn(query_data.FALL_TERM, params)
        self.assertIn(query_data.YEAR_START, params)
        self.assertIn(query_data.YEAR_END, params)
        self.assertIn("accept%", params)

    def test_term_filter_off(self):
        # When disabled, the filter should be a no-op.
        clause, params = query_data._term_filter(False)
        self.assertEqual(clause, "TRUE")
        self.assertEqual(params, [])


if __name__ == "__main__":
    unittest.main()
