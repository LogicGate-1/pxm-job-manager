# utils/sheet_parser.py
# Isolated block: ONLY parses sheet name → clean DH + table_name
# MODULAR: To add new disciplines, just edit DISCIPLINE_PATTERNS
import re

# === MODULAR DISCIPLINE MAPPING (add new ones here only) ===
DISCIPLINE_PATTERNS = {
    'AS-T1':     r'AS.*SIS\(T1\)',          # Your original - 100% untouched
    'GPU-T1':    r'GPU.*T1',
    'RT1-RT2':   r'(ROCE|R\.?|R\().*?T1.*?T2',   # Catches your ROCE sheet
    'RT2-RT3':   r'(ROCE|R\.?|R\().*?T2.*?T3',
    'SIST1-T2':  r'SIS.*T1.*T2',
}

BLACKLIST = {'R', 'R.', 'UNKNOWN'}

def normalize_type(sheet_name):
    if not sheet_name:
        return "UNKNOWN"
    s = str(sheet_name).strip()
    
    # Check modular patterns on the FULL sheet name
    for discipline, pattern in DISCIPLINE_PATTERNS.items():
        if re.search(pattern, s, re.IGNORECASE):
            return discipline
    
    # Fallback general cleanup (never touches AS-T1)
    s = s.replace('<>', '').replace('<<>>', '')
    s = s.replace('<--->', '-').replace('---', '-').replace('--', '-')
    if 'SIS' in s.upper():
        s = re.sub(r'SIS\(.*?\)', '', s, flags=re.IGNORECASE)
        s = re.sub(r'-SIS', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*\([^)]*\)', '', s)
    s = re.sub(r'[^A-Za-z0-9._-]+', '', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-_ ')
    return s if s else "UNKNOWN"

def parse_sheet_name(sheet_name):
    if ' |' not in sheet_name:
        return None, None
    parts = sheet_name.split(' |')
    original_dh = parts[0].strip()
    if '(BMZ)' in original_dh.upper():
        return None, None
    if len(parts) < 2:
        return None, None
    
    # === SKIP UNWANTED LOCATION SHEETS ===
    # This completely blocks RoCE_RoCET3HARDWARE_LOCATION.db (and any future *LOCATION sheets)
    if 'HARDWARE_LOCATION' in sheet_name.upper():
        return None, None
    
    # Existing skip for the exact unwanted R. sheets you reported earlier
    type_part = parts[1].strip().upper()
    if type_part == 'R.' and any(loc in sheet_name.upper() for loc in ['T1 | LOCATION', 'T2 | LOCATION']):
        return None, None
    
    # Use full sheet name for matching (ROCE → RT1-RT2 still works)
    normalized = normalize_type(sheet_name)
    
    # General blacklist
    if normalized in BLACKLIST or len(normalized) < 4:
        return None, None
    
    short_dh = re.sub(r'\s*\([^)]*\)', '', original_dh).strip().replace(' ', '_')
    full_name = f"{short_dh}_{normalized}"
    return short_dh, full_name