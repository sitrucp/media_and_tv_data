# Media TV and Movies - Stremaing Service Data and Outlook Calendar Event Creation

This contains instructions about how to get the data from a bunch of streaming services (Netflix, Amazon Prime, Apple TV+, Crave TV, Disney+, and Google TV) so you can use the data for your own purposes but this project focuses on using the data to create Outlook calendar events for the shows and movies you have watched.

## 🏗️ Architecture

### **Shared Components**
- **`shared_event_utils.py`**: Core shared functionality including `EventManager` class, authentication, and duplicate detection
- **Centralized Authentication**: Microsoft Graph API token management
- **Advanced Duplicate Detection**: Bulk caching with exact datetime + title matching
- **Title Normalization**: Handles encoding issues and character variations

### **Platform Modules**
Each platform has its own directory with specialized processing:
- **Netflix**: Timezone conversion and duration calculation
- **Amazon Prime TV**: EST timezone handling and bulk caching
- **Apple TV+**: Atlantic timezone and episode formatting
- **Crave TV**: Series/movie distinction and rate limiting
- **Disney+**: Watch time calculation and manual date filtering
- **Google TV**: Duration estimation and EST timezone

## 🚀 Key Features

### **1. Advanced Testing & Validation**
- **Test Mode**: Process limited records for quick testing
- **Dry Run Mode**: Process all records without creating events
- **Production Mode**: Full event creation with comprehensive logging

### **2. Defensive Programming**
- **Manual Date Filtering**: `LAST_EVENT_DATE` prevents processing old events
- **Timezone Protection**: Guards against timezone-related duplicate creation
- **Robust Error Handling**: Centralized token refresh and retry logic

### **3. Harmonized Experience**
- **Consistent Logging**: Standardized console output across all platforms
- **Unified Configuration**: Same settings pattern for all platforms
- **Comprehensive Summaries**: Detailed reporting of created vs skipped events

## 📊 Supported Platforms

| Platform | Data Source | Data File Name |
|----------|-------------|----------------|
| **Netflix** | Download data | `ViewingActivity.csv` |
| **Amazon Prime TV** | Download data | `PrimeVideo.ViewingHistory.csv` |
| **Apple TV+** | Download data | `TV App Favorites and Activity.json` |
| **Crave TV** | Manual website JSON | `watchHistory_pageNumber_0.json`, `graphql_0.json` |
| **Disney+** | Scraping watchlist API | `watchlist_progress_raw_manual_dates.csv` |
| **Google TV** | Download data | `Library.json`, `Purchase History.json` |
| **Get Outlook Events** | Microsoft Graph API | N/A (direct API access) |

## 🎛️ Quick Start

### **1. Prerequisites**
- **Microsoft Graph API Credentials**: `client_id`, `tenant_id`, `client_secret`, `user_id`
- **Required Libraries**: `pandas`, `numpy`, `requests`, `pytz`, `ftfy`
- **Python 3.9+**: For timezone support

### **2. Configuration**
```python
# In any platform's create_events.py
TEST_MODE = False      # Set to True for limited testing
DRY_RUN = True         # Set to True for safe validation
LAST_EVENT_DATE = "2025-01-01"  # Update to your desired cutoff date
```

### **3. Usage Examples**

#### **Safe Validation (Recommended First Run)**
```python
TEST_MODE = False  # Process all records
DRY_RUN = True     # Don't create events, just show what would happen
```

#### **Limited Testing**
```python
TEST_MODE = True   # Process only limited records
DRY_RUN = False    # Actually create events
TEST_LIMIT = 5     # Process only 5 records
```

#### **Production Run**
```python
TEST_MODE = False  # Process all records
DRY_RUN = False    # Actually create all events
```

### **4. Running a Platform**
```bash
cd netflix  # or any platform directory
python create_events.py
```

## 📁 Repository Structure

