from __future__ import annotations

import struct
from functools import cache
from typing import Callable, Type, TypeVar, Union

from . import types, ids

T = TypeVar("T")
__all__ = ("BinaryWriter", "write_simple")

# Header length for osu! packets (packet ID + unused byte + packet length)
HEADER_LEN = 7

# Null header template
NULL_HEADER = bytearray(b"\x00" * HEADER_LEN)


def uleb128_encode(num: int) -> bytearray:
    """Encode an int to uleb128."""
    if num == 0:
        return bytearray(b"\x00")

    arr = bytearray()
    length = 0

    while num > 0:
        arr.append(num & 127)
        num >>= 7
        if num != 0:
            arr[length] |= 128
        length += 1

    return arr


class BinaryWriter:
    """A binary serializer managing the contents of a bytearray for osu! packets."""

    __slots__ = ("_buffer",)

    def __init__(self, prealloc_header: bool = True) -> None:
        # Pre-allocate the header
        self._buffer = NULL_HEADER.copy() if prealloc_header else bytearray()

    # Primitive type writers using struct module
    def write_u8(self, num: int) -> BinaryWriter:
        """Writes an 8-bit unsigned integer into the buffer."""
        self._buffer.append(num)
        return self

    def write_i8(self, num: int) -> BinaryWriter:
        """Writes a signed 8-bit integer to the buffer."""
        self._buffer += struct.pack("<b", num)
        return self

    def write_u16(self, num: int) -> BinaryWriter:
        """Writes a 16-bit unsigned integer into the buffer."""
        self._buffer += struct.pack("<H", num)
        return self

    def write_i16(self, num: int) -> BinaryWriter:
        """Writes a signed 16-bit integer to the buffer."""
        self._buffer += struct.pack("<h", num)
        return self

    def write_u32(self, num: int) -> BinaryWriter:
        """Writes a 32-bit unsigned integer into the buffer."""
        self._buffer += struct.pack("<L", num)
        return self

    def write_i32(self, num: int) -> BinaryWriter:
        """Writes a signed 32-bit integer to the buffer."""
        self._buffer += struct.pack("<l", num)
        return self

    def write_u64(self, num: int) -> BinaryWriter:
        """Writes a 64-bit unsigned integer into the buffer."""
        self._buffer += struct.pack("<Q", num)
        return self

    def write_i64(self, num: int) -> BinaryWriter:
        """Writes a signed 64-bit integer to the buffer."""
        self._buffer += struct.pack("<q", num)
        return self

    def write_f32(self, num: float) -> BinaryWriter:
        """Writes a 32-bit floating point number into the buffer."""
        self._buffer += struct.pack("<f", num)
        return self

    # Osu!-specific type writers
    def write_uleb128(self, num: int) -> BinaryWriter:
        """Writes an unsigned LEB128 variable length integer into the buffer."""
        if num == 0:
            return self.write_u8(0)

        while num != 0:
            self.write_u8(num & 127)
            num >>= 7
            if num != 0:
                self._buffer[-1] |= 128

        return self

    def write_str(self, string: str) -> BinaryWriter:
        """Writes an osu-styled binary string into the buffer."""
        if string:
            self.write_u8(11).write_uleb128(len(string)).write_raw(string.encode())
        else:
            self.write_u8(0)
        return self

    def write_int_list(self, int_list: list[int]) -> BinaryWriter:
        """Writes a u16 prefixed list of i32s into the buffer."""
        self.write_u16(len(int_list))
        for elem in int_list:
            self.write_i32(elem)
        return self

    def write_raw(self, contents: Union[bytes, bytearray]) -> BinaryWriter:
        """Appends raw binary bytes onto the buffer."""
        self._buffer += contents
        return self

    def finish(self, packet_id: int) -> bytearray:
        """Completes packet serialization by writing the packet header to the front."""
        self._buffer[0:7] = struct.pack(
            "<HxI",
            packet_id,
            len(self._buffer) - HEADER_LEN,
        )
        return self._buffer


# Type mapping for data types to writer methods
_READERS = {
    types.BYTE: BinaryWriter.write_u8,
    types.UINT16: BinaryWriter.write_u16,
    types.SINT16: BinaryWriter.write_i16,
    types.UINT32: BinaryWriter.write_u32,
    types.SINT32: BinaryWriter.write_i32,
    types.UINT64: BinaryWriter.write_u64,
    types.SINT64: BinaryWriter.write_i64,
    types.STRING: BinaryWriter.write_str,
    types.FFLOAT: BinaryWriter.write_f32,
    types.INT_LIST: lambda self, data: self.write_int_list(data),
    types.BBYTES: lambda self, data: self.write_raw(data),
}


@cache
def _writer_from_type(data_type: int) -> Callable[[BinaryWriter, any], BinaryWriter]:
    """Fetches the binary writer function corresponding to the data type."""
    assert data_type in _READERS
    return _READERS[data_type]


def write_simple(packet_id: int) -> bytearray:
    """Writes a simple, 0 length packet containing only the header."""
    return BinaryWriter().finish(packet_id)


def build_packet_data(packet_data: list[tuple[any, int]]) -> BinaryWriter:
    """Builds packet data using the builder pattern."""
    writer = BinaryWriter()
    for data, data_type in packet_data:
        _writer_from_type(data_type)(writer, data)
    return writer
