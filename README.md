# Telegram Channel Downloader

A powerful GUI application telegram media crawler for downloading media files from Telegram channels with support for concurrent downloads, progress tracking, and selective file downloading.

## Features

- 📱 Support for both user accounts and bot tokens
- 🔍 Channel scanning with detailed file information
- ✅ Selective file downloading
- 📊 Real-time progress tracking with speed and ETA
- 💨 Concurrent downloads for better performance
- 📁 Custom download location selection
- 🎥 Special handling for videos with duration display

## Prerequisites

- Python 3.7+
- Telegram API credentials (API ID and Hash)
- Required Python packages:
  ```bash
  pip install telethon cryptg PyQt5 humanize
  ```

## Installation
Clone the repository:

```bash
git clone https://github.com/ApeSkillx/telegram-media-downloader.git
cd telegram-media-downloader
```


Install dependencies:

```bash
pip install -r requirements.txt

```

## Usage
Run the application:

```bash
python bulk_download.py
```

## Configuration
1. Enter your Telegram API credentials:
* API ID
* API Hash
* Channel link or username

2. Authenticate using either:
Phone number or Bot token

3. Scan the channel and select the files you wish to download.

4. Choose the download location and start the download process.

#### Configuration Options:
* Default concurrent downloads: 4
* Supported media types: Documents, Photos, Videos, Audio
* Maximum retry attempts: 3
* Auto-reconnect: Enabled

#### Error Handling:
The application includes robust error handling for the following scenarios:
* Network issues: Automatically retries on network failure
* Authentication failures: Provides clear error messages and prompts for re-authentication
* File download errors: Handles issues with specific files (e.g., permissions or missing files)
* Invalid inputs: Ensures users are notified if invalid credentials or channel information are provided

## Contributing
We welcome contributions! To contribute:

1. Fork this repository
2. Create a feature branch (git checkout -b feature-branch)
3. Commit your changes (git commit -m 'Add new feature')
4. Push to the branch (git push origin feature-branch)
5. Create a Pull Request
6. Please ensure your changes are well-documented and thoroughly tested.
