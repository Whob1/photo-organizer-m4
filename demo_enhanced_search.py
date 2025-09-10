#!/usr/bin/env python3
"""
Demo script showing the enhanced search capabilities of the photo organizer.
"""

import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from m4_photo_organizer.rclone_integration import Rclone
from m4_photo_organizer.config import SETTINGS

def demo_search():
    print("🔍 Photo Organizer Enhanced Search Demo")
    print("=" * 50)
    
    print(f"📋 Current Configuration:")
    print(f"  • Google Photos Mount: {SETTINGS.google_photos_mount}")
    print(f"  • Mount Exists: {SETTINGS.google_photos_mount.exists()}")
    print(f"  • Supported Extensions: {len(Rclone.SUFFIXES) if hasattr(Rclone, 'SUFFIXES') else 'N/A'}")
    print()
    
    # Create Rclone instance
    rc = Rclone()
    
    print("🔎 Performing comprehensive search...")
    files = list(rc.iter_media(max_scan=50))
    
    print(f"✅ Found {len(files)} media files")
    
    if files:
        print("\n📄 Files found:")
        for i, file_path in enumerate(files[:10], 1):
            print(f"  {i:2d}. {file_path}")
        
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more files")
            
        # Show file type breakdown
        extensions = {}
        for p in files:
            ext = p.suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1
            
        print(f"\n📊 File Types:")
        for ext, count in sorted(extensions.items()):
            print(f"  • {ext}: {count} files")
    else:
        print("\n❌ No media files found")
        print("\n💡 Try:")
        print("  • Set PHOTOORG_SEARCH_DIRS=/path/to/your/photos")
        print("  • Set PHOTOORG_GOOGLE_MOUNT=/path/to/google/photos/mount")
        print("  • Place some test images in /tmp/test_photos/")

if __name__ == "__main__":
    demo_search()