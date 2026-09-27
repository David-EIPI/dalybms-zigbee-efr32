#!/usr/bin/env python3
"""Tests for binary and S-record firmware configuration editing."""

import importlib.util
import pathlib
import struct
import tempfile
import unittest
import zlib
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "configure_image", ROOT / "tools" / "configure_image.py")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def default_block():
    entries = (
        ("serial_tx_location", 1, 0, 31),
        ("serial_rx_location", 31, 0, 31),
        ("bms_address", 1, 1, 15),
        ("zigbee_primary_mask", 0x0318C800, 0, 0x07FFF800),
        ("zigbee_secondary_mask", 0x04E73000, 0, 0x07FFF800),
        ("sample_interval_s", 30, 5, 3600),
        ("zigbee_long_poll_ms", 3000, 1000, 60000),
        ("network_loss_timeout_h", 24, 1, 720),
        ("serial_timeout_ms", 1000, 100, 5000),
    )
    block = bytearray(TOOL.HEADER.pack(
        TOOL.MARKER, 2, TOOL.HEADER.size + len(entries) * TOOL.ENTRY.size,
        len(entries), 0))
    for entry in entries:
        block.extend(TOOL.ENTRY.pack(entry[0].encode(), *entry[1:]))
    struct.pack_into("<I", block, TOOL.CRC_OFFSET, zlib.crc32(block))
    return bytes(block)


def s3(address, data):
    body = bytes([4 + len(data) + 1]) + address.to_bytes(4, "big") + data
    return "S3" + (body + bytes([(~sum(body)) & 0xff])).hex().upper()


class ConfigureImageTests(unittest.TestCase):
    def test_binary_patch_updates_value_and_crc(self):
        image = TOOL.BinaryImage(b"prefix" + default_block() + b"suffix")
        location, block = image.find_config()
        block.set("serial_tx_location", 19)
        block.set("serial_rx_location", 19)
        block.set("sample_interval_s", 45)
        image.replace(location, block.encode())
        _location, result = TOOL.BinaryImage(image.encode()).find_config()
        self.assertEqual(result.values()["serial_tx_location"], 19)
        self.assertEqual(result.values()["serial_rx_location"], 19)
        self.assertEqual(result.values()["sample_interval_s"], 45)

    def test_srecord_patch_preserves_valid_records(self):
        contents = b"before" + default_block() + b"after"
        lines = [s3(0x1000 + offset, contents[offset:offset + 24])
                 for offset in range(0, len(contents), 24)]
        image = TOOL.SRecordImage("\n".join(lines) + "\n")
        location, block = image.find_config()
        block.set("bms_address", 7)
        image.replace(location, block.encode())
        encoded = image.encode().decode()
        reparsed = TOOL.SRecordImage(encoded)
        _location, result = reparsed.find_config()
        self.assertEqual(result.values()["bms_address"], 7)

    def test_rejects_bad_ranges_and_masks(self):
        block = TOOL.ConfigBlock(default_block())
        with self.assertRaises(TOOL.ConfigError):
            block.set("bms_address", 16)
        with self.assertRaises(TOOL.ConfigError):
            block.set("zigbee_primary_mask", 1)
        self.assertEqual(block.values()["zigbee_primary_mask"], 0x0318C800)
        with self.assertRaises(TOOL.ConfigError):
            block.set("serial_rx_location", 0)
        self.assertEqual(block.values()["serial_rx_location"], 31)

    def test_patch_image_writes_separate_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "input.bin"
            output = pathlib.Path(directory) / "output.bin"
            source.write_bytes(default_block())
            TOOL.patch_image(source, output, ["network_loss_timeout_h=48"])
            self.assertNotEqual(source.read_bytes(), output.read_bytes())
            _offset, result = TOOL.load_image(output).find_config()
            self.assertEqual(result.values()["network_loss_timeout_h"], 48)

    def test_srecord_segments_are_prepared_for_flashing(self):
        contents = b"prefix" + default_block() + b"suffix"
        lines = [s3(0x2000 + offset, contents[offset:offset + 19])
                 for offset in range(0, len(contents), 19)]
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "firmware.s37"
            path.write_text("\n".join(lines) + "\n")
            segments = TOOL.prepare_flash_segments(path)
            self.assertEqual(segments, [(0x2000, contents)])

    def test_flashing_uses_only_stlink_and_sector_erase(self):
        calls = {}

        class FakeSession:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

        class FakeConnectHelper:
            @staticmethod
            def get_all_connected_probes(**kwargs):
                calls["discovery"] = kwargs
                return [type("Probe", (), {"unique_id": "STLINK1234"})()]

            @staticmethod
            def session_with_chosen_probe(**kwargs):
                calls["connect"] = kwargs
                return FakeSession()

        class FakeLoader:
            def __init__(self, session, **kwargs):
                calls["loader"] = (session, kwargs)

            def add_data(self, address, data):
                calls["data"] = (address, data)

            def commit(self):
                calls["commit"] = True

        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "firmware.bin"
            path.write_bytes(default_block())
            with mock.patch.object(
                    TOOL, "_load_pyocd",
                    return_value=(FakeConnectHelper, FakeLoader)):
                TOOL.flash_image(path, probe_uid="1234", frequency=2000000,
                                 connect_mode="under-reset")
        self.assertEqual(calls["discovery"]["unique_id"], "stlink:1234")
        self.assertEqual(calls["connect"]["unique_id"], "stlink:STLINK1234")
        self.assertEqual(calls["connect"]["options"]["frequency"], 2000000)
        self.assertEqual(calls["connect"]["options"]["connect_mode"],
                         "under-reset")
        self.assertEqual(calls["loader"][1]["chip_erase"], "sector")
        self.assertEqual(calls["data"], (0, default_block()))
        self.assertTrue(calls["commit"])


if __name__ == "__main__":
    unittest.main()
