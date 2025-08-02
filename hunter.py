import argparse
import json
import logging
import multiprocessing
import re
import time
import coloredlogs
import requests
import random

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from lxml import html
from config import RESERVED_WORDS

# === Telegram Notify Setup ===
BOT_TOKEN = "7350462424:AAEZaZ7LULk_drhpzQJQs4i6YOYoJbKAcC4"
CHAT_ID = "5309088318"

logger = logging.getLogger(__name__)
coloredlogs.install(level='INFO', fmt='%(message)s', logger=logger)

PREMIUM_USER = 'This account is already subscribed to Telegram Premium.'
CHANNEL = 'Please enter a username assigned to a user.'
NOT_FOUND = 'No Telegram users found.'


def send_telegram_notification(username):
    text = f"🔥 Maybe Free or Reserved: @{username}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        logger.warning(f"Telegram notify failed: {e}")


class TelegramUsernameChecker:

    def __init__(self, file_path=None, local_file=None, verbose=False):
        self.usernames = set()
        self.session = requests.Session()
        self.file_path = file_path
        self.local_file = local_file
        self.verbose = verbose

    def generate_random_usernames(self, length, count=1000):
        charset = 'abcdefghijklmnopqrstuvwxyz0123456789'
        generated = set()
        while len(generated) < count:
            username = ''.join(random.choices(charset, k=length))
            if username.lower() not in RESERVED_WORDS:
                generated.add(username)
        self.usernames = generated

    def load(self):
        if self.file_path:
            parsed_url = urlparse(self.file_path)
            if parsed_url.netloc != 'raw.githubusercontent.com':
                logger.error(f'URL is not from raw.githubusercontent.com: {parsed_url.netloc}')
                return
            try:
                response = requests.get(self.file_path)
                response.raise_for_status()
                content = response.text.strip()
                if not content:
                    logger.error(f'File is empty.')
                    return
                self.usernames = set(line.strip() for line in content.splitlines() if line.strip())
                return True
            except Exception as e:
                logger.error(f"Error fetching usernames: {e}")
                return

        elif self.local_file:
            try:
                with open(self.local_file, "r") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    self.usernames = set(lines)
                    return True
            except FileNotFoundError:
                logger.error(f"Local file '{self.local_file}' not found.")
                return

        else:
            try:
                length = int(input("🔢 Enter desired username length: ").strip())
                count = int(input("🔁 How many usernames to generate: ").strip())
                self.generate_random_usernames(length, count)
                return True
            except Exception as e:
                logger.error(f"Invalid input: {e}")
                return

    def get_api_url(self):
        try:
            scripts = html.fromstring(self.session.get('https://fragment.com').content).xpath('//script/text()')
            pattern = re.compile(r'ajInit\((\{.*?})\);', re.DOTALL)
            script = next((script for script in scripts if pattern.search(script)), None)
            if script:
                api_url = f'https://fragment.com{json.loads(pattern.search(script).group(1)).get("apiUrl")}'
                return api_url
        except Exception:
            return

    def get_user(self, username, api_url):
        params = {'query': username, 'months': 3, 'method': 'searchPremiumGiftRecipient'}
        try:
            response = self.session.post(api_url, data=params)
            return response.json().get('error')
        except Exception:
            return None

    def get_telegram_web_user(self, username):
        try:
            resp = self.session.get(f'https://t.me/{username}')
            return f"You can contact @{username} right away." in html.fromstring(resp.content)
        except Exception:
            return False

    def check_fragment_api(self, username, retries=3):
        if retries == 0:
            return
        self.session.headers.pop('Connection', None)
        api_url = self.get_api_url()
        if not api_url:
            logger.warning(f'@{username} ❌ Could not retrieve API URL.')
            return

        data = {'type': 'usernames', 'query': username, 'method': 'searchAuctions'}
        try:
            resp = self.session.post(api_url, data=data).json()
        except Exception:
            logger.warning(f'@{username} ❌ Failed response. Retrying...')
            time.sleep(3)
            return self.check_fragment_api(username, retries - 1)

        if not resp.get('html'):
            time.sleep(2)
            return self.check_fragment_api(username, retries - 1)

        tree = html.fromstring(resp.get('html'))
        elements = tree.xpath('//div[contains(@class, "tm-value")]')
        if len(elements) < 3:
            return

        tag, price, status = [e.text_content() for e in elements[:3]]
        if tag[1:] != username:
            return

        if price.isdigit():
            return

        user_info = self.get_user(username, api_url)

        if user_info == NOT_FOUND and status == 'Unavailable':
            entity = self.get_telegram_web_user(username)
            if not entity:
                logger.critical(f'✅ {tag} Maybe Free or Reserved ✅')
                send_telegram_notification(username)
                return True
            logger.critical(f'🔒 {tag} Privacy-restricted user')
        elif user_info == PREMIUM_USER:
            logger.info(f'{tag} 👑 Premium User')
        elif user_info == CHANNEL:
            logger.info(f'{tag} 📢 Channel')
        elif 'Bad request' in str(user_info):
            logger.warning(f'{tag} Bad request error')

    def check(self, username):
        if not re.fullmatch(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', username):
            return
        if username.lower() in RESERVED_WORDS:
            return
        return self.check_fragment_api(username.lower())

    def run(self):
        with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            future_to_username = {
                executor.submit(self.check, username): username for username in self.usernames
            }
            for future in as_completed(future_to_username):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Error for {future_to_username[future]}: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="Telegram Username Checker")
    parser.add_argument('--file', type=str, help='URL to usernames (GitHub raw)')
    parser.add_argument('--local-file', type=str, help='Local wordlist path')
    parser.add_argument('--verbose', action='store_true')
    return parser.parse_args()


def main():
    args = parse_args()
    checker = TelegramUsernameChecker(file_path=args.file, local_file=args.local_file, verbose=args.verbose)
    if checker.load():
        checker.run()


if __name__ == "__main__":
    main()
