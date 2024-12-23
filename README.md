# WordPress Article Scraper Function

This Appwrite function automatically scrapes articles from your WordPress website and stores them in an Appwrite database.

## Setup

1. Create a new Appwrite function:
   - Runtime: Python 3.10
   - Entrypoint: main.py
   - Build Commands: pip install -r requirements.txt

2. Set up the following environment variables in your Appwrite function:
   ```
   WORDPRESS_URL=https://www.yomzansi.com/
   APPWRITE_DATABASE_ID=your_database_id
   APPWRITE_COLLECTION_ID=your_collection_id
   ```

3. Schedule the function to run at your desired interval (e.g., every hour):
   - Go to your function settings
   - Enable CRON scheduling
   - Set up your desired schedule (e.g., "0 * * * *" for hourly)

## Features

- Scrapes WordPress articles using WP REST API
- Filters articles by time period (day/week/month)
- Stores articles in Appwrite database
- Prevents duplicate entries
- Handles content truncation for very long articles
- Provides execution summary with success/failure details

## Response Format

The function returns a JSON response with:
```json
{
    "success": true,
    "total_stored": 5,
    "results": {
        "day": {
            "fetched": 2,
            "stored": 1
        },
        "week": {
            "fetched": 10,
            "stored": 3
        },
        "month": {
            "fetched": 50,
            "stored": 1
        }
    }
}
```
