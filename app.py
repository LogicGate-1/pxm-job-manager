# app.py
from flask import Flask, render_template, redirect, url_for, request, jsonify
import os
import shutil

# All modular imports
from config import (
    BASE_DIR,
    DB_DIR,
    UPLOAD_FOLDER,
    JOBS_DIR,
    PXM_JOBS,
    get_pxms,
    get_pxm_jobs_dir,
    find_connected_pxms,
    add_or_update_pxm,
    update_pxm_user,
    update_pxm_device,
    remove_pxm,
    record_pxm_history,
    update_pxm_current_jobs,
    read_pxm_log,
    get_members,
    add_or_update_member,
    remove_member
)
from services.pxm_history import enrich_history_with_summary
from utils.data_utils import ensure_directories, get_data_from_db
from utils.db_creator import auto_import_excel_to_sql
from utils.job_utils import generate_file_structure
from utils.pxm_loader import load_jobs_to_pxm

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ensure_directories(UPLOAD_FOLDER, DB_DIR, JOBS_DIR, PXM_JOBS)


def _resolve_job_path(job_name):
    if not job_name:
        return None
    normalized = job_name.replace('/', os.sep).replace('\\', os.sep)
    candidate = os.path.join(JOBS_DIR, normalized)
    if os.path.isdir(candidate):
        return candidate

    basename = os.path.basename(normalized)
    for root, dirs, files in os.walk(JOBS_DIR):
        if basename in dirs:
            return os.path.join(root, basename)
    return None


def _remove_job_marker(job_name):
    job_path = _resolve_job_path(job_name)
    if not job_path:
        return False
    marker = os.path.join(job_path, '.pxm_loaded')
    if os.path.exists(marker):
        try:
            os.remove(marker)
        except Exception:
            pass
        return True
    return False


@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/jobs')
def jobs():
    all_folders = sorted([f for f in os.listdir(JOBS_DIR) if os.path.isdir(os.path.join(JOBS_DIR, f))])
    dh_list = sorted(set(f.split('_')[0] for f in all_folders if '_' in f))
    selected_dh = request.args.get('dh', dh_list[0] if dh_list else None)
    selected_type = request.args.get('type')
    job_types = []
    job_list = []
    connected_devices = find_connected_pxms()
    if selected_dh:
        matching_folders = [f for f in all_folders if f.startswith(selected_dh + '_')]
        job_types = sorted(set(f.split('_', 1)[1] for f in matching_folders))
        if not selected_type or selected_type not in job_types:
            selected_type = job_types[0] if job_types else None
        if selected_type:
            full_folder = f"{selected_dh}_{selected_type}"
            type_folder = os.path.join(JOBS_DIR, full_folder)
            if os.path.exists(type_folder):
                for f in os.listdir(type_folder):
                    if os.path.isdir(os.path.join(type_folder, f)):
                        if not os.path.exists(os.path.join(type_folder, f, '.pxm_loaded')):
                            job_list.append(f)
                job_list.sort()
    return render_template(
        'dashboard.html',
        dh_list=dh_list,
        selected_dh=selected_dh,
        job_types=job_types,
        selected_type=selected_type,
        job_list=job_list,
        connected_devices=connected_devices
    )

@app.route('/exfo', methods=['GET', 'POST'])
def exfo():
    message = None
    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'save_serial':
                drive = request.form.get('drive')
                serial = request.form.get('serial')
                user = request.form.get('user') or None
                add_or_update_pxm(drive, serial, user)
                message = f"Saved EXFO device {serial} on {drive}."
            elif action == 'assign_user':
                serial = request.form.get('serial')
                user = request.form.get('user') or None
                update_pxm_user(serial, user)
                message = f"Assigned {user or 'no user'} to {serial}."
        except Exception as e:
            message = f"Error: {str(e)}"

    connected_pxms = find_connected_pxms()
    known_pxms = get_pxms()
    return render_template('exfo.html', connected_pxms=connected_pxms, known_pxms=known_pxms, message=message)

