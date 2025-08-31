import os
import struct
from PIL import Image

# Same pixel mapping arrays as extraction (for reverse mapping)
x_offsets = [27, 26, 25, 24, 7, 6, 5, 4, 3, 2, 1, 0, 15, 14, 13, 12,
             11, 10, 9, 8, 28, 29, 30, 31, 16, 17, 18, 19, 20, 21, 22,
             23, 55, 54, 53, 52, 51, 50, 49, 48, 63, 62, 61, 60, 40, 41,
             42, 43, 44, 45, 46, 47, 32, 33, 34, 35, 36, 37, 38, 39, 56,
             57, 58, 59]
y_offsets = [960, 896, 832, 768, 704, 640, 576, 512, 448, 384, 320, 256,
             192, 128, 64, 0, 1024, 1088, 1152, 1216, 1280, 1344, 1408,
             1472, 1536, 1600, 1664, 1728, 1792, 1856, 1920, 1984]

def create_reverse_mapping():
    """Create reverse mapping from bit position to (x,y) coordinate."""
    reverse_map = {}
    for w in range(64):
        for h in range(32):
            pos = x_offsets[w] + y_offsets[h]
            reverse_map[pos] = (w, h)
    return reverse_map

def convert_bmp_to_bin(bmp_path, output_path):
    """Convert a single BMP back to 256-byte binary format."""
    # Load and prepare image
    img = Image.open(bmp_path)
    
    # Reverse the transformations that were applied during extraction
    img = img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
    
    # Convert to grayscale if needed
    if img.mode != 'L':
        img = img.convert('L')
    
    width, height = img.size
    if width != 64 or height != 32:
        print(f"Warning: {bmp_path} is not 64x32, resizing...")
        img = img.resize((64, 32))
    
    pixels = img.load()
    
    # Create reverse mapping
    reverse_map = create_reverse_mapping()
    
    # Initialize bit array (2048 bits = 256 bytes)
    bits = [0] * 2048
    
    # Fill bits array using reverse mapping
    for h in range(height):
        for w in range(width):
            pos = x_offsets[w] + y_offsets[h]
            # Convert pixel to bit (white = 1, black = 0)
            # Assuming grayscale: > 127 is white
            bit = 1 if pixels[w, h] > 127 else 0
            bits[pos] = bit
    
    # Convert bits to bytes
    binary_data = bytearray()
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        byte_value = 0
        for j, bit in enumerate(byte_bits):
            byte_value |= (bit << (7-j))  # MSB first
        binary_data.append(byte_value)
    
    # Write to file
    with open(output_path, 'wb') as f:
        f.write(binary_data)
    
    return len(binary_data)

def convert_all_bmps():
    """Convert all BMPs in convert_bmps folder to binary files."""
    input_folder = "convert_bmps"
    output_folder = "converted_bins"
    
    if not os.path.exists(input_folder):
        print(f"Error: Folder '{input_folder}' not found!")
        return
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all BMP files
    bmp_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.bmp')]
    
    if not bmp_files:
        print(f"No BMP files found in '{input_folder}'")
        return
    
    # Sort files to maintain order
    bmp_files.sort()
    
    converted_count = 0
    
    print(f"Converting {len(bmp_files)} BMP files...")
    print("=" * 50)
    
    for bmp_file in bmp_files:
        bmp_path = os.path.join(input_folder, bmp_file)
        
        # Generate output filename (replace .bmp with .bin)
        bin_filename = os.path.splitext(bmp_file)[0] + ".bin"
        bin_path = os.path.join(output_folder, bin_filename)
        
        try:
            size = convert_bmp_to_bin(bmp_path, bin_path)
            converted_count += 1
            print(f"Converted: {bmp_file} → {bin_filename} ({size} bytes)")
        except Exception as e:
            print(f"Error converting {bmp_file}: {e}")
    
    print("=" * 50)
    print(f"Conversion complete! {converted_count} files converted.")
    print(f"Binary files saved in: {output_folder}")



def main():
    print("BMP to Binary Converter")
    print("=" * 40)
    
    # Convert BMPs to individual binary files
    convert_all_bmps()

if __name__ == "__main__":
    main()