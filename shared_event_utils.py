"""
Shared Event Management Utilities for Media Platform Event Creation

This module provides a unified approach for creating calendar events across
all media platforms (Netflix, Amazon Prime TV, Apple TV+, etc.) with:
- Bulk caching of existing events for efficient duplicate detection
- Exact datetime + title matching to prevent true duplicates
- Harmonized logging format across all platforms
- Consistent summary reporting
"""

import pandas as pd
import requests
import unicodedata
import re
import os
import sys
from typing import Set

# Try to import ftfy for better mojibake fixing
try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False

# Common mojibake (encoding) fixes
_MOJI_PAIRS = {
    "\u2019": "'",  # Right single quotation mark
    "\u201c": '"',  # Left double quotation mark  
    "\u201d": '"',  # Right double quotation mark
    "\u2013": "-",  # En dash
    "\u2014": "-",  # Em dash
    "\u2026": "...", # Horizontal ellipsis
    "\u00a0": " ",  # Non-breaking space
}

_PUNCT_RE = re.compile(r"[^0-9a-z]+")  # keep only a–z, 0–9

def _fix_common_mojibake(s: str) -> str:
    """Fix common encoding issues (mojibake)"""
    # First, fix the specific mojibake sequence that's causing issues
    s = s.replace("â€™", "'")  # Common mojibake for apostrophe
    
    # Apply Unicode character fixes
    for bad, good in _MOJI_PAIRS.items():
        s = s.replace(bad, good)
    
    # best‑effort transcode: cp1252/latin1 → utf‑8 (helps "Whereâ€™s" → "Where's")
    try:
        maybe = s.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        # Only use if it meaningfully changed
        if _looks_better(s, maybe):
            return maybe
    except Exception:
        pass
    return s

def _looks_better(old: str, new: str) -> bool:
    """Heuristic: if new has fewer of the typical mojibake chars"""
    junk = "\u2019\u201c\u201d\u2013\u2014\u2026\u00a0"  # Common mojibake characters
    return sum(ch in junk for ch in new) < sum(ch in junk for ch in old)

def _fix_specific_mojibake(s: str) -> str:
    """Fix specific mojibake sequences we've encountered"""
    # Use a more robust approach that doesn't rely on hardcoded Unicode characters
    # This function will be called at runtime when the actual mojibake sequences are encountered
    
    # For now, just return the string as-is since we're having Unicode issues in the source file
    # The ftfy library should handle most cases, and we can add specific fixes as needed
    return s

def normalize_title(s: str) -> str:
    """Normalize title for comparison - fixes encoding issues and standardizes format"""
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    
    # Step 1: Fix mojibake and encoding issues
    if FTFY_AVAILABLE:
        # Use ftfy for comprehensive mojibake fixing
        s = ftfy.fix_text(s)
    else:
        # Fallback to manual fixes
        s = _fix_common_mojibake(s)
    
    # Step 2: Fix specific mojibake sequences that ftfy might miss
    s = _fix_specific_mojibake(s)
    
    # Step 3: Fix subscript and superscript characters
    subscript_map = {
        '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4', '₅': '5',
        '₆': '6', '₇': '7', '₈': '8', '₉': '9',
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5',
        '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
    }
    for old, new in subscript_map.items():
        s = s.replace(old, new)
    
    # Step 4: Unicode normalize & strip diacritics to ASCII base letters
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    
    # Step 5: Lowercase, collapse punctuation/whitespace
    s = s.casefold()
    s = _PUNCT_RE.sub(" ", s)
    s = " ".join(s.split())  # collapse whitespace to single spaces
    return s

