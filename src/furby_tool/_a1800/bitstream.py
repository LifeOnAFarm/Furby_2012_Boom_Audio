from __future__ import annotations

from dataclasses import dataclass

from .fixedpoint import add, shl, shr, sub


def to_i16(word: int) -> int:
    return ((word + 2**15) % 2**16) - 2**15


@dataclass
class BitstreamReader:
    data: list[int]
    total_bits_remaining: int
    pos: int = 0
    bits_remaining: int = 0
    current_word: int = 0
    last_bit: int = 0

    def read_bit(self) -> None:
        if self.bits_remaining == 0:
            self.current_word = self.data[self.pos]
            self.pos += 1
            self.bits_remaining = 16
        new_remaining = sub(self.bits_remaining, 1)
        self.bits_remaining = new_remaining
        shifted = shr(self.current_word, new_remaining)
        self.last_bit = shifted & 1

    def read_bits(self, width: int) -> int:
        value = 0
        for _ in range(width):
            self.read_bit()
            value = add(shl(value, 1), self.last_bit)
        return value


@dataclass
class BitstreamWriter:
    data: list[int]
    pos: int = 0
    bits_free: int = 16
    accumulator: int = 0

    def write_bits(self, value: int, width: int) -> None:
        remaining = width
        mask = 0xFFFF if width >= 16 else (1 << width) - 1
        val = value & mask

        while remaining > 0:
            if remaining >= self.bits_free:
                shift = remaining - self.bits_free
                bf_mask = 0xFFFF if self.bits_free >= 16 else (1 << self.bits_free) - 1
                self.accumulator |= (val >> shift) & bf_mask
                if self.pos >= len(self.data):
                    return
                self.data[self.pos] = to_i16(self.accumulator)
                self.pos += 1
                remaining = sub(remaining, self.bits_free)
                rem_mask = 0xFFFF if remaining >= 16 else (1 << remaining) - 1
                val &= rem_mask
                self.accumulator = 0
                self.bits_free = 16
            else:
                shift = self.bits_free - remaining
                self.accumulator |= val << shift
                self.bits_free = sub(self.bits_free, remaining)
                remaining = 0

    def flush(self) -> None:
        if self.bits_free < 16 and self.pos < len(self.data):
            self.data[self.pos] = to_i16(self.accumulator)
            self.pos += 1
            self.accumulator = 0
            self.bits_free = 16
