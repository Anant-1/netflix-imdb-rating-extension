#!/usr/bin/env python3
"""
Generates crisp PNG icons for the Chrome Extension with zero external dependencies.
Produces an IMDb-style yellow badge with dark text.
"""
import struct
import zlib
from pathlib import Path

def make_png(width, height, get_pixel_rgba):
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # filter type 0: None
        for x in range(width):
            r, g, b, a = get_pixel_rgba(x, y, width, height)
            raw_data.extend([r, g, b, a])

    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    compressed = zlib.compress(bytes(raw_data), 9)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    return png

def icon_pixel(x, y, w, h):
    # Rounded golden-yellow rectangle with dark border and IMDb star motif
    corner_radius = max(2, w // 6)
    
    # Yellow background #F5C518 -> RGB(245, 197, 24)
    # Check if in rounded rect
    dx = min(x, w - 1 - x)
    dy = min(y, h - 1 - y)
    
    if dx < corner_radius and dy < corner_radius:
        dist_sq = (corner_radius - dx)**2 + (corner_radius - dy)**2
        if dist_sq > corner_radius**2:
            return (0, 0, 0, 0) # transparent
            
    # Border
    if x == 0 or x == w - 1 or y == 0 or y == h - 1:
        return (20, 20, 20, 255)
        
    # Letter 'I' / star center accent
    mid_x, mid_y = w / 2, h / 2
    if abs(x - mid_x) < max(1, w // 7) and abs(y - mid_y) < (h // 3):
        return (18, 18, 18, 255) # Dark bar
        
    return (245, 197, 24, 255) # IMDb Gold

def generate():
    out_dir = Path(__file__).resolve().parent / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for size in (16, 32, 48, 128):
        png_data = make_png(size, size, icon_pixel)
        file_path = out_dir / f"icon{size}.png"
        with open(file_path, "wb") as f:
            f.write(png_data)
        print(f"Generated {file_path.name} ({size}x{size})")

if __name__ == "__main__":
    generate()
