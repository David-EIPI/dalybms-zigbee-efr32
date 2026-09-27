#!/usr/bin/env python3
"""Inspect or patch the CRC-protected configuration in a BMS firmware image."""

import argparse
import pathlib
import struct
import sys
import zlib

MARKER = b"BMSCFG:EFR32MG1\0"
HEADER = struct.Struct("<16sIIII")
ENTRY = struct.Struct("<24siii")
CRC_OFFSET = 28
VERSION = 2
CHANNEL_MASK = 0x07FFF800
FLASH_SIZE = 256 * 1024
PYOCD_TARGET = "efr32mg1b232f256gm48"
TX_PINS = (
    "PA0", "PA1", "PA2", "PA3", "PA4", "PA5",
    "PB11", "PB12", "PB13", "PB14", "PB15",
    "PC6", "PC7", "PC8", "PC9", "PC10", "PC11",
    "PD9", "PD10", "PD11", "PD12", "PD13", "PD14", "PD15",
    "PF0", "PF1", "PF2", "PF3", "PF4", "PF5", "PF6", "PF7",
)
RX_PINS = (
    "PA1", "PA2", "PA3", "PA4", "PA5",
    "PB11", "PB12", "PB13", "PB14", "PB15",
    "PC6", "PC7", "PC8", "PC9", "PC10", "PC11",
    "PD9", "PD10", "PD11", "PD12", "PD13", "PD14", "PD15",
    "PF0", "PF1", "PF2", "PF3", "PF4", "PF5", "PF6", "PF7", "PA0",
)
TX_OPTIONS = tuple(f"{location}: {pin}" for location, pin in enumerate(TX_PINS))
RX_OPTIONS = tuple(f"{location}: {pin}" for location, pin in enumerate(RX_PINS))
HEX_KEYS = {"zigbee_primary_mask", "zigbee_secondary_mask"}
EXPECTED_KEYS = (
    "serial_tx_location", "serial_rx_location", "bms_address",
    "zigbee_primary_mask",
    "zigbee_secondary_mask", "sample_interval_s", "zigbee_long_poll_ms",
    "network_loss_timeout_h", "serial_timeout_ms",
)


class ConfigError(ValueError):
    """Describe an invalid image or requested setting."""


class ConfigBlock:
    """Decode, validate, modify, and re-encode one configuration block."""

    def __init__(self, block):
        self.block = bytearray(block)
        marker, version, size, count, stored_crc = HEADER.unpack_from(block)
        if marker != MARKER or version != VERSION:
            raise ConfigError("unsupported configuration marker or version")
        if size != HEADER.size + count * ENTRY.size or size != len(block):
            raise ConfigError("invalid configuration size")
        check = bytearray(block)
        check[CRC_OFFSET:CRC_OFFSET + 4] = b"\0\0\0\0"
        if zlib.crc32(check) != stored_crc:
            raise ConfigError("configuration CRC-32 does not match")
        self.entries = []
        for index in range(count):
            offset = HEADER.size + index * ENTRY.size
            raw_key, value, minimum, maximum = ENTRY.unpack_from(block, offset)
            try:
                key = raw_key.split(b"\0", 1)[0].decode("ascii")
            except UnicodeDecodeError as error:
                raise ConfigError("configuration has a non-ASCII key") from error
            if not key or value < minimum or value > maximum:
                raise ConfigError(f"invalid entry {index}")
            self.entries.append([key, value, minimum, maximum])
        if len({entry[0] for entry in self.entries}) != len(self.entries):
            raise ConfigError("configuration has duplicate keys")
        if tuple(entry[0] for entry in self.entries) != EXPECTED_KEYS:
            raise ConfigError("configuration key layout does not match this tool")
        self._validate_masks()
        self._validate_serial_pins()

    def _validate_masks(self):
        values = self.values()
        primary = values.get("zigbee_primary_mask", 0)
        secondary = values.get("zigbee_secondary_mask", 0)
        if (primary | secondary) & ~CHANNEL_MASK:
            raise ConfigError("Zigbee masks may contain only channels 11 through 26")
        if primary | secondary == 0:
            raise ConfigError("at least one Zigbee channel must be enabled")

    def _validate_serial_pins(self):
        values = self.values()
        tx = values["serial_tx_location"]
        rx = values["serial_rx_location"]
        if TX_PINS[tx] == RX_PINS[rx]:
            raise ConfigError(f"USART0 TX and RX cannot both use {TX_PINS[tx]}")

    def values(self):
        """Return current values in stable table order."""
        return {key: value for key, value, _minimum, _maximum in self.entries}

    def set(self, key, value):
        """Set one named integer after checking its embedded range."""
        for entry in self.entries:
            if entry[0] == key:
                if value < entry[2] or value > entry[3]:
                    raise ConfigError(
                        f"{key} must be between {entry[2]} and {entry[3]}"
                    )
                previous = entry[1]
                entry[1] = value
                try:
                    self._validate_masks()
                    self._validate_serial_pins()
                except ConfigError:
                    entry[1] = previous
                    raise
                return
        raise ConfigError(f"unknown setting: {key}")

    def encode(self):
        """Encode entries and update the block CRC-32."""
        for index, (key, value, minimum, maximum) in enumerate(self.entries):
            offset = HEADER.size + index * ENTRY.size
            encoded = key.encode("ascii")
            if len(encoded) >= 24:
                raise ConfigError(f"setting name is too long: {key}")
            ENTRY.pack_into(self.block, offset, encoded, value, minimum, maximum)
        self.block[CRC_OFFSET:CRC_OFFSET + 4] = b"\0\0\0\0"
        struct.pack_into("<I", self.block, CRC_OFFSET, zlib.crc32(self.block))
        return bytes(self.block)


