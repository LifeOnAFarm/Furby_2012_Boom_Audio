import os
import shutil
from pathlib import Path

def duplicate_file(source_file, output_folder, base_name, start_num, end_num, extension):
    """
    Create multiple copies of a file with sequential numbering.
    
    Args:
        source_file: Path to the source file to duplicate
        output_folder: Folder where duplicates will be saved
        base_name: Base name for the files (e.g., "img_", "audio")
        start_num: Starting number (e.g., 1)
        end_num: Ending number (inclusive, e.g., 3054)
        extension: File extension (e.g., ".bmp", ".a18")
    """
    
    if not os.path.exists(source_file):
        print(f"Error: Source file '{source_file}' not found!")
        return False
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get source file size for progress info
    source_size = os.path.getsize(source_file)
    total_files = end_num - start_num + 1
    
    print(f"Duplicating '{source_file}' ({source_size} bytes)")
    print(f"Creating {total_files} copies: {base_name}{start_num:04d}{extension} to {base_name}{end_num:04d}{extension}")
    print(f"Output folder: {output_folder}")
    print("-" * 60)
    
    success_count = 0
    
    for i in range(start_num, end_num + 1):
        # Generate filename with 4-digit padding
        filename = f"{base_name}{i:04d}{extension}"
        output_path = os.path.join(output_folder, filename)
        
        try:
            # Copy the file
            shutil.copy2(source_file, output_path)
            success_count += 1
            
            # Show progress every 100 files or for small batches every 10 files
            if total_files > 100:
                if i % 100 == 0 or i == end_num:
                    print(f"Progress: {success_count}/{total_files} files created... ({filename})")
            elif total_files > 10:
                if i % 10 == 0 or i == end_num:
                    print(f"Progress: {success_count}/{total_files} files created... ({filename})")
            else:
                print(f"Created: {filename}")
                
        except Exception as e:
            print(f"Error creating {filename}: {e}")
    
    print("-" * 60)
    print(f"Duplication complete!")
    print(f"Successfully created: {success_count}/{total_files} files")
    print(f"Total space used: {success_count * source_size:,} bytes ({success_count * source_size / 1024 / 1024:.1f} MB)")
    
    return success_count == total_files

def duplicate_bmp_files():
    """Duplicate BMP files with img_ prefix."""
    print("BMP File Duplicator")
    print("=" * 40)
    
    source_file = input("Enter source BMP file path: ").strip()
    if not source_file:
        print("No file specified!")
        return
    
    # Default values for BMP
    output_folder = input("Enter output folder (default: 'duplicated_bmps'): ").strip()
    if not output_folder:
        output_folder = "duplicated_bmps"
    
    try:
        start_num = int(input("Enter starting number (default: 1): ") or "1")
        end_num = int(input("Enter ending number (default: 3054): ") or "3054")
        
        if start_num > end_num:
            print("Error: Starting number must be <= ending number!")
            return
            
        base_name = input("Enter base name (default: 'img_'): ").strip()
        if not base_name:
            base_name = "img_"
            
    except ValueError:
        print("Invalid number entered!")
        return
    
    duplicate_file(source_file, output_folder, base_name, start_num, end_num, ".bmp")

def duplicate_a18_files():
    """Duplicate A18 files with audio prefix."""
    print("A18 File Duplicator")
    print("=" * 40)
    
    source_file = input("Enter source A18 file path: ").strip()
    if not source_file:
        print("No file specified!")
        return
    
    # Default values for A18
    output_folder = input("Enter output folder (default: 'duplicated_a18s'): ").strip()
    if not output_folder:
        output_folder = "duplicated_a18s"
    
    try:
        start_num = int(input("Enter starting number (default: 1): ") or "1")
        end_num = int(input("Enter ending number: "))
        
        if start_num > end_num:
            print("Error: Starting number must be <= ending number!")
            return
            
        base_name = input("Enter base name (default: 'audio'): ").strip()
        if not base_name:
            base_name = "audio"
            
    except ValueError:
        print("Invalid number entered!")
        return
    
    duplicate_file(source_file, output_folder, base_name, start_num, end_num, ".a18")

def duplicate_any_file():
    """Duplicate any file type with custom settings."""
    print("Custom File Duplicator")
    print("=" * 40)
    
    source_file = input("Enter source file path: ").strip()
    if not source_file:
        print("No file specified!")
        return
    
    # Get file extension from source
    source_ext = Path(source_file).suffix
    
    output_folder = input("Enter output folder: ").strip()
    if not output_folder:
        print("No output folder specified!")
        return
    
    try:
        start_num = int(input("Enter starting number: "))
        end_num = int(input("Enter ending number: "))
        
        if start_num > end_num:
            print("Error: Starting number must be <= ending number!")
            return
            
        base_name = input("Enter base name (e.g., 'file_', 'data'): ").strip()
        if not base_name:
            print("No base name specified!")
            return
            
        extension = input(f"Enter file extension (default: '{source_ext}'): ").strip()
        if not extension:
            extension = source_ext
        elif not extension.startswith('.'):
            extension = '.' + extension
            
    except ValueError:
        print("Invalid number entered!")
        return
    
    duplicate_file(source_file, output_folder, base_name, start_num, end_num, extension)

def batch_duplicate():
    """Create both BMP and A18 duplicates in one go."""
    print("Batch Duplicator (BMP + A18)")
    print("=" * 40)
    
    # BMP settings
    bmp_file = input("Enter source BMP file (or press Enter to skip): ").strip()
    # A18 settings  
    a18_file = input("Enter source A18 file (or press Enter to skip): ").strip()
    
    if not bmp_file and not a18_file:
        print("No files specified!")
        return
    
    try:
        if bmp_file:
            bmp_count = int(input("How many BMP copies? (default: 3054): ") or "3054")
        if a18_file:
            a18_count = int(input("How many A18 copies? "))
    except ValueError:
        print("Invalid numbers!")
        return
    
    print("\nStarting batch duplication...")
    print("=" * 40)
    
    # Duplicate BMPs
    if bmp_file:
        print("1. Creating BMP duplicates...")
        duplicate_file(bmp_file, "duplicated_bmps", "img_", 1, bmp_count, ".bmp")
        print()
    
    # Duplicate A18s
    if a18_file:
        print("2. Creating A18 duplicates...")
        duplicate_file(a18_file, "duplicated_a18s", "audio", 1, a18_count, ".a18")
        print()
    
    print("Batch duplication complete!")

def main():
    """Main menu."""
    print("File Duplicator Tool")
    print("=" * 50)
    print("1. Duplicate BMP files (img_XXXX.bmp format)")
    print("2. Duplicate A18 files (audioXXXX.a18 format)")
    print("3. Duplicate any file type (custom format)")
    print("4. Batch duplicate (BMP + A18 together)")
    print("5. Exit")
    
    while True:
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            duplicate_bmp_files()
        elif choice == "2":
            duplicate_a18_files()
        elif choice == "3":
            duplicate_any_file()
        elif choice == "4":
            batch_duplicate()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Invalid choice! Please enter 1-5.")
        
        print("\n" + "=" * 50)

if __name__ == "__main__":
    main()