@app.route('/devices', methods=['GET', 'POST'])
def devices():
    message = None
    members_list = get_members()
    connected_devices = find_connected_pxms()
    known_devices = get_pxms()
    search_query = request.args.get('search', '').strip()

    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'register_device':
                drive = request.form.get('drive')
                serial = request.form.get('serial')
                device_name = request.form.get('device_name') or None
                member = request.form.get('member') or None
                existing = next((d for d in known_devices if d.get('serial') == serial), None)
                if existing:
                    previous_user = existing.get('user')
                    add_or_update_pxm(drive, serial, member, device_name)
                    if previous_user != member:
                        if previous_user and member:
                            record_pxm_history(serial, 'device_reassigned', user=member, details={'from': previous_user, 'to': member, 'device_name': device_name})
                        elif member:
                            record_pxm_history(serial, 'device_assigned', user=member, details={'device_name': device_name})
                        else:
                            record_pxm_history(serial, 'device_unassigned', user=previous_user, details={'device_name': device_name})
                    message = f"Updated existing device {serial}."
                else:
                    add_or_update_pxm(drive, serial, member, device_name)
                    if member:
                        record_pxm_history(serial, 'device_assigned', user=member, details={'device_name': device_name})
                    else:
                        record_pxm_history(serial, 'device_registered', details={'device_name': device_name})
                    message = f"Registered device {serial}."
            elif action == 'assign_device' or action == 'edit_device':
                serial = request.form.get('serial')
                device_name = request.form.get('device_name') or None
                member = request.form.get('member') or None
                existing = next((d for d in known_devices if d.get('serial') == serial), None)
                previous_user = existing.get('user') if existing else None
                if existing and existing.get('drive'):
                    add_or_update_pxm(existing['drive'], serial, member, device_name)
                else:
                    update_pxm_device(serial, user=member, name=device_name)
                if previous_user != member:
                    if previous_user and member:
                        record_pxm_history(serial, 'device_reassigned', user=member, details={'from': previous_user, 'to': member, 'device_name': device_name})
                    elif member:
                        record_pxm_history(serial, 'device_assigned', user=member, details={'device_name': device_name})
                    else:
                        record_pxm_history(serial, 'device_unassigned', user=previous_user, details={'device_name': device_name})
                message = f"Updated device {serial}."
            elif action == 'unassign_device':
                serial = request.form.get('serial')
                existing = next((d for d in known_devices if d.get('serial') == serial), None)
                previous_user = existing.get('user') if existing else None
                update_pxm_device(serial, user=None)
                if previous_user:
                    record_pxm_history(serial, 'device_unassigned', user=previous_user, details={'device_name': existing.get('name') if existing else None})
                message = f"Device {serial} has been unassigned."
            elif action == 'delete_device':
                serial = request.form.get('serial')
                remove_pxm(serial)
                message = f"Deleted device {serial}."
        except Exception as e:
            message = f"Error: {str(e)}"
        known_devices = get_pxms()
        connected_devices = find_connected_pxms()

    serial_index = {d['serial']: d for d in known_devices if d.get('serial')}
    for device in connected_devices:
        if device.get('serial') and device['serial'] in serial_index:
            known = serial_index[device['serial']]
            device['already_registered'] = True
            device['registered_name'] = known.get('name') or known['serial']
            device['registered_user'] = known.get('user')
            device['history'] = enrich_history_with_summary(known.get('history', []))
            issued = [h for h in device['history'] if h['event'] == 'issued']
            returned = [h for h in device['history'] if h['event'] == 'returned']
            device['last_issued'] = issued[-1]['time'] if issued else None
            device['last_returned'] = returned[-1]['time'] if returned else None
        else:
            device['already_registered'] = False
            device['history'] = []
            device['last_issued'] = None
            device['last_returned'] = None

    if search_query:
        search_lower = search_query.lower()
        known_devices = [
            d for d in known_devices
            if search_lower in d.get('serial', '').lower() or search_lower in (d.get('name') or '').lower()
        ]

    assigned_devices = [d for d in known_devices if d.get('user')]
    unassigned_devices = [d for d in known_devices if not d.get('user')]

    return render_template(
        'devices.html',
        members=members_list,
        connected_devices=connected_devices,
        known_devices=known_devices,
        assigned_devices=assigned_devices,
        unassigned_devices=unassigned_devices,
        message=message,
        search_query=search_query
    )

