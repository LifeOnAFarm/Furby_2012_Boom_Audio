from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import struct
import wave

from .analysis import analysis_filter
from .bitstream import BitstreamWriter
from .decoder import compute_bit_alloc_for_frame, increment_allocation_bins
from .fixedpoint import (
    abs_s,
    add,
    extract_l,
    l_add,
    l_deposit_l,
    l_mult,
    l_mac0,
    l_shl,
    l_shr,
    l_sub,
    mult,
    negate,
    norm_s,
    shl,
    shr,
    sub,
)
from .tables_generated import (
    BIT_ALLOC_COST,
    FWD_CODEBOOK_CODES_0,
    FWD_CODEBOOK_CODES_1,
    FWD_CODEBOOK_CODES_2,
    FWD_CODEBOOK_CODES_3,
    FWD_CODEBOOK_CODES_4,
    FWD_CODEBOOK_CODES_5,
    FWD_CODEBOOK_CODES_6,
    FWD_CODEBOOK_WIDTHS_0,
    FWD_CODEBOOK_WIDTHS_1,
    FWD_CODEBOOK_WIDTHS_2,
    FWD_CODEBOOK_WIDTHS_3,
    FWD_CODEBOOK_WIDTHS_4,
    FWD_CODEBOOK_WIDTHS_5,
    FWD_CODEBOOK_WIDTHS_6,
    GAIN_HUFFMAN_CODES,
    GAIN_HUFFMAN_BIT_WIDTHS,
    QUANT_INV_STEP,
    QUANT_LEVELS_M1,
    QUANT_NUM_COEFF,
    QUANT_ROUNDING,
    QUANT_SCALE_BY_GAIN,
    QUANT_SCALE_FACTOR,
    SCALE_FACTOR_BITS,
)


MAX_SUBBANDS = 14
SAMPLES_PER_SUBBAND = 20
FRAME_SIZE = 320


def fwd_codebook_codes(step: int) -> list[int]:
    tables = [
        FWD_CODEBOOK_CODES_0,
        FWD_CODEBOOK_CODES_1,
        FWD_CODEBOOK_CODES_2,
        FWD_CODEBOOK_CODES_3,
        FWD_CODEBOOK_CODES_4,
        FWD_CODEBOOK_CODES_5,
        FWD_CODEBOOK_CODES_6,
    ]
    return tables[step]


def fwd_codebook_widths(step: int) -> list[int]:
    tables = [
        FWD_CODEBOOK_WIDTHS_0,
        FWD_CODEBOOK_WIDTHS_1,
        FWD_CODEBOOK_WIDTHS_2,
        FWD_CODEBOOK_WIDTHS_3,
        FWD_CODEBOOK_WIDTHS_4,
        FWD_CODEBOOK_WIDTHS_5,
        FWD_CODEBOOK_WIDTHS_6,
    ]
    return tables[step]


def compute_scale_param_from_gains(gain_indices: list[int], num_subbands: int) -> int:
    total_cost = 0
    max_eff_gain = 0
    for i in range(num_subbands):
        eff = extract_l(l_add(gain_indices[i], 0x18))
        if sub(eff, max_eff_gain) > 0:
            max_eff_gain = eff
        total_cost = add(total_cost, SCALE_FACTOR_BITS[eff])

    sp = 9
    cost_check = sub(total_cost, 8)
    gain_check = sub(max_eff_gain, 0x1C)
    while not (cost_check < 0 and gain_check < 1):
        sp = sub(sp, 1)
        total_cost = shr(total_cost, 1)
        max_eff_gain = sub(max_eff_gain, 2)
        cost_check = sub(total_cost, 8)
        gain_check = sub(max_eff_gain, 0x1C)
        if sp < 0:
            break
    return sp


