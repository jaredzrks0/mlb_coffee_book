from selenium import webdriver
import chromedriver_autoinstaller
import subprocess
import json
import datetime
import os
import pickle as pkl

import pandas as pd
import configparser
import subprocess
import requests

import subprocess
import json


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
import time

from bs4 import BeautifulSoup


class TranscriptScraper():
    def __init__(self, start_date: str = '2022-04-01', end_date: str = datetime.datetime.today().strftime('%Y-%m-%d')):
        self.start_date = start_date
        self.end_date = end_date

        chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists
                                            # and if it doesn't exist, download it automatically,
                                            # then add chromedriver to path

        driver = webdriver.Chrome()
        driver.get("http://www.python.org")
        assert "Python" in driver.title

        # Load the config file
        config = configparser.ConfigParser()
        config.read('config.ini')

        # Access credentials        
        self.username = config['credentials']['username']
        self.password = config['credentials']['password']

        # Make a map for game codes to URLs
        map_path = 'data/game_code_map/map.pkl'

        if os.path.exists(map_path):
            # Read the existing map
            with open(map_path, 'rb') as f:
                self.game_code_map = pkl.load(f)
        else:
            # Ensure directory exists
            os.makedirs(os.path.dirname(map_path), exist_ok=True)

            # Save the new map
            game_code_map = {}
            with open(map_path, 'wb') as f:
                pkl.dump(game_code_map, f)
            self.game_code_map = game_code_map

    def build_and_save_transcripts(self):
        self._collect_daily_URLs()
        self._collect_game_URLs()


        for game_url in self.game_urls:
            best_home, best_away = self._get_best_broadcasts(game_url, self.username, self.password)
            time.sleep(2)
            self._download_video_and_subtitles(game_url, best_home, download_video=False)

            game_code = game_url.split('/')[4]
            self.game_code_map[game_code] = game_url
            with open('data/game_code_map/map.pkl', 'wb') as fpath:
                pkl.dump(self.game_code_map, fpath)

            self.process_download(f'data/raw_transcripts/transcript-{game_code}.en.vtt', f'data/raw_transcripts/cleaned_transcript-{game_code}.srt', final_path = 'data/processed_data/', final_name=game_code)

        print('Finished!')



    def _collect_daily_URLs(self, base_url='https://www.mlb.com/live-stream-games/') -> None:
        """
        Scrapes for and collects a list of 'day' URLs on MLB's website, with each URL containing the sublinks for individual
        game broadcasts on that day.

        Arguments
        ----------
            base_url: The root of all day URLs, with each individual day URL appending a str to the root based on the date
        """

        # Create a list of dates that are included in our pull (3 years are available)
        dates = pd.date_range(self.start_date, self.end_date)
        suffixes = [date.strftime("%Y/%m/%d") for date in dates]

        # Define the total list of URLs for the webpages with the day's games. Note this includes offseason days too
        self.day_urls = [base_url + suffix for suffix in suffixes]

    def _collect_game_URLs(self):
        # Set up storage
        self.game_urls = []
        
        # Set up Selenium
        driver = webdriver.Chrome()

        for day_url in self.day_urls:
            # Open the MLB page
            driver.get(day_url)

            # Wait for elements to load (adjust timeout as needed)
            try:
                # Wait until the element is clickable (replace with the correct selector)
                button = WebDriverWait(driver, 2.5).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))  # Modify selector as needed
                )
                button.click()
            except Exception as e:
                pass

            time.sleep(1)
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            links = soup.find_all("a", class_="whitespace-nowrap below-420:w-[100px] below-420:truncate text-mlb-blue-link")

            game_urls = []
            game_urls += ['https://www.mlb.com' + link["href"] for link in links]

            self.game_urls = self._filter_to_home_tv_urls(game_urls)


    def _filter_to_home_tv_urls(self, total_url_list):
        # Group by game ID
        grouped = defaultdict(list)
        for url in total_url_list:
            parts = url.split('/')
            game_id = parts[4]  # The 'g...' part after /tv/
            grouped[game_id].append(url)

        # Apply the rule
        filtered_urls = []
        for game_id, game_urls in grouped.items():
            if len(game_urls) == 1:
                filtered_urls.append(game_urls[0])
            elif len(game_urls) >= 2:
                filtered_urls.append(game_urls[1])  # Keep second one

        return filtered_urls      
    
    def _get_best_broadcasts(self, url, username, password):
        command = [
            'yt-dlp', '-j', '--username', username, '--password', password, url
        ]
        
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print("yt-dlp error:", result.stderr)
            return None, None

        try:
            video_info = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Failed to parse yt-dlp output as JSON.")
            return None, None
        
        formats = video_info.get('formats', [])

        home_broadcasts = [f for f in formats if 'Home' in f.get('format_note', '')]
        away_broadcasts = [f for f in formats if 'Away' in f.get('format_note', '')]

        best_home = max(home_broadcasts, key=lambda f: f.get('width', 0)) if home_broadcasts else None
        best_away = max(away_broadcasts, key=lambda f: f.get('width', 0)) if away_broadcasts else None

        home_id = best_home['format_id'] if best_home else None
        away_id = best_away['format_id'] if best_away else None

        return home_id, away_id
    
    def _download_video_and_subtitles(self, url, format_code, download_video=False):

        if format_code is None:
            return None

        # Base yt-dlp command
        command = ['yt-dlp']
    
        # Add options for subtitles
        command.extend([
            '-f', format_code,
            '--write-subs',           # Write subtitles
            '--sub-lang', 'en',       # Use English subtitles
            '--embed-subs',           # Embed subtitles in the video
            '-P', 'data/raw_transcripts',
            '-o', f'transcript-{url.split("/")[4]}',
            '--username', self.username,
            '--password', self.password,
        ])

        if download_video == False:
            command.extend(['--skip-download'])
        
        # Add the URL to the command
        command.append(url)
        print(" ".join(command))
        
        # Run the command
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Check if the download was successful
        if result.returncode == 0:
            print("Download successful!")
            print(result.stdout)
        else:
            print("Error occurred during download.")
            print(result.stderr)

    def process_download(self, input_path, output_path, final_name, final_path: str = 'data/processed_data/'):
        self._convert_vtt_to_srt(input_path, output_path)
        self.text_groups = self._extract_timestamp_groups(output_path)
        self.final_text = self._reconstruct_text_with_overlap(self.text_groups)
        with open(final_path + f'final_transcript-{final_name}.txt', 'w', encoding='utf-8') as f:
            f.write(self.final_text)
    
    def _convert_vtt_to_srt(self, input_file, output_file):
        try:
            subprocess.run(
                ['ffmpeg', '-y', '-i', input_file, '-map', '0:s:0', output_file],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"Successfully converted {input_file} to {output_file}")
        except subprocess.CalledProcessError as e:
            print("FFmpeg error:", e.stderr.decode())

    def _extract_timestamp_groups(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split on double newlines (empty line separates groups in SRT)
        groups = content.strip().split('\n\n')

        timestamp_groups = []
        for group in groups:
            lines = group.strip().split('\n')
            # Usually first line: index, second line: timestamp, rest: text
            if len(lines) >= 2:
                timestamp_line = lines[1]
                text_lines = lines[2:] if len(lines) > 2 else []
                # Join timestamp + text (skip index line)
                timestamp_groups.append('\n'.join(text_lines))
        
        return timestamp_groups
    
    def _find_overlap(self, s1, s2, min_overlap=3):
        """Find the longest overlap between the end of s1 and start of s2."""
        max_overlap = 0
        max_len = min(len(s1), len(s2))
        for length in range(max_len, min_overlap - 1, -1):
            if s1[-length:] == s2[:length]:
                return length
        return 0

    def _reconstruct_text_with_overlap(self, fragments):
        if not fragments:
            return ""

        result = fragments[0]
        for current in fragments[1:]:
            overlap_len = self._find_overlap(result, current)
            # Append only the non-overlapping part of current
            result += current[overlap_len:]
        # Optional: normalize spaces
        result = " ".join(result.split())
        return result

