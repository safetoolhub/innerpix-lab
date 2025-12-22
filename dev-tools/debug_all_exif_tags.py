#!/usr/bin/env python3
"""Ver todos los campos EXIF del archivo HEIC incluyendo IFD"""
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
import pillow_heif

pillow_heif.register_heif_opener()

heic_file = Path("/home/ed/Pictures/TEST_BASE2/IMG_0013_HAYHEIC.HEIC")

with Image.open(heic_file) as image:
    exif = image.getexif()
    
    print("=" * 80)
    print("TODOS LOS TAGS EXIF")
    print("=" * 80)
    
    for tag_id, value in exif.items():
        tag_name = TAGS.get(tag_id, f"UnknownTag_{tag_id}")
        print(f"{tag_name:30} ({tag_id:5}): {value}")
    
    # IFD (EXIF sub-tags)
    print("\n" + "=" * 80)
    print("EXIF IFD (sub-tags detallados)")
    print("=" * 80)
    
    ifd = exif.get_ifd(0x8769)  # ExifOffset IFD
    if ifd:
        for tag_id, value in ifd.items():
            tag_name = TAGS.get(tag_id, f"UnknownTag_{tag_id}")
            print(f"{tag_name:30} ({tag_id:5}): {value}")
    
    # GPS IFD
    print("\n" + "=" * 80)
    print("GPS IFD")
    print("=" * 80)
    
    try:
        gps_ifd = exif.get_ifd(0x8825)  # GPSInfo IFD
        if gps_ifd:
            from PIL.ExifTags import GPSTAGS
            for tag_id, value in gps_ifd.items():
                tag_name = GPSTAGS.get(tag_id, f"UnknownGPSTag_{tag_id}")
                print(f"{tag_name:30} ({tag_id:5}): {value}")
    except Exception as e:
        print(f"No GPS IFD: {e}")
