# main.py
from crawler import scrape_data
from cleaner import clean_data, save_data

def main():
    # Step 1: scrape raw HTML
    raw_pages = scrape_data(900000, 900100)

    print(f"Scraped {len(raw_pages)} pages")

    # Step 2: clean and structure data
    cleaned_data = clean_data(raw_pages)

    # Step 3: save to JSON
    save_data(cleaned_data)

    print("Data saved to applicant_data.json")

if __name__ == "__main__":
    main()
