import json
import glob
import csv
from datetime import datetime, timedelta
import pytz
import os
import hashlib
import sys

# Define the time zones
utc_zone = pytz.utc
est_zone = pytz.timezone('US/Eastern')
atlantic_zone = pytz.timezone('Canada/Atlantic')

# input files are the json files retrieved and processed by input_files_concatenated
output_file = 'raw_data_clean.csv'

def get_input_folder():
    if len(sys.argv) < 2:
        print("Usage: python process_raw_data.py <input_folder>")
        sys.exit(1)
    # Always resolve the input folder relative to the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(script_dir, sys.argv[1])
    if not os.path.isdir(input_folder):
        print(f"Input folder does not exist: {input_folder}")
        sys.exit(1)
    return input_folder

input_folder = get_input_folder()

# Step 1: Concatenate source data files (if more than one of each source file exists)
# eg graphql_0.json and watchHistory_pageNumber_0.json
def input_files_concatenated(file_pattern, key_path):
    combined_data = []
    # Always search in the input_folder
    search_pattern = os.path.join(input_folder, file_pattern)
    files = glob.glob(search_pattern)
    
    if not files:
        print(f"No files found for pattern: {file_pattern}")
        return combined_data
    
    for file_name in files:
        try:
            with open(file_name, 'r') as f:
                data = json.load(f)
                keys = key_path.split('/')
                for key in keys:
                    data = data[key]
                combined_data.extend(data)
        except Exception as e:
            print(f"Error processing file {file_name}: {e}")
    
    return combined_data

# Concatenate Set 1 - data source file "graphql_*.json"
set1_combined = input_files_concatenated('graphql_*.json', 'data/contentData/items')

# Concatenate Set 2 - data source file "watchHistory_pageNumber_*.json"
set2_combined = input_files_concatenated('watchHistory_pageNumber_*.json', 'content')

# Step 2: Merge the concatenated datasets
merged_data = []
for record1 in set1_combined:
    axis_id = record1.get('axisId')
    for record2 in set2_combined:
        content_id = record2.get('contentId')
        if content_id is not None and int(content_id) == axis_id:
            # Combine all fields from both records
            merged_record = {**record1, **record1.get('axisMedia', {}), **record2}
            # Rename fields to avoid conflicts
            merged_record['axisMedia_id'] = merged_record.pop('id', None)
            merged_record['axisMedia_title'] = merged_record.pop('title', None)
            merged_record['axisMedia_axisId'] = merged_record.pop('axisId', None)
            merged_record['axisMedia_mediaType'] = merged_record.pop('mediaType', None)
            merged_record['axisMedia_path'] = merged_record.pop('path', None)
            merged_record['axisMedia___typename'] = merged_record.pop('__typename', None)
            merged_record['title'] = record1.get('title') or record2.get('title')
            # Calculate the new fields
            timestamp = int(record2['timestamp']) / 1000  # Convert to seconds if necessary
            offset = int(record2['offset'])
            start_datetime_utc = datetime.utcfromtimestamp(timestamp).replace(tzinfo=utc_zone)
            start_datetime_est = start_datetime_utc.astimezone(est_zone)
            end_datetime_est = start_datetime_est + timedelta(seconds=offset)
            merged_record['start_datetime_EST'] = start_datetime_est.strftime('%Y-%m-%d %H:%M:%S')
            merged_record['duration'] = str(timedelta(seconds=offset))
            merged_record['end_datetime_EST'] = end_datetime_est.strftime('%Y-%m-%d %H:%M:%S')
            merged_data.append(merged_record)

# Step 3: Select and rename the final columns

final_data = []
for record in merged_data:
    final_record = {
        'show_name': record.get('axisMedia_title'),
        'episode_name': record.get('title'),
        'season': record.get('seasonNumber'),
        'episode': record.get('episodeNumber'),
        'start_datetime_EST': record.get('start_datetime_EST'),
        'duration_hh_mm_ss': record.get('duration'),
        'end_datetime_EST': record.get('end_datetime_EST'),
        'media_type': record.get('axisMedia_mediaType', '').lower(),
        'start_timestamp': record.get('timestamp'),
        'completed': 'yes' if record.get('completed') else 'no',
        'watch_time_seconds': record.get('offset'),
        'completed_percent': record.get('progression'),
        'contentId': record.get('contentId'),
        'mediaId': record.get('mediaId'),
        'language': record.get('language')
    }
    final_data.append(final_record)

# Step 4: Deduplicate Records Based on All Fields
unique_records = {}

for record in final_data:
    # Create a hash of the record (use all fields)
    record_hash = hashlib.md5(json.dumps(record, sort_keys=True).encode('utf-8')).hexdigest()
    
    if record_hash not in unique_records:
        unique_records[record_hash] = record

# Convert the deduplicated records back to a list
final_data = list(unique_records.values())

# Step 4: Save the merged final dataset to a CSV file

if final_data:
    keys = final_data[0].keys()
    with open(output_file, 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(final_data)

print(f"Final dataset saved to '{output_file}'.")
