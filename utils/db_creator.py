# utils/db_creator.py
import pandas as pd
import sqlite3
import os
from .sheet_parser import parse_sheet_name

def auto_import_excel_to_sql(filepath, db_dir):
    if not os.path.exists(filepath):
        return []
    excel_file = pd.ExcelFile(filepath)
    imported = []
    seen = set()
    for sheet_name in excel_file.sheet_names:
        short_dh, full_name = parse_sheet_name(sheet_name)
        if short_dh is None or full_name is None:
            continue
        key = full_name
        if key in seen:
            continue
        seen.add(key)
        df = pd.read_excel(filepath, sheet_name=sheet_name, engine='openpyxl')
        db_file = os.path.join(db_dir, f"{full_name}.db")
        conn = sqlite3.connect(db_file)
        df.to_sql(full_name, conn, if_exists='replace', index=False)
        conn.close()
        imported.append({'short_dh': short_dh, 'full_name': full_name})
    return imported