```
media_tv_and_movies/
├── README.md                           # This file - overall project documentation
├── shared_event_utils.py              # Core shared functionality
├── .gitignore                         # Consolidated gitignore for all platforms
├── netflix/
│   ├── README.md                      # Netflix-specific documentation
│   ├── create_events.py               # Netflix event creation
│   ├── process_raw_data.py            # Netflix data processing
│   ├── test_modules.py                # Netflix testing utilities
│   ├── ViewingActivity_example.csv    # Example data file
│   ├── FilteredViewingActivity_example.csv # Example processed data
│   └── create_events_log_example.txt  # Example log file
├── amazon_prime_tv/
│   ├── README.md                      # Amazon Prime TV-specific documentation
│   ├── create_events.py               # Amazon Prime TV event creation
│   ├── process_raw_data.py            # Amazon Prime TV data processing
│   ├── test.py                        # Amazon Prime TV testing utilities
│   ├── PrimeVideo.ViewingHistory_example.csv # Example data file
│   ├── PrimeVideo.ViewingHistory_clean_example.csv # Example processed data
│   └── create_event_log_example.txt   # Example log file
├── apple_tv_plus/
│   ├── README.md                      # Apple TV+ specific documentation
│   ├── create_events.py               # Apple TV+ event creation
│   ├── process_raw_data.py            # Apple TV+ data processing
│   ├── TV App Favorites and Activity_example.json # Example data file
│   ├── TV App Favorites and Activity_example.csv # Example processed data
│   └── create_events_log_example.txt  # Example log file
├── crave_tv/
│   ├── README.md                      # Crave TV-specific documentation
│   ├── create_events.py               # Crave TV event creation
│   ├── process_raw_data.py            # Crave TV data processing
│   ├── watchHistory_pageNumber_0_example.json # Example data file
│   ├── graphql_0_example.json         # Example data file
│   ├── raw_data_clean_example.csv     # Example processed data
│   └── create_events_log_example.txt  # Example log file
├── disney_plus/
│   ├── README.md                      # Disney+ specific documentation
│   ├── create_events.py               # Disney+ event creation
│   ├── get_watchlist.py               # Disney+ API wrapper
│   ├── update_manual_watchlist.py     # Manual datetime management
│   ├── watchlist_progress_raw_manual_dates_example.csv # Example data file
│   ├── create_events_log_example.txt  # Example log file
│   └── Disney-Plus-api-wrapper-master/ # Third-party Disney+ API wrapper
│       ├── src/pydisney/              # Disney+ API library
│       ├── LICENSE                    # API wrapper license
│       └── README.md                  # API wrapper documentation
├── google_tv/
│   ├── README.md                      # Google TV-specific documentation
│   ├── create_events.py               # Google TV event creation
│   ├── create_1_library_csv.py        # Convert Library.json to CSV
│   ├── create_2_purchase_history_csv.py # Convert Purchase History.json to CSV
│   ├── create_3_combine_library_purch_hist.py # Merge CSV files
│   ├── Library_example.json           # Example data file
│   ├── Library_example.csv            # Example converted data
│   ├── Purchase History_example.json  # Example data file
│   ├── Purchase History_example.csv   # Example converted data
│   ├── combine_library_purch_hist_example.csv # Example merged data
│   └── create_events_log_example.txt  # Example log file
└── get_outlook_events/
    ├── README.md                      # Get Outlook Events documentation
    └── get_events.py                  # Event retrieval and management
```

## 📖 Documentation

### **Project-Specific Details**
Each platform directory contains its own `README.md` with:
- **Data Source Instructions**: How to obtain viewing history data
- **Platform-Specific Setup**: Unique requirements and configurations
- **Workflow Details**: Step-by-step processing instructions
- **Example Directory Structures**: Expected file layouts

### **Example Files**
Each platform includes example files (e.g., `*_example.csv`, `*_example.json`) that show the expected format and structure of data files. These files will either be generated by the logging processes eg for the log files or will be source data files you will download and save in the folder. These example files:
- **Show the required format** for your actual data files
- **Include sample data** to demonstrate the expected structure
- **Are included in the repository** for reference
- **Should be replaced** with your actual data files when you run the scripts

