import hashlib
import json
from pathlib import Path
import sys

# --- Configuration ---
# The path to your clean, original WoW 3.3.5a client directory.
WOW_CLIENT_PATH = Path(r"C:\WISE\WOW335")
# The location of the Data folder.
DATA_FOLDER_PATH = WOW_CLIENT_PATH / "Data"
# Where the final manifest file will be saved.
OUTPUT_MANIFEST_PATH = Path(__file__).parent / "config" / "manifest.json"
# --- End Configuration ---

def calculate_sha256(file_path):
    """Calculates the SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read the file in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def create_manifest():
    """Scans the Data folder and creates a manifest of file paths, hashes, sizes, and modification times."""
    if not DATA_FOLDER_PATH.is_dir():
        print(f"Error: The specified Data folder does not exist: {DATA_FOLDER_PATH}")
        sys.exit(1)

    print(f"Scanning files in: {DATA_FOLDER_PATH}")
    manifest = {}
    
    files_to_scan = list(DATA_FOLDER_PATH.rglob("*"))
    total_files = len(files_to_scan)
    
    for i, file_path in enumerate(files_to_scan):
        if file_path.is_file():
            relative_path = str(file_path.relative_to(DATA_FOLDER_PATH)).replace('\\', '/')
            
            progress = (i + 1) / total_files * 100
            print(f"[{progress:.2f}%] Processing: {relative_path}")
            
            try:
                file_stat = file_path.stat()
                file_hash = calculate_sha256(file_path)
                
                if file_hash:
                    manifest[relative_path] = {
                        "hash": file_hash,
                        "size": file_stat.st_size,
                        "mtime": file_stat.st_mtime
                    }
            except OSError as e:
                print(f"Could not access file {file_path}: {e}")

    print("\nManifest generation complete.")
    
    try:
        # Ensure the config directory exists
        OUTPUT_MANIFEST_PATH.parent.mkdir(exist_ok=True)
        with open(OUTPUT_MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=4)
        print(f"Successfully saved manifest to: {OUTPUT_MANIFEST_PATH}")
    except IOError as e:
        print(f"Error writing manifest file: {e}")

if __name__ == "__main__":
    create_manifest()