def encode_gains(
    subbands: list[int],
    scale_param: int,
    num_subbands: int,
) -> tuple[list[int], list[int], list[int], int]:
    gain_indices = [0] * MAX_SUBBANDS
    gain_codes = [0] * MAX_SUBBANDS
    gain_widths = [0] * MAX_SUBBANDS
    bits_used = 0

    for sb in range(num_subbands):
        base = sb * SAMPLES_PER_SUBBAND
        energy = l_deposit_l(0)
        for j in range(SAMPLES_PER_SUBBAND):
            energy = l_mac0(energy, subbands[base + j], subbands[base + j])

        shift_count = 0
        while (energy & 0x7FFF0000) != 0:
            energy = l_shr(energy, 1)
            shift_count = add(shift_count, 1)

        check = l_sub(energy, 0x7FFF)
        check2 = add(shift_count, 0x0F)
        while check < 1 and check2 >= 0:
            energy = l_shl(energy, 1)
            check = l_sub(energy, 0x7FFF)
            shift_count -= 1
            check2 = add(shift_count, 0x0F)

        energy = l_shr(energy, 1)
        if l_sub(energy, 0x7123) >= 0:
            shift_count = add(shift_count, 1)

        sp_times2 = extract_l(l_shl(l_deposit_l(scale_param), 1))
        adjusted = l_sub(shift_count, sp_times2)
        with_offset = l_add(0x23, adjusted)
        gain_indices[sb] = extract_l(l_sub(with_offset, 0x18))

    if num_subbands >= 2:
        for i in range(num_subbands - 2, -1, -1):
            floor = sub(gain_indices[i + 1], 0x0B)
            if sub(gain_indices[i], floor) < 0:
                gain_indices[i] = floor

    lo = sub(1, 7)
    hi = sub(0x1F, 7)
    if sub(gain_indices[0], lo) < 0:
        gain_indices[0] = lo
    if sub(gain_indices[0], hi) > 0:
        gain_indices[0] = hi

    gain_widths[0] = 5
    gain_codes[0] = add(gain_indices[0], 7)
    bits_used = 5

    if num_subbands > 1:
        for sb in range(1, num_subbands):
            if sub(gain_indices[sb], sub(-8, 7)) < 0:
                gain_indices[sb] = sub(-8, 7)
            if sub(gain_indices[sb], sub(0x1F, 7)) > 0:
                gain_indices[sb] = sub(0x1F, 7)

        section_base = 24
        for sb in range(num_subbands - 1):
            diff = sub(gain_indices[sb + 1], gain_indices[sb])
            biased = sub(diff, -12)
            clamped = 0 if biased < 0 else biased
            gain_indices[sb + 1] = add(add(gain_indices[sb], clamped), -12)

            table_idx = clamped + section_base
            width = GAIN_HUFFMAN_BIT_WIDTHS[table_idx]
            code = GAIN_HUFFMAN_CODES[table_idx]
            gain_codes[sb + 1] = code
            gain_widths[sb + 1] = width
            bits_used = add(bits_used, width)
            section_base += 24

    return gain_indices, gain_codes, gain_widths, bits_used


def prescale_subbands(gain_indices: list[int], subbands: list[int], num_subbands: int) -> None:
    for sb in range(num_subbands):
        base = sb * SAMPLES_PER_SUBBAND
        shift = shr(sub(gain_indices[sb], 0x27), 1)
        if shift > 0:
            for j in range(SAMPLES_PER_SUBBAND):
                extended = l_shl(subbands[base + j], 0x10)
                rounded = l_add(extended, 0x8000)
                shifted = l_shr(rounded, shift)
                subbands[base + j] = extract_l(l_shr(shifted, 0x10))
            gain_indices[sb] = sub(gain_indices[sb], shl(shift, 1))


def select_frame_param(alloc: list[int], scratch: list[int], num_subbands: int, budget: int) -> int:
    cost = 0
    working = [0] * MAX_SUBBANDS
    for i in range(num_subbands):
        working[i] = alloc[i]
        cost = add(cost, BIT_ALLOC_COST[alloc[i]])

    if sub(cost, budget) <= 0:
        return 0

    for k in range(15):
        sb = scratch[k]
        if sb >= num_subbands:
            break
        old_step = working[sb]
        if sub(old_step, 7) < 0:
            cost = sub(cost, BIT_ALLOC_COST[old_step])
            working[sb] = add(old_step, 1)
            cost = add(cost, BIT_ALLOC_COST[working[sb]])
        if sub(cost, budget) <= 0:
            return add(k, 1)
    return 15


