"""
Generate a lightweight PDF report for Module 3 analytics.

This file converts computed stats into a simple multi-page PDF without
external dependencies. It is regenerated on "Update Analysis".
"""

import os
from datetime import datetime


def _sanitize(text):
    """Keep ASCII-only text for simple PDF encoding."""
    if text is None:
        return ""
    # Keep ASCII only for simple PDF encoding
    return "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in str(text))


def _wrap(text, width=90):
    """Word-wrap a string into fixed-width lines."""
    text = _sanitize(text)
    if len(text) <= width:
        return [text]
    words = text.split()
    lines = []
    cur = []
    count = 0
    for w in words:
        if count + len(w) + (1 if cur else 0) > width:
            lines.append(" ".join(cur))
            cur = [w]
            count = len(w)
        else:
            cur.append(w)
            count += len(w) + (1 if cur else 0)
    if cur:
        lines.append(" ".join(cur))
    return lines


def _escape_pdf(text):
    """Escape PDF control characters."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_simple_pdf(lines, path):
    """Write a minimal PDF from a list of lines."""
    # Basic PDF with Helvetica, multi-page support
    page_width = 612
    page_height = 792
    left_margin = 72
    top_margin = 720
    line_height = 14

    pages = []
    current = []
    y = top_margin
    for line in lines:
        if y < 72:
            pages.append(current)
            current = []
            y = top_margin
        current.append(line)
        y -= line_height
    if current:
        pages.append(current)

    # 1-based object indexing
    objects = [None]

    def add_obj(obj_str):
        objects.append(obj_str)
        return len(objects) - 1

    font_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_id = add_obj("<< /Type /Pages /Kids [] /Count 0 >>")  # placeholder

    page_ids = []
    for page_lines in pages:
        content = "BT\n/F1 10 Tf\n{0} {1} Td\n{2} TL\n".format(left_margin, top_margin, line_height)
        for line in page_lines:
            content += "({0}) Tj\nT*\n".format(_escape_pdf(line))
        content += "ET\n"
        content_bytes = content.encode("latin-1", "replace")
        content_id = add_obj(
            "<< /Length {0} >>\nstream\n{1}\nendstream".format(
                len(content_bytes), content_bytes.decode("latin-1", "replace")
            )
        )
        page_id = add_obj(
            "<< /Type /Page /Parent {0} 0 R /MediaBox [0 0 {1} {2}] "
            "/Contents {3} 0 R /Resources << /Font << /F1 {4} 0 R >> >> >>".format(
                pages_id, page_width, page_height, content_id, font_id
            )
        )
        page_ids.append(page_id)

    kids = " ".join([f"{pid} 0 R" for pid in page_ids])
    objects[pages_id] = "<< /Type /Pages /Kids [ {0} ] /Count {1} >>".format(kids, len(page_ids))

    catalog_id = add_obj(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    # Build xref
    pdf = "%PDF-1.4\n"
    offsets = [0]
    for i in range(1, len(objects)):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n{objects[i]}\nendobj\n"
    xref_pos = len(pdf)
    pdf += "xref\n0 {0}\n".format(len(objects))
    pdf += "0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n"
    pdf += "trailer\n<< /Size {0} /Root {1} 0 R >>\nstartxref\n{2}\n%%EOF\n".format(
        len(objects), catalog_id, xref_pos
    )

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(pdf.encode("latin-1", "replace"))


def generate_pdf_report(results, path):
    """Render results into a PDF and write it to disk."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    year_results = results.get("year_2026", {})
    all_results = results.get("all_time", {})
    lines = []
    lines.extend(_wrap("Module 3 Analysis Report"))
    lines.extend(_wrap(f"Generated: {now}"))
    lines.append("")

    def section(title):
        lines.append(title)
        lines.append("-" * len(title))

    section("Summary (Fall Term Added in 2026 + 2026 Acceptances)")
    items = [
        ("Applicants surveyed (all time)", results.get("total_applicants")),
        ("Fall term entries (2026)", year_results.get("fall_2026_count")),
        ("International share (2026 cohort)", year_results.get("percent_international")),
        ("Acceptance rate (2026 cohort)", year_results.get("acceptance_rate_fall_2026")),
        ("JHU MS in CS applicants (2026 cohort)", year_results.get("jhu_masters_cs")),
    ]
    for label, value in items:
        lines.extend(_wrap(f"{label}: {value}"))
    lines.append("")

    section("Applicant Metrics (2026 Cohort)")
    metrics = year_results.get("average_metrics") or {}
    lines.extend(_wrap(f"Average GPA: {metrics.get('avg_gpa')}"))
    lines.extend(_wrap(f"Average GRE Quant: {metrics.get('avg_gre')}"))
    lines.extend(_wrap(f"Average GRE Verbal: {metrics.get('avg_gre_v')}"))
    lines.extend(_wrap(f"Average GRE Analytical Writing: {metrics.get('avg_gre_aw')}"))
    lines.extend(_wrap(f"Average GPA (American, 2026 cohort): {year_results.get('avg_gpa_american_fall_2026')}"))
    lines.extend(_wrap(f"Average GPA (Acceptances, 2026 cohort): {year_results.get('avg_gpa_acceptances_fall_2026')}"))
    lines.append("")

    section("Top PhD CS Acceptances (2026 Cohort)")
    lines.extend(_wrap(f"Raw university names: {year_results.get('top_phd_acceptances_2026_raw')}"))
    lines.extend(_wrap(f"LLM-generated names: {year_results.get('top_phd_acceptances_2026_llm')}"))
    lines.append("")

    section("Additional Insights (2026 Cohort)")
    lines.extend(_wrap(f"Percent reporting GPA: {year_results.get('additional_question_1')}%"))
    lines.extend(_wrap(f"Avg GRE (International): {year_results.get('additional_question_2')}"))
    lines.append("")

    section("Summary (All Entries)")
    items = [
        ("Total entries", all_results.get("total_entries")),
        ("International share (all entries)", all_results.get("percent_international")),
        ("Acceptance rate (all entries)", all_results.get("acceptance_rate_fall_2026")),
        ("JHU MS in CS applicants (all entries)", all_results.get("jhu_masters_cs")),
    ]
    for label, value in items:
        lines.extend(_wrap(f"{label}: {value}"))
    lines.append("")

    section("Applicant Metrics (All Entries)")
    metrics = all_results.get("average_metrics") or {}
    lines.extend(_wrap(f"Average GPA: {metrics.get('avg_gpa')}"))
    lines.extend(_wrap(f"Average GRE Quant: {metrics.get('avg_gre')}"))
    lines.extend(_wrap(f"Average GRE Verbal: {metrics.get('avg_gre_v')}"))
    lines.extend(_wrap(f"Average GRE Analytical Writing: {metrics.get('avg_gre_aw')}"))
    lines.extend(_wrap(f"Average GPA (American): {all_results.get('avg_gpa_american_fall_2026')}"))
    lines.extend(_wrap(f"Average GPA (Acceptances): {all_results.get('avg_gpa_acceptances_fall_2026')}"))
    lines.append("")

    section("Top PhD CS Acceptances (All Entries)")
    lines.extend(_wrap(f"Raw university names: {all_results.get('top_phd_acceptances_2026_raw')}"))
    lines.extend(_wrap(f"LLM-generated names: {all_results.get('top_phd_acceptances_2026_llm')}"))
    lines.append("")

    section("Additional Insights (All Entries)")
    lines.extend(_wrap(f"Percent reporting GPA: {all_results.get('additional_question_1')}%"))
    lines.extend(_wrap(f"Avg GRE (International): {all_results.get('additional_question_2')}"))
    lines.append("")

    section("Query Descriptions")
    queries = [
        {
            "title": "Applicants surveyed (all entries)",
            "query": "SELECT COUNT(*) FROM applicants;",
            "why": "Counts the total number of applicant entries used for the analysis."
        },
        {
            "title": "2026 cohort (Fall term entries + 2026 acceptances)",
            "query": "SELECT COUNT(*) FROM applicants WHERE (term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31');",
            "why": "Counts Fall-term entries added in 2026 plus accepted applicants notified in 2026."
        },
        {
            "title": "International share (2026 cohort)",
            "query": "SELECT COUNT(*) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND us_or_international NOT IN ('American','Other'); "
                     "SELECT COUNT(*) FROM applicants WHERE (term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31');",
            "why": "Computes the share of international applicants in the 2026 cohort."
        },
        {
            "title": "Average metrics (2026 cohort)",
            "query": "SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND (gpa IS NOT NULL OR gre IS NOT NULL OR gre_v IS NOT NULL OR gre_aw IS NOT NULL);",
            "why": "Calculates average GPA and GRE metrics for the 2026 cohort."
        },
        {
            "title": "Average GPA (American, 2026 cohort)",
            "query": "SELECT AVG(gpa) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND us_or_international='American' AND gpa IS NOT NULL;",
            "why": "Finds the average GPA for American applicants in the 2026 cohort."
        },
        {
            "title": "Acceptance rate (2026 cohort)",
            "query": "SELECT COUNT(*) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND status ILIKE 'accept%'; "
                     "SELECT COUNT(*) FROM applicants WHERE (term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31');",
            "why": "Divides accepted applicants by total applicants in the 2026 cohort."
        },
        {
            "title": "Average GPA (Acceptances, 2026 cohort)",
            "query": "SELECT AVG(gpa) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND status ILIKE 'accept%' AND gpa IS NOT NULL;",
            "why": "Averages GPA among accepted applicants in the 2026 cohort."
        },
        {
            "title": "JHU MS in CS applicants (2026 cohort)",
            "query": "SELECT COUNT(*) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND degree ILIKE '%Master%' AND llm_generated_program ILIKE '%Computer Science%' AND (llm_generated_university ILIKE ANY(ARRAY['%Johns Hopkins University%','%Johns Hopkins Univ%','%John Hopkins%','%Johns Hopkins%','%John Hopkins University%','%Johns Hopkins Univeristy%','%JHU%']) OR program ILIKE ANY(ARRAY['%Johns Hopkins University%','%Johns Hopkins Univ%','%John Hopkins%','%Johns Hopkins%','%John Hopkins University%','%Johns Hopkins Univeristy%','%JHU%']));",
            "why": "Counts JHU master's in CS applicants in the 2026 cohort, including common name variants."
        },
        {
            "title": "Top PhD CS acceptances (raw university, 2026 cohort)",
            "query": "SELECT COUNT(*) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND status ILIKE 'accept%' AND degree ILIKE '%PhD%' AND llm_generated_program ILIKE '%Computer Science%' AND program ILIKE ANY(ARRAY['%Georgetown University%','%MIT%','%Stanford University%','%Carnegie Mellon University%']);",
            "why": "Counts accepted PhD CS applicants in the 2026 cohort using raw university names in program."
        },
        {
            "title": "Top PhD CS acceptances (LLM university, 2026 cohort)",
            "query": "SELECT COUNT(*) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND status ILIKE 'accept%' AND degree ILIKE '%PhD%' AND llm_generated_program ILIKE '%Computer Science%' AND llm_generated_university IN ('Georgetown University','MIT','Stanford University','Carnegie Mellon University');",
            "why": "Counts accepted PhD CS applicants in the 2026 cohort using LLM-normalized university names."
        },
        {
            "title": "Additional Q1 (Percent reporting GPA, 2026 cohort)",
            "query": "SELECT COUNT(*) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND gpa IS NOT NULL; "
                     "SELECT COUNT(*) FROM applicants WHERE (term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31');",
            "why": "Computes what percent of the 2026 cohort reported a GPA."
        },
        {
            "title": "Additional Q2 (Avg GRE, International, 2026 cohort)",
            "query": "SELECT AVG(gre) FROM applicants WHERE ((term ILIKE 'Fall' AND date_added BETWEEN '2026-01-01' AND '2026-12-31') OR (status ILIKE 'accept%' AND COALESCE(acceptance_date, date_added) BETWEEN '2026-01-01' AND '2026-12-31')) AND us_or_international NOT IN ('American','Other') AND gre IS NOT NULL;",
            "why": "Computes the average GRE Quant for international applicants in the 2026 cohort."
        },
        {
            "title": "All entries: Total applicants",
            "query": "SELECT COUNT(*) FROM applicants;",
            "why": "Counts all applicants in the database."
        },
        {
            "title": "All entries: International share",
            "query": "SELECT COUNT(*) FROM applicants WHERE us_or_international NOT IN ('American','Other'); SELECT COUNT(*) FROM applicants;",
            "why": "Computes international share across all records."
        },
        {
            "title": "All entries: Acceptance rate",
            "query": "SELECT COUNT(*) FROM applicants WHERE status ILIKE 'accept%'; SELECT COUNT(*) FROM applicants;",
            "why": "Acceptance rate across all records."
        },
        {
            "title": "All entries: JHU MS in CS applicants",
            "query": "SELECT COUNT(*) FROM applicants WHERE degree ILIKE '%Master%' AND llm_generated_program ILIKE '%Computer Science%' AND (llm_generated_university ILIKE ANY(ARRAY['%Johns Hopkins University%','%Johns Hopkins Univ%','%John Hopkins%','%Johns Hopkins%','%John Hopkins University%','%Johns Hopkins Univeristy%','%JHU%']) OR program ILIKE ANY(ARRAY['%Johns Hopkins University%','%Johns Hopkins Univ%','%John Hopkins%','%Johns Hopkins%','%John Hopkins University%','%Johns Hopkins Univeristy%','%JHU%']));",
            "why": "Counts applicants who applied to JHU for a master's in CS across all records, including common name variants."
        },
        {
            "title": "All entries: Average metrics",
            "query": "SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants WHERE gpa IS NOT NULL OR gre IS NOT NULL OR gre_v IS NOT NULL OR gre_aw IS NOT NULL;",
            "why": "Average metrics across all records."
        },
        {
            "title": "All entries: Top PhD CS acceptances (raw university)",
            "query": "SELECT COUNT(*) FROM applicants WHERE status ILIKE 'accept%' AND degree ILIKE '%PhD%' AND llm_generated_program ILIKE '%Computer Science%' AND program ILIKE ANY(ARRAY['%Georgetown University%','%MIT%','%Stanford University%','%Carnegie Mellon University%']);",
            "why": "Accepted PhD CS applicants across all records using raw university names in program."
        },
        {
            "title": "All entries: Top PhD CS acceptances (LLM university)",
            "query": "SELECT COUNT(*) FROM applicants WHERE status ILIKE 'accept%' AND degree ILIKE '%PhD%' AND llm_generated_program ILIKE '%Computer Science%' AND llm_generated_university IN ('Georgetown University','MIT','Stanford University','Carnegie Mellon University');",
            "why": "Accepted PhD CS applicants across all records using LLM university."
        },
        {
            "title": "All entries: Additional Q1 (Percent reporting GPA)",
            "query": "SELECT COUNT(*) FROM applicants WHERE gpa IS NOT NULL; SELECT COUNT(*) FROM applicants;",
            "why": "Percent of applicants with GPA across all records."
        },
        {
            "title": "All entries: Additional Q2 (Avg GRE, International)",
            "query": "SELECT AVG(gre) FROM applicants WHERE us_or_international NOT IN ('American','Other') AND gre IS NOT NULL;",
            "why": "Average GRE Quant for international applicants across all records."
        },
    ]

    for q in queries:
        lines.append("")
        lines.extend(_wrap(q["title"]))
        lines.extend(_wrap(f"Query: {q['query']}"))
        lines.extend(_wrap(f"Why: {q['why']}"))

    _write_simple_pdf(lines, path)