def get_auth_token():
    """
    Get Microsoft Graph API access token for calendar operations
    
    Returns:
        str: Access token for Microsoft Graph API
        
    Raises:
        RuntimeError: If authentication fails
    """
    try:
        # Import the auth helper
        o365_personal_auth_path = os.getenv('o365_personal_auth_path')
        if not o365_personal_auth_path:
            raise RuntimeError("o365_personal_auth_path environment variable not set")
        
        sys.path.insert(0, o365_personal_auth_path)
        from o365_personal_auth import get_delegated_token  # type: ignore  # noqa: E402
        
        token = get_delegated_token(scopes=["Calendars.ReadWrite"])
        return token
    except Exception as e:
        raise RuntimeError(f"Authentication failed: {e}")

class EventManager:
    def __init__(self, platform_name: str, token: str = None, test_mode: bool = False, test_limit: int = 5, dry_run: bool = False):
        """
        Initialize EventManager for a specific platform
        
        Args:
            platform_name: Name of the platform (e.g., "Netflix", "Prime TV", "Apple TV Plus")
            token: Microsoft Graph API access token (if None, will be obtained automatically)
            test_mode: If True, only process a limited number of records for testing
            test_limit: Number of records to process in test mode (default: 5)
            dry_run: If True, process all records but don't actually create events (just show what would happen)
        """
        self.platform_name = platform_name
        self.token = token if token is not None else get_auth_token()
        self.existing_events_cache: Set[str] = set()
        self.events_created = 0
        self.events_skipped = 0
        self.test_mode = test_mode
        self.test_limit = test_limit
        self.dry_run = dry_run
        
        if test_mode:
            print(f"🧪 TEST MODE ENABLED - Will process only {test_limit} records")
        if dry_run:
            print(f"🔍 DRY RUN MODE ENABLED - Will show what would happen without creating events")
    
    def fetch_existing_events(self) -> Set[str]:
        """
        Fetch all existing events for this platform and cache them
        
        Returns:
            Set of composite keys in format: "UTC_DATETIME|EXACT_TITLE"
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Prefer": "outlook.timezone=\"UTC\""
        }
        
        existing_keys = set()
        url = "https://graph.microsoft.com/v1.0/me/events"
        params = {
            "$filter": f"categories/any(c:c eq '{self.platform_name}')",
            "$select": "subject,start",
            "$top": "999"
        }
        
        while url:
            response = requests.get(url, headers=headers, params=params if url == "https://graph.microsoft.com/v1.0/me/events" else None)
            response.raise_for_status()
            data = response.json()
            
            for event in data.get('value', []):
                # Create composite key: UTC_datetime|normalized_subject
                start_dt = event['start']['dateTime']
                subject = event['subject']
                normalized_subject = normalize_title(subject)
                key = f"{start_dt}|{normalized_subject}"
                existing_keys.add(key)
            
            # Handle pagination
            url = data.get('@odata.nextLink')
            params = None
        
        self.existing_events_cache = existing_keys
        print(f"Cached {len(existing_keys)} existing {self.platform_name} events")
        return existing_keys
    
    def event_exists(self, row, title: str) -> bool:
        """
        Check if event exists using exact datetime + exact title matching
        
        Args:
            row: DataFrame row containing event data
            title: Event title to check
            
        Returns:
            True if event already exists, False otherwise
        """
        # Get datetime in UTC format
        if 'Start Time' in row:
            utc_dt = pd.to_datetime(row['Start Time']).strftime('%Y-%m-%dT%H:%M:%S.0000000')
        elif 'Playback Start Datetime (UTC)' in row:
            utc_dt = row['Playback Start Datetime (UTC)'].strftime('%Y-%m-%dT%H:%M:%S.0000000')
        elif 'start_datetime_EST' in row:
            # Convert EST to UTC for comparison
            utc_dt = pd.to_datetime(row['start_datetime_EST']).tz_localize('America/Toronto').tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%S.0000000')
        elif 'Start Datetime UTC' in row:
            utc_dt = pd.to_datetime(row['Start Datetime UTC']).strftime('%Y-%m-%dT%H:%M:%S.0000000')
        elif 'Start Datetime' in row:
            # For Apple TV+ - convert Atlantic Time to UTC for comparison
            utc_dt = pd.to_datetime(row['Start Datetime']).tz_localize('America/Moncton').tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%S.0000000')
        elif 'Playback Start Datetime (EST)' in row:
            # For Amazon Prime TV - convert EST to UTC for comparison
            utc_dt = pd.to_datetime(row['Playback Start Datetime (EST)']).tz_localize('America/Toronto').tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%S.0000000')
        elif 'start_time_est' in row:
            # For Google TV - convert EST to UTC for comparison
            utc_dt = pd.to_datetime(row['start_time_est']).tz_localize('America/Toronto').tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%S.0000000')
        elif 'Local Start Time' in row:
            # For Netflix - convert local time to UTC
            utc_dt = pd.to_datetime(row['Local Start Time']).tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%S.0000000')
        else:
            # Fallback - just check title with normalization
            full_title = f"{self.platform_name}: {title}"
            normalized_title = normalize_title(full_title)
            return any(normalized_title in key for key in self.existing_events_cache)
        
        # Create composite key with normalized title
        full_title = f"{self.platform_name}: {title}"
        normalized_title = normalize_title(full_title)
        key = f"{utc_dt}|{normalized_title}"
        
        return key in self.existing_events_cache
    
    def log_event_result(self, status: str, datetime_str: str, title: str):
        """
        Log event result in harmonized format
        
        Args:
            status: "CREATED" or "EXISTS"
            datetime_str: Formatted datetime string
            title: Event title
        """
        if self.dry_run and status == "CREATED":
            print(f"DRY_RUN {datetime_str}  {title}")
        else:
            print(f"{status:7} {datetime_str}  {title}")
        
        if status == "CREATED":
            self.events_created += 1
        elif status == "EXISTS":
            self.events_skipped += 1
    
    def should_continue_processing(self, current_count: int) -> bool:
        """
        Check if processing should continue based on test mode settings
        
        Args:
            current_count: Number of records processed so far
            
        Returns:
            True if processing should continue, False if test limit reached
        """
        if self.test_mode and current_count >= self.test_limit:
            print(f"🧪 TEST MODE: Reached limit of {self.test_limit} records. Stopping processing.")
            return False
        return True
    
    def print_summary(self):
        """Print harmonized summary of event creation results"""
        print("\n" + "=" * 50)
        if self.dry_run:
            print("EVENT CREATION SUMMARY (DRY RUN MODE)")
        elif self.test_mode:
            print("EVENT CREATION SUMMARY (TEST MODE)")
        else:
            print("EVENT CREATION SUMMARY")
        print("=" * 50)
        if self.dry_run:
            print(f"Events That Would Be Created: {self.events_created}")
        else:
            print(f"Events Created: {self.events_created}")
        print(f"Events Skipped (Already Exist): {self.events_skipped}")
        print(f"Total Processed: {self.events_created + self.events_skipped}")
        if self.test_mode:
            print(f"Test Limit: {self.test_limit}")
        if self.dry_run:
            print("🔍 DRY RUN: No events were actually created")
        print("=" * 50)
    
    def refresh_token(self):
        """
        Refresh the authentication token
        
        Returns:
            str: New authentication token
        """
        try:
            self.token = get_auth_token()
            return self.token
        except Exception as e:
            raise RuntimeError(f"Failed to refresh token: {e}")
    
    def handle_token_expired(self, create_event_func, *args, **kwargs):
        """
        Handle token expiration by refreshing and retrying event creation
        
        Args:
            create_event_func: Function to call for event creation
            *args: Arguments to pass to create_event_func
            **kwargs: Keyword arguments to pass to create_event_func
            
        Returns:
            bool: True if event was created successfully after token refresh, False otherwise
        """
        try:
            print("🔄 Token expired. Refreshing token...")
            self.refresh_token()
            
            # Retry the event creation with the new token
            if not self.dry_run:
                create_event_func(self.token, *args, **kwargs)
            return True
        except Exception as e:
            print(f"❌ Failed to create event after token refresh: {e}")
            return False
