"""Unit tests for query_data helper filters."""

import unittest

from M3_material import query_data


class QueryFilterTests(unittest.TestCase):
    def test_term_filter_on(self):
        clause, params = query_data._term_filter(True)
        self.assertIn(query_data.FALL_TERM, params)
        self.assertIn(query_data.YEAR_START, params)
        self.assertIn(query_data.YEAR_END, params)
        self.assertIn("accept%", params)

    def test_term_filter_off(self):
        clause, params = query_data._term_filter(False)
        self.assertEqual(clause, "TRUE")
        self.assertEqual(params, [])


if __name__ == "__main__":
    unittest.main()
