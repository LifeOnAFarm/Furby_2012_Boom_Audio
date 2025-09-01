import os
import struct
from PIL import Image

# Pixel mapping arrays for images
x_offsets = [27, 26, 25, 24, 7, 6, 5, 4, 3, 2, 1, 0, 15, 14, 13, 12,
             11, 10, 9, 8, 28, 29, 30, 31, 16, 17, 18, 19, 20, 21, 22,
             23, 55, 54, 53, 52, 51, 50, 49, 48, 63, 62, 61, 60, 40, 41,
             42, 43, 44, 45, 46, 47, 32, 33, 34, 35, 36, 37, 38, 39, 56,
             57, 58, 59]
y_offsets = [960, 896, 832, 768, 704, 640, 576, 512, 448, 384, 320, 256,
             192, 128, 64, 0, 1024, 1088, 1152, 1216, 1280, 1344, 1408,
             1472, 1536, 1600, 1664, 1728, 1792, 1856, 1920, 1984]

def get_bits(byte):
    """Convert a byte into a list of 8 bits (MSB first)."""
    return [(byte >> i) & 1 for i in reversed(range(8))]

def analyze_header(rom_data):
    """Read offsets from the ROM header."""
    num_offsets = struct.unpack('<I', rom_data[0:4])[0]
    offsets = []
    for i in range(num_offsets):
        offset = struct.unpack('<I', rom_data[4 + i*4 : 8 + i*4])[0]
        offsets.append(offset)
    return offsets

def extract_audio_tracks(rom_data, offsets):
    """Extract audio tracks from ROM data."""
    os.makedirs("a18_files", exist_ok=True)
    audio_offsets = []
    audio_count = 0
    
    for start in offsets:
        end_idx = offsets.index(start) + 1
        end = offsets[end_idx] if end_idx < len(offsets) else len(rom_data)
        
        # Only process if audio marker present
        if rom_data[start+4:start+6] != b'\x80\x3e':
            continue
        
        track_data = rom_data[start:end]
        audio_count += 1
        filename = f"a18_files/audio{audio_count:04d}.a18"
        with open(filename, "wb") as out:
            out.write(track_data)
        
        audio_offsets.append(start)
        print(f"Audio Track {audio_count}: {len(track_data)} bytes → {filename}")
    
    return audio_offsets

def extract_images(rom_path, offsets, audio_offsets):
    """Extract 256-byte image records, skipping audio offsets."""
    os.makedirs("imgs", exist_ok=True)
    image_count = 0
    
    with open(rom_path, "rb") as f:
        for i, start in enumerate(offsets):
            if start in audio_offsets:
                continue
            
            end = offsets[i+1] if i < len(offsets)-1 else os.path.getsize(rom_path)
            size = end - start
            if size != 256:
                continue  # Skip non-image records
            
            f.seek(start)
            buf = f.read(size)
            
            bits = []
            for b in buf:
                bits.extend(get_bits(b))
            
            width, height = 64, 32
            img = Image.new("RGB", (width, height), "white")
            pixels = img.load()
            
            for h in range(height):
                for w in range(width):
                    pos = x_offsets[w] + y_offsets[h]
                    bit = bits[pos]
                    pixels[w, h] = (255, 255, 255) if bit else (0, 0, 0)
            image_count += 1
            img = img.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
            img.save(f"imgs/img_{image_count:04d}.bmp")
            print(f"Extracted image at offset {hex(start)}")

def main():
    rom_path = "rom/rom_dump.bin"
    with open(rom_path, "rb") as f:
        rom_data = f.read()
    
    print("Reading header and offsets...")
    offsets = analyze_header(rom_data)
    
    print("\nExtracting audio tracks...")
    audio_offsets = extract_audio_tracks(rom_data, offsets)
    
    print("\nExtracting images...")
    extract_images(rom_path, offsets, audio_offsets)
    
    print("\nExtraction complete!")

if __name__ == "__main__":
    print("Furby ROM Extractor")
    print("=" * 40)
    main()
