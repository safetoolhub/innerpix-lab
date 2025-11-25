import os
from pathlib import Path
from collections import Counter
import sys

# Add project root to path
sys.path.append(os.getcwd())
from config import Config

def analyze_directory(path):
    print(f"Analyzing directory: {path}")
    path = Path(path)
    
    if not path.exists():
        print(f"Error: Path {path} does not exist.")
        return

    extension_counts = Counter()
    total_files = 0
    
    supported_images = Config.SUPPORTED_IMAGE_EXTENSIONS
    supported_videos = Config.SUPPORTED_VIDEO_EXTENSIONS
    
    print(f"Supported Images: {supported_images}")
    print(f"Supported Videos: {supported_videos}")
    
    skipped_files = []
    
    for root, dirs, files in os.walk(path):
        for file in files:
            total_files += 1
            # Get actual extension case
            ext_actual = Path(file).suffix
            ext_lower = ext_actual.lower()
            extension_counts[ext_actual] += 1
            
            if ext_lower not in supported_images and ext_lower not in supported_videos:
                if len(skipped_files) < 20:
                    skipped_files.append(os.path.join(root, file))

    print(f"\nTotal Files Found: {total_files}")
    
    print("\nExtension Counts:")
    for ext, count in extension_counts.most_common():
        status = "SUPPORTED" if (ext in supported_images or ext in supported_videos) else "UNSUPPORTED"
        print(f"{ext}: {count} ({status})")
        
    print("\nTop 20 Unsupported/Skipped Files:")
    for f in skipped_files:
        print(f)

if __name__ == "__main__":
    analyze_directory("/home/ed/Pictures")
