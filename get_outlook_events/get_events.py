# get_events.py

import os
import sys
import pandas as pd
import requests
import pytz
from datetime import datetime, timedelta
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

# Import shared utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_event_utils import get_auth_token

# --- Debug Toggle --- #
DEBUG_MODE = False  # Set to True for fetching just 1 event for testing

# -------- File Output ------------------------------------------------------------
excel_file_out = ("tv_and_movie_events.xlsx")

# -------- Helpers ------------------------------------------------------------
EST = pytz.timezone("US/Eastern")

def to_est(dt_str):
    if "." in dt_str:
        head, tail = dt_str.split(".")
        dt_str = f"{head}.{tail[:6]}"
    return (datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
            .replace(tzinfo=pytz.utc)
            .astimezone(EST))

def make_event_id(title, start_str, max_len=250):
    eid = f"{title}_{start_str}"
    return eid[:max_len]

# -------- Calendar Query -----------------------------------------------------
def fetch_events(token, categories, start_dt, end_dt, existing_ids, next_num):
    s, e = start_dt.isoformat() + "Z", end_dt.isoformat() + "Z"
    url = (f"https://graph.microsoft.com/v1.0/me/calendarView"
           f"?startDateTime={s}&endDateTime={e}"
           f"&$select=subject,start,end,categories"
           f"&$top=100&$count=true")
    headers = {"Authorization": f"Bearer {token}"}

    items, page = [], 0
    while url:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        page += 1
        print(f"  • page {page}")
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
        if url is None and len(items) == 10_000 and data.get("@odata.count", 0) > 10_000:
            print("  ! hit 10,000-item cap; consider smaller chunks")
            break

    brand_new = []
    cat_match = 0
    for ev in items:
        if not any(c in ev.get("categories", []) for c in categories):
            continue
        cat_match += 1

        s_est = to_est(ev["start"]["dateTime"])
        e_est = to_est(ev["end"]["dateTime"])
        start_str = s_est.strftime("%Y-%m-%d %H:%M:%S")
        end_str = e_est.strftime("%Y-%m-%d %H:%M:%S")
        eid = make_event_id(ev["subject"], start_str)

        if eid in existing_ids:
            continue

        brand_new.append({
            "Title": ev["subject"] or "",
            "Start Datetime": start_str,
            "End Datetime": end_str,
            "Duration Minutes": (e_est - s_est).total_seconds() / 60,
            "Date Added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Categories": "; ".join(ev.get("categories", [])),
            "EventID": eid,
            "EventNumber": next_num,
        })

        existing_ids.add(eid)
        next_num += 1

        if DEBUG_MODE:
            print("🔍 DEBUG_MODE active – breaking after 1 event.")
            break

    return brand_new, len(items), cat_match, next_num

# -------- Excel I/O ----------------------------------------------------------

def load_existing():
    if os.path.exists(excel_file_out):
        df = pd.read_excel(excel_file_out)
        id_set = set(df.get("EventID", []).dropna().astype(str))
        max_num = pd.to_numeric(df.get("EventNumber", []), errors="coerce").max()
        last_num = 999 if pd.isna(max_num) else int(max_num)
    else:
        cols = ["Title", "Start Datetime", "End Datetime", "Duration Minutes",
                "Date Added", "Categories", "EventNumber", "EventID"]
        df = pd.DataFrame(columns=cols)
        id_set, last_num = set(), 999
    return df, id_set, last_num

def save_excel(df, table_name="Events"):
    df.to_excel(excel_file_out, index=False)
    wb = load_workbook(excel_file_out)
    ws = wb.active
    max_row = ws.max_row
    max_col = ws.max_column
    last_col_l = get_column_letter(max_col)
    table_ref = f"A1:{last_col_l}{max_row}"

    if table_name in ws.tables:
        del ws.tables[table_name]

    tbl = Table(displayName=table_name, ref=table_ref)
    tbl.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium9", showFirstColumn=False,
        showLastColumn=False, showRowStripes=True, showColumnStripes=False
    )
    ws.add_table(tbl)
    wb.save(excel_file_out)
    print(f"✅ Saved & table '{table_name}' refreshed → {excel_file_out}")

# -------- Main ---------------------------------------------------------------
def main():
    token = get_auth_token()
    categories = ["Netflix", "Apple TV Plus", "Prime TV", "Google TV", "Crave TV", "Disney Plus"]

    start_all = datetime(2011, 1, 1)
    end_all = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    chunk_days = 90

    existing_df, existing_ids, last_num = load_existing()
    next_num = last_num + 1
    new_rows = []

    current = start_all
    while current < end_all:
        chunk_end = min(end_all, current + timedelta(days=chunk_days) - timedelta(seconds=1))
        print(f"\nProcessing {current.date()} → {chunk_end.date()}")

        len(existing_ids)
        rows, raw_count, cat_match, next_num = fetch_events(
            token, categories, current, chunk_end, existing_ids, next_num
        )
        after = len(existing_ids)

        print(f"    ↳ {len(rows)} new events, total {after}")

        new_rows.extend(rows)
        current = chunk_end + timedelta(seconds=1)

    if new_rows:
        df_final = pd.concat([existing_df, pd.DataFrame(new_rows)], ignore_index=True)
        save_excel(df_final)
        print(f"🔄 Total new events appended: {len(new_rows)}")
    else:
        print("No new events to add — Excel is up-to-date!")

if __name__ == "__main__":
    main()
