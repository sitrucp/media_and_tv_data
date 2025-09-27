# process_raw_data.py

import json
import pandas as pd
from datetime import datetime, timedelta, timezone

input_file = 'TV App Favorites and Activity.json'
output_file = 'TV App Favorites and Activity.csv'

def ms_to_hhmm(ms):
    seconds = int(ms / 1000)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"

def extract_details(description, media_type):
    parts = description.split(" (", 1)
    details = {'Show Name': parts[0], 'Type': media_type}
    episode_details = parts[1].split(', ') if len(parts) > 1 else []

    for part in episode_details:
        if 'Episode Title' in part:
            details['Episode Title'] = part.split('[', 1)[1].split(']', 1)[0]
        elif 'Episode Number' in part:
            details['Episode Number'] = part.split('[', 1)[1].split(']', 1)[0]
        elif 'Season Number' in part:
            details['Season Number'] = part.split('[', 1)[1].split(']', 1)[0]
    return details

with open(input_file, 'r', encoding='utf-8') as file:
    data = json.load(file)

extracted_data = []

for event in data['events']:
    interpretation = event.get('event_interpretation', {})
    stored_event = event.get('stored_event', {})

    # Handle renamed description key
    desc_key = 'human_readable_media_description' if 'human_readable_media_description' in interpretation else 'media_description'
    media_type = stored_event.get('media_type', '')

    details = extract_details(interpretation.get(desc_key, ''), media_type)

    # Handle renamed playback position key
    pc_key = 'play_cursor_in_milliseconds' if 'play_cursor_in_milliseconds' in stored_event else 'play_position_in_milliseconds'
    play_position_ms = stored_event.get(pc_key, 0) or 0  # default to 0 if None

    # End time in UTC
    end_time_utc = datetime.fromtimestamp(stored_event['timestamp'] / 1000.0, tz=timezone.utc)

    # Start time from play position
    start_time_utc = end_time_utc - timedelta(milliseconds=play_position_ms)

    details.update({
        'Start Datetime UTC': start_time_utc.strftime('%Y-%m-%dT%H:%M:%S'),
        'End Datetime UTC': end_time_utc.strftime('%Y-%m-%dT%H:%M:%S'),
        'Duration': ms_to_hhmm(play_position_ms)
    })

    extracted_data.append(details)

# DataFrame creation
df = pd.DataFrame(extracted_data)

# Clean up season/episode number formatting
for col in ['Season Number', 'Episode Number']:
    if col in df.columns:
        df[col] = df[col].fillna('').astype(str)
        df[col] = df[col].apply(lambda x: x.rstrip('.0') if '.' in x else x)

# Define column order
column_order = [
    'Show Name', 'Episode Title', 'Season Number', 'Episode Number',
    'Start Datetime UTC', 'End Datetime UTC', 'Duration', 'Type'
]
for col in column_order:
    if col not in df.columns:
        df[col] = ''

df = df[column_order]

# Sort newest first by End Datetime UTC
df['Sort Datetime'] = pd.to_datetime(df['End Datetime UTC'], utc=True)
df = df.sort_values(by='Sort Datetime', ascending=False).drop(columns=['Sort Datetime'])

df.to_csv(output_file, index=False)
print("Data saved to", output_file)
