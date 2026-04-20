from __future__ import annotations


MAX_16 = 0x7FFF
MIN_16 = -0x8000
MAX_32 = 0x7FFFFFFF
MIN_32 = -0x80000000


def saturate(val: int) -> int:
    if val > MAX_16:
        return MAX_16
    if val < MIN_16:
        return MIN_16
    return val


def add(a: int, b: int) -> int:
    return saturate(a + b)


def sub(a: int, b: int) -> int:
    return saturate(a - b)


def abs_s(val: int) -> int:
    if val == MIN_16:
        return MAX_16
    if val < 0:
        return -val
    return val


def negate(val: int) -> int:
    if val == MIN_16:
        return MAX_16
    return -val


def shr(val: int, shift: int) -> int:
    if shift < 0:
        if shift < -16:
            return shl(val, 16)
        return shl(val, -shift)
    if shift > 14:
        return -1 if val < 0 else 0
    if val < 0:
        return ~((~val) >> (shift & 0x1F))
    return val >> (shift & 0x1F)


def shl(val: int, shift: int) -> int:
    if shift < 0:
        if shift < -16:
            return shr(val, 16)
        return shr(val, -shift)
    result = (1 << (shift & 0x1F)) * val
    if (shift < 16 or val == 0) and result - int((result + 2**15) % 2**16 - 2**15) == 0:
        return result
    return MIN_16 if val < 1 else MAX_16


def mult(a: int, b: int) -> int:
    result = (a * b) >> 15
    sign_extended = result | ~0xFFFF if (result & 0x10000) != 0 else result
    return saturate(sign_extended)


def l_mult(a: int, b: int) -> int:
    result = a * b
    if result != 0x40000000:
        return result * 2
    return MAX_32


def l_add(a: int, b: int) -> int:
    result = (a + b) & 0xFFFFFFFF
    if result & 0x80000000:
        result -= 0x100000000
    if ((a ^ b) & MIN_32) == 0 and ((result ^ a) & MIN_32) != 0:
        return MIN_32 if a < 0 else MAX_32
    return result


def l_sub(a: int, b: int) -> int:
    result = (a - b) & 0xFFFFFFFF
    if result & 0x80000000:
        result -= 0x100000000
    if ((a ^ b) & MIN_32) != 0 and ((result ^ a) & MIN_32) != 0:
        return MIN_32 if a < 0 else MAX_32
    return result


def l_mac(acc: int, a: int, b: int) -> int:
    return l_add(acc, l_mult(a, b))


def l_shl(val: int, shift: int) -> int:
    if shift <= 0:
        if shift < -32:
            return l_shr(val, 32)
        return l_shr(val, -shift)
    v = val
    s = shift
    while True:
        if v > 0x3FFFFFFF:
            return MAX_32
        if v < -0x40000000:
            return MIN_32
        v *= 2
        s -= 1
        if s <= 0:
            return v


def l_shr(val: int, shift: int) -> int:
    if shift < 0:
        if shift < -32:
            return l_shl(val, 32)
        return l_shl(val, -shift)
    if shift > 30:
        return -1 if val < 0 else 0
    if val < 0:
        return ~((~val) >> (shift & 0x1F))
    return val >> (shift & 0x1F)


def extract_h(val: int) -> int:
    return val >> 16


def extract_l(val: int) -> int:
    return ((val + 2**15) % 2**16) - 2**15


def l_deposit_l(val: int) -> int:
    return val


def norm_s(val: int) -> int:
    if val == 0:
        return 0
    if val == -1:
        return 15
    v = (~val if val < 0 else val) & 0xFFFF
    count = 0
    while v < 0x4000:
        v <<= 1
        count += 1
    return count


def l_mult0(a: int, b: int) -> int:
    return a * b


def l_mac0(acc: int, a: int, b: int) -> int:
    return l_add(acc, l_mult0(a, b))
