from flask import render_template
from . import bp
from M3_material.query_data import (
    count_fall_2026_entries,
    percent_international_students,
    average_metrics_all_applicants,
    avg_gpa_american_fall_2026,
    acceptance_rate_fall_2026,
    avg_gpa_acceptances_fall_2026,
    count_jhu_masters_cs,
    count_top_phd_acceptances_2026_raw_university,
    count_top_phd_acceptances_2026_llm,
    additional_question_1,
    additional_question_2
)

@bp.route("/projects/module-3")
def module_3_project():
    results = {
        "fall_2026_count": count_fall_2026_entries(),
        "percent_international": percent_international_students(),
        "average_metrics": average_metrics_all_applicants(),
        "avg_gpa_american_fall_2026": avg_gpa_american_fall_2026(),
        "acceptance_rate_fall_2026": acceptance_rate_fall_2026(),
        "avg_gpa_acceptances_fall_2026": avg_gpa_acceptances_fall_2026(),
        "jhu_masters_cs": count_jhu_masters_cs(),
        "top_phd_acceptances_2026_raw": count_top_phd_acceptances_2026_raw_university(),
        "top_phd_acceptances_2026_llm": count_top_phd_acceptances_2026_llm(),
        "additional_question_1": additional_question_1(),
        "additional_question_2": additional_question_2(),
    }
    return render_template("project_module_3.html", results=results)
