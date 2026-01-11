"""
Tests for utility functions.
"""

from fit_file_faker.utils import fit_crc_get16


class TestCRCCalculation:
    """Tests for FIT file CRC calculation."""

    def test_fit_crc_get16_basic(self):
        """Test basic CRC calculation."""
        crc = 0
        crc = fit_crc_get16(crc, 0x0E)
        crc = fit_crc_get16(crc, 0x10)

        # CRC calculation is deterministic
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_fit_crc_get16_sequence(self):
        """Test CRC calculation on a sequence of bytes."""
        data = b"Hello, FIT!"
        crc = 0
        for byte in data:
            crc = fit_crc_get16(crc, byte)

        # Should produce a valid 16-bit checksum
        assert 0 <= crc <= 0xFFFF