class BinaryImage:
    """Provide random access to a flat binary image."""

    def __init__(self, data):
        self.data = bytearray(data)

    def find_config(self):
        offset = _unique_marker(self.data)
        size = _block_size(self.data, offset)
        return offset, ConfigBlock(self.data[offset:offset + size])

    def replace(self, offset, block):
        self.data[offset:offset + len(block)] = block

    def encode(self):
        return bytes(self.data)


class SRecordImage:
    """Parse an S-record image while preserving its record ordering."""

    ADDRESS_LENGTH = {"0": 2, "1": 2, "2": 3, "3": 4,
                      "5": 2, "6": 3, "7": 4, "8": 3, "9": 2}

    def __init__(self, text):
        self.records = []
        self.memory = {}
        for number, original in enumerate(text.splitlines(), 1):
            line = original.strip()
            if not line:
                continue
            if len(line) < 4 or line[0] != "S" or line[1] not in self.ADDRESS_LENGTH:
                raise ConfigError(f"invalid S-record on line {number}")
            try:
                raw = bytes.fromhex(line[2:])
            except ValueError as error:
                raise ConfigError(f"invalid hex on line {number}") from error
            if len(raw) != raw[0] + 1 or sum(raw) & 0xff != 0xff:
                raise ConfigError(f"invalid count or checksum on line {number}")
            address_length = self.ADDRESS_LENGTH[line[1]]
            address = int.from_bytes(raw[1:1 + address_length], "big")
            data = raw[1 + address_length:-1]
            record = [line[1], address, data, original]
            self.records.append(record)
            if line[1] in "123":
                for offset, byte in enumerate(data):
                    location = address + offset
                    if location in self.memory:
                        raise ConfigError(f"overlapping S-record data at 0x{location:x}")
                    self.memory[location] = byte

    def find_config(self):
        matches = []
        for address, byte in self.memory.items():
            if byte == MARKER[0] and all(
                    self.memory.get(address + i) == expected
                    for i, expected in enumerate(MARKER)):
                matches.append(address)
        if len(matches) != 1:
            raise ConfigError(f"expected one configuration marker, found {len(matches)}")
        address = matches[0]
        try:
            header = bytes(self.memory[address + i] for i in range(HEADER.size))
        except KeyError as error:
            raise ConfigError("configuration header crosses an S-record gap") from error
        size = _block_size(header, 0)
        try:
            block = bytes(self.memory[address + i] for i in range(size))
        except KeyError as error:
            raise ConfigError("configuration crosses a gap in the S-record") from error
        return address, ConfigBlock(block)

    def replace(self, address, block):
        for offset, byte in enumerate(block):
            if address + offset not in self.memory:
                raise ConfigError("configuration replacement crosses an image gap")
            self.memory[address + offset] = byte

    def encode(self):
        lines = []
        for record_type, address, old_data, original in self.records:
            if record_type not in "123":
                lines.append(original)
                continue
            data = bytes(self.memory[address + i] for i in range(len(old_data)))
            address_length = self.ADDRESS_LENGTH[record_type]
            count = address_length + len(data) + 1
            body = bytes([count]) + address.to_bytes(address_length, "big") + data
            checksum = (~sum(body)) & 0xff
            lines.append("S" + record_type + (body + bytes([checksum])).hex().upper())
        return ("\n".join(lines) + "\n").encode("ascii")


