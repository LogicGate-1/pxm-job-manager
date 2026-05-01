import datetime
from services.pxm_registry import _load_pxms, _save_pxms


def _build_event_summary(event, user=None, details=None):
    details = details or {}
    if event == "device_registered":
        return "Device registered"
    if event == "device_assigned":
        if user:
            return f"Assigned to {user}"
        return "Device assigned"
    if event == "device_reassigned":
        old = details.get("from")
        new = details.get("to")
        if old and new:
            return f"Reassigned from {old} to {new}"
        if new:
            return f"Assigned to {new}"
        return "Device reassigned"
    if event == "device_unassigned":
        if user:
            return f"Unassigned from {user}"
        return "Device unassigned"
    if event == "jobs_assigned":
        return "Jobs assigned"
    if event == "jobs_unassigned":
        return "Jobs unassigned"
    return event.replace("_", " ").capitalize()


def record_pxm_history(serial, event, user=None, details=None):
    pxms = _load_pxms()
    pxm = next((p for p in pxms if p.get("serial") == serial), None)
    if not pxm:
        return

    if isinstance(details, dict):
        details = {k: v for k, v in details.items() if v is not None}

    entry = {
        "event": event,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": user,
        "details": details if details is not None else [],
        "summary": _build_event_summary(event, user=user, details=details)
    }
    pxm.setdefault("history", []).append(entry)
    _save_pxms(pxms)


def log_unassigned_jobs(serial, jobs, removed_from_device=False):
    if not serial:
        return
    details = {
        "jobs": jobs,
        "removed_from_device": removed_from_device
    }
    record_pxm_history(serial, "jobs_unassigned", user=None, details=details)


def enrich_history_with_summary(history):
    for entry in history:
        if entry.get("event") in ["jobs_assigned", "jobs_unassigned"] or entry.get("summary") is None:
            entry["summary"] = _build_event_summary(entry.get("event"), user=entry.get("user"), details=entry.get("details"))
    return history


def read_pxm_log(limit=100):
    pxms = _load_pxms()
    entries = []
    for pxm in pxms:
        for history_item in pxm.get("history", []):
            entry = history_item.copy()
            entry["serial"] = pxm.get("serial")
            entry["drive"] = pxm.get("drive")
            entry["summary"] = _build_event_summary(entry.get("event"), user=entry.get("user"), details=entry.get("details"))
            details = entry.get("details")
            if isinstance(details, dict):
                entry["removed_from_device"] = details.get("removed_from_device")
                entry["jobs"] = details.get("jobs") or []
            elif isinstance(details, list):
                entry["jobs"] = details
            else:
                entry["jobs"] = []
            entries.append(entry)
    entries.sort(key=lambda item: item.get("time", ""), reverse=True)
    return entries[:limit]
