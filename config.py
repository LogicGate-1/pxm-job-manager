from services.paths import BASE_DIR, DB_DIR, UPLOAD_FOLDER, JOBS_DIR, PXM_JOBS
from services.pxm_registry import (
    get_pxms,
    get_pxm_jobs_dir,
    find_connected_pxms,
    add_or_update_pxm,
    update_pxm_user,
    update_pxm_device,
    remove_pxm,
    update_pxm_current_jobs,
)
from services.pxm_history import (
    record_pxm_history,
    log_unassigned_jobs,
    read_pxm_log,
)
from services.members import (
    get_members,
    add_or_update_member,
    remove_member,
)

COLUMN_MAPPING = {
    'type': 'TYPE',
    'a_room': 'A-ROOM',
    'a_rack': 'A-RACK',
    'a_ru': 'A-RU',
    'a_device': 'A-DEVICE SIMPLE',
    'a_model': 'A-DEVICE (MODEL#)',
    'z_room': 'Z-ROOM',
    'z_rack': 'Z-RACK',
    'z_ru': 'Z-RU',
    'z_device': 'Z-DEVICE SIMPLE',
    'a_port': 'A-PORT',
}