def _unique_marker(data):
    first = data.find(MARKER)
    if first < 0:
        raise ConfigError("configuration marker was not found")
    if data.find(MARKER, first + 1) >= 0:
        raise ConfigError("configuration marker is not unique")
    return first


def _block_size(data, offset):
    if len(data) < offset + HEADER.size:
        raise ConfigError("truncated configuration header")
    marker, version, size, count, _crc = HEADER.unpack_from(data, offset)
    if marker != MARKER or version != VERSION or size != HEADER.size + count * ENTRY.size:
        raise ConfigError("invalid configuration header")
    return size


def load_image(path):
    """Load either Motorola S-record or flat binary input."""
    data = pathlib.Path(path).read_bytes()
    if data.lstrip().startswith(b"S"):
        try:
            return SRecordImage(data.decode("ascii"))
        except UnicodeDecodeError as error:
            raise ConfigError("S-record image is not ASCII") from error
    return BinaryImage(data)


def parse_value(text):
    """Accept decimal or conventional 0x-prefixed integers."""
    try:
        return int(text, 0)
    except ValueError as error:
        raise ConfigError(f"invalid integer: {text}") from error


def display(block):
    """Format settings for command-line inspection."""
    lines = []
    for key, value, minimum, maximum in block.entries:
        shown = f"0x{value:08x}" if key in HEX_KEYS else str(value)
        suffix = ""
        if key == "serial_tx_location":
            suffix = f" ({TX_PINS[value]})"
        elif key == "serial_rx_location":
            suffix = f" ({RX_PINS[value]})"
        lines.append(f"{key}={shown}{suffix}  [{minimum}..{maximum}]")
    return "\n".join(lines)


def patch_image(source, destination, assignments):
    """Apply assignments and write a validated image to a new path."""
    image = load_image(source)
    location, block = image.find_config()
    for assignment in assignments:
        if "=" not in assignment:
            raise ConfigError(f"expected NAME=VALUE: {assignment}")
        key, value = assignment.split("=", 1)
        block.set(key.strip(), parse_value(value.strip()))
    image.replace(location, block.encode())
    pathlib.Path(destination).write_bytes(image.encode())
    return block


def prepare_flash_segments(path):
    """Validate an application image and return its addressed flash segments."""
    image = load_image(path)
    image.find_config()
    if isinstance(image, BinaryImage):
        segments = [(0, bytes(image.data))]
    else:
        if not image.memory:
            raise ConfigError("S-record image contains no data")
        segments = []
        start = previous = None
        data = bytearray()
        for address in sorted(image.memory):
            if previous is None or address != previous + 1:
                if data:
                    segments.append((start, bytes(data)))
                start = address
                data = bytearray()
            data.append(image.memory[address])
            previous = address
        segments.append((start, bytes(data)))
    if any(not data or address < 0 or address + len(data) > FLASH_SIZE
           for address, data in segments):
        raise ConfigError("image data falls outside the 256 KiB MCU flash")
    return segments


def _load_pyocd():
    """Import pyOCD only when the user explicitly requests flashing."""
    try:
        from pyocd.core.helpers import ConnectHelper
        from pyocd.flash.loader import FlashLoader
    except ImportError as error:
        raise ConfigError(
            "pyOCD is required only for flashing. Install it with "
            "'python3 -m pip install pyocd', then install target support with "
            "'pyocd pack update' and "
            "'pyocd pack install EFR32MG1B232F256GM48'."
        ) from error
    return ConnectHelper, FlashLoader


