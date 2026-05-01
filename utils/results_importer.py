# utils/results_importer.py   ← REPLACE THE ENTIRE FILE WITH THIS
import os
import sqlite3
from datetime import datetime
import pandas as pd
from config import DB_DIR, PXM_JOBS

def ensure_results_table(db_dir=DB_DIR):
    """Safe create-only (no drop on page load — fixes empty state)"""
    results_db_file = os.path.join(db_dir, "DH5_AS-T1_results.db")
    conn = sqlite3.connect(results_db_file)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS "DH5_AS-T1_results" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            test_name TEXT NOT NULL,
            test_date TEXT,
            tester TEXT DEFAULT 'PXM',
            opm_files TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def pull_and_import_results(pxm_jobs_dir=PXM_JOBS):
    if not os.path.exists(pxm_jobs_dir):
        return "❌ PXM drive not found.\n\nPlease connect your PXM (as drive E:) and click 'Upload Test Results' again."

    # One-time migration only on button click (old table is safely replaced)
    results_db_file = os.path.join(DB_DIR, "DH5_AS-T1_results.db")
    conn = sqlite3.connect(results_db_file)
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS "DH5_AS-T1_results"')  # safe — no real data yet
    cursor.execute('''
        CREATE TABLE "DH5_AS-T1_results" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            test_name TEXT NOT NULL,
            test_date TEXT,
            tester TEXT DEFAULT 'PXM',
            opm_files TEXT,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

    ensure_results_table()
    conn = sqlite3.connect(results_db_file)
    cursor = conn.cursor()

    imported = 0
    for job in os.listdir(pxm_jobs_dir):
        job_path = os.path.join(pxm_jobs_dir, job)
        if not os.path.isdir(job_path): continue

        for test in os.listdir(job_path):
            test_path = os.path.join(job_path, test)
            if not os.path.isdir(test_path): continue
            if test.lower() in ['archive', 'db']: continue

            opm_list = [f for f in os.listdir(test_path) if f.lower().endswith('.opm')]
            opm_str = ','.join(opm_list) if opm_list else ''

            cursor.execute('SELECT 1 FROM "DH5_AS-T1_results" WHERE job_name=? AND test_name=?', (job, test))
            if cursor.fetchone(): continue

            today = datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute('''
                INSERT INTO "DH5_AS-T1_results" 
                (job_name, test_name, test_date, tester, opm_files, notes)
                VALUES (?, ?, ?, 'PXM', ?, 'Contains .opm files')
            ''', (job, test, today, opm_str))
            imported += 1

    conn.commit()
    conn.close()
    return f"✅ Imported {imported} real test folder(s)!\n(archive + db skipped — your 3 test folders should now appear)"

def get_results_data(db_dir=DB_DIR):
    ensure_results_table(db_dir)
    results_db_file = os.path.join(db_dir, "DH5_AS-T1_results.db")
    if not os.path.exists(results_db_file):
        return []
    conn = sqlite3.connect(results_db_file)
    df = pd.read_sql_query('SELECT * FROM "DH5_AS-T1_results" ORDER BY job_name, test_name', conn)
    conn.close()
    return df.to_dict('records') if not df.empty else []