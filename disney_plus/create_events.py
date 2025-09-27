import pandas as pd
import requests
import sys
import os
import logging

# Import shared utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_event_utils import EventManager

#--- Define files ---#
input_file = "watchlist_progress_raw_manual_dates.csv"
create_events_log = "create_events_log.txt"

# Test mode settings - Set to True for testing with limited records
TEST_MODE = False  # Set to True to enable test mode
TEST_LIMIT = 3     # Number of records to process in test mode

# Dry run mode settings - Set to True to see what would happen without creating events
DRY_RUN = True     # Set to True to enable dry run mode (processes all records but doesn't create events)

# Last event date filter - Only process events after this date (manually update as needed)
LAST_EVENT_DATE = "2025-09-24"  # Format: YYYY-MM-DD

#--- Setup logging ---#
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(create_events_log),
        logging.StreamHandler(sys.stdout)
    ]
)

#--- Function to create a calendar event using Microsoft Graph API ---#
def create_calendar_event(token, row):
    # Title format changed to include show, name, season, and episode
    if row['media_type'] == 'series':
        title = f"Disney Plus: {row['show_name']} {row['episode_name']} S:{row['season']} E:{row['episode']}"
    else:
        title = f"Disney Plus: {row['show_name']}"

    description_html = (
        f"Title: {title}<br>"
        f"Start: {row['start_datetime_EST']}<br>"
        f"End: {row['end_datetime_EST']}<br>"
        f"Duration: {row['watch_time_seconds']} seconds"
    )

    event_payload = {
        "subject": title,
        "start": {"dateTime": row['start_datetime_EST'], "timeZone": "Eastern Standard Time"},
        "end": {"dateTime": row['end_datetime_EST'], "timeZone": "Eastern Standard Time"},
        "body": {"contentType": "HTML", "content": description_html},
        "categories": ["Disney Plus"]
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    # Changed to use /me/events instead of /users/{user_id}/events
    response = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=event_payload)
    response.raise_for_status()


#--- Main script to process the CSV data and create events ---#
def main():
    try:
        # Initialize event manager with test mode and dry run settings
        # Token will be obtained automatically by EventManager
        event_manager = EventManager("Disney Plus", test_mode=TEST_MODE, test_limit=TEST_LIMIT, dry_run=DRY_RUN)
    except RuntimeError as e:
        logging.error(f"Authentication failed: {e}")
        return
    
    # Fetch and cache existing events
    event_manager.fetch_existing_events()

    # Read the input data file
    df = pd.read_csv(input_file)

    # Filter out records without start_datetime_EST
    df = df.dropna(subset=['start_datetime_EST'])
    df = df[df['start_datetime_EST'].str.strip() != '']

    # Convert 'start_datetime_EST' to datetime objects
    df['start_datetime_EST'] = pd.to_datetime(df['start_datetime_EST'])

    # Filter by last event date to only process new events
    last_event_date = pd.to_datetime(LAST_EVENT_DATE)
    df = df[df['start_datetime_EST'] > last_event_date]
    logging.info(f"Filtering to events after {LAST_EVENT_DATE}. Found {len(df)} records to process.")


    # Calculate end_datetime_EST using start_datetime_EST + watch_time_seconds
    df['end_datetime_EST'] = df['start_datetime_EST'] + pd.to_timedelta(df['watch_time_seconds'], unit='seconds')

    # Convert datetime columns to ISO format for API
    df['start_datetime_EST'] = df['start_datetime_EST'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    df['end_datetime_EST'] = df['end_datetime_EST'].dt.strftime('%Y-%m-%dT%H:%M:%S')

    # Convert season and episode to strings for display
    df['season'] = df['season'].astype(str)
    df['episode'] = df['episode'].astype(str)

    # Process each row
    for index, row in df.iterrows():
        if row['media_type'] == 'series':
            title = f"{row['show_name']} {row['episode_name']} S:{row['season']} E:{row['episode']}"
        else:
            title = row['show_name']
        
        datetime_str = row['start_datetime_EST']
        
        try:
            if event_manager.event_exists(row, title):
                event_manager.log_event_result("EXISTS", datetime_str, title)
                continue
                
            # Create event (or simulate in dry run mode)
            if not event_manager.dry_run:
                create_calendar_event(event_manager.token, row)
            event_manager.log_event_result("CREATED", datetime_str, title)
            
            # Event created successfully
            
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                # Use centralized token refresh logic
                if event_manager.handle_token_expired(create_calendar_event, row):
                    event_manager.log_event_result("CREATED", datetime_str, title)
                    # Event created successfully after token refresh
                    break
                else:
                    logging.error(f"Failed to create event for {row['start_datetime_EST']} {title} after token refresh")
            else:
                logging.error(f"Error creating event for {row['start_datetime_EST']} {title}: {e}")

    
    # Print summary
    event_manager.print_summary()

if __name__ == "__main__":
    main()

