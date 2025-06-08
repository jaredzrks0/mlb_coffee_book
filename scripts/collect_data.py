from mlb_coffee_book import TranscriptScraper

if __name__ == "__main__":
    scraper = TranscriptScraper(start_date="2023-05-01", end_date="2023-05-01")

    scraper.build_and_save_transcripts()
