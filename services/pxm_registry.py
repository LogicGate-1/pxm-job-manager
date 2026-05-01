import ctypes
import json
import os
import re
import string
from services.paths import BASE_DIR

PXMS_FILE = os.path.join(BASE_DIR, "pxms.json")


def _load_pxms():
    if not os.path.exists(PXMS_FILE):
        return []
    try:
        with open(PXMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_pxms(pxms):
    with open(PXMS_FILE, "w", encoding="utf-8") as f:
        json.dump(pxms, f, indent=4, ensure_ascii=False)


def _normalize_drive(drive):
    if not drive:
        return None
    drive = str(drive).strip().upper()
    if len(drive) == 2 and drive[1] == ':':
        return drive
    if len(drive) == 3 and drive[1] == ':' and drive[2] == '\\':
        return drive[:2]
    return drive


def _drive_root(drive):
    drive = _normalize_drive(drive)
    if not drive:
        return None
    return f"{drive}\\"


def _drive_exists(drive):
    root = _drive_root(drive)
    return bool(root and os.path.exists(root))


def _get_mounted_drives():
    mounted = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            mounted.append(f"{letter}:")
    return mounted


def _get_volume_label(drive):
    root = _drive_root(drive)
    if not root or os.name != 'nt':
        return None
    try:
        volume_name_buffer = ctypes.create_unicode_buffer(1024)
        file_system_name_buffer = ctypes.create_unicode_buffer(1024)
        serial_number = ctypes.c_uint(0)
        max_component_length = ctypes.c_uint(0)
        file_system_flags = ctypes.c_uint(0)
        result = ctypes.windll.kernel32.GetVolumeInformationW(
            root,
            volume_name_buffer,
            ctypes.sizeof(volume_name_buffer),
            ctypes.byref(serial_number),
            ctypes.byref(max_component_length),
            ctypes.byref(file_system_flags),
            file_system_name_buffer,
            ctypes.sizeof(file_system_name_buffer)
        )
        if result:
            label = volume_name_buffer.value
            return label.strip() if label else None
    except Exception:
        pass
    return None


def _looks_like_pxm_label(label):
    if not label or not isinstance(label, str):
        return False
    label = label.strip().upper()
    if not label:
        return False
    # Most EXFO/PXM serial labels start with letters and contain digits
    return bool(re.match(r'^[A-Z]{2,5}\d{4,}$', label))


def get_pxms():
    return _load_pxms()


def get_pxm_jobs_dir(serial):
    if not serial:
        return None
    pxms = _load_pxms()
    pxm = next((p for p in pxms if p.get("serial") == serial), None)
    if not pxm:
        return None
    drive = _normalize_drive(pxm.get("drive"))
    if not drive:
        return None
    return os.path.join(_drive_root(drive), "Jobs")


def find_connected_pxms():
    pxms = _load_pxms()
    known_by_drive = {}
    known_by_serial = {}
    for pxm in pxms:
        drive = _normalize_drive(pxm.get("drive"))
        serial = pxm.get("serial")
        if drive:
            known_by_drive[drive] = pxm
        if serial:
            known_by_serial[serial] = pxm

    connected = []
    for drive in _get_mounted_drives():
        serial = _get_volume_label(drive)
        serial_match = known_by_serial.get(serial) if serial else None
        drive_match = known_by_drive.get(drive)
        matched = serial_match if serial_match else (drive_match if not serial else None)
        jobs_root = _drive_root(drive)
        if matched:
            device = matched.copy()
            device["drive"] = drive
            device["jobs_dir"] = os.path.join(jobs_root, "Jobs")
            connected.append(device)
        elif _looks_like_pxm_label(serial):
            connected.append({
                "drive": drive,
                "serial": serial,
                "user": None,
                "name": None,
                "history": [],
                "current_jobs": [],
                "jobs_dir": os.path.join(jobs_root, "Jobs")
            })

    return connected


def add_or_update_pxm(drive, serial, user=None, name=None):
    drive = _normalize_drive(drive)
    pxms = _load_pxms()
    existing = next((p for p in pxms if p.get("serial") == serial), None)
    if existing:
        existing["drive"] = drive
        existing["user"] = user
        existing["name"] = name
    else:
        pxms.append({
            "drive": drive,
            "serial": serial,
            "user": user,
            "name": name,
            "history": [],
            "current_jobs": []
        })
    _save_pxms(pxms)


def update_pxm_user(serial, user):
    pxms = _load_pxms()
    existing = next((p for p in pxms if p.get("serial") == serial), None)
    if existing:
        existing["user"] = user
        _save_pxms(pxms)


def update_pxm_device(serial, user=None, name=None):
    pxms = _load_pxms()
    existing = next((p for p in pxms if p.get("serial") == serial), None)
    if existing:
        if user is not None:
            existing["user"] = user
        if name is not None:
            existing["name"] = name
        _save_pxms(pxms)


def remove_pxm(serial):
    pxms = [p for p in _load_pxms() if p.get("serial") != serial]
    _save_pxms(pxms)


def update_pxm_current_jobs(serial, jobs):
    pxms = _load_pxms()
    existing = next((p for p in pxms if p.get("serial") == serial), None)
    if existing is not None:
        existing["current_jobs"] = jobs or []
        _save_pxms(pxms)
