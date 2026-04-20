from __future__ import annotations

from pathlib import Path


IMAGE_RECORD_SIZE = 256
IMAGE_WIDTH = 64
IMAGE_HEIGHT = 32

x_offsets = [
    27, 26, 25, 24, 7, 6, 5, 4, 3, 2, 1, 0, 15, 14, 13, 12,
    11, 10, 9, 8, 28, 29, 30, 31, 16, 17, 18, 19, 20, 21, 22,
    23, 55, 54, 53, 52, 51, 50, 49, 48, 63, 62, 61, 60, 40, 41,
    42, 43, 44, 45, 46, 47, 32, 33, 34, 35, 36, 37, 38, 39, 56,
    57, 58, 59,
]
y_offsets = [
    960, 896, 832, 768, 704, 640, 576, 512, 448, 384, 320, 256,
    192, 128, 64, 0, 1024, 1088, 1152, 1216, 1280, 1344, 1408,
    1472, 1536, 1600, 1664, 1728, 1792, 1856, 1920, 1984,
]


def get_bits(byte: int) -> list[int]:
    return [(byte >> i) & 1 for i in reversed(range(8))]


def decode_image_record(data: bytes):
    from PIL import Image

    if len(data) != IMAGE_RECORD_SIZE:
        raise ValueError(f"Image record must be {IMAGE_RECORD_SIZE} bytes, got {len(data)}")

    bits: list[int] = []
    for byte in data:
        bits.extend(get_bits(byte))

    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "white")
    pixels = image.load()

    for h in range(IMAGE_HEIGHT):
        for w in range(IMAGE_WIDTH):
            pos = x_offsets[w] + y_offsets[h]
            bit = bits[pos]
            pixels[w, h] = (255, 255, 255) if bit else (0, 0, 0)

    return image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)


def encode_image_to_record(image) -> bytes:
    from PIL import Image

    img = image.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.FLIP_TOP_BOTTOM)
    if img.mode != "L":
        img = img.convert("L")
    if img.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
        img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT))

    pixels = img.load()
    bits = [0] * (IMAGE_RECORD_SIZE * 8)

    for h in range(IMAGE_HEIGHT):
        for w in range(IMAGE_WIDTH):
            pos = x_offsets[w] + y_offsets[h]
            bits[pos] = 1 if pixels[w, h] > 127 else 0

    output = bytearray()
    for i in range(0, len(bits), 8):
        value = 0
        for j, bit in enumerate(bits[i:i + 8]):
            value |= bit << (7 - j)
        output.append(value)

    return bytes(output)


def convert_bmp_file_to_record(input_path: str | Path, output_path: str | Path) -> int:
    from PIL import Image

    image = Image.open(input_path)
    data = encode_image_to_record(image)
    Path(output_path).write_bytes(data)
    return len(data)
