# Telegram Username Checker

A high-performance Python tool to check the availability and status of Telegram usernames. This script uses the Fragment.com API combined with Telegram's public web interface to identify usernames that might be free, reserved, premium, channels, or privacy-restricted. It supports various input sources and sends Telegram notifications for interesting results.

---

## Features

- **Multi-threaded processing** for fast username checks using all CPU cores.
- **Fragment.com API integration** to get detailed username auction and status info.
- **Telegram web scraping** to verify if usernames are contactable.
- **Reserved words filtering** to exclude unwanted usernames.
- **Flexible input methods**:
  - Load usernames from a GitHub raw URL.
  - Load usernames from a local wordlist file.
  - Generate random usernames interactively.
- **Telegram bot notifications** for possibly free or reserved usernames.
- **Robust retry and error handling** to manage network or API failures.
- **Verbose logging** option for detailed debug output.

---

## Requirements

- Python 3.7+
- Dependencies:
  - `requests`
  - `lxml`
  - `coloredlogs`

Install dependencies with:

```bash
pip install -r requirements.txt
