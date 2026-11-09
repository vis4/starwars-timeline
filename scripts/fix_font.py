"""Repair StarJedi-DGRW.ttf for browsers.

The 1998 font's `post` table declares glyph names for 98 glyphs, which doesn't match the
font's glyph count, so Chrome's font sanitizer (OTS) rejects the whole file. Browsers
don't need glyph names, so we replace `post` with a version 3.0 table (header only, no
names) and recompute checksums. Everything else is copied byte for byte.

Usage: python3 -I scripts/fix_font.py fonts/StarJedi-DGRW.ttf fonts/StarJedi-web.ttf
"""

import struct
import sys


def checksum(data):
    data += b"\0" * (-len(data) % 4)
    return sum(struct.unpack(f">{len(data) // 4}I", data)) & 0xFFFFFFFF


def main(src, dst):
    d = open(src, "rb").read()
    sfnt, num = struct.unpack(">IH", d[:6])
    tables = {}
    for i in range(num):
        tag, _cs, off, length = struct.unpack(">4sIII", d[12 + 16 * i:28 + 16 * i])
        tables[tag] = bytearray(d[off:off + length])

    post = tables[b"post"]
    tables[b"post"] = bytearray(struct.pack(">I", 0x00030000) + post[4:32])  # v3.0: header only

    head = tables[b"head"]
    head[8:12] = b"\0\0\0\0"  # checkSumAdjustment, recomputed below

    tags = sorted(tables)
    n = len(tags)
    pow2 = 1 << (n.bit_length() - 1)
    header = struct.pack(">IHHHH", sfnt, n, pow2 * 16, pow2.bit_length() - 1, n * 16 - pow2 * 16)
    offset = 12 + 16 * n
    directory, body = b"", b""
    for tag in tags:
        data = bytes(tables[tag])
        directory += struct.pack(">4sIII", tag, checksum(data), offset, len(data))
        padded = data + b"\0" * (-len(data) % 4)
        body += padded
        offset += len(padded)
    font = bytearray(header + directory + body)

    adj = (0xB1B0AFBA - checksum(bytes(font))) & 0xFFFFFFFF
    head_off = 12 + 16 * n + sum(len(tables[t]) + (-len(tables[t]) % 4) for t in tags[:tags.index(b"head")])
    font[head_off + 8:head_off + 12] = struct.pack(">I", adj)
    open(dst, "wb").write(font)
    print(f"wrote {dst} ({len(font)} bytes)")


if __name__ == "__main__":
    main(*sys.argv[1:3])
