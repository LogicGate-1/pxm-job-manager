# utils/data_utils.py
import sqlite3
import pandas as pd
import os

def ensure_directories(*dirs):
    """Create directories safely. Skips external drives (like PXM E:) if not connected."""
    for d in dirs:
        if not d:
            continue
        # Special handling for drive letters (e.g. 'E:\\Jobs')
        drive_root = None
        if len(str(d)) >= 2 and str(d)[1] == ':':
            drive_root = str(d)[0] + ':\\'
        if drive_root and not os.path.exists(drive_root):
            print(f"WARNING: PXM drive {drive_root[0]}: not connected - skipping folder creation")
            continue
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            print(f"WARNING: Could not create directory {d}: {e}")

def get_data_from_db(selected_db, db_dir):
    """Fixed version - safely handles table names with hyphens (DH16_RT1-RT2, etc.)"""
    db_file = os.path.join(db_dir, f"{selected_db}.db")
    conn = sqlite3.connect(db_file)
    query = f'SELECT * FROM "{selected_db}"'
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def import_excel_to_sql(filepath, selected_sheet, db_dir):
    # Legacy function (not used by Create Jobs) - left unchanged
    dh = selected_sheet.split(' |')[0].strip() if ' |' in selected_sheet else selected_sheet
    df = pd.read_excel(filepath, sheet_name=selected_sheet, engine='openpyxl')
    dynamic_db_file = os.path.join(db_dir, f"{dh}.db")
    conn = sqlite3.connect(dynamic_db_file)
    df.to_sql(dh, conn, if_exists='replace', index=False)
    conn.close()
    return dh