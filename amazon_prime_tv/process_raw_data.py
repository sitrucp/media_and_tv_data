import pandas as pd
import numpy as np
import logging

input_file = "PrimeVideo.ViewingHistory.csv"
output_file = "PrimeVideo.ViewingHistory_clean.csv"

df = pd.read_csv(input_file)

# Normalize Title
df['Title'] = df['Title'].astype(str).str.strip('"')
df = df[df['Title'] != "Not available"]

# Parse start/end datetimes (UTC)
df['Playback Start Datetime (UTC)'] = pd.to_datetime(
    df['Playback Start Datetime (UTC)'], format='%Y-%m-%dT%H:%M:%SZ', errors='coerce'
)
df = df.dropna(subset=['Playback Start Datetime (UTC)'])

# Compute duration minutes (ceil)
df['Duration Minutes'] = np.ceil(df['Seconds Viewed'] / 60).astype(int)

# Autoplay filter: drop only short (<10m) autoplay rows
if 'Is Autoplay' in df.columns:
    autoplay_norm = (
        df['Is Autoplay'].astype(str)
        .str.strip('"').str.strip().str.lower()
        .map({'yes': 'yes', 'true': 'yes', '1': 'yes',
              'no': 'no', 'false': 'no', '0': 'no'})
        .fillna('unknown')
    )
    pre_rows = len(df)
    df = df[~(autoplay_norm.eq('yes') & (df['Duration Minutes'] < 10))]
    logging.info(f"Removed short autoplay rows: {pre_rows - len(df)} (remaining {len(df)})")

# Derive original end per segment (needed for span logic)
df['Segment End Datetime (UTC)'] = df['Playback Start Datetime (UTC)'] + pd.to_timedelta(df['Duration Minutes'], unit='m')

# Derive watch date (UTC). If you need local date, localize then convert.
df['Watch Date'] = df['Playback Start Datetime (UTC)'].dt.date

# Aggregate per Title + Watch Date
daily = df.groupby(['Title', 'Watch Date']).agg(
    Daily_Start=('Playback Start Datetime (UTC)', 'min'),
    Daily_End_Span=('Segment End Datetime (UTC)', 'max'),
    Duration_Minutes=('Duration Minutes', 'sum'),
    Session_Count=('Duration Minutes', 'count')
).reset_index()

# Option A (default here): Event end reflects full span (may include gaps)
daily['Playback Start Datetime (UTC)'] = daily['Daily_Start']
daily['Playback End Datetime (UTC)'] = daily['Daily_End_Span']

# Option B (uncomment to use continuous packed duration instead of span)
# daily['Playback End Datetime (UTC)'] = daily['Daily_Start'] + pd.to_timedelta(daily['Duration_Minutes'], unit='m')

# Post-aggregation filter: remove day entries whose summed watch time <10 minutes (if desired)
MIN_DAILY_MINUTES = 10
pre_filter = len(daily)
daily = daily[daily['Duration_Minutes'] >= MIN_DAILY_MINUTES]
logging.info(f"Daily aggregates dropped for <{MIN_DAILY_MINUTES} min: {pre_filter - len(daily)}")

# Format datetimes
daily['Playback Start Datetime (UTC)'] = pd.to_datetime(daily['Playback Start Datetime (UTC)']).dt.strftime('%Y-%m-%d %H:%M:%S')
daily['Playback End Datetime (UTC)'] = pd.to_datetime(daily['Playback End Datetime (UTC)']).dt.strftime('%Y-%m-%d %H:%M:%S')

# Final column order
agg_df = daily[['Playback Start Datetime (UTC)', 'Playback End Datetime (UTC)',
                'Watch Date', 'Title', 'Duration_Minutes', 'Session_Count']]

# Sort latest first
agg_df = agg_df.sort_values(['Watch Date', 'Playback Start Datetime (UTC)'], ascending=[False, False])

agg_df.to_csv(output_file, index=False)
print("data saved to:", output_file)