# main.py

# Import the scraping function from scrape.py
from scrape import scrape_data

# Import the cleaning and saving functions from clean.py
from clean import clean_data, save_data


def main():
    """
    Main function to orchestrate the GradCafe data pipeline.

    Steps:
        1. Scrape raw applicant HTML pages from GradCafe.
        2. Clean and structure the scraped data.
        3. Save the cleaned data as a JSON file.

    Notes:
        - Configuration variables define the range of GradCafe entry IDs
          and output filename.
        - Prints progress updates to the console.
    """

    # ----- CONFIGURATION -----
    START_ENTRY = 950000       # Starting GradCafe entry ID to scrape
    END_ENTRY = 994305         # Ending GradCafe entry ID (exclusive) for ~30,000 entries
    OUTPUT_FILE = "applicant_data.json"  # JSON file to save cleaned data
    # -------------------------

    # Step 1: Scrape raw applicant pages
    print("Starting GradCafe scrape...")
    raw_pages = scrape_data(START_ENTRY, END_ENTRY)  # Returns list of dicts with 'url' and 'html'

    # Print the number of valid pages successfully scraped
    print(f"Scraped {len(raw_pages)} valid applicant pages")

    # Step 2: Clean and structure the raw HTML data
    print("Cleaning and structuring data...")
    cleaned_data = clean_data(raw_pages)  # Returns a list of structured applicant records

    # Step 3: Save the structured data to a JSON file
    print("Saving data to JSON...")
    save_data(cleaned_data, OUTPUT_FILE)

    # Final confirmation message
    print(f"Pipeline complete. Data saved to {OUTPUT_FILE}")


# Standard Python entry point
# Ensures that main() runs only when this script is executed directly,
# not when it is imported as a module
if __name__ == "__main__":
    main()
