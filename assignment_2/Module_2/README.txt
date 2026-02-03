
README.txt

<<<<<<< HEAD
<<<<<<< HEAD
Name: [Your Name]  
JHED ID: [Your JHED ID]

Module Info:  
Module: [Module Name/Number]  
Assignment: GradCafe Data Scraper and Cleaner  
Due Date: [Assignment Due Date]
=======
=======
>>>>>>> b218d296dd78c67a7242a850a77cdb87c4de2a2e
Name: Samuel McKey  
JHED ID: DDF40C

Module Info:  
Module: Module 2
Assignment: GradCafe Data Scraper and Cleaner  
Due Date: 2-1-26
<<<<<<< HEAD
>>>>>>> b218d296dd78c67a7242a850a77cdb87c4de2a2e
=======
>>>>>>> b218d296dd78c67a7242a850a77cdb87c4de2a2e

---

Approach:

This project is designed to scrape applicant data from GradCafe, clean and structure it, and save it in a JSON format. The workflow is organized into three main scripts: `scrape.py`, `clean.py`, and `main.py`.

1. scrape.py
-------------
Purpose: Collect raw HTML pages from GradCafe applicant entries.

- Uses `urllib3.PoolManager` with a custom User-Agent to mimic a browser and send HTTP GET requests.
- Iterates over a range of entry numbers provided by the user (`start_entry` to `end_entry`).
- For each entry:
  - Constructs the URL in the format: `https://www.thegradcafe.com/result/{entry_id}`.
  - Sends an HTTP request and decodes the HTML.
  - Parses the HTML using `BeautifulSoup` to extract the text content.
  - Performs validation:
    - Skips entries with HTTP status not equal to 200.
    - Skips invalid entries that contain the placeholder date `31/12/1969`.
- Collects valid pages into a list of dictionaries with the structure: `{"url": <entry_url>, "html": <raw_html>}`.
- Returns this list to be processed by the cleaning script.

Notes:
- Optional polite scraping delay (`time.sleep`) is commented out but can be enabled to reduce server load.
- Exceptions during HTTP requests are caught and logged to prevent the pipeline from crashing.

2. clean.py
------------
Purpose: Transform raw HTML pages into structured applicant data.

- Defines the `clean_data(raw_pages)` function, which iterates over the raw HTML pages:
  - Uses `BeautifulSoup` to parse each page and extract plain text.
  - Extracts the following fields using regex and helper functions:
    - `program`, `university`, `comments`, `date_added` (notification date)
    - Applicant status: normalized into `"accepted"`, `"rejected"`, or `"waitlisted"`.
    - `acceptance_date`, `rejection_date`
    - Program metadata: `degree_type`, `start_term`, `start_year`
    - `citizenship` (International/American)
    - GRE scores: `gre_total`, `gre_verbal`, `gre_aw`
    - `gpa` (robustly handles missing or invalid entries)
- Helper functions:
  - `_extract()`: General regex extractor.
  - `_extract_notes()`: Extracts notes from the text before the "Timeline" section.
  - `_extract_degree_type()`: Parses degree type between "Type" and "Degree".
  - `_extract_gpa()`: Extracts undergrad GPA while handling `NONE`, `0`, or malformed text.
  - `_none_if_zero()`: Converts zero values to `None`.
  - `_normalize_decision()`: Converts textual decision into standard labels.
- `save_data(data, filename)`: Saves cleaned data to a JSON file.
- `load_data(filename)`: Loads JSON data for future use.

3. main.py
-----------
Purpose: Orchestrate the full pipeline from scraping to cleaned JSON output.

- Configurable variables:
  - `START_ENTRY` and `END_ENTRY`: Define the range of GradCafe entries to scrape.
  - `OUTPUT_FILE`: Filename to save cleaned data.
- Steps:
  1. Call `scrape_data` to gather raw pages.
  2. Pass raw pages to `clean_data` to extract structured fields.
  3. Save the cleaned data to JSON using `save_data`.
- Outputs informative print statements to track progress and completion.

---

How to Run:

1. Ensure all dependencies are installed:
2. Make sure all three scripts (`main.py`, `scrape.py`, `clean.py`) are in the same directory.
3. Run the pipeline:
4. The pipeline will:
- Scrape pages from the configured entry range.
- Clean and structure the data.
- Save results to `applicant_data.json`.

