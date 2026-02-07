from flask import render_template
from datetime import datetime
from . import bp

# Import PostgreSQL query functions
from query_data import (
    count_fall_2026_entries,
    percent_international_students,
    average_metrics_all_applicants,
    average_gpa_american_fall_2026,
    percent_acceptances_fall_2026,
    avg_gpa_accepted_fall_2026,
    jhu_ms_cs_count,
    phd_cs_acceptances_2026_raw_university,
    phd_cs_acceptances_2026_llm_university,
    avg_gpa_by_citizenship,
    acceptance_rate_by_degree
)

@bp.route("/")
def home():
    return render_template("home.html")

@bp.route("/about")
def about():
    return render_template("about.html")

@bp.route("/projects")
def projects():
    return render_template("projects.html")

@bp.route("/projects/module-1")
def module_1_project():
    return render_template("project_module_1.html")

@bp.route("/projects/module-3")
def module_3_project():
    fall_2026_count = count_fall_2026_entries()
    intl_percent = percent_international_students()

    avg_gpa, avg_gre, avg_gre_v, avg_gre_aw = average_metrics_all_applicants()
    avg_amer_gpa = average_gpa_american_fall_2026()

    acceptance_pct = percent_acceptances_fall_2026()
    accepted_avg_gpa = avg_gpa_accepted_fall_2026()

    jhu_cs_ms = jhu_ms_cs_count()

    raw_phd_accepts = phd_cs_acceptances_2026_raw_university()
    llm_phd_accepts = phd_cs_acceptances_2026_llm_university()

    gpa_by_citizenship = avg_gpa_by_citizenship()
    acceptance_by_degree = acceptance_rate_by_degree()

    return render_template(
        "project_module_3.html",
        fall_2026_count=fall_2026_count,
        intl_percent=intl_percent,
        avg_gpa=avg_gpa,
        avg_gre=avg_gre,
        avg_gre_v=avg_gre_v,
        avg_gre_aw=avg_gre_aw,
        avg_amer_gpa=avg_amer_gpa,
        acceptance_pct=acceptance_pct,
        accepted_avg_gpa=accepted_avg_gpa,
        jhu_cs_ms=jhu_cs_ms,
        raw_phd_accepts=raw_phd_accepts,
        llm_phd_accepts=llm_phd_accepts,
        gpa_by_citizenship=gpa_by_citizenship,
        acceptance_by_degree=acceptance_by_degree
    )

@bp.app_context_processor
def inject_year():
    return {"current_year": datetime.now().year}
