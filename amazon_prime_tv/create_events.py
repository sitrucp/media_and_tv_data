import pandas as pd
import requests
from datetime import timedelta
import pytz
import sys
import os
import logging

# Import shared utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_event_utils import EventManager

#--- Define files ---#
input_file = "PrimeVideo.ViewingHistory_clean.csv"
create_event_log = "create_events_log.txt"

# Test mode settings - Set to True for testing with limited records
TEST_MODE = False  # Set to True to enable test mode
TEST_LIMIT = 10     # Number of records to process in test mode

# Dry run mode settings - Set to True to see what would happen without creating events
DRY_RUN = False     # Set to True to enable dry run mode (processes all records but doesn't create events)

# Last event date filter - Only process events after this date (manually update as needed)
LAST_EVENT_DATE = "2025-01-01"  # Format: YYYY-MM-DD

#--- Setup logging ---#
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(create_event_log),
        logging.StreamHandler(sys.stdout)
    ]
)

#--- Function to convert timezone and calculate end time  ---#

def adjust_times(df):
    logging.info("Adjusting timezones for the records")
    utc_zone = pytz.utc
    est_zone = pytz.timezone('America/New_York')
    for index, row in df.iterrows():
        try:
            # Directly use the Timestamp object
            start_time_utc = row['Playback Start Datetime (UTC)'].replace(tzinfo=utc_zone)
            # Calculate end time in UTC
            duration = timedelta(minutes=row['Duration_Minutes'])
            end_time_utc = start_time_utc + duration
            # Convert both times to EST
            start_time_est = start_time_utc.astimezone(est_zone).strftime('%Y-%m-%d %H:%M:%S')
            end_time_est = end_time_utc.astimezone(est_zone).strftime('%Y-%m-%d %H:%M:%S')
            # Update DataFrame
            df.at[index, 'Playback Start Datetime (EST)'] = start_time_est
            df.at[index, 'Playback End Datetime (EST)'] = end_time_est
        except Exception as e:
            logging.error(f"Error adjusting times for row {index}: {e}")


#--- Function to create a calendar event using Microsoft Graph API ---#

def create_calendar_event(access_token, row):
    # Create the event description, incorporating the duration
    description_html = (
        f"Title: {row['Title']}<br>"
        f"Start: {row['Playback Start Datetime (EST)']}<br>"
        f"End: {row['Playback End Datetime (EST)']}<br>"
        f"Duration: {row['Duration_Minutes']} minutes"
    )

    # Adjusted event payload to use the pre-calculated times and duration
    event_payload = {
        "subject": f"Prime TV: {row['Title']}",
        "start": {"dateTime": row['Playback Start Datetime (EST)'], "timeZone": "America/Toronto"},
        "end": {"dateTime": row['Playback End Datetime (EST)'], "timeZone": "America/Toronto"},
        "body": {"contentType": "HTML", "content": description_html},
        "categories": ["Prime TV"]
    }

    # Send the request to create the event
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    response = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=event_payload)
    response.raise_for_status()  # Ensure successful request

#--- Main script to process the CSV data and create events ---#

def main():
    logging.info("Starting the process of reading CSV data and creating events")

    try:
        # Initialize event manager with test mode and dry run settings
        # Token will be obtained automatically by EventManager
        event_manager = EventManager("Prime TV", test_mode=TEST_MODE, test_limit=TEST_LIMIT, dry_run=DRY_RUN)
    except RuntimeError as e:
        logging.error(f"Authentication failed: {e}")
        return
    
    # Fetch and cache existing events
    event_manager.fetch_existing_events()
    
    # Load the CSV file
    df = pd.read_csv(input_file)
    logging.info(f"CSV data loaded successfully with {len(df)} records")

    # Filter out blank rows
    df = df.dropna(how='all')
    logging.info(f"Data after removing blank rows: {len(df)} records")

    # Remove rows with invalid or missing datetime
    df = df.dropna(subset=['Playback Start Datetime (UTC)'])
    logging.info(f"Data after removing rows with missing datetimes: {len(df)} records")

    # Convert 'Playback Start Datetime (UTC)' to datetime
    df['Playback Start Datetime (UTC)'] = pd.to_datetime(df['Playback Start Datetime (UTC)'], errors='coerce')
    
    # Filter out rows where datetime conversion failed
    df = df.dropna(subset=['Playback Start Datetime (UTC)'])
    logging.info(f"Data after ensuring valid datetimes: {len(df)} records")

    # Adjust times
    adjust_times(df)

    # Filter by last event date to only process new events
    last_event_date = pd.to_datetime(LAST_EVENT_DATE)
    df = df[pd.to_datetime(df['Playback Start Datetime (EST)']) > last_event_date]
    logging.info(f"Filtering to events after {LAST_EVENT_DATE}. Found {len(df)} records to process.")

    # Ensure the DataFrame is not empty after filtering
    if df.empty:
        logging.info("No new events to create.")
        return

    # Process each row
    processed_count = 0
    for index, row in df.iterrows():
        # Check if we should continue processing (for test mode)
        if not event_manager.should_continue_processing(processed_count):
            break
            
        datetime_str = row['Playback Start Datetime (EST)']
        
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
            
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                # Use centralized token refresh logic
                if event_manager.handle_token_expired(create_calendar_event, row):
                    event_manager.log_event_result("CREATED", datetime_str, row['Title'])
                    processed_count += 1
                else:
                    logging.error(f"Failed to create event for {row['Playback Start Datetime (EST)']} {row['Title']} after token refresh")
            else:
                logging.error(f"HTTP error while creating event {row['Title']}: {e}")
        except Exception as e:
            logging.error(f"Failed to create event for {row['Playback Start Datetime (EST)']} {row['Title']} Error: {e}")

    # Print summary
    event_manager.print_summary()
    logging.info("Process completed successfully.")

if __name__ == "__main__":
    main()
