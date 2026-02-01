# main.py
from scrape import scrape_data
from clean import clean_data, save_data


def main():
    """
    Orchestrates the GradCafe scraping and cleaning pipeline.
    """

    # ----- CONFIGURATION -----
    START_ENTRY = 800000
    END_ENTRY = 900000      # 30,000 entry window
    OUTPUT_FILE = "applicant_data.json"
    # -------------------------

    print("Starting GradCafe scrape...")
    raw_pages = scrape_data(START_ENTRY, END_ENTRY)
    print(f"Scraped {len(raw_pages)} valid applicant pages")

    print("Cleaning and structuring data...")
    cleaned_data = clean_data(raw_pages)

    print("Saving data to JSON...")
    save_data(cleaned_data, OUTPUT_FILE)

    print(f"Pipeline complete. Data saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