@app.route('/devices/status')
def devices_status():
    connected_devices = find_connected_pxms()
    serials = sorted({d['serial'] for d in connected_devices if d.get('serial')})
    drives = sorted({d['drive'] for d in connected_devices if d.get('drive')})
    return jsonify({
        'serials': serials,
        'drives': drives
    })

@app.route('/pxm-log')
def pxm_log():
    log_entries = read_pxm_log(limit=100)
    return render_template('pxm_logs.html', logs=log_entries)

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/members', methods=['GET', 'POST'])
def members():
    message = None
    roles = ['Admin', 'Manager', 'Editor', 'Viewer']
    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'add_member':
                name = request.form.get('name')
                role = request.form.get('role')
                add_or_update_member(name, role)
                message = f"Added member '{name}' with role {role}."
            elif action == 'update_member':
                name = request.form.get('member_name')
                role = request.form.get('role')
                add_or_update_member(name, role)
                message = f"Updated {name}'s role to {role}."
            elif action == 'delete_member':
                name = request.form.get('member_name')
                remove_member(name)
                message = f"Removed member '{name}'."
        except Exception as e:
            message = f"Error: {str(e)}"

    members_list = get_members()
    return render_template('members.html', members=members_list, roles=roles, message=message)

@app.route('/rack-lookup')
def rack_lookup():
    return render_template('rack_lookup.html')

@app.route('/customer-projects')
def customer_projects():
    return render_template('customer_projects.html')

@app.route('/packing-slips')
def packing_slips():
    return render_template('packing_slips.html')

@app.route('/create-jobs', methods=['GET', 'POST'])
def create_jobs():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                filename = file.filename
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                try:
                    created = auto_import_excel_to_sql(filepath, DB_DIR)
                    for item in created:
                        full_name = item['full_name']
                        df = get_data_from_db(full_name, DB_DIR)
                        generate_file_structure(full_name, df, JOBS_DIR)
                    return redirect(url_for('jobs'))
                except Exception as e:
                    return render_template('create_jobs.html', message=f"Error: {str(e)}")
    return render_template('create_jobs.html')

def _normalize_job_basename(job_name):
    if not job_name or not isinstance(job_name, str):
        return None
    normalized = job_name.replace('\\', os.sep).replace('/', os.sep)
    return os.path.basename(normalized).strip()


