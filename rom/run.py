import struct

with open("rom_dump.bin", "rb") as f:
    rom_data = f.read()

# Skip first DWORD
offset = 4
pointers = []

while offset + 4 <= len(rom_data):
    ptr = struct.unpack("<I", rom_data[offset:offset+4])[0]
    if ptr == 0:
        break  # Stop at buffer of zeros
    pointers.append(ptr)
    offset += 4

print(f"Found {len(pointers)} pointers")
print(f"Last few pointers: {pointers[-10:]}")
