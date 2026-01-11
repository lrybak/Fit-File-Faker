"""
Utility functions for Fit File Faker.
"""

import logging

from fit_tool.base_type import BaseType
from fit_tool.field import Field

_logger = logging.getLogger("garmin")
_original_get_length_from_size = Field.get_length_from_size


def _lenient_get_length_from_size(base_type, size):
    """
    Lenient version that truncates instead of raising exception.

    Some manufacturers (e.g., COROS) create FIT files with fields where
    the size is not a multiple of the base type size. Instead of failing,
    we truncate to the nearest valid length.
    """
    if base_type == BaseType.STRING or base_type == BaseType.BYTE:
        return 0 if size == 0 else 1
    else:
        length = size // base_type.size

        if length * base_type.size != size:
            _logger.debug(
                f"Field size ({size}) not multiple of type size ({base_type.size}), "
                f"truncating to length {length}"
            )
            return length

        return length


def apply_fit_tool_patch():
    """
    Apply monkey patch to fit_tool to handle malformed FIT files.

    Some manufacturers (e.g., COROS) create FIT files with fields where
    the size is not a multiple of the base type size. This patch makes
    fit_tool more lenient by truncating to the nearest valid length
    instead of raising an exception.
    """
    Field.get_length_from_size = staticmethod(_lenient_get_length_from_size)


def fit_crc_get16(crc: int, byte: int) -> int:
    """
    Calculate FIT file CRC-16 checksum.

    Arguments
    ---------
        crc: Current CRC value (16-bit unsigned)
        byte: Byte to add to checksum (8-bit unsigned)

    Returns
    -------
        Updated CRC value (16-bit unsigned)

    Examples
    --------

        # Calculate CRC for a byte array
        def calculate_fit_crc(data: bytes) -> int:
            '''Calculate CRC-16 for FIT file data.'''
            crc = 0
            for byte in data:
                crc = fit_crc_get16(crc, byte)
            return crc

    """
    crc_table = [
        0x0000,
        0xCC01,
        0xD801,
        0x1400,
        0xF001,
        0x3C00,
        0x2800,
        0xE401,
        0xA001,
        0x6C00,
        0x7800,
        0xB401,
        0x5000,
        0x9C01,
        0x8801,
        0x4400,
    ]

    # Compute checksum of lower four bits of byte
    tmp = crc_table[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ crc_table[byte & 0xF]

    # Now compute checksum of upper four bits of byte
    tmp = crc_table[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0xF]

    return crc
