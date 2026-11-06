"""A small QR code encoder: text in, a grid of dark and light modules out.

Pixel art already is a grid, so a QR code on a slide is just another sprite.
This covers what slides need: byte mode (any UTF-8 text, so any URL), error
correction level M (survives about 15% damage, plenty for a projector), and
versions 1 to 10 (up to 213 bytes). No dependency, so it also runs on the
phone inside Pyodide.

The steps follow the QR standard (ISO/IEC 18004):
  1. data bits: mode, length, bytes, terminator, padding
  2. split into blocks and add Reed-Solomon error correction to each
  3. interleave the blocks
  4. draw the fixed patterns (finders, timing, alignment, version info)
  5. lay the bits in the zigzag, try all 8 masks, keep the least ugly one
  6. write the format bits (level + mask)
"""
from __future__ import annotations

from functools import lru_cache

MAX_BYTES = 213  # version 10, level M

# Level M, versions 1-10: (error correction codewords per block,
# [(number of blocks, data codewords per block), ...]).
BLOCKS_M: dict[int, tuple[int, list[tuple[int, int]]]] = {
    1: (10, [(1, 16)]),
    2: (16, [(1, 28)]),
    3: (26, [(1, 44)]),
    4: (18, [(2, 32)]),
    5: (24, [(2, 43)]),
    6: (16, [(4, 27)]),
    7: (18, [(4, 31)]),
    8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]),
    10: (26, [(4, 43), (1, 44)]),
}
ALIGNMENT = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
             7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
LEVEL_M_BITS = 0b00


class QrTooLong(ValueError):
    pass


# --- Reed-Solomon over GF(256) -------------------------------------------------

EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def gf_mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


@lru_cache(maxsize=None)
def generator(degree: int) -> tuple[int, ...]:
    """(x - a^0)(x - a^1)...(x - a^(degree-1)), highest power first."""
    poly = [1]
    for i in range(degree):
        poly = [a ^ gf_mul(b, EXP[i]) for a, b in zip(poly + [0], [0] + poly)]
    return tuple(poly)


def ec_codewords(data: list[int], degree: int) -> list[int]:
    """The remainder of data * x^degree divided by the generator."""
    gen = generator(degree)
    remainder = list(data) + [0] * degree
    for i in range(len(data)):
        factor = remainder[i]
        if factor:
            for j in range(1, len(gen)):
                remainder[i + j] ^= gf_mul(gen[j], factor)
    return remainder[len(data):]


# --- Data -----------------------------------------------------------------------


def data_capacity(version: int) -> int:
    return sum(count * size for count, size in BLOCKS_M[version][1])


def byte_capacity(version: int) -> int:
    length_bits = 8 if version < 10 else 16
    return (data_capacity(version) * 8 - 4 - length_bits) // 8


def pick_version(length: int) -> int:
    for version in BLOCKS_M:
        if length <= byte_capacity(version):
            return version
    raise QrTooLong(f"{length} bytes is too long for a QR code here (at most {MAX_BYTES})")


