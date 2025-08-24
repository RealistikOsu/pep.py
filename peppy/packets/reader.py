from __future__ import annotations

import struct

from . import types


def uleb128_decode(data: bytes) -> tuple[int, int]:
    """Decode a uleb128 to int."""
    shift = 0
    value = 0
    length = 0

    while True:
        b = data[length]
        length += 1
        value |= int(b & 127) << shift
        if b & 128 == 0:
            break
        shift += 7

    return value, length


def unpack_data(data: bytes, data_type: int) -> any:
    """Unpacks a single section of a packet."""
    if data_type == types.UINT16:
        return struct.unpack("<H", data)[0]
    elif data_type == types.SINT16:
        return struct.unpack("<h", data)[0]
    elif data_type == types.UINT32:
        return struct.unpack("<L", data)[0]
    elif data_type == types.SINT32:
        return struct.unpack("<l", data)[0]
    elif data_type == types.UINT64:
        return struct.unpack("<Q", data)[0]
    elif data_type == types.SINT64:
        return struct.unpack("<q", data)[0]
    elif data_type == types.FFLOAT:
        return struct.unpack("<f", data)[0]
    else:
        return struct.unpack("<B", data)[0]


def read_packet_id(stream: bytes) -> int:
    """Read packet ID (first two bytes) from a packet."""
    return unpack_data(stream[0:2], types.UINT16)


def read_packet_length(stream: bytes) -> int:
    """Read packet data length (3:7 bytes) from a packet."""
    return unpack_data(stream[3:7], types.UINT32)


def read_packet_data(
    stream: bytes,
    structure: list[tuple[str, int]] | None = None,
    has_first_bytes: bool = True,
) -> dict[str, any]:
    """
    Read packet data from stream according to structure.

    Args:
        stream: Packet bytes
        structure: Packet structure as list of (name, data_type) tuples
        has_first_bytes: If True, stream has packet ID and length bytes

    Returns:
        Dictionary mapping field names to unpacked values
    """
    if structure is None:
        structure = []

    data = {}

    # Skip packet ID and packet length if needed
    if has_first_bytes:
        end = 7
        start = 7
    else:
        end = 0
        start = 0

    # Read packet
    for name, data_type in structure:
        start = end
        unpack = True

        if data_type == types.INT_LIST:
            # sInt32 list - unpack manually
            unpack = False

            # Read length (uInt16)
            length = unpack_data(stream[start : start + 2], types.UINT16)

            # Read all ints inside list
            data[name] = []
            for j in range(length):
                data[name].append(
                    unpack_data(
                        stream[start + 2 + (4 * j) : start + 2 + (4 * (j + 1))],
                        types.SINT32,
                    )
                )

            # Update end
            end = start + 2 + (4 * length)
        elif data_type == types.STRING:
            # String - don't unpack
            unpack = False

            # Check empty string
            if stream[start] == 0:
                # Empty string
                data[name] = ""
                end = start + 1
            else:
                # Non-empty string
                # Read length and calculate end
                length = uleb128_decode(stream[start + 1 :])
                end = start + length[0] + length[1] + 1

                # Read bytes
                data[name] = stream[start + 1 + length[1] : end].decode()
        elif data_type == types.BYTE:
            end = start + 1
        elif data_type in (types.UINT16, types.SINT16):
            end = start + 2
        elif data_type in (types.UINT32, types.SINT32, types.FFLOAT):
            end = start + 4
        elif data_type in (types.UINT64, types.SINT64):
            end = start + 8

        # Unpack if needed
        if unpack:
            data[name] = unpack_data(stream[start:end], data_type)

    return data