def flash_image(path, probe_uid=None, pack=None, frequency=1000000,
                connect_mode="halt", progress=None):
    """Program a validated image through an ST-Link probe using pyOCD."""
    if frequency <= 0:
        raise ConfigError("SWD frequency must be positive")
    if pack is not None and not pathlib.Path(pack).is_file():
        raise ConfigError(f"CMSIS pack does not exist: {pack}")
    segments = prepare_flash_segments(path)
    ConnectHelper, FlashLoader = _load_pyocd()
    probe_filter = "stlink:" + (probe_uid or "")
    options = {
        "target_override": PYOCD_TARGET,
        "frequency": frequency,
        "connect_mode": connect_mode,
    }
    if pack is not None:
        options["pack"] = str(pack)
    try:
        probes = ConnectHelper.get_all_connected_probes(
            blocking=False, unique_id=probe_filter)
        if not probes:
            raise ConfigError("no matching ST-Link probe was found")
        if len(probes) > 1:
            identifiers = ", ".join(probe.unique_id for probe in probes)
            raise ConfigError(
                f"multiple ST-Link probes matched ({identifiers}); use --probe")
        selected_probe = "stlink:" + probes[0].unique_id
        session = ConnectHelper.session_with_chosen_probe(
            blocking=False, return_first=True,
            unique_id=selected_probe, options=options)
        if session is None:
            raise ConfigError("no matching ST-Link probe was found")
        with session:
            loader = FlashLoader(
                session, progress=progress, chip_erase="sector")
            for address, data in segments:
                loader.add_data(address, data)
            loader.commit()
    except ConfigError:
        raise
    except Exception as error:
        raise ConfigError(
            f"pyOCD flashing failed: {error}. Ensure the EFR32MG1B device "
            "pack is installed or supply its .pack file explicitly."
        ) from error