def forward_quantize(samples: list[int], num_levels: int, step: int, gain: int) -> tuple[int, int, int]:
    max_level = QUANT_INV_STEP[step]
    divisor = add(max_level, 1)
    rounding = QUANT_ROUNDING[step]
    scale_by_gain = QUANT_SCALE_BY_GAIN[gain] if 0 <= gain < len(QUANT_SCALE_BY_GAIN) else 0

    prod = l_mult(QUANT_SCALE_FACTOR[step], scale_by_gain)
    prod = l_shr(prod, 1)
    prod = l_add(prod, 0x1000)
    prod = l_shr(prod, 0x0D)
    prod = l_shr(prod, 2)
    quant_scale = extract_l(prod)

    symbol = 0
    sign_bits = 0
    num_signs = 0

    for j in range(num_levels):
        sample = samples[j]
        magnitude = abs_s(sample)
        scaled = l_mult(magnitude, quant_scale)
        scaled = l_shr(scaled, 1)
        rounded = l_add(scaled, rounding)
        shifted = l_shr(rounded, 0x0D)
        level = extract_l(shifted)
        if sub(level, max_level) > 0:
            level = max_level

        if level != 0:
            num_signs = add(num_signs, 1)
            sign_bits = shl(sign_bits, 1)
            if sample > 0:
                sign_bits = add(sign_bits, 1)

        acc = l_mult(symbol, divisor)
        acc = l_shr(acc, 1)
        symbol = add(extract_l(acc), level)

    return symbol, sign_bits, num_signs


def encode_subframes(
    subbands: list[int],
    alloc: list[int],
    gain_indices: list[int],
    num_subbands: int,
) -> tuple[list[int], list[int]]:
    encoded_data = [0] * 560
    subband_bits = [0] * MAX_SUBBANDS
    enc_pos = 0

    for sb in range(num_subbands):
        step = alloc[sb]
        base = sb * SAMPLES_PER_SUBBAND
        subband_bits[sb] = 0
        if sub(step, 7) >= 0:
            continue

        gain = gain_indices[sb]
        num_subframes = QUANT_NUM_COEFF[step]
        num_levels = QUANT_LEVELS_M1[step]
        if num_subframes < 1:
            continue

        in_pos = base
        for _ in range(num_subframes):
            symbol, sign_bits, num_signs = forward_quantize(
                subbands[in_pos:], num_levels, step, gain
            )
            in_pos += num_levels

            code = fwd_codebook_codes(step)[symbol]
            width = fwd_codebook_widths(step)[symbol]
            encoded_data[enc_pos] = width
            encoded_data[enc_pos + 1] = code
            encoded_data[enc_pos + 2] = num_signs
            encoded_data[enc_pos + 3] = sign_bits
            enc_pos += 4
            subband_bits[sb] = add(subband_bits[sb], add(width, num_signs))

    return encoded_data, subband_bits


def write_bitstream(
    output: list[int],
    gain_codes: list[int],
    gain_widths: list[int],
    num_subbands: int,
    frame_param: int,
    encoded_data: list[int],
    alloc: list[int],
) -> None:
    bw = BitstreamWriter(output)
    for sb in range(num_subbands):
        bw.write_bits(gain_codes[sb], gain_widths[sb])

    bw.write_bits(frame_param, 4)

    enc_pos = 0
    for sb in range(num_subbands):
        step = alloc[sb]
        if sub(step, 7) >= 0:
            continue
        num_subframes = QUANT_NUM_COEFF[step]
        if num_subframes < 1:
            continue
        for _ in range(num_subframes):
            width = encoded_data[enc_pos]
            code = encoded_data[enc_pos + 1]
            num_signs = encoded_data[enc_pos + 2]
            sign_bits = encoded_data[enc_pos + 3]
            enc_pos += 4
            bw.write_bits(code, width)
            if num_signs > 0:
                bw.write_bits(sign_bits, num_signs)
    bw.flush()


