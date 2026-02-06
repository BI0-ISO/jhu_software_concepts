from query_data import *

# Question 1
fall_2026_count = count_fall_2026_entries()
print(f"There are {fall_2026_count} application entries for Fall 2026.")

# Question 2
intl_percent = percent_international_students()
print(f"{intl_percent}% of all applications were submitted by international students.")

# Question 3
avg_gpa, avg_gre, avg_gre_v, avg_gre_aw = average_metrics_all_applicants()
print(
    f"Among applicants who reported these metrics, the average GPA is {avg_gpa}, "
    f"the average GRE Quant score is {avg_gre}, "
    f"the average GRE Verbal score is {avg_gre_v}, "
    f"and the average GRE Analytical Writing score is {avg_gre_aw}."
)

# Question 4
avg_gpa_amer = avg_gpa_american_fall_2026()
print(f"American applicants applying for Fall 2026 have an average GPA of {avg_gpa_amer}.")

# Question 5
accept_pct_2026 = percent_acceptances_fall_2026()
print(f"{accept_pct_2026}% of Fall 2026 applications resulted in acceptances.")

# Question 6
avg_gpa_accepted = avg_gpa_accepted_fall_2026()
print(f"Applicants accepted for Fall 2026 have an average GPA of {avg_gpa_accepted}.")

# Question 7
jhu_cs_ms = jhu_ms_cs_count()
print(
    f"There are {jhu_cs_ms} application entries from students who applied to "
    f"Johns Hopkins University for a master’s degree in Computer Science."
)

# Question 8 (raw university names)
raw_phd_cs = phd_cs_acceptances_2026_raw_university()
print(
    f"Using the raw university names, there are {raw_phd_cs} accepted PhD "
    f"Computer Science applications in Fall 2026 from Georgetown University, "
    f"MIT, Stanford University, or Carnegie Mellon University."
)

# Question 9 (LLM-generated university names)
llm_phd_cs = phd_cs_acceptances_2026_llm_university()
print(
    f"When using the LLM-generated university field, this number changes to "
    f"{llm_phd_cs}, suggesting improved recognition of universities with "
    f"inconsistent or acronym-based names."
)

# Additional Question 1
print("\nAverage GPA by citizenship status:")
for status, gpa in avg_gpa_by_citizenship():
    print(f"  {status}: {gpa}")

# Additional Question 2
print("\nAcceptance rates by degree type:")
for degree, rate in acceptance_rate_by_degree():
    print(f"  {degree}: {rate}%")
