import pandas as pd
import time
import requests
import sys 
import os
import logging

# Import shared utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_event_utils import EventManager

#--- Data source ---#
input_file = "raw_data_clean.csv"
create_events_log = "create_events_log.txt"

# Test mode settings - Set to True for testing with limited records
TEST_MODE = False  # Set to True to enable test mode
TEST_LIMIT = 3     # Number of records to process in test mode

# Dry run mode settings - Set to True to see what would happen without creating events
DRY_RUN = True     # Set to True to enable dry run mode (processes all records but doesn't create events)

# Last event date filter - Only process events after this date (manually update as needed)
LAST_EVENT_DATE = "2025-01-01"  # Format: YYYY-MM-DD

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
    logging.info("Starting to create a calendar event")
    # Format the start and end times for the event payload
    start_time_formatted = row['start_datetime_EST'].strftime('%Y-%m-%dT%H:%M:%S')
    end_time_formatted = row['end_datetime_EST'].strftime('%Y-%m-%dT%H:%M:%S')

    # Determine title_complete based on mediaType
    if row['media_type'] == 'movie':
        title_complete = row['show_name']
    elif row['media_type'] == 'series':
        title_complete = f"{row['show_name'] } - {row['episode_name']} S{row['season']} E{row['episode']}"
    else:
        title_complete = row['show_name']


    # create the event description
    description_html = (
        f"Title: {title_complete}<br>"
        f"Start: {start_time_formatted}<br>"
        f"End: {end_time_formatted}<br>"
        f"Duration: {row['duration_hh_mm_ss']}<br>"
        f"Attributes: {(str(row['media_type']).lower().replace(',', ', ') if pd.notna(row['media_type']) else 'None')}"
    )

    # Then, include this HTML-formatted description in your payload
    event_payload = {
        "subject": f"Crave TV: {title_complete}",
        "start": {
            "dateTime": start_time_formatted,
            "timeZone": "America/Toronto"
        },
        "end": {
            "dateTime": end_time_formatted,
            "timeZone": "America/Toronto"
        },
        "body": {
            "contentType": "HTML",
            "content": description_html
        },
        "categories": ["Crave TV"]
    }

    # Send the request to create the event
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post("https://graph.microsoft.com/v1.0/me/events",
                             headers=headers, json=event_payload)
    response.raise_for_status()  # Ensure successful request

#--- Main script to process the CSV data and create events ---#
def main():
    try:
        # Initialize event manager with test mode and dry run settings
        # Token will be obtained automatically by EventManager
        event_manager = EventManager("Crave TV", test_mode=TEST_MODE, test_limit=TEST_LIMIT, dry_run=DRY_RUN)
    except RuntimeError as e:
        logging.error(f"Authentication failed: {e}")
        return
    
    # Fetch and cache existing events
    event_manager.fetch_existing_events()

    # Read the CSV file, ensuring datetime parsing
    df_full = pd.read_csv(input_file, parse_dates=["start_datetime_EST", "end_datetime_EST"]) 

    # Filter by last event date to only process new events
    last_event_date = pd.to_datetime(LAST_EVENT_DATE)
    df = df_full[df_full['start_datetime_EST'] > last_event_date]
    logging.info(f"Filtering to events after {LAST_EVENT_DATE}. Found {len(df)} records to process.")

    # Process each row
    for index, row in df.iterrows():
        # Determine title_complete based on mediaType
        if row['media_type'] == 'movie':
            title_complete = row['show_name']
        elif row['media_type'] == 'series':
            title_complete = f"{row['show_name'] } - {row['episode_name']} S{row['season']} E{row['episode']}"
        else:
            title_complete = row['show_name']
        
        datetime_str = row['start_datetime_EST'].strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            if event_manager.event_exists(row, title_complete):
                event_manager.log_event_result("EXISTS", datetime_str, title_complete)
                continue
            
            # Create event (or simulate in dry run mode)
            if not event_manager.dry_run:
                create_calendar_event(event_manager.token, row)
            event_manager.log_event_result("CREATED", datetime_str, title_complete)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Use centralized token refresh logic
                if event_manager.handle_token_expired(create_calendar_event, row):
                    event_manager.log_event_result("CREATED", datetime_str, title_complete)
                else:
                    logging.error(f"Failed to create event for {row['start_datetime_EST']}-{row['show_name']}-{row['episode_name']}-S{row['season']} E{row['episode']} after token refresh")
            elif e.response.status_code == 429:
                # Extract wait time from 'Retry-After' or default to 60 seconds
                retry_after = int(e.response.headers.get('Retry-After', 60))
                logging.warning(f"Rate limit hit, waiting for {retry_after} seconds before retrying...")
                time.sleep(retry_after)  
                # Optionally, retry the failed request here or log it for a manual retry later
            else:
                logging.error(f"Failed to create event for {row['start_datetime_EST']}-{row['show_name']}-{row['episode_name']}-S{row['season']} E{row['episode']}. Error: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while creating the event for {row['start_datetime_EST']}-{row['show_name']}-{row['episode_name']}-S{row['season']} E{row['episode']}. Error: {e}")
    
    # Print summary
    event_manager.print_summary()

if __name__ == "__main__":
    main()