@dataclass
class EncoderState:
    bitrate: int
    bits_per_frame: int
    encoded_frame_size: int
    num_subbands: int
    analysis_memory: list[int] = field(default_factory=lambda: [0] * 320)

    @classmethod
    def new(cls, bitrate: int) -> "EncoderState":
        if bitrate < 4800 or bitrate > 32000:
            raise ValueError(f"invalid bitrate {bitrate}")
        snapped = ((bitrate + 400) // 800) * 800
        if snapped != bitrate:
            raise ValueError(f"invalid bitrate {bitrate}")
        if bitrate >= 16000:
            num_subbands = 14
        elif bitrate >= 12000:
            num_subbands = 12
        elif bitrate >= 9600:
            num_subbands = 10
        else:
            num_subbands = 8
        return cls(
            bitrate=bitrate,
            bits_per_frame=bitrate // 50,
            encoded_frame_size=bitrate // 800,
            num_subbands=num_subbands,
        )

    def encode_frame_to_words(self, pcm_input: list[int]) -> list[int]:
        subbands = [0] * FRAME_SIZE
        scale_param = analysis_filter(
            pcm_input,
            self.analysis_memory,
            subbands,
            FRAME_SIZE,
        )
        return self.encode_frame(subbands, scale_param)

    def encode_frame(self, subbands: list[int], scale_param: int) -> list[int]:
        gain_indices, gain_codes, gain_widths, bits_used = encode_gains(
            subbands,
            scale_param,
            self.num_subbands,
        )
        decoder_sp = compute_scale_param_from_gains(gain_indices, self.num_subbands)
        remaining_bits = sub(sub(self.bits_per_frame, bits_used), 4)
        alloc, scratch = compute_bit_alloc_for_frame(
            remaining_bits,
            self.num_subbands,
            gain_indices[: self.num_subbands],
        )
        frame_param = select_frame_param(alloc, scratch, self.num_subbands, remaining_bits)
        increment_allocation_bins(frame_param, alloc, scratch)

        offset = add(shl(decoder_sp, 1), 0x18)
        for i in range(self.num_subbands):
            gain_indices[i] = add(gain_indices[i], offset)

        prescale_subbands(gain_indices, subbands, self.num_subbands)
        encoded_data, _subband_bits = encode_subframes(
            subbands,
            alloc,
            gain_indices,
            self.num_subbands,
        )

        output = [0] * self.encoded_frame_size
        write_bitstream(
            output,
            gain_codes,
            gain_widths,
            self.num_subbands,
            frame_param,
            encoded_data,
            alloc,
        )
        return output


def read_wav_samples(path: str | Path) -> tuple[list[int], int]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width != 2:
        raise ValueError("only 16-bit PCM WAV files are supported")
    if channels not in (1, 2):
        raise ValueError(f"unsupported channel count: {channels}")

    raw = struct.unpack("<" + "h" * (len(frames) // 2), frames)
    if channels == 1:
        return list(raw), sample_rate

    samples = []
    for i in range(0, len(raw), 2):
        samples.append((raw[i] + raw[i + 1]) // 2)
    return samples, sample_rate


def encode_wav_to_a18_bytes(path: str | Path, bitrate: int = 16000) -> bytes:
    samples, sample_rate = read_wav_samples(path)
    if sample_rate != 16000:
        raise ValueError(f"expected 16000 Hz WAV input, got {sample_rate}")

    state = EncoderState.new(bitrate)
    payload_words: list[int] = []
    for offset in range(0, len(samples), FRAME_SIZE):
        frame = samples[offset : offset + FRAME_SIZE]
        if len(frame) < FRAME_SIZE:
            frame = frame + [0] * (FRAME_SIZE - len(frame))
        payload_words.extend(state.encode_frame_to_words(frame))

    payload = struct.pack("<" + "h" * len(payload_words), *payload_words)
    return struct.pack("<IH", len(payload), bitrate) + payload


def encode_wav_to_a18_file(
    input_path: str | Path,
    output_path: str | Path,
    bitrate: int = 16000,
) -> None:
    Path(output_path).write_bytes(encode_wav_to_a18_bytes(input_path, bitrate=bitrate))
