"""Near-duplicate screenshots: pHash within a few bits is the same image recompressed."""

MAX_DISTANCE = 4
# 64 bits in 5 parts: with at most 4 differing bits, at least one part is identical (pigeonhole).
_SEGMENT_BITS = (13, 13, 13, 13, 12)


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def segments(phash: str) -> list[str]:
    value, parts, shift = int(phash, 16), [], 0
    for index, bits in enumerate(_SEGMENT_BITS):
        parts.append(f"{index}:{(value >> shift) & ((1 << bits) - 1):x}")
        shift += bits
    return parts


def nearest(phash: str, candidates: set[str]) -> str | None:
    within = [c for c in candidates if hamming(phash, c) <= MAX_DISTANCE]
    return min(within, key=lambda c: hamming(phash, c), default=None)
