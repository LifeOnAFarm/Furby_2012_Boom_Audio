import os
import struct
from pathlib import Path

def get_file_size(file_path):
    """Get the size of a file in bytes."""
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def validate_a18_file(file_path):
    """Check if A18 file has the expected audio marker at offset 4-5."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read(6)  # Read first 6 bytes
            if len(data) >= 6:
                # Check for audio marker 0x80, 0x3E at bytes 4-5
                return data[4:6] == b'\x80\x3E'
    except:
        pass
    return False

def validate_bin_file(file_path):
    """Check if BIN file is exactly 256 bytes (image data)."""
    return get_file_size(file_path) == 256

def build_rom(bin_folder="converted_bins", a18_folder="converted_a18", output_file="combined_rom.bin"):
    """
    Build a ROM file by combining all .bin and .a18 files with proper header.
    Structure: [count][offsets...][audio_files...][image_files...]
    """
    
    print("ROM Builder - Matching Reference Structure")
    print("=" * 50)
    
    # Collect and validate files
    audio_files = []
    image_files = []
    
    # Collect A18 files (audio)
    if os.path.exists(a18_folder):
        a18_files = sorted([f for f in os.listdir(a18_folder) if f.lower().endswith('.a18')])
        for f in a18_files:
            file_path = os.path.join(a18_folder, f)
            if validate_a18_file(file_path):
                audio_files.append((file_path, f, 'A18'))
                print(f"Valid audio: {f} ({get_file_size(file_path)} bytes)")
            else:
                print(f"Warning: {f} doesn't have audio marker 0x80 0x3E at offset 4-5")
    else:
        print(f"Warning: {a18_folder} folder not found")
    
    # Collect BIN files (images)  
    if os.path.exists(bin_folder):
        bin_files = sorted([f for f in os.listdir(bin_folder) if f.lower().endswith('.bin')])
        for f in bin_files:
            file_path = os.path.join(bin_folder, f)
            if validate_bin_file(file_path):
                image_files.append((file_path, f, 'BIN'))
                print(f"Valid image: {f} (256 bytes)")
            else:
                print(f"Warning: {f} is not 256 bytes ({get_file_size(file_path)} bytes)")
    else:
        print(f"Warning: {bin_folder} folder not found")
    
    # Combine in order: audio first, then images (as per reference ROM)
    all_files = audio_files + image_files
    
    if not all_files:
        print("Error: No valid files found to combine!")
        return False
    
    print(f"\nTotal files to combine: {len(all_files)} ({len(audio_files)} audio + {len(image_files)} images)")
    print("-" * 50)
    
    # Calculate header size (no padding - files start right after header)
    num_files = len(all_files)
    header_size = 4 + (num_files * 4)  # 4 bytes for count + 4 bytes per offset
    
    # Calculate offsets (start immediately after header)
    offsets = []
    current_offset = header_size
    
    print("File layout:")
    print(f"Header size: {header_size} bytes (0x{header_size:X})")
    print(f"Data starts immediately at offset: 0x{current_offset:X}")
    print()
    
    # Audio files section
    if audio_files:
        print("AUDIO FILES:")
        for i, (file_path, filename, file_type) in enumerate(audio_files):
            file_size = get_file_size(file_path)
            offsets.append(current_offset)
            print(f"  {filename}: offset 0x{current_offset:X} ({current_offset}), size {file_size} bytes")
            current_offset += file_size
    
    # Image files section  
    if image_files:
        print("\nIMAGE FILES:")
        for i, (file_path, filename, file_type) in enumerate(image_files):
            file_size = get_file_size(file_path)  # Should be 256
            offsets.append(current_offset)
            print(f"  {filename}: offset 0x{current_offset:X} ({current_offset}), size {file_size} bytes")
            current_offset += file_size
    
    total_rom_size = current_offset
    print(f"\nTotal ROM size: {total_rom_size:,} bytes (0x{total_rom_size:X})")
    print("-" * 50)
    
    # Build the ROM
    try:
        with open(output_file, 'wb') as rom_file:
            # Write header: file count (4 bytes, little-endian)
            rom_file.write(struct.pack('<I', num_files))
            print(f"Written file count: {num_files} (0x{num_files:X})")
            
            # Write all offsets (4 bytes each, little-endian)
            for i, offset in enumerate(offsets):
                rom_file.write(struct.pack('<I', offset))
            print(f"Written {len(offsets)} file offsets")
            
            # Write file data directly (no padding)
            files_written = 0
            
            # Write audio files first
            if audio_files:
                print("\nWriting audio files:")
                for i, (file_path, filename, file_type) in enumerate(audio_files):
                    try:
                        with open(file_path, 'rb') as input_file:
                            data = input_file.read()
                            rom_file.write(data)
                            files_written += 1
                            
                            # Verify audio marker
                            marker = "✓" if len(data) >= 6 and data[4:6] == b'\x80\x3E' else "✗"
                            print(f"  {marker} {filename} ({len(data)} bytes)")
                    except Exception as e:
                        print(f"  Error reading {filename}: {e}")
                        return False
            
            # Write image files
            if image_files:
                print("\nWriting image files:")
                for i, (file_path, filename, file_type) in enumerate(image_files):
                    try:
                        with open(file_path, 'rb') as input_file:
                            data = input_file.read()
                            rom_file.write(data)
                            files_written += 1
                            
                            # Verify size
                            marker = "✓" if len(data) == 256 else "✗"
                            print(f"  {marker} {filename} ({len(data)} bytes)")
                    except Exception as e:
                        print(f"  Error reading {filename}: {e}")
                        return False
            
            print("-" * 50)
            print(f"ROM built successfully!")
            print(f"Output: {output_file}")
            print(f"Files included: {files_written}/{num_files}")
            print(f"Total size: {os.path.getsize(output_file):,} bytes (0x{os.path.getsize(output_file):X})")
            
            # Show structure summary matching your reference
            print(f"\nROM Structure Summary:")
            print(f"  Header: 0x0 - 0x{header_size-1:X} ({header_size} bytes)")
            if audio_files:
                first_audio_offset = header_size
                print(f"  Audio: 0x{first_audio_offset:X} onwards ({len(audio_files)} files)")
            if image_files:
                first_image_offset = offsets[len(audio_files)] if image_files else 0
                print(f"  Images: 0x{first_image_offset:X} onwards ({len(image_files)} files, 256 bytes each)")
            
            return True
            
    except Exception as e:
        print(f"Error writing ROM file: {e}")
        return False

def verify_rom(rom_file):
    """Verify the ROM structure by reading the header and checking file markers."""
    if not os.path.exists(rom_file):
        print(f"ROM file {rom_file} not found!")
        return False
    
    print(f"\nVerifying ROM: {rom_file}")
    print("-" * 30)
    
    try:
        with open(rom_file, 'rb') as f:
            # Read number of files
            num_files_data = f.read(4)
            if len(num_files_data) != 4:
                print("Error: Cannot read file count from header")
                return False
                
            num_files = struct.unpack('<I', num_files_data)[0]
            print(f"Number of files: {num_files} (0x{num_files:X})")
            
            # Read offsets
            offsets = []
            for i in range(num_files):
                offset_data = f.read(4)
                if len(offset_data) != 4:
                    print(f"Error: Cannot read offset {i}")
                    return False
                offset = struct.unpack('<I', offset_data)[0]
                offsets.append(offset)
            
            print(f"\nFirst 10 file offsets:")
            for i, offset in enumerate(offsets[:10]):
                print(f"  File {i}: offset 0x{offset:X} ({offset})")
            if len(offsets) > 10:
                print(f"  ... and {len(offsets)-10} more")
            
            # Verify file types by checking markers
            audio_count = 0
            image_count = 0
            
            print(f"\nFile type analysis (first 10 files):")
            for i, offset in enumerate(offsets[:10]):
                f.seek(offset)
                data = f.read(10)  # Read first 10 bytes
                
                if len(data) >= 6 and data[4:6] == b'\x80\x3E':
                    file_type = "AUDIO"
                    audio_count += 1
                elif i < len(offsets) - 1:
                    file_size = offsets[i + 1] - offset
                    if file_size == 256:
                        file_type = "IMAGE"
                        image_count += 1
                    else:
                        file_type = f"UNKNOWN ({file_size} bytes)"
                else:
                    # Last file
                    rom_size = os.path.getsize(rom_file)
                    file_size = rom_size - offset
                    if file_size == 256:
                        file_type = "IMAGE"
                        image_count += 1
                    else:
                        file_type = f"UNKNOWN ({file_size} bytes)"
                
                hex_preview = ' '.join(f'{b:02X}' for b in data[:6])
                print(f"  File {i}: {file_type} - {hex_preview}...")
            
            # Count all files
            for i, offset in enumerate(offsets):
                f.seek(offset)
                data = f.read(6)
                
                if len(data) >= 6 and data[4:6] == b'\x80\x3E':
                    if i >= 10:  # Don't double count first 10
                        audio_count += 1
                else:
                    if i >= 10:  # Don't double count first 10
                        image_count += 1
            
            print(f"\nFile summary:")
            print(f"  Audio files (with 0x80 0x3E marker): {audio_count}")
            print(f"  Image files (256 bytes): {image_count}")
            print(f"  Total: {audio_count + image_count}")
            
            rom_size = os.path.getsize(rom_file)
            print(f"\nROM file size: {rom_size:,} bytes (0x{rom_size:X})")
            print("ROM verification complete!")
            return True
            
    except Exception as e:
        print(f"Error verifying ROM: {e}")
        return False

def main():
    """Main function with user options."""
    print("ROM Builder Tool - Reference Structure Match")
    print("=" * 50)
    print("1. Build ROM from converted files (8MB)")
    print("2. Build ROM with custom size")
    print("3. Verify existing ROM structure") 
    print("4. Build and verify ROM")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        success = build_rom()
        if success:
            print("\n✓ ROM build completed successfully!")
        else:
            print("\n✗ ROM build failed!")
    
    elif choice == "2":
        try:
            size_mb = int(input("Enter target ROM size in MB (default: 8): ") or "8")
            success = build_rom(target_size_mb=size_mb)
            if success:
                print("\n✓ ROM build completed successfully!")
            else:
                print("\n✗ ROM build failed!")
        except ValueError:
            print("Invalid size!")
            
    elif choice == "3":
        rom_file = input("Enter ROM filename (default: combined_rom.bin): ").strip()
        if not rom_file:
            rom_file = "combined_rom.bin"
        verify_rom(rom_file)
        
    elif choice == "4":
        success = build_rom()
        if success:
            print("\n✓ ROM build completed successfully!")
            verify_rom("combined_rom.bin")
        else:
            print("\n✗ ROM build failed!")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()