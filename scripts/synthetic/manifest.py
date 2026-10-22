# scripts/synthetic/manifest.py
import json
import os
from datetime import datetime

def write_manifest(output_dir: str = "data/rq3_dataset"):
    """Write generation manifest."""
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "output_dir": output_dir,
        "folders": []
    }
    
    for root, dirs, files in os.walk(output_dir):
        if files:
            manifest["folders"].append({
                "path": root.replace(output_dir, "").strip(os.sep),
                "file_count": len(files)
            })
    
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"  Manifest written to {manifest_path}")