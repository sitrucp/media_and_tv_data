import pandas as pd
import requests
from datetime import timedelta
import pytz
from dateutil import parser
import sys 
import os
import logging

# Import shared utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_event_utils import EventManager

input_file = "combine_library_purch_hist.csv"
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

#--- Function to convert timezone and calculate end time  ---#
def append_duration_and_convert_time(df):
    est_zone = pytz.timezone('America/New_York')
    utc_zone = pytz.utc
    durations = []  # To store duration for each row
    start_times = []  # To store converted start times for each row
    end_times = []  # To store calculated end times for each row

    for _, row in df.iterrows():
        # Convert time to datetime object and adjust timezone
        start_time_utc = parser.parse(row['time']).replace(tzinfo=utc_zone)
        start_time_est = start_time_utc.astimezone(est_zone)
        start_times.append(start_time_est.strftime('%Y-%m-%dT%H:%M:%S'))
        
        # Calculate duration and end time
        if row['documentType'] == 'Tv Episode':
            duration = 50  # minutes
        elif row['documentType'] == 'Movie':
            duration = 100  # minutes
        else:
            duration = 0
        durations.append(duration)  # Append calculated duration
        end_time_est = start_time_est + timedelta(minutes=duration)
        end_times.append(end_time_est.strftime('%Y-%m-%dT%H:%M:%S'))
    
    # Add new columns to DataFrame
    df['start_time_est'] = start_times
    df['end_time_est'] = end_times
    df['duration'] = durations


#--- Function to create a calendar event using Microsoft Graph API ---#
def create_calendar_event(token, row):
    # Use the pre-calculated and formatted values directly
    start_time_formatted = row['start_time_est']
    end_time_formatted = row['end_time_est']
    duration_minutes = row['duration']  # Assuming duration is calculated in minutes in the DataFrame

    # create the event description, incorporating the duration
    description_html = (
        f"Title: {row['title']}<br>"
        f"Start: {start_time_formatted}<br>"
        f"End: {end_time_formatted}<br>"
        f"Duration: {duration_minutes} minutes<br>"
        f"Attributes: {(str(row['documentType']).replace(',', ', ') if pd.notna(row['documentType']) else 'None')}"
    )

    # Adjusted event payload to use the pre-calculated times and duration
    event_payload = {
        "subject": f"Google TV: {row['title']}",
        "start": {"dateTime": start_time_formatted, "timeZone": "America/Toronto"},
        "end": {"dateTime": end_time_formatted, "timeZone": "America/Toronto"},
        "body": {"contentType": "HTML", "content": description_html},
        "categories": ["Google TV"]
    }

    # Send the request to create the event
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=event_payload)
    response.raise_for_status()  # Ensure successful request


#--- Main script to process the CSV data and create events ---#
def main():
    try:
        # Initialize event manager with test mode and dry run settings
        # Token will be obtained automatically by EventManager
        event_manager = EventManager("Google TV", test_mode=TEST_MODE, test_limit=TEST_LIMIT, dry_run=DRY_RUN)
    except RuntimeError as e:
        print(f"Authentication failed: {e}")
        return
    
    # Fetch and cache existing events
    event_manager.fetch_existing_events()
    
    df = pd.read_csv(input_file) 
    df = df.dropna(subset=['time'])
    append_duration_and_convert_time(df)  # Convert times and append duration

    # Filter by last event date to only process new events
    last_event_date = pd.to_datetime(LAST_EVENT_DATE)
    df = df[pd.to_datetime(df['start_time_est']) > last_event_date]
    print(f"Filtering to events after {LAST_EVENT_DATE}. Found {len(df)} records to process.")

    # Process each row
    for index, row in df.iterrows():
        datetime_str = row['start_time_est']
        
        try:
            if event_manager.event_exists(row, row['title']):
                event_manager.log_event_result("EXISTS", datetime_str, row['title'])
                continue
            
            # Create event (or simulate in dry run mode)
            if not event_manager.dry_run:
                create_calendar_event(event_manager.token, row)
            event_manager.log_event_result("CREATED", datetime_str, row['title'])
            
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                # Use centralized token refresh logic
                if event_manager.handle_token_expired(create_calendar_event, row):
                    event_manager.log_event_result("CREATED", datetime_str, row['title'])
                else:
                    print(f"Failed to create event for {row['start_time_est']} {row['title']} after token refresh")
            else:
                print(f"HTTP error while creating event {row['title']}: {e}")
        except Exception as e:
            print(f"Failed to create event for {row['start_time_est']} {row['title']} Error: {e}")
    
    # Print summary
    event_manager.print_summary()

if __name__ == "__main__":
    main()

