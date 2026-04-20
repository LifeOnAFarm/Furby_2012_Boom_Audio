from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import struct
import wave

from .bitstream import BitstreamReader
from .fixedpoint import add, extract_l, l_add, l_mult0, l_shr, mult, negate, shl, shr, sub
from .synthesis import synthesize
from .tables_generated import (
    BIT_ALLOC_COST,
    CODEBOOK_TREE_0,
    CODEBOOK_TREE_1,
    CODEBOOK_TREE_2,
    CODEBOOK_TREE_3,
    CODEBOOK_TREE_4,
    CODEBOOK_TREE_5,
    CODEBOOK_TREE_6,
    GAIN_HUFFMAN_TREE,
    QUANT_INV_STEP,
    QUANT_LEVELS_M1,
    QUANT_NUM_COEFF,
    QUANT_RECON_LEVELS,
    QUANT_STEP_SIZE,
    SCALE_FACTOR_BITS,
)


MAX_SUBBANDS = 14
SAMPLES_PER_SUBBAND = 20
FRAME_SIZE = 320
NOISE_GAINS = [0x16A1, 0x2000, 0x5A82]


def codebook_tree(step: int) -> list[int]:
    trees = [
        CODEBOOK_TREE_0,
        CODEBOOK_TREE_1,
        CODEBOOK_TREE_2,
        CODEBOOK_TREE_3,
        CODEBOOK_TREE_4,
        CODEBOOK_TREE_5,
        CODEBOOK_TREE_6,
    ]
    return trees[step]


def noise_prng(state: list[int]) -> int:
    val = extract_l(l_add(state[0], state[3]))
    if (val & 0x8000) != 0:
        val = add(val, 1)
    state[3] = state[2]
    state[2] = state[1]
    state[1] = state[0]
    state[0] = val
    return val


def inverse_quantize(symbol: int, digits: list[int], step: int) -> int:
    nonzero = 0
    divisor = add(QUANT_INV_STEP[step], 1)
    step_size = QUANT_STEP_SIZE[step]
    num_digits = sub(QUANT_LEVELS_M1[step], 1)
    if num_digits >= 0:
        count = num_digits + 1
        val = symbol
        for j in range(count - 1, -1, -1):
            quotient = mult(val, step_size)
            prod_lo = extract_l(l_mult0(quotient, divisor))
            remainder = sub(val, prod_lo)
            digits[j] = remainder
            if remainder != 0:
                nonzero = add(nonzero, 1)
            val = quotient
    return nonzero


def compute_allocation(gains: list[int], num_subbands: int, threshold: int) -> list[int]:
    alloc = [0] * MAX_SUBBANDS
    for i in range(num_subbands):
        q = shr(sub(threshold, gains[i]), 1)
        if q < 0:
            q = 0
        if sub(q, 7) > 0:
            q = 7
        alloc[i] = q
    return alloc


def search_threshold(gains: list[int], num_subbands: int, budget: int) -> int:
    thresh = -32
    step = 32
    while True:
        candidate = add(thresh, step)
        local_alloc = compute_allocation(gains, num_subbands, candidate)
        cost = 0
        for i in range(num_subbands):
            cost = add(cost, BIT_ALLOC_COST[local_alloc[i]])
        target = sub(budget, 0x20)
        if sub(cost, target) >= 0:
            thresh = candidate
        step = shr(step, 1)
        if step <= 0:
            break
    return thresh


def optimize_allocation(
    alloc: list[int],
    gains: list[int],
    budget: int,
    num_subbands: int,
    num_iterations: int,
    threshold: int,
) -> tuple[list[int], list[int]]:
    inc_cost = 0
    for i in range(num_subbands):
        inc_cost = add(inc_cost, BIT_ALLOC_COST[alloc[i]])

    dec_alloc = alloc[:]
    inc_alloc = alloc[:]
    dec_cost = inc_cost
    max_iter = num_iterations - 1
    low_idx = num_iterations
    high_idx = num_iterations
    swap_log = [0] * 32

    for _ in range(max_iter):
        total = add(dec_cost, inc_cost)
        doubled_budget = shl(budget, 1)
        if sub(total, doubled_budget) < 1:
            best_idx = 0
            best_metric = 99
            for idx in range(num_subbands):
                if dec_alloc[idx] > 0:
                    metric = sub(sub(threshold, gains[idx]), shl(dec_alloc[idx], 1))
                    if sub(metric, best_metric) < 0:
                        best_idx = idx
                        best_metric = metric
            low_idx = sub(low_idx, 1)
            swap_log[low_idx] = best_idx
            old_step = dec_alloc[best_idx]
            dec_cost = sub(dec_cost, BIT_ALLOC_COST[old_step])
            dec_alloc[best_idx] = sub(old_step, 1)
            dec_cost = add(dec_cost, BIT_ALLOC_COST[dec_alloc[best_idx]])
        else:
            best_idx = 0
            best_metric = -99
            idx = sub(num_subbands, 1)
            while idx >= 0:
                i = idx
                if sub(inc_alloc[i], 7) < 0:
                    metric = sub(sub(threshold, gains[i]), shl(inc_alloc[i], 1))
                    if sub(metric, best_metric) > 0:
                        best_metric = metric
                        best_idx = i
                idx -= 1
            swap_log[high_idx] = best_idx
            high_idx = add(high_idx, 1)
            old_step = inc_alloc[best_idx]
            if sub(old_step, 7) < 0:
                inc_cost = sub(inc_cost, BIT_ALLOC_COST[old_step])
                inc_alloc[best_idx] = add(old_step, 1)
                inc_cost = add(inc_cost, BIT_ALLOC_COST[inc_alloc[best_idx]])

    scratch = [0] * 32
    out_idx = 0
    log_idx = low_idx
    while out_idx < max_iter:
        scratch[out_idx] = swap_log[log_idx]
        log_idx += 1
        out_idx += 1
    return dec_alloc, scratch


