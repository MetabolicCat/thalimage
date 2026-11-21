"""The perceptual hash: a 64-bit fingerprint of what a picture looks like.

A DCT hash (pHash): the picture in greyscale at 32x32, transformed, keeps
one bit per low frequency, set when that frequency is above their median:
half the bits are set (fewer only where frequencies tie at the median),
so two hashes nearly always differ by an even count of bits.
A picture that is not square is centred on a white square first, rather
than stretched: measured on a library, that held edits as close with a
quarter of the unrelated pictures coming as near (#158). The picture is
shrunk to a bounded long edge before it is padded, so the square never
follows the picture's own long edge.
Resizing, re-encoding and colour changes move few bits; cropping moves
more the more is cut. Unlike the picture hash, it decodes the picture:
decoders disagreeing on a few pixels shift it by a bit at most.
"""

import math
import statistics
from pathlib import Path

from PIL import Image

# Raised when the hash changes, so the next scan computes it again.
# 4: shrink before padding, so a tall or wide picture no longer needs a
#    square whose side is its long edge.
PERCEPTUAL_HASH_VERSION = 4

_SIZE = 32  # the side of the greyscale picture transformed
_LONG_EDGE = 1024  # the picture is shrunk to this before it is padded
# Modes whose resize gives the same pixels as converting to RGBA first.
_RESIZE_BEFORE_ALPHA = {"RGB", "RGBA", "L", "LA"}
_KEPT = 8  # the lowest frequencies kept, per axis: 64 bits
BITS = _KEPT * _KEPT  # the length of a hash

_COSINES = [
    [math.cos(math.pi * (2 * x + 1) * u / (2 * _SIZE)) for x in range(_SIZE)]
    for u in range(_KEPT)
]


def perceptual_hash(path: Path) -> int:
    """The picture's perceptual hash, as a signed 64-bit integer (what
    SQLite stores). Transparent areas and the padding count as white."""
    with Image.open(path) as img:
        # Shrink first: padding at the picture's own long edge would allocate
        # that edge's square (an 800x12000 picture asked for 12000²).
        if img.mode in _RESIZE_BEFORE_ALPHA:
            # In the mode the file already has: converting a tall picture to
            # RGBA makes a full-size copy before the shrink can happen.
            img.thumbnail((_LONG_EDGE, _LONG_EDGE), Image.Resampling.LANCZOS)
            rgba = img.convert("RGBA")
        else:
            # Palettes would resize as raw channel values, so convert first;
            # the shrink still bounds the square.
            rgba = img.convert("RGBA")
            rgba.thumbnail((_LONG_EDGE, _LONG_EDGE), Image.Resampling.LANCZOS)
    side = max(rgba.size)
    flat = Image.new("RGBA", (side, side), "white")
    flat.alpha_composite(rgba, ((side - rgba.width) // 2, (side - rgba.height) // 2))
    grey = flat.convert("L").resize((_SIZE, _SIZE), Image.Resampling.LANCZOS)
    pixels = grey.tobytes()
    rows = [pixels[y * _SIZE : (y + 1) * _SIZE] for y in range(_SIZE)]
    # The 2D DCT, separably: along the rows, then down the columns.
    across = [[sum(c * p for c, p in zip(cos, row, strict=True)) for cos in _COSINES] for row in rows]
    freqs = [
        sum(c * across[y][u] for y, c in enumerate(cos)) for cos in _COSINES for u in range(_KEPT)
    ]
    median = statistics.median(freqs)
    bits = sum(1 << i for i, f in enumerate(freqs) if f > median)
    return bits - (1 << BITS) if bits >= 1 << (BITS - 1) else bits


def distance(a: int, b: int) -> float:
    """How far apart two perceptual hashes are: the share of their bits that
    differ, from 0 (the same) to 1."""
    return ((a ^ b) & ((1 << BITS) - 1)).bit_count() / BITS
