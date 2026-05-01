import json
import os
from services.paths import BASE_DIR

MEMBERS_FILE = os.path.join(BASE_DIR, "members.json")


def _load_members():
    if not os.path.exists(MEMBERS_FILE):
        return []
    try:
        with open(MEMBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_members(members):
    with open(MEMBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(members, f, indent=4, ensure_ascii=False)


def get_members():
    return _load_members()


def add_or_update_member(name, role):
    members = _load_members()
    existing = next((m for m in members if m.get("name") == name), None)
    if existing:
        existing["role"] = role
    else:
        members.append({"name": name, "role": role})
    _save_members(members)


def remove_member(name):
    members = [m for m in _load_members() if m.get("name") != name]
    _save_members(members)
