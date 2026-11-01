import unittest

from src.decode import decode_string, decode_uint256, format_units


class DecodeTests(unittest.TestCase):
    def test_uint_and_decimal_conversion(self):
        self.assertEqual(decode_uint256("0x" + "0" * 63 + "6"), 6)
        self.assertEqual(format_units(3000000000000006, 6), "3000000000.000006")
        self.assertEqual(format_units(100, 0), "100")

    def test_dynamic_string(self):
        encoded = "0x" + "0" * 62 + "20" + "0" * 63 + "4" + "55534443" + "0" * 56
        self.assertEqual(decode_string(encoded), "USDC")

    def test_malformed_responses(self):
        with self.assertRaises(ValueError):
            decode_uint256("0x")
        with self.assertRaises(ValueError):
            decode_string("0x")
        with self.assertRaises(ValueError):
            format_units(1, -1)
        with self.assertRaises(ValueError):
            format_units(-1, 0)

    def test_string_requires_valid_alignment_and_padding(self):
        valid = "0x" + "0" * 62 + "20" + "0" * 63 + "4" + "55534443" + "0" * 56
        self.assertEqual(decode_string(valid), "USDC")

        misaligned = "0x" + "0" * 63 + "21" + "0" * 63 + "4" + "55534443" + "0" * 56
        with self.assertRaises(ValueError):
            decode_string(misaligned)

        nonzero_padding = valid[:-2] + "01"
        with self.assertRaises(ValueError):
            decode_string(nonzero_padding)

        truncated = valid[:-64]
        with self.assertRaises(ValueError):
            decode_string(truncated)


if __name__ == "__main__":
    unittest.main()