from __future__ import annotations

from .filterbank import inverse
from .fixedpoint import extract_h, l_mac, l_shl, negate, shl, shr
from .tables_generated import SYNTH_OVERLAP_OFFSETS


def synthesize(
    subband_samples: list[int],
    memory: list[int],
    frame_size: int,
    scale_param: int,
) -> list[int]:
    n = frame_size
    half = shr(frame_size, 1)
    filtered = inverse(subband_samples, frame_size)

    if scale_param > 0:
        for i in range(n):
            filtered[i] = shr(filtered[i], scale_param)
    elif scale_param < 0:
        shift = negate(scale_param)
        for i in range(n):
            filtered[i] = shl(filtered[i], shift)

    output = [0] * n
    for k in range(half):
        acc = l_mac(0, SYNTH_OVERLAP_OFFSETS[k], filtered[half - 1 - k])
        acc = l_mac(acc, SYNTH_OVERLAP_OFFSETS[n - 1 - k], memory[k])
        output[k] = extract_h(l_shl(acc, 2))

    for k in range(half):
        acc = l_mac(0, SYNTH_OVERLAP_OFFSETS[half + k], filtered[k])
        acc = l_mac(acc, negate(SYNTH_OVERLAP_OFFSETS[half - 1 - k]), memory[half - 1 - k])
        output[half + k] = extract_h(l_shl(acc, 2))

    memory[:half] = filtered[half : half + half]
    return output
