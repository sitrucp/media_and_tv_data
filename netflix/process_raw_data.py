import pandas as pd
import pytz

input_file = "ViewingActivity.csv"
output_file = "FilteredViewingActivity.csv"
log_file = "last_event_date.csv"

country_timezones = {
    'CA': 'America/Toronto',  # Canada, Toronto
    'US': 'America/New_York',  # United States, New York
    'SG': 'Asia/Singapore',  # Singapore
    'MY': 'Asia/Kuala_Lumpur',  # Malaysia, Kuala Lumpur
    'NL': 'Europe/Amsterdam',  # Netherlands, Amsterdam
    'PL': 'Europe/Warsaw',  # Poland, Warsaw
    'DE': 'Europe/Berlin',  # Germany, Berlin
    'HR': 'Europe/Zagreb',  # Croatia, Zagreb
    'GR': 'Europe/Athens',  # Greece, Athens
    'HU': 'Europe/Budapest',  # Hungary, Budapest
    'FR': 'Europe/Paris',  # France, Paris
    'AE': 'Asia/Dubai',  # United Arab Emirates, Dubai
    'SE': 'Europe/Stockholm',  # Sweden, Stockholm
    'JP': 'Asia/Tokyo',  # Japan, Tokyo
    'PT': 'Europe/Lisbon',  # Portugal, Lisbon
    'GB': 'Europe/London',  # United Kingdom, London
    'SA': 'Asia/Riyadh',  # Saudi Arabia, Riyadh
    'CZ': 'Europe/Prague',  # Czech Republic, Prague
    'DK': 'Europe/Copenhagen',  # Denmark, Copenhagen
    'EE': 'Europe/Tallinn',  # Estonia, Tallinn
    'FI': 'Europe/Helsinki',  # Finland, Helsinki
    'NO': 'Europe/Oslo',  # Norway, Oslo
}

def filter_duration(duration_str):
    """Filter the data converting '00:00:05' format for minutes filter"""
    try:
        hours, minutes, seconds = duration_str.split(':') 
        return int(hours) * 60 + int(minutes)  # Returns total minutes
    except ValueError as e:
        print(f"Error parsing duration: {e}")
        return 0

def convert_to_local_time(utc_time, country_code):
    """Convert UTC datetime to local time based on country code, accounting for DST, and return the timezone."""
    timezone_str = country_timezones.get(country_code)
    if timezone_str:
        # Ensure the datetime is timezone-aware
        utc_zone = pytz.utc
        utc_time = utc_time.replace(tzinfo=utc_zone)
        
        # Convert to the target timezone with DST consideration
        target_timezone = pytz.timezone(timezone_str)
        local_time = utc_time.astimezone(target_timezone)
        return local_time, timezone_str  # Return both the local time and the timezone string
    else:
        return utc_time, "UTC"  # Fallback to UTC if no timezone is found

def get_country_code(country_str):
    """Extracts the country code from the 'Country' column."""
    return country_str.split(' ')[0]  # Assumes format "Code (Country Name)"

def apply_conversion_and_capture_timezone(row):
    """Apply the conversion and capture both local time and timezone"""
    local_time, timezone_str = convert_to_local_time(row['Start Time'], get_country_code(row['Country']))
    return pd.Series([local_time, timezone_str], index=['Local Start Time', 'Timezone'])

def main():
    """Main function to process Netflix viewing data and create filtered CSV"""
    print("Starting Netflix data processing...")
    
    # Read the last record date from the log file
    print(f"Reading log file: {log_file}")
    log_df = pd.read_csv(log_file)
    last_record_date_str = log_df.iloc[0]['last_record_date']  # Assuming there's only one record
    print(f"Last record date string: {last_record_date_str}")
    last_record_date = pd.to_datetime(last_record_date_str).date()
    print(f"Last record date: {last_record_date}")

    # Read the CSV file, ensuring datetime parsing
    print(f"Reading input file: {input_file}")
    df = pd.read_csv(input_file, parse_dates=["Start Time"])
    print("CSV file read successfully")

    # Filter to exclude non-relevant records
    df_filtered = df[(df["Supplemental Video Type"].isnull()) & 
                              (df['Duration'].apply(filter_duration) >= 10)].copy()
    print(f"Filtered DataFrame:\n{df_filtered.head()}")
    
    # Convert 'Start Time' to local time and get IANA timezone value from 'Country'
    df_filtered[['Local Start Time', 'Timezone']] = df_filtered.apply(apply_conversion_and_capture_timezone, axis=1)
    print("Converted to local time")

    # Create local start date to compare to last_record_date to filter
    df_filtered['Local Start Time xTimezone'] = df_filtered['Local Start Time'].astype(str)
    df_filtered['Local Start Time xTimezone'] = df_filtered['Local Start Time xTimezone'].str.slice(stop=-6)
    df_filtered['Local Start Time xTimezone'] = pd.to_datetime(df_filtered['Local Start Time xTimezone'])
    df_filtered['Local Start Date'] = df_filtered['Local Start Time xTimezone'].dt.date
    print("Prepared date comparison")

    # Filter by retrieve log last record date
    df_filtered = df_filtered[df_filtered['Local Start Date'] > last_record_date].copy()
    print(f"Filtered by last record date:\n{df_filtered.head()}")
    
    # Sort the DataFrame by 'Local Start Time' in ascending order
    df_sorted = df_filtered.sort_values(by='Local Start Date', ascending=True)
    print("Sorted DataFrame")
    
    # Save df_filtered to a CSV file
    df_sorted.to_csv(output_file, index=False)
    print(f"Filtered data saved to {output_file}")

    print(f"Processing complete. {len(df_sorted)} records processed.")
    print(f"Output file: {output_file}")
    
    return df_sorted

if __name__ == "__main__":
    main()
