# Using Existing Chrome Session for Reddit Scraping

This guide shows you how to manually log into Reddit once and let the scraper reuse that session, avoiding repeated logins and captchas.

## Quick Start

### Method 1: Using .env Configuration (Recommended)

1. **Start Chrome with debugging enabled:**
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev_session"
   ```

2. **Log into Reddit** in that Chrome window manually

3. **Update your `.env` file:**
   ```bash
   # Enable Chrome session reuse
   USE_EXISTING_CHROME_SESSION=True
   CHROME_DEBUG_PORT=9222
   ```

4. **Run your scraper normally** - it will automatically connect to your existing Chrome:
   ```bash
   poetry run python run.py
   ```

### Method 2: Programmatic Control

```python
from app.collectors.reddit_selenium_collector import RedditSeleniumCollector

# Connect to existing Chrome session
collector = RedditSeleniumCollector(
    use_existing_session=True,
    debug_port=9222
)

# Scrape normally - uses your existing login
posts = collector.collect_from_subreddit("Economics", limit=10)
collector.close()
```

## Benefits

✅ **Skip automated login** - Use your manual login session  
✅ **Avoid captchas** - Solve them once manually  
✅ **Reusable session** - Browser stays open between runs  
✅ **Easy debugging** - See exactly what's happening  
✅ **Session persistence** - No re-authentication needed  

## Configuration Options

### .env Settings

```bash
# Use existing Chrome session instead of creating new one
USE_EXISTING_CHROME_SESSION=False  # Set to True to enable

# Port for Chrome remote debugging
CHROME_DEBUG_PORT=9222  # Default port, change if needed
```

## Troubleshooting

### Chrome won't connect
- Make sure Chrome is running with `--remote-debugging-port=9222`
- Check that the port matches your `.env` setting
- Try closing all Chrome instances and starting fresh

### Session expired
- Just log in again manually in the Chrome window
- The scraper will use the new session automatically

### Port already in use
- Change the port in both the Chrome command and `.env`:
  ```bash
  google-chrome --remote-debugging-port=9223 --user-data-dir="/tmp/chrome_dev_session"
  ```
  ```bash
  CHROME_DEBUG_PORT=9223
  ```

## Advanced Usage

### Using with scheduled tasks

When using cron or schedulers:

1. Start Chrome once manually:
   ```bash
   google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev_session" &
   ```

2. Log into Reddit manually

3. Set up your .env to use the existing session

4. Your scheduled scraper will reuse this session indefinitely

### Multiple ports for different services

```bash
# Reddit scraping
google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_reddit" &

# Twitter scraping (if needed)
google-chrome --remote-debugging-port=9223 --user-data-dir="/tmp/chrome_twitter" &
```

Then configure each collector with the appropriate port.
