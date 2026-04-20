from __future__ import annotations

from . import filterbank
from .fixedpoint import abs_s, add, extract_h, l_add, l_mac, l_mult, l_shr, negate, norm_s, shl, shr, sub
from .tables_generated import ANALYSIS_WINDOW


def analysis_filter(
    pcm_input: list[int],
    memory: list[int],
    subband_output: list[int],
    frame_size: int,
) -> int:
    n = frame_size
    half = shr(frame_size, 1)
    windowed = [0] * 320

    for k in range(half):
        acc = l_mac(0, ANALYSIS_WINDOW[half - 1 - k], memory[half - 1 - k])
        acc = l_mac(acc, ANALYSIS_WINDOW[half + k], memory[half + k])
        windowed[k] = extract_h(acc)

    for k in range(half):
        acc = l_mac(0, ANALYSIS_WINDOW[n - 1 - k], pcm_input[k])
        acc = l_mac(acc, negate(ANALYSIS_WINDOW[k]), pcm_input[n - 1 - k])
        windowed[half + k] = extract_h(acc)

    memory[:n] = pcm_input[:n]

    max_abs = 0
    for sample in windowed[:n]:
        mag = abs_s(sample)
        if sub(mag, max_abs) > 0:
            max_abs = mag

    if sub(max_abs, 14000) >= 0:
        scale_param = 0
    else:
        adjusted = add(max_abs, 1) if sub(max_abs, 0x1B6) < 0 else max_abs
        product = l_mult(adjusted, 0x2573)
        shifted = l_shr(product, 0x14)
        norm_val = norm_s(int(shifted))
        scale_param = 9 if norm_val == 0 else sub(norm_val, 6)

    sum_abs = 0
    for sample in windowed[:n]:
        sum_abs = l_add(sum_abs, abs_s(sample))
    if max_abs < l_shr(sum_abs, 7):
        scale_param = sub(scale_param, 1)

    if scale_param > 0:
        for i in range(n):
            windowed[i] = shl(windowed[i], scale_param)
    elif scale_param < 0:
        shift = negate(scale_param)
        for i in range(n):
            windowed[i] = shr(windowed[i], shift)

    filterbank.forward(windowed, subband_output, frame_size)
    return scale_param