@app.route('/load-to-pxm', methods=['POST'])
def load_to_pxm():
    selected = request.form.getlist('selected_jobs')
    drive_letter = request.form.get('drive_letter', 'E:').strip().upper()
    if not selected:
        return "No jobs selected", 400
    if not drive_letter.endswith(':'):
        drive_letter += ':'
    try:
        full_paths = [os.path.join(JOBS_DIR, s) for s in selected]
        pxm_jobs_dir = os.path.join(drive_letter, 'Jobs')
        msg = load_jobs_to_pxm(full_paths, pxm_jobs_dir)

        connected = find_connected_pxms()
        serial = next((d['serial'] for d in connected if d['drive'] == drive_letter and d.get('serial')), None)
        if serial:
            pxm = next((p for p in get_pxms() if p['serial'] == serial), None)
            if not pxm:
                add_or_update_pxm(drive_letter, serial, None, None)
                pxm = next((p for p in get_pxms() if p['serial'] == serial), None)
            elif pxm.get('drive') != drive_letter:
                add_or_update_pxm(drive_letter, serial, pxm.get('user'), pxm.get('name'))
            record_pxm_history(serial, 'jobs_assigned', user=pxm.get('user') if pxm else None, details=selected)
            update_pxm_current_jobs(serial, [ _normalize_job_basename(job) for job in selected if _normalize_job_basename(job) ])

        return msg
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/unassign', methods=['POST'])
def unassign_jobs():
    selected = request.form.getlist('selected_jobs')
    selected = list(dict.fromkeys([item for item in selected if item]))
    selected_serial = request.form.get('pxm_serial')
    if not selected:
        return "No jobs selected", 400
    if not selected_serial:
        return "Device serial is required to unassign.", 400

    connected = find_connected_pxms()
    connected_serials = {d['serial'] for d in connected if d.get('serial')}
    if selected_serial not in connected_serials:
        return "Device is not connected. Reinsert the PXM and try again.", 400

    removed_markers = 0
    removed_from_pxm = 0
    for job_name in selected:
        # remove source marker so job returns to the main Jobs list
        for root, dirs, files in os.walk(JOBS_DIR):
            if job_name in dirs:
                marker = os.path.join(root, job_name, '.pxm_loaded')
                if os.path.exists(marker):
                    os.remove(marker)
                    removed_markers += 1
                break

        # remove copied job folder from the connected PXM drive
        device = next((d for d in connected if d.get('serial') == selected_serial), None)
        if device:
            job_folder = os.path.join(device['jobs_dir'], job_name)
            if os.path.exists(job_folder) and os.path.isdir(job_folder):
                try:
                    shutil.rmtree(job_folder)
                    removed_from_pxm += 1
                except Exception:
                    pass

    pxm = next((p for p in get_pxms() if p['serial'] == selected_serial), None)
    if pxm:
        current_jobs = pxm.get('current_jobs', [])
        remaining_jobs = [job for job in current_jobs if job not in selected]
        update_pxm_current_jobs(selected_serial, remaining_jobs)
        try:
            record_pxm_history(selected_serial, 'jobs_unassigned', user=pxm.get('user'), details=selected)
        except Exception:
            pass

    msg = f"✅ Unassigned {len(selected)} job(s) — they are now back on the Jobs page!"
    if removed_from_pxm:
        msg += f"\n✅ Removed {removed_from_pxm} job folder(s) from connected PXM drive(s)."

    return msg

