"""
Quick CLI test runner for query_data.py.

This script prints the answers that the dashboard displays, and helps validate
the SQL queries without running the Flask app.
"""

try:
    from .query_data import (
        acceptance_rate_fall_2026,
        additional_question_1,
        additional_question_2,
        avg_gpa_acceptances_fall_2026,
        avg_gpa_american_fall_2026,
        average_metrics_all_applicants,
        count_fall_2026_entries,
        count_jhu_masters_cs,
        count_top_phd_acceptances_2026_llm,
        count_top_phd_acceptances_2026_raw_university,
        percent_international_students,
    )
except ImportError:  # fallback when run as a script
    from query_data import (
        acceptance_rate_fall_2026,
        additional_question_1,
        additional_question_2,
        avg_gpa_acceptances_fall_2026,
        avg_gpa_american_fall_2026,
        average_metrics_all_applicants,
        count_fall_2026_entries,
        count_jhu_masters_cs,
        count_top_phd_acceptances_2026_llm,
        count_top_phd_acceptances_2026_raw_university,
        percent_international_students,
    )


def main():
    """Print the dashboard answers without starting the Flask app."""
    # Question 1
    fall_2026_count = count_fall_2026_entries(True)
    print(f"There are {fall_2026_count} application entries in the 2026 cohort.")

    # Question 2
    intl_percent = percent_international_students(True)
    print(
        f"{intl_percent}% of all applications were submitted by international students."
    )

    # Question 3
    metrics = average_metrics_all_applicants(True)
    print(
        f"Among applicants who reported these metrics, the average GPA is {metrics['avg_gpa']}, "
        f"the average GRE Quant score is {metrics['avg_gre']}, "
        f"the average GRE Verbal score is {metrics['avg_gre_v']}, "
        f"and the average GRE Analytical Writing score is {metrics['avg_gre_aw']}."
    )

    # Question 4
    avg_gpa_amer = avg_gpa_american_fall_2026(True)
    print(
        f"American applicants in the 2026 cohort have an average GPA of {avg_gpa_amer}."
    )

    # Question 5
    accept_pct_2026 = acceptance_rate_fall_2026(True)
    print(
        f"{accept_pct_2026}% of 2026 cohort applications resulted in acceptances."
    )

    # Question 6
    avg_gpa_accepted = avg_gpa_acceptances_fall_2026(True)
    print(
        "Accepted applicants in the 2026 cohort have an average GPA of "
        f"{avg_gpa_accepted}."
    )

    # Question 7
    jhu_cs_ms = count_jhu_masters_cs(True)
    print(
        "There are "
        f"{jhu_cs_ms} application entries from students who applied to "
        "Johns Hopkins University for a master’s degree in Computer Science."
    )

    # Question 8 (raw university names)
    raw_phd_cs = count_top_phd_acceptances_2026_raw_university(True)
    print(
        f"Using the raw university names, there are {raw_phd_cs} accepted PhD "
        "Computer Science applications in the 2026 cohort from Georgetown University, "
        "MIT, Stanford University, or Carnegie Mellon University."
    )

    # Question 9 (LLM-generated university names)
    llm_phd_cs = count_top_phd_acceptances_2026_llm(True)
    print(
        f"When using the LLM-generated university field, this number changes to "
        f"{llm_phd_cs}, suggesting improved recognition of universities with "
        f"inconsistent or acronym-based names."
    )

    # Additional Question 1
    print("\nAdditional Question 1 Result:")
    print(f"  {additional_question_1(True)}")

    # Additional Question 2
    print("\nAdditional Question 2 Result:")
    print(f"  {additional_question_2(True)}")


if __name__ == "__main__":
    main()
