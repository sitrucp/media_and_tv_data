# Get Outlook Events - Calendar Event Management

This is the **Get Outlook Events** module of the [Media TV and Movies - Calendar Event Creation System](../README.md). This module retrieves, manages, and visualizes existing calendar events from Outlook.

## 📋 Overview

This module is part of a comprehensive, harmonized system for creating calendar events from media platform viewing data. For general information about the project architecture, features, and setup, see the [main project README](../README.md).

## 🎯 Get Outlook Events-Specific Features

- **Event Retrieval**: Fetch existing calendar events from Outlook
- **Data Export**: Export events to Excel and CSV formats
- **Event Management**: Edit and update existing calendar events
- **Visualization**: Create charts and visualizations of viewing data
- **SharePoint Integration**: Sync events with SharePoint lists

## 📊 Data Sources

### **Input**: Microsoft Graph API Calendar Events
- **Source**: Outlook calendar via Microsoft Graph API
- **Processing**: Retrieved, processed, and exported by various utility scripts
- **Format**: JSON from API, exported to Excel/CSV formats

## 🚀 Quick Start

### **Prerequisites**
- **Microsoft Graph API Credentials**: See [main project README](../README.md) for setup
- **Required Libraries**: `pandas`, `numpy`, `requests`, `pytz`, `openpyxl`

### **Step 1: Retrieve Calendar Events**
```bash
python get_events.py
```
- **Input**: Microsoft Graph API calendar endpoint
- **Output**: `tv_and_movie_events.xlsx` (exported events)

### **Step 2: Additional Features (Optional)**
- **Use the event data that was downloaded to do analysis or view in Excel file.

## ⚙️ Configuration Options

### **Event Retrieval Settings**
```python
# In get_events.py
START_DATE = "2024-01-01"  # Start date for event retrieval
END_DATE = "2025-12-31"    # End date for event retrieval
CATEGORY_FILTER = "Netflix" # Filter by specific platform category
```

### **Export Settings**
```python
# In get_events.py
EXPORT_FORMAT = "xlsx"      # Export format: xlsx, csv, or both
INCLUDE_DETAILS = True      # Include detailed event information
```

## 📁 Directory Structure

```
get_outlook_events/
├── README.md                    # This file
├── get_events.py               # Main event retrieval script
├── tv_and_movie_events.xlsx    # Exported events (ignored by git)
```

## 📝 Expected Output

### **Console Logging**
```
Starting Outlook event retrieval...
Access token obtained successfully
Retrieving events from 2024-01-01 to 2025-12-31
Found 150 events in calendar
Filtering by category: Netflix
Found 25 Netflix events
Exporting to Excel format...
Events exported to tv_and_movie_events.xlsx
```

### **Export Files**
- **`tv_and_movie_events.xlsx`**: Complete event data in Excel format
- **`viz_chart_tv_movie.png`**: Visualization chart of viewing patterns

## 🔧 Additional Features

### **Event Management**
- **Event Retrieval**: Fetch existing calendar events from Outlook
- **Data Export**: Export events to Excel and CSV formats
- **Event Editing**: Modify and update existing calendar events
- **Data Visualization**: Create charts and visualizations of viewing data

## 🔗 Related Documentation

- **[Main Project README](../README.md)**: Overall system architecture and setup
- **[Technical Documentation](../README.md#technical-documentation)**: Detailed system implementation
- **[Platform Modules](../README.md#supported-platforms)**: Individual platform event creation modules

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.
