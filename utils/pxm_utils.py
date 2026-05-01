# utils/pxm_utils.py
import os
import shutil
from config import JOBS_DIR

def copy_jobs_to_pxm(selected_jobs, drive_letter, selected_type, jobs_dir=JOBS_DIR):
    """Copies entire job folders (with info.json) directly to PXM:\Jobs\ """
    if not drive_letter or not drive_letter.endswith(':'):
        return "❌ Invalid drive letter. Example: E:"

    pxm_root = drive_letter + '\\'
    if not os.path.exists(pxm_root):
        return f"❌ Drive {drive_letter} not found.\n\nMake sure:\n• PXM is connected via USB-C\n• PXM is in 'USB transfer mode'\n• Try E: or F:"

    jobs_dest = os.path.join(pxm_root, 'Jobs')
    os.makedirs(jobs_dest, exist_ok=True)

    type_folder = os.path.join(jobs_dir, selected_type)
    copied_count = 0
    errors = []

    for job_name in selected_jobs:
        src_path = os.path.join(type_folder, job_name)
        dst_path = os.path.join(jobs_dest, job_name)

        if not os.path.exists(src_path):
            errors.append(f"Missing source: {job_name}")
            continue

        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)

        try:
            shutil.copytree(src_path, dst_path)
            copied_count += 1
        except Exception as e:
            errors.append(f"Failed {job_name}: {str(e)}")

    if copied_count > 0:
        msg = f"✅ Success! Copied {copied_count} job(s) to PXM:\\Jobs\\"
        if errors:
            msg += f"\n\nWarnings: {', '.join(errors)}"
        return msg
    else:
        return "❌ No jobs were copied.\n\nMake sure:\n• PXM is connected and in USB transfer mode\n• You selected the correct drive (E: or F:)\n• You have at least one job checked"