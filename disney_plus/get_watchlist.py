import sys
import os

# Add the modified pydisney path first so it takes precedence
sys.path.insert(0, "Disney-Plus-api-wrapper-master/src")
from pydisney import DisneyAPI

#--- Get config variables ---#
# Try to use existing token.json first, then fall back to config
token_file_exists = os.path.exists("token.json")
if token_file_exists:
    print("Using existing token.json file for authentication")
    email = "dummy@email.com"  # Won't be used if token.json is valid
    password = "dummy_password"
else:
    config_path = os.getenv("ENV_VARS_PATH")  # Get path to directory contaiining config_disneyplus.py
    if not config_path:
        raise ValueError("ENV_VARS_PATH environment variable not set and no token.json found")
    sys.path.insert(0, config_path)
    from config_disneyplus import config_disneyplus # type: ignore

    email = config_disneyplus["email"]
    password = config_disneyplus["password"]

# Get set_id from environment variable or config
set_id = os.getenv("DISNEY_SET_ID")
if not set_id:
    # Try to get from config if available
    try:
        set_id = config_disneyplus.get("set_id")
    except:  # noqa: E722
        pass
    
if not set_id:
    raise ValueError("DISNEY_SET_ID environment variable not set. Please set your Disney+ set ID.")

api = DisneyAPI(email=email, password=password, force_login=False)

print("DisneyAPI initialized successfully!")
print(f"Account: {api.account.email if api.account else 'Unknown'}")
print(f"Country: {api.account.country if api.account else 'Unknown'}")
print("=== STEP 1: Testing get_watchlist_items ===")
print("Attempting to fetch watchlist items...")

items = api.get_watchlist_items(set_id)

print(f"Watchlist items fetched successfully! Found {len(items)} items.")
print("\nShows/Movies in your watchlist:")
for i, item in enumerate(items):
    title = item["visuals"]["title"]
    item_id = item["id"]
    print(f"{i+1}. {title} (ID: {item_id})")

# Test Step 2: Get entity details for one item
print("\n=== STEP 2: Testing get_entity_details ===")
test_item = items[11]  # Loki (good test case as it has episodes)
test_title = test_item["visuals"]["title"]
test_id = test_item["id"]

print(f"Testing entity details for: {test_title} (ID: {test_id})")

entity_details = api.get_entity_details(test_id)
page_data = entity_details["data"]["page"]

# Debug: Check what's actually in the page data
print(f"Page keys: {list(page_data.keys())}")

# Try to find params or other entity type indicators
page_params = page_data.get("params", {})
entity_type = page_params.get("entity_type")

if not entity_type:
    # Try alternative locations for entity type
    entity_type = page_data.get("entity_type")
    if not entity_type:
        # Try to infer from containers
        containers = page_data.get("containers", [])
        has_episodes = any(c.get("type") == "episodes" for c in containers)
        entity_type = "series" if has_episodes else "movie"
        print(f"Inferred entity type: {entity_type}")
    else:
        print(f"Found entity type in page data: {entity_type}")
else:
    print(f"Found entity type in params: {entity_type}")

containers = page_data.get("containers", [])

print(f"Entity type: {entity_type}")
print(f"Found {len(containers)} containers in entity details")

for i, container in enumerate(containers):
    container_type = container["type"]
    item_count = len(container.get("items", []))
    season_count = len(container.get("seasons", []))
    print(f"  Container {i+1}: type='{container_type}', items={item_count}, seasons={season_count}")

# Test the new logic for series
if entity_type == "series":
    print("\n=== Testing Series Logic ===")
    for container in containers:
        if container["type"] == "episodes":
            seasons = container.get("seasons", [])
            print(f"Found {len(seasons)} seasons in episodes container")
            
            for season_idx, season in enumerate(seasons):
                season_id = season["id"]
                season_name = season.get("visuals", {}).get("name", f"Season {season_idx+1}")
                episodes = season.get("items", [])
                print(f"  {season_name} (ID: {season_id}): {len(episodes)} episodes loaded by default")
                
                # Show first few episodes from default load
                for ep_idx, episode in enumerate(episodes[:3]):
                    ep_title = episode.get("visuals", {}).get("episodeTitle", "No title")
                    duration = episode.get("visuals", {}).get("durationMs")
                    pid = episode.get("personalization", {}).get("pid")
                    print(f"    Episode {ep_idx+1}: '{ep_title}' (duration: {duration}ms, PID: {'Yes' if pid else 'No'})")
                    
                if len(episodes) > 3:
                    print(f"    ... and {len(episodes)-3} more episodes")
                
                # NEW: Test get_season_episodes for this specific season
                print(f"\n=== STEP 2.5: Testing get_season_episodes for {season_name} ===")
                try:
                    season_episodes = api.get_season_episodes(season_id)
                    print(f"✅ get_season_episodes returned {len(season_episodes)} episodes for {season_name}")
                    
                    # Compare with what was in the default load
                    if len(season_episodes) != len(episodes):
                        print(f"⚠️  Note: get_season_episodes returned {len(season_episodes)} episodes, "
                              f"but default load had {len(episodes)} episodes")
                    
                    # Show first few episodes from season API
                    print("First 3 episodes from get_season_episodes:")
                    for ep_idx, episode in enumerate(season_episodes[:3]):
                        ep_title = episode.get("visuals", {}).get("episodeTitle", "No title")
                        ep_number = episode.get("visuals", {}).get("episodeNumber", "?")
                        duration = episode.get("visuals", {}).get("durationMs")
                        pid = episode.get("personalization", {}).get("pid")
                        print(f"    S{season_idx+1}E{ep_number}: '{ep_title}' (duration: {duration}ms, PID: {'Yes' if pid else 'No'})")
                    
                    if len(season_episodes) > 3:
                        print(f"    ... and {len(season_episodes)-3} more episodes")
                        
                except Exception as e:
                    print(f"❌ get_season_episodes failed for {season_name}: {e}")

