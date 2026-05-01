import sys
import os
import sqlite3

def inspect_db(db_name):
    db_path = os.path.join('data', f'{db_name}.db')
    if not os.path.exists(db_path):
        print(f'❌ DB not found: {db_path}')
        print('   Make sure you ran "Create Jobs" first and the file exists in data/')
        return

    conn = sqlite3.connect(db_path)
    table_name = db_name

    print(f'=== TABLE: "{table_name}" ===')
    print('COLUMNS (name, type, notnull, default, pk):')
    for row in conn.execute(f'PRAGMA table_info("{table_name}");').fetchall():
        print(row)

    print('\n=== FIRST 5 ROWS (preview) ===')
    for row in conn.execute(f'SELECT * FROM "{table_name}" LIMIT 5;').fetchall():
        print(row)

    conn.close()
    print(f'\n✅ Done inspecting {db_path}')

if __name__ == '__main__':
    # Default to your DB if no argument given
    db_name = sys.argv[1] if len(sys.argv) > 1 else 'DH16_RT1-RT2'
    inspect_db(db_name)