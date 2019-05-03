#!/usr/bin/python3
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from math import log

from crash.util.symbols import Types

types = Types('unsigned long')

def check_bitmap_type(bitmap):
    if ((bitmap.type.code != gdb.TYPE_CODE_ARRAY or
         bitmap[0].type.code != types.unsigned_long_type.code or
         bitmap[0].type.sizeof != types.unsigned_long_type.sizeof) and
        (bitmap.type.code != gdb.TYPE_CODE_PTR or
         bitmap.type.target().code != types.unsigned_long_type.code or
         bitmap.type.target().sizeof != types.unsigned_long_type.sizeof)):
        raise TypeError("bitmaps are expected to be arrays of unsigned long not `{}'"
                        .format(bitmap.type))

def for_each_set_bit(bitmap, size_in_bytes=None):
    check_bitmap_type(bitmap)

    if size_in_bytes is None:
        size_in_bytes = bitmap.type.sizeof

    bits_per_ulong = types.unsigned_long_type.sizeof * 8

    size = size_in_bytes * 8
    idx = 0
    bit = 0
    while size > 0:
        ulong = bitmap[idx]

        if ulong != 0:
            for off in range(min(size, bits_per_ulong)):
                if ulong & 1 != 0:
                    yield bit
                bit += 1
                ulong >>= 1
        else:
            bit += bits_per_ulong

        size -= bits_per_ulong
        idx += 1

def _find_first_set_bit(val):
    r = 1

    if val == 0:
        return 0

    if (val & 0xffffffff) == 0:
        val >>= 32
        r += 32

    if (val & 0xffff) == 0:
        val >>= 16
        r += 16

    if (val & 0xff) == 0:
        val >>= 8
        r += 8

    if (val & 0xf) == 0:
        val >>= 4
        r += 4

    if (val & 0x3) == 0:
        val >>= 2
        r += 2

    if (val & 0x1) == 0:
        val >>= 1
        r += 1

    return r

def find_next_zero_bit(bitmap, start, size_in_bytes=None):
    check_bitmap_type(bitmap)

    if size_in_bytes is None:
        size_in_bytes = bitmap.type.sizeof

    elements = size_in_bytes // types.unsigned_long_type.sizeof

    if start > size_in_bytes << 3:
        raise IndexError("Element {} is out of range ({} elements)"
                                                .format(start, elements))

    element = start // (types.unsigned_long_type.sizeof << 3)
    offset = start % (types.unsigned_long_type.sizeof << 3)

    for n in range(element, elements):
        item = ~bitmap[n]
        if item == 0:
            continue

        if offset > 0:
            item &= ~((1 << offset) - 1)

        v = _find_first_set_bit(item)
        if v > 0:
            ret = n * (types.unsigned_long_type.sizeof << 3) + v
            assert(ret >= start)
            return ret

        offset = 0

    return 0

def find_first_zero_bit(bitmap, size_in_bytes=None):
    return find_next_zero_bit(bitmap, 0, size_in_bytes)

def find_next_set_bit(bitmap, start, size_in_bytes=None):
    check_bitmap_type(bitmap)

    if size_in_bytes is None:
        size_in_bytes = bitmap.type.sizeof

    elements = size_in_bytes // types.unsigned_long_type.sizeof

    if start > size_in_bytes << 3:
        raise IndexError("Element {} is out of range ({} elements)"
                                                .format(start, elements))

    element = start // (types.unsigned_long_type.sizeof << 3)
    offset = start % (types.unsigned_long_type.sizeof << 3)

    for n in range(element, elements):
        if bitmap[n] == 0:
            continue

        item = bitmap[n]
        if offset > 0:
            item &= ~((1 << offset) - 1)

        v = _find_first_set_bit(item)
        if v > 0:
            ret = n * (types.unsigned_long_type.sizeof << 3) + v
            assert(ret >= start)
            return ret

        offset = 0

    return 0

def find_first_set_bit(bitmap, size_in_bytes=None):
    return find_next_set_bit(bitmap, 0, size_in_bytes)

def _find_last_set_bit(val):
    r = types.unsigned_long_type.sizeof << 3

    if val == 0:
        return 0

    if (val & 0xffffffff00000000) == 0:
        val <<= 32
        r -= 32

    if (val & 0xffff000000000000) == 0:
        val <<= 16
        r -= 16

    if (val & 0xff00000000000000) == 0:
        val <<= 8
        r -= 8

    if (val & 0xf000000000000000) == 0:
        val <<= 4
        r -= 4

    if (val & 0xc000000000000000) == 0:
        val <<= 2
        r -= 2

    if (val & 0x8000000000000000) == 0:
        val <<= 1
        r -= 1

    return r

def find_last_set_bit(bitmap, size_in_bytes=None):
    check_bitmap_type(bitmap)

    if size_in_bytes is None:
        size_in_bytes = bitmap.type.sizeof

    elements = size_in_bytes // types.unsigned_long_type.sizeof

    for n in range(elements - 1, -1, -1):
        if bitmap[n] == 0:
            continue

        v = _find_last_set_bit(bitmap[n])
        if v > 0:
            return n * (types.unsigned_long_type.sizeof << 3) + v

    return 0