elif entity_type == "movie":
    print("\n=== Testing Movie Logic ===")
    page_pid = entity_details["data"]["page"].get("personalization", {}).get("pid")
    print(f"Movie PID at page level: {'Yes' if page_pid else 'No'}")
    
    # Check containers for movie details
    for container in containers:
        if container["type"] == "details":
            duration = container.get("visuals", {}).get("duration", {}).get("runtimeMs")
            print(f"Movie duration: {duration}ms")

# Optionally show structure of just one item instead of full JSON
# print(f"\nFirst item details:")
# print(json.dumps(items[0], indent=2))

print("\n=== STEP 3: Testing get_watchlist_progress ===")
print("This will fetch all episodes from all seasons and get user progress...")

progress_data = api.get_watchlist_progress(set_id)

print(f"\nFound {len(progress_data)} items with progress data:")

# Group by show for better display
shows_progress = {}
for item in progress_data:
    show_title = item["show_title"]
    # Handle empty or missing show titles
    if not show_title or show_title.strip() == "":
        show_title = "No title provided"
        item["show_title"] = show_title  # Update the item so CSV export gets the corrected name
    
    if show_title not in shows_progress:
        shows_progress[show_title] = []
    shows_progress[show_title].append(item)

for show_title, items in shows_progress.items():
    print(f"\n📺 {show_title} ({len(items)} items)")
    
    # Check if it's a series or movie
    if any(item.get("episodeTitle") for item in items):
        # It's a series
        seasons = {}
        for item in items:
            season_name = item.get("season_name", "Unknown Season")
            if season_name not in seasons:
                seasons[season_name] = []
            seasons[season_name].append(item)
        
        for season_name, episodes in seasons.items():
            print(f"  🎬 {season_name} ({len(episodes)} episodes)")
            for episode in episodes[:3]:  # Show first 3 episodes
                ep_title = episode.get("episodeTitle", "No title")
                progress = episode.get("progressPercentage")
                progress_str = f"{progress:.1f}%" if progress else "Not started"
                remaining = episode.get("secondsRemaining")
                remaining_str = f" ({remaining//60}m {remaining%60}s left)" if remaining else ""
                print(f"    - {ep_title}: {progress_str}{remaining_str}")
            if len(episodes) > 3:
                print(f"    ... and {len(episodes)-3} more episodes")
    else:
        # It's a movie
        item = items[0]  # Should only be one item for movies
        progress = item.get("progressPercentage")
        progress_str = f"{progress:.1f}%" if progress else "Not started"
        remaining = item.get("secondsRemaining")
        remaining_str = f" ({remaining//60}m {remaining%60}s left)" if remaining else ""
        duration = item.get("durationMs")
        duration_str = f" (Runtime: {duration//60000}m)" if duration else ""
        print(f"  🎥 Movie: {progress_str}{remaining_str}{duration_str}")

print("\n=== Summary ===")
print(f"Total shows/movies: {len(shows_progress)}")
print(f"Total items with progress tracking: {len(progress_data)}")

# Optional: Save to CSV with custom column structure
try:
    import csv
    csv_filename = "watchlist_progress_raw.csv"
    
    # Transform data to match desired column structure
    # Filter to only include items with progress > 0
    csv_rows = []
    for item in progress_data:
        # Only include items that have been started (progress > 0)
        progress_pct = item.get('progressPercentage', 0) or 0
        if progress_pct <= 0:
            continue  # Skip items with no progress
        
        # Extract season and episode numbers directly from the API data
        season_number = item.get('seasonNumber')
        episode_number = item.get('episodeNumber')
        
        # Convert to integers if they're strings
        if season_number:
            try:
                season_number = int(season_number)
            except (ValueError, TypeError):
                season_number = None
                
        if episode_number:
            try:
                episode_number = int(episode_number)
            except (ValueError, TypeError):
                episode_number = None
        
        # Calculate completed status (yes if > 80% progress)
        completed = 'yes' if progress_pct > 80 else 'no'
        
        # Convert duration from milliseconds to seconds
        duration_ms = item.get('durationMs', 0) or 0
        watch_time_seconds = duration_ms // 1000 if duration_ms else None
        
        row = {
            'show_name': item.get('show_title', ''),
            'episode_name': item.get('episodeTitle', ''),
            'season': season_number,
            'episode': episode_number,
            'start_datetime_EST': None,
            'duration_hh_mm_ss': None,
            'end_datetime_EST': None,
            'media_type': item.get('entity_type', ''),
            'start_timestamp': None,
            'completed': completed,
            'watch_time_seconds': watch_time_seconds,
            'completed_percent': progress_pct,
            'contentId': item.get('personalization_pid', ''),
            'mediaId': None,
            'language': None
        }
        csv_rows.append(row)
    
    # Define the column order as requested
    fieldnames = [
        'show_name', 'episode_name', 'season', 'episode', 'start_datetime_EST',
        'duration_hh_mm_ss', 'end_datetime_EST', 'media_type', 'start_timestamp',
        'completed', 'watch_time_seconds', 'completed_percent', 'contentId',
        'mediaId', 'language'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"Progress data exported to {csv_filename} with {len(csv_rows)} rows")
except Exception as e:
    print(f"Failed to export CSV: {e}")

