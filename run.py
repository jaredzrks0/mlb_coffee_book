from mlb_coffee_book import TranscriptScraper, DatasetBuilder
from datetime import datetime

import argparse

def main(start_date, end_date, do_scrape):
    if do_scrape:
        scraper = TranscriptScraper(start_date=start_date, end_date=end_date)
        scraper.build_and_save_transcripts()

    dataset_builder = DatasetBuilder()
    dataset, files = dataset_builder.build_dataset()

    return dataset, files

if __name__ == '__main__':
    today_str = datetime.today().strftime('%m-%d-%Y')

    parser = argparse.ArgumentParser(description='Build MLB dataset with optional scraping.')
    parser.add_argument('--start-date', type=str, default=today_str, help='Start date in MM-DD-YYYY format (default: today)')
    parser.add_argument('--end-date', type=str, default=today_str, help='End date in MM-DD-YYYY format (default: today)')
    parser.add_argument('--scrape', action='store_true', help='Include this flag to scrape transcripts')

    args = parser.parse_args()
    dataset, files = main(start_date=args.start_date, end_date=args.end_date, do_scrape=args.scrape)





