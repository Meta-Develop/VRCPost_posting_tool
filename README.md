# VRCPost Posting Tool

A desktop application for scheduled posting and automatic story updates on VRCPost.

## Features

- **Scheduled Posting**: Automatically post photos with text at a specified date and time
- **Story Updates**: Automatically update stories at a specified time
- **Schedule Management**: Recurring posts (daily/weekly/monthly) and batch scheduling
- **Image Management**: Image preview and drag-and-drop support
- **Settings Management**: Configure target URL, browser options, and more from the GUI
- **Log Viewer**: View, filter, and export logs in real time within the app

## Requirements

- Python 3.10 or later
- Google Chrome or a Chromium-based browser

## Installation

```bash
# Clone the repository
git clone https://github.com/Meta-Develop/VRCPost_posting_tool.git
cd VRCPost_posting_tool

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e .

# Install Playwright browser
playwright install chromium
```

## Usage

```bash
# Launch the GUI
vrcpost-poster

# Or run directly
python -m src
```

### Initial Setup

1. When you launch the app, the VRCPost login screen will appear
2. Log in with your Google account or email address
3. After logging in, session information is saved securely

### Scheduled Posting

1. Open the "Post" tab
2. Select an image (drag-and-drop supported)
3. Enter text
4. Check "Schedule Post" and set the date and time
5. Click the "Post" button

### Story Updates

1. Open the "Story" tab
2. Select an image for the story
3. Enter text (optional)
4. Check "Schedule Update" and set the time
5. Click "Upload"

### Schedule Management

You can view all registered jobs in the "Schedule" tab.
Job selection and cancellation are also available from this tab.

### Settings

From the "Settings" tab, you can change the target URL, browser options,
post defaults, scheduler concurrency, and more.
Settings are saved to `config/settings.json`.

### Logs

The "Log" tab lets you view application logs in real time.
You can filter by log level or export logs to a text file.

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Lint
python -m ruff check src/ tests/
```

## License

MIT License