@app.route('/assigned')
def assigned_jobs():
    pxms = get_pxms()                                      # from config
    connected_devices = find_connected_pxms()
    requested_serial = request.args.get('pxm')
    connected_serials = [d.get('serial') for d in connected_devices if d.get('serial')]
    known_serials = {p.get('serial') for p in pxms if p.get('serial')}
    unknown_connected = [s for s in connected_serials if s not in known_serials]

    if requested_serial:
        selected_serial = requested_serial
    elif unknown_connected:
        selected_serial = unknown_connected[0]
    elif connected_serials:
        selected_serial = connected_serials[0]
    else:
        selected_serial = pxms[0]['serial'] if pxms else None

    selected_device = next((p for p in pxms if p['serial'] == selected_serial), None)
    connected_device = next((d for d in connected_devices if d.get('serial') == selected_serial), None)
    if selected_serial and selected_device:
        pxm_jobs_dir = connected_device['jobs_dir'] if connected_device else get_pxm_jobs_dir(selected_serial)
    elif selected_serial and connected_device:
        selected_device = connected_device
        pxm_jobs_dir = connected_device['jobs_dir']
    else:
        pxm_jobs_dir = get_pxm_jobs_dir(selected_serial) if selected_serial else None

    selected_user = selected_device.get('user') if selected_device else None
    selected_device_history = selected_device.get('history', []) if selected_device else []
    selected_device_history = enrich_history_with_summary(selected_device_history)
    selected_device_connected = selected_serial in {d.get('serial') for d in connected_devices if d.get('serial')}

    known_serials = {p.get('serial') for p in pxms if p.get('serial')}
    extra_unregistered = [d for d in connected_devices if d.get('serial') and d['serial'] not in known_serials]
    pxm_options = pxms + extra_unregistered
    assigned_devices = [p for p in pxms if p.get('user')]
    unassigned_devices = [p for p in pxms if not p.get('user')]
    for extra in extra_unregistered:
        unassigned_devices.append(extra)

    def _normalize_job_basename(job_name):
        if not job_name or not isinstance(job_name, str):
            return None
        normalized = job_name.replace('\\', os.sep).replace('/', os.sep)
        return os.path.basename(normalized).strip()

    def _reconstruct_jobs_from_history(history_events):
        jobs = []
        for event in history_events:
            details = event.get('details') or []
            if not isinstance(details, list):
                continue
            if event.get('event') == 'jobs_assigned':
                for job in details:
                    name = _normalize_job_basename(job)
                    if name and name not in jobs:
                        jobs.append(name)
            elif event.get('event') == 'jobs_unassigned':
                for job in details:
                    name = _normalize_job_basename(job)
                    while name in jobs:
                        jobs.remove(name)
        return jobs

    assigned_jobs = []
    recovery_message = None
    if selected_device_connected and pxm_jobs_dir and os.path.exists(pxm_jobs_dir):
        actual_jobs = []
        for f in os.listdir(pxm_jobs_dir):
            if os.path.isdir(os.path.join(pxm_jobs_dir, f)) and "RU" in f:
                actual_jobs.append(f)
        actual_jobs.sort()

        metadata_jobs = [ _normalize_job_basename(j) for j in selected_device.get('current_jobs', []) if _normalize_job_basename(j) ]
        if not metadata_jobs:
            metadata_jobs = _reconstruct_jobs_from_history(selected_device_history)

        missing_jobs = [job for job in metadata_jobs if job not in actual_jobs]
        extra_jobs = [job for job in actual_jobs if job not in metadata_jobs]
        if missing_jobs or extra_jobs:
            for job in missing_jobs:
                _remove_job_marker(job)
            update_pxm_current_jobs(selected_serial, actual_jobs)
            if missing_jobs:
                try:
                    record_pxm_history(selected_serial, 'jobs_unassigned', user=selected_user, details=missing_jobs)
                except Exception:
                    pass
            if extra_jobs:
                try:
                    record_pxm_history(selected_serial, 'jobs_assigned', user=selected_user, details=extra_jobs)
                except Exception:
                    pass
            recovery_parts = []
            if missing_jobs:
                recovery_parts.append(f"removed from the device and recovered: {', '.join(missing_jobs)}")
            if extra_jobs:
                recovery_parts.append(f"found on device and synced: {', '.join(extra_jobs)}")
            recovery_message = f"The following jobs were reconciled: {'; '.join(recovery_parts)}."
            pxms = get_pxms()
            selected_device = next((p for p in pxms if p['serial'] == selected_serial), None)
            selected_device_history = selected_device.get('history', []) if selected_device else []
            selected_device_history = enrich_history_with_summary(selected_device_history)

        assigned_jobs = actual_jobs
    elif selected_device:
        if selected_device.get('current_jobs'):
            assigned_jobs = [ _normalize_job_basename(j) for j in selected_device.get('current_jobs', []) if _normalize_job_basename(j) ]
        else:
            assigned_jobs = _reconstruct_jobs_from_history(selected_device_history)

    return render_template(
        'jobs_assigned.html',
        assigned_jobs=assigned_jobs,
        pxm_serial=selected_serial,
        pxms=pxms,                     # pass full list for dropdown
        selected_pxm=selected_serial,
        selected_user=selected_user,
        selected_device=selected_device,
        selected_device_connected=selected_device_connected,
        selected_device_history=selected_device_history,
        recovery_message=recovery_message,
        connected_devices=connected_devices,
        assigned_devices=assigned_devices,
        unassigned_devices=unassigned_devices,
        pxm_options=pxm_options
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9443)