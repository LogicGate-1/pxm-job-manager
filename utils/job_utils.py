import os
import sys
import pandas as pd
import re   # <-- used for dot-cleaning + B##- stripping

# Add root directory to sys.path for imports when run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COLUMN_MAPPING
from .job_folder_creator import create_job_folder

# Fallback keywords (A-PORT is the single source for global Min/Max)
KEYWORD_FALLBACK = {
    'type': 'TYPE',
    'a_room': 'A-ROOM',
    'a_rack': 'A-RACK',
    'a_ru': 'A-RU',
    'a_device': 'A-DEVICE SIMPLE',      # used for folder name (NSJ-AS1-1)
    'a_model': 'A-DEVICE (MODEL#)',     # used ONLY for QFX Min/Max decision
    'z_room': 'Z-ROOM',
    'z_rack': 'Z-RACK',
    'z_ru': 'Z-RU',
    'z_device': 'Z-DEVICE SIMPLE',
    # === ONLY EDIT THIS IF YOUR EXCEL COLUMN IS NAMED DIFFERENTLY ===
    'a_port': 'A-PORT'   # <-- this is now the single source for global Min & Max
}

def get_column_name(df, key):
    exact = COLUMN_MAPPING.get(key)
    if exact in df.columns:
        return exact
    keyword = KEYWORD_FALLBACK.get(key, '')
    keyword_parts = keyword.upper().split()
    for col in df.columns:
        col_upper = col.upper().replace('\n', ' ')
        if all(part in col_upper for part in keyword_parts):
            return col
    raise KeyError(f"No column found for {key} using exact '{exact}' or keyword '{keyword}'")

def normalize_type(type_raw):
    """Clean TYPE column for folder names:
       - Collapses R..T2-T3 or R. T2-T3 into R.T2-T3
       - Keeps all previous AS-T1 / SIS / QFX logic intact"""
    if not type_raw:
        return "UNKNOWN"
    s = str(type_raw).strip()
    
    if 'SIS' in s:
        return s.replace('-SIS(', '-').replace(')', '')
    elif '(' in s and ')' in s:
        return s.replace('(', '.').replace(')', '')
    else:
        # Replace spaces with dots, then collapse any sequence of dots into ONE dot
        s = s.replace(' ', '.')
        s = re.sub(r'\.+', '.', s)
        return s

def generate_file_structure(discipline_name, df, jobs_dir):
    """Now uses full discipline_name (DH16_RT1-RT2) as top-level folder under jobs/"""
    df.columns = [col.strip() for col in df.columns]
    
    try:
        type_col = get_column_name(df, 'type')
        a_room_col = get_column_name(df, 'a_room')
        a_rack_col = get_column_name(df, 'a_rack')
        a_ru_col = get_column_name(df, 'a_ru')
        a_device_col = get_column_name(df, 'a_device')
        a_model_col = get_column_name(df, 'a_model')
        z_room_col = get_column_name(df, 'z_room')
        z_rack_col = get_column_name(df, 'z_rack')
        z_ru_col = get_column_name(df, 'z_ru')
        z_device_col = get_column_name(df, 'z_device')
        # GLOBAL A-PORT column (used for both Min and Max across entire sheet)
        a_port_col = get_column_name(df, 'a_port')
    except KeyError as e:
        actual_cols = ', '.join(df.columns)
        return f"Error finding columns: {str(e)}. Actual columns: {actual_cols}."
    
    created_folders = []
    
    if df.empty:
        return "Error: Empty data."
    
    # === GLOBAL MIN / MAX FROM ENTIRE A-PORT COLUMN (with cleaning) ===
    port_series = df[a_port_col].dropna().astype(str).str.strip()
    
    # 1. Ignore any port containing "SPARE" (case-insensitive)
    port_series = port_series[~port_series.str.contains('SPARE', case=False, na=False)]
    
    # 2. Clean each port (SWP prefix + 0/0/XX → XX for AS-T1)
    def clean_port(p):
        p = str(p).strip()
        # Remove leading "swp" prefix (for RT jobs)
        if p.upper().startswith('SWP'):
            p = p[3:].lstrip()
        # Remove any leading "X/Y/" pattern (for AS-T1 jobs)
        if '/' in p:
            p = p.split('/')[-1]
        return p
    
    port_series = port_series.apply(clean_port)
    
    # 3. Compute global min/max from the cleaned non-SPARE ports
    if not port_series.empty:
        global_min_port = port_series.min()
        global_max_port = port_series.max()
    else:
        global_min_port = ''
        global_max_port = ''
    
    type_folder = os.path.join(jobs_dir, discipline_name)
    if not os.path.exists(type_folder):
        os.makedirs(type_folder)
    
    required_cols = set([type_col, a_room_col, a_rack_col, a_ru_col, a_device_col, a_model_col,
                         z_room_col, z_rack_col, z_ru_col, z_device_col])
    unique_jobs = df[list(required_cols)].drop_duplicates()
    for _, row in unique_jobs.iterrows():
        type_raw = str(row[type_col]).strip()
        is_r_type = 'R' in type_raw.upper()
        
        if is_r_type:
            room_col = z_room_col
            rack_col = z_rack_col
            ru_col = z_ru_col
            device_col = z_device_col
        else:
            room_col = a_room_col
            rack_col = a_rack_col
            ru_col = a_ru_col
            device_col = a_device_col
        
        device_full = str(row[device_col]).strip()
        model_full = str(row[a_model_col]).strip()
        room = str(row[room_col]).strip()
        rack = str(row[rack_col]).strip()
        ru = str(row[ru_col]).strip()
        
        if pd.isna(row[room_col]) or pd.isna(row[rack_col]) or pd.isna(row[ru_col]) or pd.isna(row[device_col]) \
           or not room or room == '-' or not rack or rack == '-' or not ru or ru == '-' or not device_full or device_full == '-':
            continue
        
        ru_processed = 'RU' + ru.split('/')[0]
        
        # === NEW: strip any leading B##- (B20-, B19-, etc.) for R-type jobs only ===
        device = re.sub(r'^B\d+-', '', device_full) if is_r_type else device_full
        
        if is_r_type:
            normalized_type = normalize_type(type_raw)
            folder_name = f"{normalized_type} {discipline_name.split('_')[0]} {rack} {ru_processed} {device}"
        else:
            folder_name = f"{type_raw} {room} {rack} {ru_processed} {device}"
        
        sub_folder_path, newly_created = create_job_folder(
            type_folder, folder_name, rack, ru_processed, device, is_r_type,
            device_model=model_full,
            min_port=global_min_port,
            max_port=global_max_port
        )
        if newly_created:
            created_folders.append(sub_folder_path)
    
    if created_folders:
        return "File structure created successfully!"
    else:
        return "File structure processed, but no valid jobs found."