def increment_allocation_bins(count: int, alloc: list[int], scratch: list[int]) -> None:
    remaining = count
    idx = 0
    while remaining > 0:
        subband = scratch[idx]
        alloc[subband] = add(alloc[subband], 1)
        idx += 1
        remaining = sub(remaining, 1)


def compute_bit_alloc_for_frame(remaining_bits: int, num_subbands: int, gains: list[int]) -> tuple[list[int], list[int]]:
    if sub(remaining_bits, 0x140) > 0:
        excess = sub(remaining_bits, 0x140)
        reduced = shr(extract_l(l_mult0(excess, 5)), 3)
        budget = add(reduced, 0x140)
    else:
        budget = remaining_bits

    threshold = search_threshold(gains, num_subbands, budget)
    alloc = compute_allocation(gains, num_subbands, threshold)
    return optimize_allocation(alloc, gains, budget, num_subbands, 16, threshold)


@dataclass
class DecoderState:
    bitrate: int
    bits_per_frame: int
    encoded_frame_size: int
    num_subbands: int
    prng_state: list[int] = field(default_factory=lambda: [1, 1, 1, 1])
    synth_memory: list[int] = field(default_factory=lambda: [0] * 160)

    @classmethod
    def new(cls, bitrate: int) -> "DecoderState":
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

    def decode_gains(self, bs: BitstreamReader) -> tuple[list[int], list[int], int]:
        gains = [0] * MAX_SUBBANDS
        scale_factors = [0] * MAX_SUBBANDS
        initial_gain = sub(bs.read_bits(5), 7)
        bs.total_bits_remaining = sub(bs.total_bits_remaining, 5)

        differentials = [0] * MAX_SUBBANDS
        tree_base = 23
        for d in range(self.num_subbands - 1):
            node = 0
            while True:
                bs.read_bit()
                entry = node + tree_base
                node = GAIN_HUFFMAN_TREE[entry][0] if bs.last_bit == 0 else GAIN_HUFFMAN_TREE[entry][1]
                bs.total_bits_remaining = sub(bs.total_bits_remaining, 1)
                if node <= 0:
                    break
            differentials[d] = negate(node)
            tree_base += 23

        gains[0] = initial_gain
        for i in range(self.num_subbands - 1):
            gains[i + 1] = extract_l(l_add(l_add(gains[i], differentials[i]), -12))

        total_cost = 0
        max_eff_gain = 0
        for i in range(self.num_subbands):
            eff_i16 = extract_l(l_add(gains[i], 0x18))
            if sub(eff_i16, max_eff_gain) > 0:
                max_eff_gain = eff_i16
            total_cost = add(total_cost, SCALE_FACTOR_BITS[eff_i16])

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

        offset = sp * 2 + 0x18
        for i in range(self.num_subbands):
            scale_factors[i] = SCALE_FACTOR_BITS[extract_l(l_add(gains[i], offset))]

        return gains, scale_factors, sp

    def set_error_state(self, current_sb: int, alloc: list[int]) -> None:
        next_sb = current_sb + 1
        if next_sb < self.num_subbands:
            for i in range(next_sb, self.num_subbands):
                alloc[i] = 7
        alloc[current_sb] = 7

    def decode_subframes(self, bs: BitstreamReader, scale_factors: list[int], alloc: list[int]) -> list[int]:
        output = [0] * FRAME_SIZE
        error = False
        for sb in range(self.num_subbands):
            step = alloc[sb]
            scale = scale_factors[sb]
            out_base = sb * SAMPLES_PER_SUBBAND
            for k in range(SAMPLES_PER_SUBBAND):
                output[out_base + k] = 0

            if sub(step, 7) < 0 and not error:
                tree = codebook_tree(step)
                num_subframes = QUANT_NUM_COEFF[step]
                num_levels = QUANT_LEVELS_M1[step]
                out_pos = out_base
                sf = 0
                while sf < num_subframes:
                    if bs.total_bits_remaining < 1:
                        error = True
                        self.set_error_state(sb, alloc)
                        break

                    node = 0
                    while True:
                        if bs.total_bits_remaining < 1:
                            error = True
                            self.set_error_state(sb, alloc)
                            for k in range(SAMPLES_PER_SUBBAND):
                                output[out_base + k] = 0
                            break
                        bs.read_bit()
                        child = tree[node * 2] if bs.last_bit == 0 else tree[node * 2 + 1]
                        node = child
                        bs.total_bits_remaining = sub(bs.total_bits_remaining, 1)
                        if child <= 0:
                            break
                    if error:
                        break

                    symbol = negate(node)
                    digits = [0] * 6
                    num_nonzero = inverse_quantize(symbol, digits, step)
                    if sub(bs.total_bits_remaining, num_nonzero) < 0:
                        error = True
                        self.set_error_state(sb, alloc)
                        for k in range(SAMPLES_PER_SUBBAND):
                            output[out_base + k] = 0
                        break

                    sign_bits = 0
                    sign_mask = 0
                    if num_nonzero != 0:
                        for _ in range(num_nonzero):
                            bs.read_bit()
                            sign_bits = add(shl(sign_bits, 1), bs.last_bit)
                            bs.total_bits_remaining = sub(bs.total_bits_remaining, 1)
                        sign_mask = shl(1, sub(num_nonzero, 1))

                    if num_levels > 0:
                        for j in range(num_levels):
                            recon = QUANT_RECON_LEVELS[step][digits[j]]
                            sample = extract_l(l_shr(l_mult0(scale, recon), 12))
                            if sample != 0:
                                if (sign_mask & sign_bits) == 0:
                                    sample = negate(sample)
                                sign_mask = shr(sign_mask, 1)
                            output[out_pos] = sample
                            out_pos += 1

                    sf += 1
            elif error:
                alloc[sb] = 7

            current_step = alloc[sb]
            if current_step in (5, 6):
                noise_level = mult(scale, NOISE_GAINS[current_step - 5])
                neg_noise = negate(noise_level)
                prng_val = noise_prng(self.prng_state)
                for k in range(10):
                    pos = out_base + k
                    if output[pos] == 0:
                        output[pos] = noise_level if (prng_val & 1) != 0 else neg_noise
                        prng_val = shr(prng_val, 1)
                prng_val = noise_prng(self.prng_state)
                for k in range(10, 20):
                    pos = out_base + k
                    if output[pos] == 0:
                        output[pos] = noise_level if (prng_val & 1) != 0 else neg_noise
                        prng_val = shr(prng_val, 1)

            if current_step == 7:
                noise_level = mult(scale, NOISE_GAINS[2])
                neg_noise = negate(noise_level)
                prng_val = noise_prng(self.prng_state)
                for k in range(10):
                    output[out_base + k] = noise_level if (prng_val & 1) != 0 else neg_noise
                    prng_val = shr(prng_val, 1)
                prng_val = noise_prng(self.prng_state)
                for k in range(10, 20):
                    output[out_base + k] = noise_level if (prng_val & 1) != 0 else neg_noise
                    prng_val = shr(prng_val, 1)

        if error:
            bs.total_bits_remaining = sub(bs.total_bits_remaining, 1)
        return output

    def decode_frame_words(self, frame_words: list[int]) -> list[int]:
        bs = BitstreamReader(frame_words, self.bits_per_frame)
        gains, scale_factors, scale_param = self.decode_gains(bs)
        frame_param = bs.read_bits(4)
        bs.total_bits_remaining = sub(bs.total_bits_remaining, 4)
        alloc, scratch = compute_bit_alloc_for_frame(bs.total_bits_remaining, self.num_subbands, gains[: self.num_subbands])
        increment_allocation_bins(frame_param, alloc, scratch)
        subband = self.decode_subframes(bs, scale_factors, alloc)
        for s in range(self.num_subbands * SAMPLES_PER_SUBBAND, FRAME_SIZE):
            subband[s] = 0
        return synthesize(subband, self.synth_memory, FRAME_SIZE, scale_param)


