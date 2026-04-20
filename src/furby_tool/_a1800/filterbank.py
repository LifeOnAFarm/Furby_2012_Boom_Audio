from __future__ import annotations

from .fixedpoint import add, extract_h, extract_l, l_add, l_mac, l_shl, l_shr, l_sub, negate, shl, shr
from .tables_generated import (
    COSINE_MOD_MATRIX,
    FILTERBANK_COEFF_0,
    FILTERBANK_COEFF_1,
    FILTERBANK_COEFF_2,
    FILTERBANK_COEFF_3,
    FILTERBANK_COEFF_4,
)


def inverse(input_samples: list[int], frame_size: int) -> list[int]:
    n = frame_size
    buf_a = [0] * 320
    buf_b = [0] * 320

    src_pos = 0
    front = 0
    back = n
    while front < back:
        a = input_samples[src_pos]
        b = input_samples[src_pos + 1]
        src_pos += 2

        s = extract_l(l_shr(l_add(a, b), 1))
        d = extract_l(l_shr(l_add(a, -b), 1))

        back -= 1
        buf_a[front] = s
        front += 1
        buf_a[back] = d

    butterfly_16(buf_a, buf_b, n, 1)
    butterfly_16(buf_b, buf_a, n, 2)
    butterfly_16(buf_a, buf_b, n, 3)
    butterfly_16(buf_b, buf_a, n, 4)

    for g in range(32):
        for k in range(10):
            acc = 0
            for j in range(10):
                acc = l_mac(acc, buf_a[g * 10 + j], COSINE_MOD_MATRIX[k + j * 10])
            buf_b[g * 10 + k] = extract_h(l_shr(acc, 1))

    buf_a[:n] = buf_b[:n]

    reconstruct(buf_a, buf_b, n, 4, FILTERBANK_COEFF_0)
    reconstruct(buf_b, buf_a, n, 3, FILTERBANK_COEFF_1)
    reconstruct(buf_a, buf_b, n, 2, FILTERBANK_COEFF_2)
    reconstruct(buf_b, buf_a, n, 1, FILTERBANK_COEFF_3)
    output = [0] * 320
    reconstruct(buf_a, output, n, 0, FILTERBANK_COEFF_4)

    if frame_size == 320:
        for i in range(n):
            output[i] = shl(output[i], 1)

    return output


def butterfly_16(src: list[int], dst: list[int], n: int, stage: int) -> None:
    group_size = shr(n, stage)
    num_groups = shl(1, stage)

    src_pos = 0
    for g in range(num_groups):
        base = g * group_size
        front = base
        back = base + group_size
        while front < back:
            a = src[src_pos]
            b = src[src_pos + 1]
            src_pos += 2

            back -= 1
            dst[front] = add(a, b)
            front += 1
            dst[back] = add(a, negate(b))


def reconstruct(src: list[int], dst: list[int], n: int, stage: int, coeffs: list[int]) -> None:
    group_size = shr(n, stage)
    num_groups = shl(1, stage)
    half = group_size // 2

    for g in range(num_groups):
        src_base = g * group_size
        dst_base = g * group_size

        src_first = src_base
        src_second = src_base + half
        dst_front = dst_base
        dst_back = dst_base + group_size
        ci = 0

        while dst_front < dst_back:
            a = src[src_first]
            b = src[src_first + 1]
            c = src[src_second]
            d = src[src_second + 1]
            src_first += 2
            src_second += 2

            c0 = coeffs[ci]
            c1 = coeffs[ci + 1]
            c2 = coeffs[ci + 2]
            c3 = coeffs[ci + 3]
            ci += 4

            val_a = extract_h(l_shl(l_mac(l_mac(0, c0, a), negate(c1), c), 1))
            val_b = extract_h(l_shl(l_mac(l_mac(0, c1, a), c0, c), 1))
            val_c = extract_h(l_shl(l_mac(l_mac(0, c2, b), c3, d), 1))
            val_d = extract_h(l_shl(l_mac(l_mac(0, c3, b), negate(c2), d), 1))

            dst[dst_front] = val_a
            dst[dst_front + 1] = val_c
            dst[dst_back - 1] = val_b
            dst[dst_back - 2] = val_d

            dst_front += 2
            dst_back -= 2
