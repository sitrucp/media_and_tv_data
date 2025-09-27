# Run this ad-hoc analysis script in the same folder as the two CSVs.

import pandas as pd

before_file = "PrimeVideo.ViewingHistory_clean_original.csv"   # BEFORE (max per title)
after_file  = "PrimeVideo.ViewingHistory_clean.csv"            # AFTER (sum & autoplay filtered)

before = pd.read_csv(before_file)
after  = pd.read_csv(after_file)

before['Title'] = before['Title'].astype(str).str.strip()
after['Title']  = after['Title'].astype(str).str.strip()

before_unique = before['Title'].nunique()
after_unique  = after['Title'].nunique()

merged = before[['Title','Duration Minutes']].merge(
    after[['Title','Duration Minutes']],
    on='Title',
    how='inner',
    suffixes=('_before','_after')
)

merged['delta'] = merged['Duration Minutes_after'] - merged['Duration Minutes_before']
greater_count = (merged['delta'] > 0).sum()
less_count    = (merged['delta'] < 0).sum()
equal_count   = (merged['delta'] == 0).sum()

overlap_count = merged['Title'].nunique()
dropped_count = before_unique - overlap_count
added_count   = after_unique - overlap_count

print("=== Comparison Summary ===")
print(f"Unique titles BEFORE: {before_unique}")
print(f"Unique titles AFTER : {after_unique}")
print(f"Overlapping titles  : {overlap_count}")
print()
print(f"Durations greater in AFTER : {greater_count}")
print(f"Durations less in AFTER    : {less_count}")
print(f"Durations equal            : {equal_count}")
print()
print(f"Titles removed (before only): {dropped_count}")
print(f"Titles added (after only)   : {added_count}")

# Identify dropped and added titles
before_titles = set(before['Title'].unique())
after_titles  = set(after['Title'].unique())

dropped_titles = sorted(before_titles - after_titles)
added_titles   = sorted(after_titles - before_titles)

if dropped_titles:
    print("\nDropped titles (present BEFORE, absent AFTER):")
    for t in dropped_titles:
        print("  -", t)
else:
    print("\nNo dropped titles.")

if added_titles:
    print("\nAdded titles (present AFTER, absent BEFORE):")
    for t in added_titles:
        print("  +", t)
else:
    print("\nNo added titles.")

# Optional: list titles whose duration increased
increased = merged[merged['delta'] > 0].sort_values('delta', ascending=False)
if not increased.empty:
    print("\nTitles with increased duration (delta minutes):")
    for _, r in increased.iterrows():
        print(f"  + {r['Title']}: {r['Duration Minutes_before']} -> {r['Duration Minutes_after']} (Δ {r['delta']})")

# Optional: list titles whose duration decreased
decreased = merged[merged['delta'] < 0].sort_values('delta')
if not decreased.empty:
    print("\nTitles with decreased duration (delta minutes):")
    for _, r in decreased.iterrows():
        print(f"  - {r['Title']}: {r['Duration Minutes_before']} -> {r['Duration Minutes_after']} (Δ {r['delta']})")