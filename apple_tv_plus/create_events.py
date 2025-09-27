# create_events.py

import pandas as pd
import requests
import sys
import os
import logging
from zoneinfo import ZoneInfo  # Python 3.9+

# Import shared utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_event_utils import EventManager

DEBUG_MODE = False  # Set False to process all

# Test mode settings - Set to True for testing with limited records
TEST_MODE = False  # Set to True to enable test mode
TEST_LIMIT = 3     # Number of records to process in test mode

# Dry run mode settings - Set to True to see what would happen without creating events
DRY_RUN = True     # Set to True to enable dry run mode (processes all records but doesn't create events)

# Last event date filter - Only process events after this date (manually update as needed)
LAST_EVENT_DATE = "2025-01-01"  # Format: YYYY-MM-DD

# --- Local Timezone Setting ---
LOCAL_TIMEZONE = ZoneInfo("America/Moncton")  # Atlantic Time

# --- Files ---
input_file = "TV App Favorites and Activity.csv"  # Extractor output
create_event_log = "create_event_log.txt"

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',   # removed date/time
    handlers=[
        logging.FileHandler(create_event_log),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Helpers ---
def build_event_title(row):
    if row['Type'] == 'TV':
        return f"Apple TV Plus: {row['Show Name']} {row['Episode Title']} S:{row['Season Number']} E:{row['Episode Number']}"
    else:
        return f"Apple TV Plus: {row['Show Name']}"

def create_calendar_event(token, row, title):
    description_html = (
        f"Title: {title}<br>"
        f"Start: {row['Start Datetime']}<br>"
        f"End: {row['End Datetime']}<br>"
        f"Duration: {row['Duration']}"
    )

    payload = {
        "subject": title,
        "start": {"dateTime": row['Start Datetime'], "timeZone": LOCAL_TIMEZONE.key},
        "end": {"dateTime": row['End Datetime'], "timeZone": LOCAL_TIMEZONE.key},
        "body": {"contentType": "HTML", "content": description_html},
        "categories": ["Apple TV Plus"]
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=payload)
    response.raise_for_status()

# --- Main ---
def main():
    try:
        # Initialize event manager with test mode and dry run settings
        # Token will be obtained automatically by EventManager
        event_manager = EventManager("Apple TV Plus", test_mode=TEST_MODE, test_limit=TEST_LIMIT, dry_run=DRY_RUN)
    except RuntimeError as e:
        logging.error(f"Authentication error: {e}")
        return
    
    # Fetch and cache existing events
    event_manager.fetch_existing_events()

    # If your CSV sometimes comes in with cp1252, this read will still work, but we normalize later anyway.
    df = pd.read_csv(input_file)

    # Convert from UTC to local timezone
    df['Start Datetime'] = pd.to_datetime(df['Start Datetime UTC'], utc=True).dt.tz_convert(LOCAL_TIMEZONE)
    df['End Datetime'] = pd.to_datetime(df['End Datetime UTC'], utc=True).dt.tz_convert(LOCAL_TIMEZONE)

    # Format for Microsoft Graph (without timezone suffix, Graph uses 'timeZone' field)
    df['Start Datetime'] = df['Start Datetime'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    df['End Datetime'] = df['End Datetime'].dt.strftime('%Y-%m-%dT%H:%M:%S')

    # Filter by last event date to only process new events
    last_event_date = pd.to_datetime(LAST_EVENT_DATE)
    df = df[pd.to_datetime(df['Start Datetime']) > last_event_date]
    logging.info(f"Filtering to events after {LAST_EVENT_DATE}. Found {len(df)} records to process.")

    processed_count = 0
    for _, row in df.iterrows():
        # Check if we should continue processing (for test mode)
        if not event_manager.should_continue_processing(processed_count):
            break
            
        title = build_event_title(row)
        datetime_str = row['Start Datetime']
        
        try:
            if event_manager.event_exists(row, title.replace("Apple TV Plus: ", "")):
                event_manager.log_event_result("EXISTS", datetime_str, title.replace("Apple TV Plus: ", ""))
                processed_count += 1
                continue
            
            # Create event (or simulate in dry run mode)
            if not event_manager.dry_run:
                create_calendar_event(event_manager.token, row, title)
            event_manager.log_event_result("CREATED", datetime_str, title.replace("Apple TV Plus: ", ""))
            processed_count += 1
            
            # Event created successfully

        except requests.HTTPError as e:
            if e.response.status_code == 401:
                # Use centralized token refresh logic
                if event_manager.handle_token_expired(create_calendar_event, row, title):
                    event_manager.log_event_result("CREATED", datetime_str, title.replace("Apple TV Plus: ", ""))
                    processed_count += 1
                    # Event created successfully after token refresh
                else:
                    logging.error(f"Failed to create event {title} after token refresh")
            else:
                logging.error(f"HTTP error while creating event {title}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while creating event {title}: {e}")

        if DEBUG_MODE:
            break
    
    # Print summary
    event_manager.print_summary()

if __name__ == "__main__":
    main()