def decode_a18_bytes(data: bytes) -> tuple[int, list[int]]:
    if len(data) < 6:
        raise ValueError("file too small")
    data_length = struct.unpack_from("<I", data, 0)[0]
    bitrate = struct.unpack_from("<H", data, 4)[0]
    payload = data[6 : 6 + data_length]
    state = DecoderState.new(bitrate)
    frame_bytes = state.encoded_frame_size * 2
    if len(payload) % frame_bytes != 0:
        payload = payload[: len(payload) - (len(payload) % frame_bytes)]
    samples: list[int] = []
    for offset in range(0, len(payload), frame_bytes):
        chunk = payload[offset : offset + frame_bytes]
        words = list(struct.unpack("<" + "h" * state.encoded_frame_size, chunk))
        samples.extend(state.decode_frame_words(words))
    return bitrate, samples


def write_wav(path: str | Path, samples: list[int], sample_rate: int = 16000) -> None:
    out = Path(path)
    with wave.open(str(out), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack("<" + "h" * len(samples), *samples))


def decode_file(input_path: str | Path, output_path: str | Path, sample_rate: int = 16000) -> None:
    bitrate, samples = decode_a18_bytes(Path(input_path).read_bytes())
    write_wav(output_path, samples, sample_rate=sample_rate)
