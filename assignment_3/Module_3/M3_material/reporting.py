import os
from datetime import datetime


def _sanitize(text):
    if text is None:
        return ""
    # Keep ASCII only for simple PDF encoding
    return "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in str(text))


def _wrap(text, width=90):
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
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_simple_pdf(lines, path):
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
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.extend(_wrap("Module 3 Analysis Report"))
    lines.extend(_wrap(f"Generated: {now}"))
    lines.append("")

    def section(title):
        lines.append(title)
        lines.append("-" * len(title))

    section("Snapshot")
    items = [
        ("Applicants surveyed", results.get("total_applicants")),
        ("Fall 2026 entries", results.get("fall_2026_count")),
        ("International share (%)", results.get("percent_international")),
        ("Acceptance rate Fall 2026 (%)", results.get("acceptance_rate_fall_2026")),
        ("JHU MS in CS applicants", results.get("jhu_masters_cs")),
    ]
    for label, value in items:
        lines.extend(_wrap(f"{label}: {value}"))
    lines.append("")

    section("Applicant Metrics")
    metrics = results.get("average_metrics") or {}
    lines.extend(_wrap(f"Average GPA: {metrics.get('avg_gpa')}"))
    lines.extend(_wrap(f"Average GRE Quant: {metrics.get('avg_gre')}"))
    lines.extend(_wrap(f"Average GRE Verbal: {metrics.get('avg_gre_v')}"))
    lines.extend(_wrap(f"Average GRE Analytical Writing: {metrics.get('avg_gre_aw')}"))
    lines.extend(_wrap(f"Average GPA (American, Fall 2026): {results.get('avg_gpa_american_fall_2026')}"))
    lines.extend(_wrap(f"Average GPA (Acceptances, Fall 2026): {results.get('avg_gpa_acceptances_fall_2026')}"))
    lines.append("")

    section("Top PhD CS Acceptances (2026)")
    lines.extend(_wrap(f"Raw university names: {results.get('top_phd_acceptances_2026_raw')}"))
    lines.extend(_wrap(f"LLM-generated names: {results.get('top_phd_acceptances_2026_llm')}"))
    lines.append("")

    section("Additional Insights")
    lines.extend(_wrap(f"International count (Fall 2026): {results.get('additional_question_1')}"))
    lines.extend(_wrap(f"Avg GRE (PhD CS, Fall 2026): {results.get('additional_question_2')}"))
    lines.append("")

    section("Query Descriptions")
    queries = [
        {
            "title": "Applicants surveyed",
            "query": "SELECT COUNT(*) FROM applicants;",
            "why": "Counts the total number of applicant entries used for the analysis."
        },
        {
            "title": "Fall 2026 entries",
            "query": "SELECT COUNT(*) FROM applicants WHERE term = 'Fall' AND year = 2026;",
            "why": "Counts all applications for the Fall 2026 term."
        },
        {
            "title": "International share",
            "query": "SELECT COUNT(*) FROM applicants WHERE us_or_international NOT IN ('American','Other'); "
                     "SELECT COUNT(*) FROM applicants;",
            "why": "Computes the share of international applicants by dividing international count by total."
        },
        {
            "title": "Average metrics",
            "query": "SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants WHERE gpa IS NOT NULL OR gre IS NOT NULL OR gre_v IS NOT NULL OR gre_aw IS NOT NULL;",
            "why": "Calculates average GPA and GRE metrics for applicants who reported them."
        },
        {
            "title": "Average GPA (American, Fall 2026)",
            "query": "SELECT AVG(gpa) FROM applicants WHERE term='Fall' AND year=2026 AND us_or_international='American' AND gpa IS NOT NULL;",
            "why": "Finds the average GPA for American applicants in Fall 2026."
        },
        {
            "title": "Acceptance rate (Fall 2026)",
            "query": "SELECT COUNT(*) FROM applicants WHERE term='Fall' AND year=2026 AND status ILIKE 'accept%'; "
                     "SELECT COUNT(*) FROM applicants WHERE term='Fall' AND year=2026;",
            "why": "Divides the number of accepted applicants by total Fall 2026 applicants."
        },
        {
            "title": "Average GPA (Acceptances, Fall 2026)",
            "query": "SELECT AVG(gpa) FROM applicants WHERE term='Fall' AND year=2026 AND status ILIKE 'accept%' AND gpa IS NOT NULL;",
            "why": "Averages GPA among accepted applicants for Fall 2026."
        },
        {
            "title": "JHU MS in CS applicants",
            "query": "SELECT COUNT(*) FROM applicants WHERE llm_generated_university IN ('Johns Hopkins University','JHU') AND degree ILIKE '%Master%' AND llm_generated_program ILIKE '%Computer Science%';",
            "why": "Counts applicants who applied to JHU for a master's in CS using LLM-normalized fields."
        },
        {
            "title": "Top PhD CS acceptances (raw university)",
            "query": "SELECT COUNT(*) FROM applicants WHERE year=2026 AND status ILIKE 'accept%' AND llm_generated_program ILIKE '%PhD%' AND llm_generated_program ILIKE '%Computer Science%' AND university IN ('Georgetown University','MIT','Stanford University','Carnegie Mellon University');",
            "why": "Counts accepted PhD CS applicants to a set of top universities using the raw university field."
        },
        {
            "title": "Top PhD CS acceptances (LLM university)",
            "query": "SELECT COUNT(*) FROM applicants WHERE year=2026 AND status ILIKE 'accept%' AND llm_generated_program ILIKE '%PhD%' AND llm_generated_program ILIKE '%Computer Science%' AND llm_generated_university IN ('Georgetown University','MIT','Stanford University','Carnegie Mellon University');",
            "why": "Same as above, but uses LLM-normalized university names to handle inconsistencies."
        },
        {
            "title": "Additional Q1 (International count, Fall 2026)",
            "query": "SELECT COUNT(*) FROM applicants WHERE term='Fall' AND year=2026 AND us_or_international NOT IN ('American','Other');",
            "why": "Counts international applicants for Fall 2026."
        },
        {
            "title": "Additional Q2 (Avg GRE, PhD CS, Fall 2026)",
            "query": "SELECT AVG(gre) FROM applicants WHERE term='Fall' AND year=2026 AND llm_generated_program ILIKE '%PhD%' AND llm_generated_program ILIKE '%Computer Science%' AND gre IS NOT NULL;",
            "why": "Computes the average GRE Quant for Fall 2026 PhD CS applicants."
        },
    ]

    for q in queries:
        lines.append("")
        lines.extend(_wrap(q["title"]))
        lines.extend(_wrap(f"Query: {q['query']}"))
        lines.extend(_wrap(f"Why: {q['why']}"))

    _write_simple_pdf(lines, path)