def run_gui(initial=None):
    """Open the standard-library Tk GUI for loading and saving an image."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("BMS firmware configurator")
    source = tk.StringVar(value=str(initial or ""))
    destination = tk.StringVar()
    probe_uid = tk.StringVar()
    pack_path = tk.StringVar()
    frequency = tk.StringVar(value="1000000")
    connect_mode = tk.StringVar(value="halt")
    status = tk.StringVar()
    variables = {}
    loaded = {"block": None}

    def browse_source():
        path = filedialog.askopenfilename(filetypes=[
            ("Firmware images", "*.s37 *.srec *.s19 *.bin"), ("All files", "*")])
        if path:
            source.set(path)
            destination.set(str(pathlib.Path(path).with_name(
                pathlib.Path(path).stem + "-configured" + pathlib.Path(path).suffix)))
            load()

    def load():
        try:
            image = load_image(source.get())
            _location, block = image.find_config()
            loaded["block"] = block
            for key, value, _minimum, _maximum in block.entries:
                shown = f"0x{value:08x}" if key in HEX_KEYS else str(value)
                if key == "serial_tx_location":
                    shown = TX_OPTIONS[value]
                elif key == "serial_rx_location":
                    shown = RX_OPTIONS[value]
                variables[key].set(shown)
        except (OSError, ConfigError) as error:
            messagebox.showerror("Cannot load image", str(error))

    def save(do_flash=False):
        if loaded["block"] is None:
            load()
        if loaded["block"] is None:
            return
        path = destination.get() or filedialog.asksaveasfilename()
        if not path:
            return
        assignments = []
        try:
            for key in variables:
                text = variables[key].get()
                if key == "serial_tx_location":
                    text = str(TX_OPTIONS.index(text))
                elif key == "serial_rx_location":
                    text = str(RX_OPTIONS.index(text))
                assignments.append(f"{key}={text}")
            patch_image(source.get(), path, assignments)
            destination.set(path)
            if not do_flash:
                messagebox.showinfo("Image saved", f"Wrote configured image:\n{path}")
                return
            if not messagebox.askyesno(
                    "Flash EFR32MG1B",
                    f"Program {path} through ST-Link?\n\n"
                    "This will erase and replace the application flash sectors."):
                return
            status.set("Flashing…")
            root.update_idletasks()

            def progress(value):
                status.set(f"Flashing… {int(value * 100)}%")
                root.update_idletasks()

            flash_image(path, probe_uid.get().strip() or None,
                        pack_path.get().strip() or None,
                        parse_value(frequency.get()), connect_mode.get(), progress)
            status.set("Flash complete")
            messagebox.showinfo("Flash complete", "Firmware programmed successfully.")
        except (OSError, ConfigError, ValueError) as error:
            status.set("")
            messagebox.showerror("Operation failed", str(error))

    frame = ttk.Frame(root, padding=12)
    frame.grid(sticky="nsew")
    ttk.Label(frame, text="Input image").grid(row=0, column=0, sticky="w")
    ttk.Entry(frame, textvariable=source, width=56).grid(row=0, column=1, sticky="ew")
    ttk.Button(frame, text="Browse…", command=browse_source).grid(row=0, column=2)
    ttk.Button(frame, text="Load", command=load).grid(row=1, column=2)
    ttk.Label(frame, text="Output image").grid(row=2, column=0, sticky="w")
    ttk.Entry(frame, textvariable=destination, width=56).grid(row=2, column=1, sticky="ew")
    for row, key in enumerate((
            "serial_tx_location", "serial_rx_location", "bms_address",
            "zigbee_primary_mask",
            "zigbee_secondary_mask", "sample_interval_s",
            "zigbee_long_poll_ms", "network_loss_timeout_h",
            "serial_timeout_ms"), 3):
        variables[key] = tk.StringVar()
        ttk.Label(frame, text=key.replace("_", " ").title()).grid(
            row=row, column=0, sticky="w")
        if key == "serial_tx_location":
            widget = ttk.Combobox(frame, textvariable=variables[key],
                                  values=TX_OPTIONS, state="readonly", width=42)
        elif key == "serial_rx_location":
            widget = ttk.Combobox(frame, textvariable=variables[key],
                                  values=RX_OPTIONS, state="readonly", width=42)
        else:
            widget = ttk.Entry(frame, textvariable=variables[key], width=45)
        widget.grid(row=row, column=1, sticky="ew")
    ttk.Separator(frame).grid(row=12, column=0, columnspan=3,
                              pady=8, sticky="ew")
    ttk.Label(frame, text="ST-Link probe ID (optional)").grid(
        row=13, column=0, sticky="w")
    ttk.Entry(frame, textvariable=probe_uid, width=45).grid(
        row=13, column=1, sticky="ew")
    ttk.Label(frame, text="CMSIS .pack path (optional)").grid(
        row=14, column=0, sticky="w")
    ttk.Entry(frame, textvariable=pack_path, width=45).grid(
        row=14, column=1, sticky="ew")
    ttk.Label(frame, text="SWD frequency (Hz)").grid(
        row=15, column=0, sticky="w")
    ttk.Entry(frame, textvariable=frequency, width=45).grid(
        row=15, column=1, sticky="ew")
    ttk.Label(frame, text="Connect mode").grid(row=16, column=0, sticky="w")
    ttk.Combobox(frame, textvariable=connect_mode,
                 values=("halt", "under-reset"), state="readonly", width=42).grid(
        row=16, column=1, sticky="ew")
    buttons = ttk.Frame(frame)
    buttons.grid(row=17, column=1, pady=(12, 0), sticky="e")
    ttk.Button(buttons, text="Save", command=save).grid(row=0, column=0)
    ttk.Button(buttons, text="Save and flash",
               command=lambda: save(True)).grid(row=0, column=1, padx=(8, 0))
    ttk.Label(frame, textvariable=status).grid(row=18, column=1, sticky="e")
    frame.columnconfigure(1, weight=1)
    if source.get():
        destination.set(str(pathlib.Path(source.get()).with_name(
            pathlib.Path(source.get()).stem + "-configured"
            + pathlib.Path(source.get()).suffix)))
        root.after(0, load)
    root.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", nargs="?", help="input .s37/.srec/.s19 or .bin")
    parser.add_argument("-o", "--output", help="write patched image here")
    parser.add_argument("--in-place", action="store_true", help="overwrite input image")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--show", action="store_true", help="print current settings")
    parser.add_argument("--gui", action="store_true", help="open graphical configurator")
    parser.add_argument("--flash", action="store_true",
                        help="flash the selected image through ST-Link using pyOCD")
    parser.add_argument("--probe", help="optional ST-Link unique ID substring")
    parser.add_argument("--pack", help="optional EFR32MG1B CMSIS .pack path")
    parser.add_argument("--frequency", type=int, default=1000000,
                        help="SWD frequency in Hz (default: 1000000)")
    parser.add_argument("--connect-mode", choices=("halt", "under-reset"),
                        default="halt", help="pyOCD connection mode")
    args = parser.parse_args(argv)
    if args.gui or not args.image:
        run_gui(args.image)
        return 0
    try:
        image = load_image(args.image)
        location, block = image.find_config()
        flash_path = args.image
        if args.show or not args.set:
            print(display(block))
        if args.set:
            destination = args.image if args.in_place else args.output
            if not destination:
                parser.error("--set requires --output or --in-place")
            block = patch_image(args.image, destination, args.set)
            flash_path = destination
            print(f"wrote {destination} with valid CRC-32")
            if args.show:
                print(display(block))
        if args.flash:
            flash_image(flash_path, args.probe, args.pack, args.frequency,
                        args.connect_mode)
            print(f"flashed {flash_path} through ST-Link")
        return 0
    except (OSError, ConfigError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    sys.exit(main())