---

Known Bugs:

- Polite scraping delay is disabled; running a large range of entries quickly may overload GradCafe or trigger rate-limiting.
- Some unusual or malformed GradCafe entries may not be captured properly (e.g., entries missing expected fields entirely).
- GPA extraction relies on the text being between "Undergrad GPA" and "GRE General"; if GradCafe changes formatting, GPA may fail to parse.
- Timeouts or connection issues may skip entries silently, though errors are printed to console.
- For very large ranges (30,000+ entries), scraping may take a long time and could benefit from batching or asynchronous requests.
- If the applicant used emojis in their notes, the emoji to text translation was not removed. Plan is to remove this later if comments will be used for future coding assignments 

---

The instructor provided code was used to further clean the data: 

The following steps were used: 

1. Add the zipped files Download zipped files to your repository area as a sub-package, i.e., module_2/llm_hosting
2. Enter the subfolder
3. pip install -r requirements.txt
3. Run python app.py --file applicant_data.json --stdout > full_out.json

During evaluation of the data cleaning pipeline, it was observed that the automated cleaning process occasionally produces incorrect or inconsistent outputs. Specific issues include:

- The `university` field is not always correctly extracted; some entries may be missing or misattributed.
- These issues highlight limitations of the current regex-based approach and the need for additional normalization or verification steps to ensure data accuracy.

Edits made to improve LLM code: 

Overview
--------
This version of app.py includes improvements to how program and university names are standardized
using a local LLM. The main goal was to reduce incorrect university outputs and improve canonical
matching for programs and universities.

1. Improved Post-Processing of Universities
------------------------------------------
- Expanded abbreviation handling:
    - Ensures common short forms like 'McG', 'UBC', 'uoft' are correctly mapped to full university names.
    - Added stricter regex and full string match to avoid accidental misclassification.
- Canonical/fuzzy matching:
    - Prioritizes exact matches from canon_universities.txt.
    - Uses fuzzy matching with a safe cutoff if no exact match is found.
    - Returns "Unknown" if no reasonable match is found.
- Capitalization and spelling fixes:
    - Normalizes "Of" → "of" in university names.
    - Applies common spelling corrections (e.g., McGiill → McGill).

2. Improved Program Name Post-Processing
----------------------------------------
- Common program fixes:
    - Corrects partial or misspelled programs (e.g., Mathematic → Mathematics).
- Title-case normalization:
    - Ensures all program names follow standard capitalization.
- Fuzzy mapping to canonical list:
    - Matches against canon_programs.txt for standardization.

3. Fallback Parsing Enhancements
--------------------------------
- _split_fallback() now better handles:
    - Inputs that are not valid JSON.
    - Inputs without commas or "at" separators.
    - High-confidence expansions for well-known abbreviations.

4. LLM Prompt Improvements
--------------------------
- SYSTEM_PROMPT updated to explicitly emphasize:
    - Correct university spelling and capitalization.
    - Returning "Unknown" if university cannot be inferred.
    - Clear JSON output format.
- Few-shot examples updated to include abbreviations and partial names for better model guidance.

5. CLI and API Output
---------------------
- Output keys remain:
    - llm-generated-program
    - llm-generated-university
- LLM-generated values now pass through stricter post-normalization before being returned.

6. Notes on Running on Apple M3 Pro
------------------------------------
- For safe GPU usage, do NOT set N_GPU_LAYERS to 20. Recommended safe values:
    export N_GPU_LAYERS=6
    export N_THREADS=20
    python llm_hosting/app.py --file applicant_data.json --out llm_extend_applicant_data.json
- Using too many GPU layers may crash the model due to GPU memory limits.

Summary
-------
These changes improve the accuracy, stability, and consistency of university and program
standardization:
- Fewer misclassified universities.
- Better handling of abbreviations and misspellings.
- Safer and more reliable LLM output processing.

---

Requirement Compliance Explanation:

This section maps the assignment requirements to how they are satisfied in the project:

1. Programmatically pull data from GradCafe using Python  
- `scrape.py` uses `urllib3` to retrieve HTML pages.

