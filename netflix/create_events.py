import pandas as pd
import requests
from datetime import timedelta
import sys 
import os
import logging

# Import shared utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_event_utils import EventManager

input_file = "FilteredViewingActivity.csv"
create_events_log = "create_events_log.txt"

# Test mode settings - Set to True for testing with limited records
TEST_MODE = False  # Set to True to enable test mode
TEST_LIMIT = 10     # Number of records to process in test mode

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
    # Calculate the local end time by adding the duration to the local start time
    duration_hours, duration_minutes, _ = [int(x) for x in row['Duration'].split(':')]
    duration_delta = timedelta(hours=duration_hours, minutes=duration_minutes)
    local_end_time = row['Local Start Time'] + duration_delta

    # Format the start and end times for the event payload
    start_time_formatted = row['Local Start Time'].strftime('%Y-%m-%dT%H:%M:%S')
    end_time_formatted = local_end_time.strftime('%Y-%m-%dT%H:%M:%S')

    # Format the start time for the description using the original local time
    start_time_for_description = row['Local Start Time'].strftime('%Y-%m-%d %H:%M:%S')
    end_time_for_description = local_end_time.strftime('%Y-%m-%d %H:%M:%S')

    # create the event description
    description_html = (
        f"Title: {row['Title']}<br>"
        f"Start: {start_time_for_description}<br>"
        f"End: {end_time_for_description}<br>"
        f"Duration: {row['Duration']}<br>"
        f"Attributes: {(str(row['Attributes']).replace(',', ', ') if pd.notna(row['Attributes']) else 'None')}<br>"
        f"Device: {row['Device Type']}<br>"
        f"Country: {row['Country']}"
    )

    # Then, include this HTML-formatted description in your payload
    event_payload = {
        "subject": f"Netflix: {row['Title']}",
        "start": {
            "dateTime": start_time_formatted,
            "timeZone": row['Timezone']
        },
        "end": {
            "dateTime": end_time_formatted,
            "timeZone": row['Timezone']
        },
        "body": {
            "contentType": "HTML",
            "content": description_html
        },
        "categories": ["Netflix"]
    }

    # Send the request to create the event
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post("https://graph.microsoft.com/v1.0/me/events",
                             headers=headers, json=event_payload)
    response.raise_for_status()  # Ensure successful request

#--- Main script to create calendar events from processed data ---#

def main():
    print("Starting Netflix event creation...")
    
    try:
        # Initialize event manager with test mode and dry run settings
        # Token will be obtained automatically by EventManager
        event_manager = EventManager("Netflix", test_mode=TEST_MODE, test_limit=TEST_LIMIT, dry_run=DRY_RUN)
        print('Access token obtained successfully')
    except RuntimeError as e:
        print(f"Authentication failed: {e}")
        return
    
    # Fetch and cache existing events
    event_manager.fetch_existing_events()
    
    # Read the processed CSV file
    print(f"Reading processed input file: {input_file}")
    df = pd.read_csv(input_file, parse_dates=["Local Start Time"])
    print("Processed CSV file read successfully")
    print(f"Found {len(df)} records to process")
    
    # Filter by last event date to only process new events
    last_event_date = pd.to_datetime(LAST_EVENT_DATE)
    df = df[df['Local Start Time'] > last_event_date]
    print(f"Filtering to events after {LAST_EVENT_DATE}. Found {len(df)} records to process.")

    # Process each row
    processed_count = 0
    for index, row in df.iterrows():
        # Check if we should continue processing (for test mode)
        if not event_manager.should_continue_processing(processed_count):
            break
            
        datetime_str = row['Local Start Time'].strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            if event_manager.event_exists(row, row['Title']):
                event_manager.log_event_result("EXISTS", datetime_str, row['Title'])
                processed_count += 1
                continue
            
            # Create event (or simulate in dry run mode)
            if not event_manager.dry_run:
                create_calendar_event(event_manager.token, row)
            event_manager.log_event_result("CREATED", datetime_str, row['Title'])
            processed_count += 1
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Use centralized token refresh logic
                if event_manager.handle_token_expired(create_calendar_event, row):
                    event_manager.log_event_result("CREATED", datetime_str, row['Title'])
                    processed_count += 1
                else:
                    print(f"Failed to create event for {row['Title']} after token refresh")
            else:
                print(f"HTTPError: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"General exception: {e}")
    
    # Print summary
    event_manager.print_summary()

if __name__ == "__main__":
    main()
