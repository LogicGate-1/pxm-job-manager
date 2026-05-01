# utils/job_folder_creator.py
# Isolated block: ONLY creates one job subfolder + info.json
import os
import json

def create_job_folder(type_folder, folder_name, rack, ru_processed, device, is_r_type=False, device_model="", min_port="", max_port=""):
    """Creates the job subfolder (if missing) and ALWAYS writes info.json.
    Returns (sub_folder_path, newly_created) so job_utils.py can keep the same counting logic."""
    sub_folder_path = os.path.join(type_folder, folder_name)
    
    newly_created = not os.path.exists(sub_folder_path)
    if newly_created:
        os.makedirs(sub_folder_path, exist_ok=True)
    
    # info.json creation
    base_name = f"{rack}-RU{ru_processed[2:]}-{device.replace('NAC-', '')}"
    
    # === GLOBAL Min/Max (same for every job in the discipline) ===
    min_suffix = min_port
    max_suffix = max_port
    
    info_data = {
        "Name": folder_name,
        "Min": f"{base_name}-{min_suffix}",
        "Max": f"{base_name}-{max_suffix}",
        "Operator": "",
        "Company": "",
        "Customer": ""
    }
    info_path = os.path.join(sub_folder_path, "info.json")
    
    # Clear any existing file first
    if os.path.exists(info_path):
        try:
            os.remove(info_path)
        except Exception:
            pass
    
    try:
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, indent=4)
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied writing info.json to:\n{info_path}\n\n"
            f"Common cause: Project folder inside OneDrive (file locking during sync). "
            f"Move the entire EXFO_Dashboard folder outside OneDrive (e.g. C:\\EXFO_Dashboard) and try again."
        ) from e
    except OSError as e:
        raise OSError(f"OS error writing {info_path}: {str(e)}") from e
    
    return sub_folder_path, newly_created