2. Use only libraries covered in Module 2  
- Uses `urllib3`, `json`, `re`, `BeautifulSoup`.

3. Data categories pulled include:  
- Program Name, University, Comments, Date Added, URL, Applicant Status, Acceptance/Rejection Dates, Semester & Year, International/American, GRE Scores, Masters/PhD, GPA.  
- All extracted via regex and/or BeautifulSoup.  

4. Use urllib for URL management  
- `urllib3` handles HTTP requests.  

5. Store data in JSON as `applicant_data.json`  
- `save_data()` writes structured JSON.

6. Include at least 30,000 entries  
- Pipeline supports large ranges; `main.py` can be configured to reach 30,000+.  

7. Include a README  
- This file.  

8. Be on GitHub in `jhu_software_concepts/assignment_2/module_2`  
- Repository structure assumed.  

9. Comply with robots.txt (screenshot evidence)  
- Mentioned in README; screenshot.jpg included in folder.  

10. Include `requirements.txt`  
 - Should include `beautifulsoup4` and `urllib3`.

11. Python 3.10+  
 - All code compatible with Python 3.10+.

12. Clean data as specified  
 - `clean.py` removes HTML, normalizes missing data, extracts all fields.

13. Use BeautifulSoup/string/regex for extraction  
 - All extraction done via regex & BeautifulSoup.

14. Functions as required: `scrape_data()`, `clean_data()`, `save_data()`, `load_data()`  
 - All implemented; private helpers use `_` prefix.

15. Scraping under `scrape.py` / cleaning under `clean.py`  
 - Satisfied.

16. No remnant HTML  
 - `BeautifulSoup.get_text()` used.

17. Unavailable data consistently as `None`  
 - `_none_if_zero()` and helper functions handle this.

18. Remove unexpected/messy info  
 - Regex and helper methods sanitize data.

19. Accurate information  
 - Mostly accurate; edge cases noted in Instructor Notes.

20. Well-commented, clear variables  
 - Docstrings and comments present; variable names descriptive.

21. Do not use methods outside BeautifulSoup/string/regex  
 -  All extraction uses compliant methods.

---

Robot.txt information: 

# As a condition of accessing this website, you agree to abide by the following
# content signals:

# (a)  If a Content-Signal = yes, you may collect content for the corresponding
#      use.
# (b)  If a Content-Signal = no, you may not collect content for the
#      corresponding use.
# (c)  If the website operator does not include a Content-Signal for a
#      corresponding use, the website operator neither grants nor restricts
#      permission via Content-Signal with respect to the corresponding use.

# The content signals and their meanings are:

# search:   building a search index and providing search results (e.g., returning
#           hyperlinks and short excerpts from your website's contents). Search does not
#           include providing AI-generated search summaries.
# ai-input: inputting content into one or more AI models (e.g., retrieval
#           augmented generation, grounding, or other real-time taking of content for
#           generative AI search answers).
# ai-train: training or fine-tuning AI models.

# ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF
# RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790 ON COPYRIGHT
# AND RELATED RIGHTS IN THE DIGITAL SINGLE MARKET.

# BEGIN Cloudflare Managed content

User-agent: *
Content-Signal: search=yes,ai-train=no
Allow: /

User-agent: Amazonbot
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: GPTBot
Disallow: /

User-agent: meta-externalagent
Disallow: /

# END Cloudflare Managed Content

User-agent: *
Disallow: /cgi-bin/
Disallow: /index-ad-test.php

User-agent: ia_archiver
Disallow: /

User-agent: ia_archiver/1.6
Disallow: /

User-Agent: sitecheck.internetseer.com
Disallow: /

User-agent: Computer_and_Automation_Research_Institute_Crawler
Disallow: /

User-agent: dotbot
Disallow: /

User-agent: YandexBot
Disallow: /

User-agent: Mediapartners-Google
Disallow:

User-agent: Opebot-v (https://www.1plusx.com (https://www.1plusx.com/)) 
<<<<<<< HEAD
<<<<<<< HEAD
Allow: /
=======
Allow: /
>>>>>>> b218d296dd78c67a7242a850a77cdb87c4de2a2e
=======
Allow: /
>>>>>>> b218d296dd78c67a7242a850a77cdb87c4de2a2e
