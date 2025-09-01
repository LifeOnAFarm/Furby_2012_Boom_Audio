import re

def text_to_bin(input_file, output_file):
    with open(input_file, "r") as f:
        lines = f.readlines()

    bytearray_out = bytearray()

    for line in lines:
        # Skip progress lines
        if line.strip().startswith("# Progress:"):
            continue

        # Remove the leading address like "0x00000:"
        line = re.sub(r"^0x[0-9A-Fa-f]+:\s*", "", line)

        # Remove extra spacing that breaks groups
        parts = line.strip().split()

        # Filter out non-hex entries (in case of formatting issues)
        for p in parts:
            if re.fullmatch(r"[0-9A-Fa-f]{2}", p):
                bytearray_out.append(int(p, 16))

    # Write to .bin
    with open(output_file, "wb") as out:
        out.write(bytearray_out)

if __name__ == "__main__":
    text_to_bin("furby_dump_full.txt", "rom_dump.bin")
    print("Done! Wrote rom_dump.bin")
