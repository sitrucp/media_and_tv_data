import csv
import shutil
import os
from datetime import datetime

RAW_FILE = 'watchlist_progress_raw.csv'
MANUAL_FILE = 'watchlist_progress_raw_manual_dates.csv'
BACKUP_DIR = 'watchlist_backups'
BACKUP_FILE_TEMPLATE = os.path.join(BACKUP_DIR, 'watchlist_progress_raw_manual_dates_bu_{date}.csv')

def backup_manual_file():
    # Create backup directory if it doesn't exist
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Created backup directory: {BACKUP_DIR}")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    backup_file = BACKUP_FILE_TEMPLATE.format(date=date_str)
    shutil.copy2(MANUAL_FILE, backup_file)
    print(f"Backup created: {backup_file}")

def get_content_ids(file_path):
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {row['contentId'] for row in reader}

def get_new_records(raw_file, existing_content_ids):
    with open(raw_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row['contentId'] not in existing_content_ids]

def append_records_to_manual(records):
    if not records:
        print("No new records to add.")
        return
    with open(MANUAL_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        for row in records:
            writer.writerow(row)
    print(f"Appended {len(records)} new records to {MANUAL_FILE}")

def main():
    backup_manual_file()
    existing_content_ids = get_content_ids(MANUAL_FILE)
    new_records = get_new_records(RAW_FILE, existing_content_ids)
    append_records_to_manual(new_records)

if __name__ == '__main__':
    main()
