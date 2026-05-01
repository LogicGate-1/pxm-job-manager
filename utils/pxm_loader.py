# utils/pxm_loader.py
import os
import shutil

def load_jobs_to_pxm(selected_job_paths, pxm_jobs_dir):
    """Copies jobs DIRECTLY into the PXM's Jobs folder (no extra serial parent folder)."""
    if not os.path.exists(pxm_jobs_dir):
        os.makedirs(pxm_jobs_dir)
    
    loaded_count = 0
    for job_path in selected_job_paths:
        if not os.path.exists(job_path):
            continue
        folder_name = os.path.basename(job_path)
        dest_path = os.path.join(pxm_jobs_dir, folder_name)
        
        if os.path.exists(dest_path):
            try:
                shutil.rmtree(dest_path)
            except:
                pass
        
        try:
            shutil.copytree(job_path, dest_path)
            # Mark as loaded
            marker = os.path.join(job_path, '.pxm_loaded')
            with open(marker, 'w') as f:
                f.write('loaded')
            loaded_count += 1
        except PermissionError:
            return "❌ PXM drive access denied.\n\nPut the PXM in **USB transfer mode** and try again."
        except Exception as e:
            return f"Error loading jobs: {str(e)}"
    
    return f"✅ Successfully loaded {loaded_count} job(s) to PXM!"