### **Technical Documentation**
See the [Technical Documentation](#technical-documentation) section below for comprehensive system details.

## 🔧 Configuration Options

### **Test Mode Settings**
```python
TEST_MODE = False  # Set to True for limited testing
TEST_LIMIT = 10    # Number of records to process in test mode
```

### **Dry Run Mode Settings**
```python
DRY_RUN = True     # Set to True to see what would happen without creating events
```

### **Date Filtering**
```python
LAST_EVENT_DATE = "2025-01-01"  # Only process events after this date
```

## 📊 Expected Output

### **Console Logging**
```
🔍 DRY RUN MODE ENABLED - Will show what would happen without creating events
Starting Netflix event creation...
Access token obtained successfully
Cached 150 existing Netflix events
Found 25 records to process
Filtering to events after 2025-01-01. Found 20 records to process.
EXISTS  2024-04-28 15:54:32  The Crown S6 E1
DRY_RUN 2024-04-28 16:30:15  The Crown S6 E2
```

### **Summary Report**
```
==================================================
EVENT CREATION SUMMARY (DRY RUN MODE)
==================================================
Events That Would Be Created: 3
Events Skipped (Already Exist): 2
Total Processed: 5
🔍 DRY RUN: No events were actually created
==================================================
```

## 🛡️ Error Handling

- **Automatic Token Refresh**: 401 errors trigger automatic token refresh and retry
- **Rate Limiting**: Built-in support for API rate limits (especially Crave TV)
- **Data Validation**: Comprehensive timezone and date validation
- **Encoding Issues**: Automatic normalization handles mojibake and Unicode problems

## 🎯 Benefits

### **1. Reliability**
- **Bulk Caching**: Reduces API calls and improves performance
- **Exact Duplicate Detection**: Prevents true duplicates while allowing legitimate variations
- **Defensive Programming**: Manual date filtering protects against timezone issues

### **2. Maintainability**
- **Shared Utilities**: Single source of truth for common functionality
- **Consistent Patterns**: All platforms follow the same architecture
- **Clean Code**: Consolidated, well-documented codebase

### **3. User Experience**
- **Harmonized Logging**: Consistent, informative console output
- **Testing Modes**: Safe validation without risk of unwanted events
- **Clear Feedback**: Detailed summaries and error messages

## 🚀 Getting Started

1. **Clone the repository**
2. **Set up Microsoft Graph API credentials**
3. **Install required Python packages**
4. **Choose a platform and follow its specific README.md**
5. **Start with dry run mode for safe validation**
6. **Configure date filtering as needed**
7. **Run in production mode**

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome. The modular architecture makes it easy to add new platforms or enhance existing functionality.

## 📞 Support

For platform-specific issues, refer to the individual platform README.md files. For general system questions, see the [Technical Documentation](#technical-documentation) section above for detailed technical documentation.

---

## 📚 Technical Documentation

### **Architecture Overview**

A comprehensive, harmonized system for creating calendar events from media platform viewing data. All platforms (Netflix, Amazon Prime TV, Apple TV+, Crave TV, Disney+, Google TV) use a shared architecture for consistent, reliable event creation with advanced duplicate detection and testing capabilities.

### **Core Components**

#### **1. Shared Event Management (`shared_event_utils.py`)**
- **`EventManager` Class**: Centralized event creation, duplicate detection, and logging
- **`get_auth_token()` Function**: Centralized Microsoft Graph API authentication
- **`normalize_title()` Function**: Advanced title normalization for encoding issues

#### **2. Platform Modules**
Each platform has a dedicated `create_events.py` module that:
- Processes platform-specific CSV data
- Uses the shared `EventManager` for all operations
- Handles platform-specific timezone and formatting requirements

### **Key Features**

#### **1. Advanced Duplicate Detection**
- **Bulk Caching**: Fetches all existing events once per run
- **Exact Matching**: Same datetime + same title = duplicate
- **Title Normalization**: Handles encoding issues (mojibake, Unicode)
- **Smart Logic**: Allows rewatches (different datetime) and metadata updates (different title)

#### **2. Testing & Validation Modes**
- **Test Mode**: Process limited records for quick testing
- **Dry Run Mode**: Process all records without creating events
- **Production Mode**: Full event creation with comprehensive logging

#### **3. Defensive Date Filtering**
- **Manual Control**: `LAST_EVENT_DATE` filter prevents processing old events
- **Timezone Protection**: Guards against timezone-related duplicate creation
- **Easy Maintenance**: Simple date string to update per platform

#### **4. Centralized Token Management**
- **Automatic Authentication**: Token obtained automatically by `EventManager`
- **Token Refresh**: Centralized 401 error handling with automatic retry
- **Consistent Error Handling**: Unified approach across all platforms

### **Platform Details**

| Platform | Category | Input File | Key Features |
|----------|----------|------------|--------------|
| **Netflix** | "Netflix" | `FilteredViewingActivity.csv` | Timezone conversion, duration calculation |
| **Amazon Prime TV** | "Prime TV" | `PrimeVideo.ViewingHistory_clean.csv` | EST timezone, bulk caching |
| **Apple TV+** | "Apple TV Plus" | `TV App Favorites and Activity.csv` | Atlantic timezone, episode formatting |
| **Crave TV** | "Crave TV" | `raw_data_clean.csv` | Series/movie distinction, rate limiting |
| **Disney+** | "Disney Plus" | `watchlist_progress_raw_manual_dates.csv` | Watch time calculation, manual date filtering |
| **Google TV** | "Google TV" | `combine_library_purch_hist.csv` | Duration estimation, EST timezone |

### **Technical Implementation**

#### **EventManager Class**
```python
class EventManager:
    def __init__(self, platform_name, token=None, test_mode=False, test_limit=5, dry_run=False)
    def fetch_existing_events(self) -> Set[str]
    def event_exists(self, row, title: str) -> bool
    def log_event_result(self, status: str, datetime_str: str, title: str)
    def should_continue_processing(self, current_count: int) -> bool
    def print_summary(self)
    def refresh_token(self)
    def handle_token_expired(self, create_event_func, *args, **kwargs)
```

#### **Title Normalization**
```python
def normalize_title(s: str) -> str:
    # Fixes mojibake, Unicode normalization, case folding, punctuation collapse
    # Handles: â€™ → ', â€œ → ", â€ → ", etc.
```

### **Error Handling**

#### **Token Management**
- **Automatic Refresh**: 401 errors trigger automatic token refresh
- **Retry Logic**: Failed events are retried with new token
- **Graceful Degradation**: Clear error messages for authentication failures

#### **Rate Limiting**
- **Crave TV**: Built-in rate limiting with `Retry-After` header support
- **All Platforms**: Centralized error handling for HTTP errors

#### **Data Validation**
- **Timezone Handling**: Proper timezone conversion and validation
- **Date Filtering**: Manual date filtering prevents timezone-related issues
- **Encoding Issues**: Automatic normalization handles mojibake and Unicode problems

### **Benefits**

#### **1. Reliability**
- **Bulk Caching**: Reduces API calls and improves performance
- **Exact Duplicate Detection**: Prevents true duplicates while allowing legitimate variations
- **Defensive Programming**: Manual date filtering protects against timezone issues

#### **2. Maintainability**
- **Shared Utilities**: Single source of truth for common functionality
- **Consistent Patterns**: All platforms follow the same architecture
- **Clean Code**: Removed redundant code and outdated patterns

#### **3. User Experience**
- **Harmonized Logging**: Consistent, informative console output
- **Testing Modes**: Safe validation without risk of unwanted events
- **Clear Feedback**: Detailed summaries and error messages

#### **4. Flexibility**
- **Easy Configuration**: Simple boolean flags for different modes
- **Platform-Specific**: Each platform handles its unique requirements
- **Extensible**: Easy to add new platforms following the same pattern

---

**Status**: ✅ **Production Ready** - All platforms harmonized with centralized event management, advanced duplicate detection, and comprehensive testing capabilities.

