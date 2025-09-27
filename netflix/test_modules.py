#!/usr/bin/env python3
"""
Test script to verify both modules work correctly after the split.
This script tests the modules without actually creating calendar events.
"""

import pandas as pd
import os
import sys

def test_process_raw_data():
    """Test the process_raw_data module"""
    print("Testing process_raw_data module...")
    
    # Check if required input file exists
    if not os.path.exists("ViewingActivity.csv"):
        print("❌ ViewingActivity.csv not found. Cannot test process_raw_data module.")
        return False
    
    # Check if log file exists
    if not os.path.exists("last_event_date.csv"):
        print("❌ last_event_date.csv not found. Cannot test process_raw_data module.")
        return False
    
    try:
        # Import and run the process_raw_data module
        import process_raw_data
        result_df = process_raw_data.main()
        
        # Check if output file was created
        if os.path.exists("FilteredViewingActivity.csv"):
            print("✅ process_raw_data module completed successfully")
            print(f"✅ Output file created: FilteredViewingActivity.csv")
            print(f"✅ Processed {len(result_df)} records")
            return True
        else:
            print("❌ Output file FilteredViewingActivity.csv was not created")
            return False
            
    except Exception as e:
        print(f"❌ Error testing process_raw_data module: {e}")
        return False

def test_create_events_structure():
    """Test the create_events module structure without actually creating events"""
    print("\nTesting create_events module structure...")
    
    # Check if processed input file exists
    if not os.path.exists("FilteredViewingActivity.csv"):
        print("❌ FilteredViewingActivity.csv not found. Run process_raw_data first.")
        return False
    
    try:
        # Import the create_events module
        import create_events
        
        # Check if required functions exist
        required_functions = ['event_exists', 'create_calendar_event', 'main']
        for func_name in required_functions:
            if hasattr(create_events, func_name):
                print(f"✅ Function {func_name} found")
            else:
                print(f"❌ Function {func_name} not found")
                return False
        
        # Test reading the processed CSV
        df = pd.read_csv("FilteredViewingActivity.csv", parse_dates=["Local Start Time"])
        print(f"✅ Successfully read processed CSV with {len(df)} records")
        
        # Check required columns
        required_columns = ['Title', 'Local Start Time', 'Timezone', 'Duration', 'Start Time', 'Local Start Date']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        else:
            print("✅ All required columns present in processed data")
        
        print("✅ create_events module structure is correct")
        return True
        
    except Exception as e:
        print(f"❌ Error testing create_events module: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("Testing Netflix Module Split")
    print("=" * 60)
    
    # Test process_raw_data module
    process_test_passed = test_process_raw_data()
    
    # Test create_events module structure
    events_test_passed = test_create_events_structure()
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    if process_test_passed and events_test_passed:
        print("🎉 All tests passed! The module split was successful.")
        print("\nNext steps:")
        print("1. Run 'python process_raw_data.py' to process Netflix data")
        print("2. Run 'python create_events.py' to create calendar events")
    else:
        print("❌ Some tests failed. Please check the issues above.")
        
    return process_test_passed and events_test_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