def codewords(payload: bytes, version: int) -> list[int]:
    bits: list[int] = []

    def put(value: int, width: int) -> None:
        bits.extend((value >> (width - 1 - i)) & 1 for i in range(width))

    put(0b0100, 4)  # byte mode
    put(len(payload), 8 if version < 10 else 16)
    for byte in payload:
        put(byte, 8)
    capacity = data_capacity(version) * 8
    put(0, min(4, capacity - len(bits)))  # terminator
    bits.extend([0] * (-len(bits) % 8))
    data = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = [0xEC, 0x11]
    while len(data) < data_capacity(version):
        data.append(pad[(len(data) - len(bits) // 8) % 2])

    ec_per_block, groups = BLOCKS_M[version]
    blocks: list[list[int]] = []
    at = 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(data[at:at + size])
            at += size
    ec_blocks = [ec_codewords(block, ec_per_block) for block in blocks]

    out: list[int] = []
    for i in range(max(len(b) for b in blocks)):
        out.extend(block[i] for block in blocks if i < len(block))
    for i in range(ec_per_block):
        out.extend(block[i] for block in ec_blocks)
    return out


# --- The grid -------------------------------------------------------------------


def bch(value: int, poly: int, width: int) -> int:
    """value followed by its BCH remainder (format and version information)."""
    shifted = value << width
    top = poly.bit_length() - 1
    while shifted.bit_length() > top:
        shifted ^= poly << (shifted.bit_length() - poly.bit_length())
    return (value << width) | shifted


def format_bits(mask: int) -> int:
    return bch((LEVEL_M_BITS << 3) | mask, 0b10100110111, 10) ^ 0b101010000010010


def version_bits(version: int) -> int:
    return bch(version, 0b1111100100101, 12)


class Grid:
    def __init__(self, version: int):
        self.version = version
        self.size = 17 + 4 * version
        self.dark = [[False] * self.size for _ in range(self.size)]
        self.fixed = [[False] * self.size for _ in range(self.size)]

    def set(self, row: int, col: int, dark: bool) -> None:
        self.dark[row][col] = dark
        self.fixed[row][col] = True

    def draw_function_patterns(self) -> None:
        n = self.size
        for row, col in ((0, 0), (0, n - 7), (n - 7, 0)):
            self.finder(row, col)
        for i in range(8, n - 8):
            self.set(6, i, i % 2 == 0)
            self.set(i, 6, i % 2 == 0)
        centres = ALIGNMENT[self.version]
        last = len(centres) - 1
        for i, r in enumerate(centres):
            for j, c in enumerate(centres):
                if (i, j) not in ((0, 0), (0, last), (last, 0)):  # those three would sit on finders
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            self.set(r + dr, c + dc, max(abs(dr), abs(dc)) != 1)
        # Reserve the format areas now (filled in at the end) and the dark module.
        self.write_format(0)
        self.set(n - 8, 8, True)
        if self.version >= 7:
            bits = version_bits(self.version)
            for i in range(18):
                bit = bool((bits >> i) & 1)
                a, b = i // 3, n - 11 + i % 3
                self.set(a, b, bit)
                self.set(b, a, bit)

    def finder(self, top: int, left: int) -> None:
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = top + dr, left + dc
                if 0 <= r < self.size and 0 <= c < self.size:
                    ring = max(abs(dr - 3), abs(dc - 3))
                    self.set(r, c, ring != 2 and ring != 4)

    def write_format(self, mask: int) -> None:
        n = self.size
        bits = format_bits(mask)
        bit = [bool((bits >> i) & 1) for i in range(15)]
        # Around the top-left finder.
        for i in range(6):
            self.set(i, 8, bit[i])
        self.set(7, 8, bit[6])
        self.set(8, 8, bit[7])
        self.set(8, 7, bit[8])
        for i in range(9, 15):
            self.set(8, 14 - i, bit[i])
        # Split between the other two finders.
        for i in range(8):
            self.set(8, n - 1 - i, bit[i])
        for i in range(8, 15):
            self.set(n - 15 + i, 8, bit[i])

    def place_data(self, data: list[int]) -> None:
        bits = [(byte >> (7 - i)) & 1 for byte in data for i in range(8)]
        n = self.size
        at = 0
        col = n - 1
        upward = True
        while col > 0:
            if col == 6:  # the vertical timing line is skipped entirely
                col -= 1
            rows = range(n - 1, -1, -1) if upward else range(n)
            for row in rows:
                for c in (col, col - 1):
                    if not self.fixed[row][c]:
                        # Leftover modules (remainder bits) stay light.
                        self.dark[row][c] = bool(bits[at]) if at < len(bits) else False
                        at += 1
            upward = not upward
            col -= 2


MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def apply_mask(grid: Grid, mask: int) -> list[list[bool]]:
    test = MASKS[mask]
    return [[grid.dark[r][c] ^ (not grid.fixed[r][c] and test(r, c)) for c in range(grid.size)]
            for r in range(grid.size)]


def penalty(m: list[list[bool]]) -> int:
    """The standard's four ugliness scores; the mask with the lowest wins."""
    n = len(m)
    score = 0
    lines = m + [list(col) for col in zip(*m)]
    for line in lines:  # runs of 5 or more of one colour
        run, prev = 0, None
        for cell in line:
            if cell == prev:
                run += 1
            else:
                if run >= 5:
                    score += run - 2
                run, prev = 1, cell
        if run >= 5:
            score += run - 2
    for r in range(n - 1):  # 2x2 blocks of one colour
        for c in range(n - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                score += 3
    pattern_a = [True, False, True, True, True, False, True, False, False, False, False]
    pattern_b = pattern_a[::-1]
    for line in lines:  # things that look like finder patterns
        for i in range(n - 10):
            window = line[i:i + 11]
            if window == pattern_a or window == pattern_b:
                score += 40
    dark = sum(map(sum, m))
    score += abs(dark * 20 - n * n * 10) // (n * n) * 10  # far from half dark
    return score


def encode(text: str, mask: int | None = None) -> list[list[bool]]:
    """The QR code for `text` as rows of booleans (True = dark), no quiet zone."""
    payload = text.encode("utf-8")
    version = pick_version(len(payload))
    grid = Grid(version)
    grid.draw_function_patterns()
    grid.place_data(codewords(payload, version))

    def finished(m: int) -> list[list[bool]]:
        grid.write_format(m)
        return apply_mask(grid, m)

    if mask is None:
        mask = min(range(8), key=lambda m: penalty(finished(m)))
    return finished(mask)
