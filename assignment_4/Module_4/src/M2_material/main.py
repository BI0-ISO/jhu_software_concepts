"""
Standalone scraper runner (Module 2 legacy).

This script scrapes a large range of GradCafe IDs and writes a JSON snapshot.
It is not used by the web app, but it is kept as a bulk-scrape utility.
"""
try:
    from .scrape import scrape_data
    from .clean import clean_data, save_data
except ImportError:  # fallback when run as a script
    from scrape import scrape_data
    from clean import clean_data, save_data

# Run configuration for bulk scraping.
START_ENTRY = 950000
TOTAL_VALID_ENTRIES = 50000
CHUNK_SIZE = 5000
END_ENTRY = 1000000
OUTPUT_FILE = "applicant_data.json"

def main():
    print(f"Starting scraping from entry {START_ENTRY}...")

    all_cleaned_data = []
    valid_entries_collected = 0

    # Iterate the GradCafe result IDs and clean each page.
    scraper = scrape_data(START_ENTRY, END_ENTRY)

    for page in scraper:
        entry_id = page["url"].split("/")[-1]

        # Clean the HTML into a structured record.
        cleaned = clean_data([page])[0]
        all_cleaned_data.append(cleaned)
        valid_entries_collected += 1

        # Live terminal update
        print(f"Current entry ID: {entry_id} | Valid entries collected: {valid_entries_collected}")

        # Auto-save every CHUNK_SIZE valid entries to avoid data loss.
        if valid_entries_collected % CHUNK_SIZE == 0:
            print(f"\nAuto-saving data to {OUTPUT_FILE}...")
            save_data(all_cleaned_data, OUTPUT_FILE)
            print("Data saved.\n")

        if valid_entries_collected >= TOTAL_VALID_ENTRIES:
            break

    # Final save
    save_data(all_cleaned_data, OUTPUT_FILE)
    print(f"\nScraping complete! Total valid entries collected: {len(all_cleaned_data)}")
    print(f"Final data saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
