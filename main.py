import os
import shutil
from config import BASE_DIR  # Import dynamic base path for portability

# Step 1: Define paths using BASE_DIR
jobs_dir = os.path.join(BASE_DIR, "jobs")
job_folder = "AS-T1"
job_path = os.path.join(jobs_dir, job_folder)

# Step 2: Create the AS-T1 folder under jobs/ if it doesn't exist
os.makedirs(job_path, exist_ok=True)

# Step 3: Remove any existing contents (files or subfolders) inside AS-T1 to ensure it's empty
for item in os.listdir(job_path):
    item_path = os.path.join(job_path, item)
    if os.path.isdir(item_path):
        shutil.rmtree(item_path)  # Recursively delete subfolders
    else:
        os.remove(item_path)  # Delete files

print(f"Folder created or reset (contents cleared): {job_path}")
